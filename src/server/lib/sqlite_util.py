# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120
"""
This file provide tools to manipulate database with more ease
"""

# Python core libs
import sqlite3
import datetime
import traceback
import collections

# Project specific libs
import util
import type_util


IntegrityError = sqlite3.IntegrityError

# FIXME LATER: remove this if transactions are ok:
import logging
log = logging.getLogger("aziugo")


def get_now(conn):
    return conn.execute("SELECT (CAST(strftime('%s', 'now', 'utc') AS int))").fetchval()


class Transaction(object):
    """
    Class to manage nestable transactions
    It should be used with the 'with' keyword.
    Usage:

      with Transaction(conn) as tr:  # Start the transaction
        conn.execute("coucou")       # Do whatever you want with any cursor
        tr.cancel()                  # You can force rollback
      # If everything is fine, auto-commit happened at the end of the 'with'
      # If an exception happen, it will be rollbacked automatically

    Warning:
        Running sql commands inside a canceled transaction could lead to database integrity issues.
        You should stop the with block of the transaction as soon as you cancel it
    """
    # FIXME LATER: find a better implementation to get ride of the previous warning, even with user messing up with
    # nested transactions (like canceling parent in child but still doing requests in child)

    _conn_stack_active = {}

    def __init__(self, conn):
        """
        :param conn:        An already opened sqlite3 connection
        :type conn:         sqlite3.Connection|sqlite3.Cursor
        """
        try:
            self._conn = conn.connection
        except AttributeError:
            self._conn = conn
        self._level = -1
        self._previous_isolation_level = None
        self._start_time = datetime.datetime.utcnow()

    def cancel(self):
        """
        Cancel current transaction

        Warning:
            Running sql commands inside a canceled transaction could lead to database integrity issues.
            You should stop the with block of the transaction as soon as you cancel it
        """
        if self.is_canceled():
            return
        self._rollback()

    def is_canceled(self):
        """ Does the current transaction is canceled ?
        :rtype:     bool
        """
        if self._level < 0:
            return True
        conn_id = id(self._conn)
        if conn_id not in Transaction._conn_stack_active.keys():
            return True
        if len(Transaction._conn_stack_active[conn_id]) <= self._level:
            return True
        if not Transaction._conn_stack_active[conn_id][self._level]:
            return True
        return False

    @property
    def level(self):
        """ Get the level of transaction of this
        :rtype:     The level of nested transaction
        """
        return self._level

    def _begin(self):
        conn_id = id(self._conn)
        if conn_id not in Transaction._conn_stack_active.keys():
            Transaction._conn_stack_active[conn_id] = []
        self._level = len(Transaction._conn_stack_active[conn_id])
        if self._level == 0:
            self._previous_isolation_level = self._conn.isolation_level
            self._conn.isolation_level = None
            self._conn.execute("BEGIN")
        else:
            self._conn.execute("SAVEPOINT trans_level_" + str(self._level))
        Transaction._conn_stack_active[conn_id].append(True)

    def _rollback(self):
        conn_id = id(self._conn)
        if conn_id not in Transaction._conn_stack_active.keys():
            raise RuntimeError("Should not happen: transaction stack corrupted")
        for i in range(self._level, len(Transaction._conn_stack_active[conn_id])):
            Transaction._conn_stack_active[conn_id][i] = False
        if self._level == 0:
            self._conn.execute("ROLLBACK")
        else:
            self._conn.execute("ROLLBACK TO SAVEPOINT trans_level_" + str(self._level))

    def _commit(self):
        if self._level == 0:
            self._conn.execute("COMMIT")
        else:
            self._conn.execute("RELEASE SAVEPOINT trans_level_" + str(self._level))

    def _finally(self):
        elapsed = datetime.datetime.utcnow() - self._start_time
        if elapsed > datetime.timedelta(seconds=1):
            log.warning("Database transaction took more than a second. Stacktrace:" +
                        "\n".join([str(l) for l in reversed(traceback.format_stack())]))
        conn_id = id(self._conn)
        if self._level == 0:
            self._conn.isolation_level = self._previous_isolation_level
            self._conn.commit()
            del Transaction._conn_stack_active[conn_id]
        else:
            Transaction._conn_stack_active[conn_id] = Transaction._conn_stack_active[conn_id][0:self._level]

    def __enter__(self):
        self._begin()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        try:
            if not self.is_canceled():
                if exception_type:
                    self._rollback()
                else:
                    self._commit()
        finally:
            self._finally()
        self._conn = None


def delete_with_date(conn, table, element_id, id_field="id"):
    """
    Mark a row as deleted when it use delete_date and delete_random fields

    :param conn:            The database connection
    :type conn:             sqlite3.Connection|sqlite3.Cursor
    :param table:           The table to change
    :type table:            str
    :param element_id:      The id of the row
    :type element_id:       int
    :param id_field:        The id field name. Optional, default 'id'
    :type id_field:         str
    """
    conn.execute("""UPDATE `""" + table + """`
                       SET delete_date = CAST(strftime('%s', 'now', 'utc') AS INTEGER),
                           delete_random = RANDOM()
                      WHERE `""" + id_field + """` = ? """, [element_id])


def hist_insert(conn, table, values, now=None):
    """
    Insert or update a line in database which use the history pattern

    :param conn:                The database connection
    :type conn:                 sqlite3.Connection|sqlite3.Cursor
    :param table:               The table to change
    :type table:                str
    :param values:              The new value to apply
    :type values:               dict[str, any]
    :param now:                 The time of change. Optional, default None
    :type now:                  int|None
    :return:                    A list of filtered row after modification
    :rtype:                     sqlite3.Row
    """

    with Transaction(conn) as t:
        # Ensure we have a cursor
        try:
            conn = conn.cursor()
        except AttributeError:
            pass

        if now is None:
            now = get_now(conn)

        fields = values.keys()

        hist_rowid = conn.execute(""" INSERT INTO `""" + table + """_history`
                                           ( """ + ', '.join(fields) + """, start_time, end_time)
                                     VALUES (""" + ', '.join(['?'] * len(fields)) + """, ?, NULL)""",
                                  [values[f] for f in fields] + [now]).lastrowid
        conn.execute(""" SELECT * FROM `""" + table + """_history` LIMIT 0""").fetchone()
        all_fields = [d[0] for d in conn.description if d[0] not in ('start_time', 'end_time')]
        new_rowid = conn.execute(""" INSERT INTO `""" + table + """`
                                         SELECT """ + ', '.join(all_fields) + """
                                           FROM `""" + table + """_history`
                                          WHERE rowid = ? """, [hist_rowid]).lastrowid
        return conn.execute("SELECT * FROM `" + table + "` WHERE rowid = ?", [new_rowid]).fetchone()


def hist_update(conn, table, values, where, now=None):
    """
    Update several lines in database which use the history pattern

    :param conn:                The database connection
    :type conn:                 sqlite3.Connection|sqlite3.Cursor
    :param table:               The table to change
    :type table:                str
    :param values:              The new value to apply
    :type values:               dict[str, any]
    :param where:               The "WHERE" keys and values to select elements to update
    :type where:                list[tuple[str, str, any]|str]
    :param now:                 The time of change. Optional, default None
    :type now:                  int|None
    :return:                    A list of filtered row after modification
    :rtype:                     list[sqlite3.Row]
    """

    with Transaction(conn) as t:
        # Ensure we have a cursor
        try:
            conn = conn.cursor()
        except AttributeError:
            pass

        if now is None:
            now = get_now(conn)

        query = "SELECT * FROM `" + table + "_history` WHERE end_time IS NULL "
        query_conditions, query_args = parse_conditions(where)
        if query_conditions:
            query += " AND "+" AND ".join(query_conditions)
        current_lines = conn.execute(query, query_args).fetchall()
        fields = [d[0] for d in conn.description if d[0] not in ('row_id', 'id', 'start_time', 'end_time')]

        results = []

        if not current_lines:
            return results
        for line in current_lines:
            if not line:
                continue

            # Collect old values to keep them, and try to detect no change
            final_values = values.copy()
            changes_detected = False

            for field in fields:
                current_value = line[field]
                if field not in values.keys():
                    final_values[field] = line[field]
                    continue
                if isinstance(current_value, float):
                    if util.float_equals(current_value, values[field]):
                        changes_detected = True
                elif current_value != values[field]:
                    changes_detected = True

            # Do the job if change is detected
            if not changes_detected:
                results.append(line)
            else:
                conn.execute("UPDATE `" + table + "_history` SET end_time = ? WHERE id = ?",
                             [now, line['id']])
                query = """INSERT INTO `""" + table + """_history`
                                             ( """ + ', '.join(fields) + """, start_time, end_time)
                                     VALUES (""" + ', '.join(['?'] * len(fields)) + """, ?, NULL)"""
                new_hist_rowid = conn.execute(query, [final_values[f] for f in fields] + [now]).lastrowid
                new_line = conn.execute("SELECT * FROM `" + table + "_history` WHERE rowid = ?",
                                        [new_hist_rowid]).fetchone()
                results.append(new_line)
                conn.execute("DELETE FROM `" + table + "` WHERE id = ?", [line['id']])
                conn.execute(""" INSERT INTO `""" + table + """` (id, """ + ", ".join(fields) + """)
                                      SELECT id, """ + ", ".join(fields) + """
                                        FROM  `""" + table + """_history`
                                        WHERE `""" + table + """_history`.id = ? """, [new_line['id']])
        return results


def hist_upsert(conn, table, values, where, default_values=None, now=None):
    """
    Insert or update a line in database which use the history pattern

    :param conn:                The database connection
    :type conn:                 sqlite3.Connection|sqlite3.Cursor
    :param table:               The table to change
    :type table:                str
    :param values:              The new value to apply
    :type values:               dict[str, any]
    :param where:               The "WHERE" values to select one to insert or update
    :type where:                list[tuple[str, str, any]|str]
    :param default_values:      Default values, overridden by existing values. Optional, default None
    :type default_values:       dict[str, any]|None
    :param now:                 The time of change. Optional, default None
    :type now:                  int|None
    :return:                    A list of filtered row after modification
    :rtype:                     sqlite3.Row
    """

    with Transaction(conn) as t:
        # Ensure we have a cursor
        try:
            conn = conn.cursor()
        except AttributeError:
            pass

        if now is None:
            now = get_now(conn)
        if default_values is None:
            default_values = {}

        query = "SELECT rowid, * FROM `" + table + "_history` WHERE end_time IS NULL "
        query_conditions, query_args = parse_conditions(where)
        if query_conditions:
            query += " AND "+" AND ".join(query_conditions)
        query += " LIMIT 2"

        current_lines = conn.execute(query, query_args).fetchall()
        if len(current_lines) > 1:
            raise RuntimeError("Too many lines corresponding to the provided where clauses")
        fields = [d[0] for d in conn.description if d[0] not in ('row_id', 'id', 'start_time', 'end_time')]

        if len(current_lines) == 0:  # Not found so we insert new value
            known_values = default_values.copy()
            for w_clause in where:
                if len(w_clause) == 3 and w_clause[1] in ("==", "="):
                    known_values[w_clause[0]] = w_clause[2]
                elif len(w_clause) == 2:
                    if type_util.is_string(w_clause[1]) and w_clause[1].lower().strip() == "is null":
                        known_values[w_clause[0]] = None
            known_values.update(values)
            known_fields = known_values.keys()
            new_rowid = conn.execute(""" INSERT INTO `""" + table + """_history`
                                               ( """ + ', '.join(known_fields) + """, start_time, end_time)
                                         VALUES (""" + ', '.join(['?'] * len(known_fields)) + """, ?, NULL)""",
                                     [known_values[f] for f in known_fields] + [now]).lastrowid
            result_rowid = conn.execute(""" INSERT OR REPLACE INTO `"""+table+"""` (id,  """+', '.join(fields)+""")
                                                    SELECT id, """ + ', '.join(fields) + """
                                                      FROM `""" + table + """_history`
                                                     WHERE rowid = ? """, [new_rowid]).lastrowid
        else:  # Found old one, collect old values to keep them, and try to detect no change
            line = current_lines[0]
            final_values = values.copy()
            changes_detected = False

            for field in fields:
                current_value = line[field]
                if field not in values.keys():
                    final_values[field] = current_value
                    continue
                if isinstance(current_value, float):
                    if util.float_equals(current_value, values[field]):
                        changes_detected = True
                elif current_value != values[field]:
                    changes_detected = True

            # Do the job if change is detected
            if not changes_detected:
                return line
            else:
                conn.execute("UPDATE `" + table + "_history` SET end_time = ? WHERE id = ?", [now, line['id']])
                query = """INSERT INTO `""" + table + """_history`
                                     ( """ + ', '.join(fields) + """, start_time, end_time)
                             VALUES (""" + ', '.join(['?'] * len(fields)) + """, ?, NULL)"""
                line_rowid = conn.execute(query, [final_values[f] for f in fields] + [now]).lastrowid
                conn.execute(""" DELETE FROM `""" + table + """` WHERE id = ?""", [line['id']])
                result_rowid = conn.execute(""" INSERT INTO `""" + table + """` (id, """ + ", ".join(fields) + """)
                                                  SELECT id, """ + ", ".join(fields) + """
                                                    FROM  `""" + table + """_history`
                                                    WHERE rowid = ?""", [line_rowid]).lastrowid
        return conn.execute("SELECT * FROM `" + table + "` WHERE rowid = ?", [result_rowid]).fetchone()


def hist_remove(conn, table, where, now=None):
    if now is None:
        now = get_now(conn)
    with Transaction(conn) as t:
        query = """UPDATE `"""+table+"""_history`
                      SET end_time = ?
                    WHERE end_time IS NULL """
        query_conditions, query_args = parse_conditions(where)
        if query_conditions:
            query += " AND "+" AND ".join(query_conditions)
        conn.execute(query, [now] + query_args)
        query = "DELETE FROM `"+table+"` "
        if query_conditions:
            query += " WHERE " + " AND ".join(query_conditions)
        conn.execute(query, query_args)


def to_dict(obj):
    """
    Transform a sqlite3 request result into a dict or a list of dict

    :param obj:     The sqlite request result
    :type obj:      sqlite3.Row|list[sqlite3.Row]|None
    :return:        A readable representation of the results
    :rtype:         dict[str, any]|list[dict[str, any]]|None
    """
    if not obj:
        return None
    try:
        return [dict(zip(r.keys(), r)) for r in obj]
    except StandardError:
        return dict(zip(obj.keys(), obj))


def parse_conditions(where):
    query_str = []
    query_args = []
    for cond in where:
        if type_util.is_string(cond):
            query_str.append(str(cond))
        elif len(cond) == 2:
            query_str.append("`" + str(cond[0]) + "` " + str(cond[1]))
        elif len(cond) == 3:
            if isinstance(cond[2], collections.Iterable) and not type_util.is_string(cond[2]):
                query_str.append("`" + str(cond[0]) + "` " + str(cond[1]) + " (" + ", ".join(["?"] * len(cond[2])) + ")")
                query_args.extend(cond[2])
            else:
                query_str.append("`" + str(cond[0]) + "` " + str(cond[1]) + " ? ")
                query_args.append(cond[2])
        else:
            raise RuntimeError("Unable to understand sql condition "+repr(cond))
    return query_str, query_args
