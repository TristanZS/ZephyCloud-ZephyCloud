# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120
"""
This file provide tools to manipulate database with more ease
"""

# Python core libs
import datetime
import collections
import json
import uuid
import decimal
import logging

# Third party lib
import psycopg2
import psycopg2.extras
import psycopg2.extensions

# Project specific libs
import error_util
import type_util
import date_util
import util


IntegrityError = psycopg2.IntegrityError
DEBUG_WRAPPER = False

log = logging.getLogger("aziugo")


class ConnectionWrapper(object):
    IN_TRANS = (psycopg2.extensions.TRANSACTION_STATUS_ACTIVE, psycopg2.extensions.TRANSACTION_STATUS_INTRANS)

    def __init__(self, *args, **kwargs):
        super(ConnectionWrapper, self).__init__()
        self._conn = None
        self._cursor = None
        self._conn_param_args = args
        self._conn_param_kwargs = kwargs
        self._trans_stack = []
        self.IntegrityError = psycopg2.IntegrityError

    def close(self):
        if self._cursor:
            if DEBUG_WRAPPER:
                print "conn " + str(id(self)) + ": closing default cursor"
            self._cursor.close()
            self._cursor = None
        if self._conn:
            if not self._conn.autocommit and self._conn.get_transaction_status() in ConnectionWrapper.IN_TRANS:
                if DEBUG_WRAPPER:
                    print "conn "+str(id(self))+": commit because of close"
                self._conn.commit()
            if DEBUG_WRAPPER:
                print "conn " + str(id(self)) + ": closing connection"
            self._conn.close()
            self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            if DEBUG_WRAPPER:
                print "conn " + str(id(self)) + ": create conn"
            if "cursor_factory" not in self._conn_param_kwargs.keys():
                self._conn_param_kwargs["cursor_factory"] = psycopg2.extras.DictCursor
            self._conn = psycopg2.connect(*self._conn_param_args, **self._conn_param_kwargs)
            self._conn.set_client_encoding("utf8")
        return self._conn

    @property
    def default_cursor(self):
        if self._cursor is None:
            self._cursor = self.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return self._cursor

    def _on_error(self):
        if not any(self._trans_stack):
            self.close()

    def cursor(self, *args, **kwargs):
        return CursorWrapper(self, *args, **kwargs)

    def execute(self, query, vars=None):
        try:
            self.default_cursor.execute(query, vars)
            return self.default_cursor
        except error_util.all_errors:
            with error_util.before_raising():
                if DEBUG_WRAPPER:
                    print "conn " + str(id(self)) + ": error detected"
                self._on_error()

    def executemany(self, query, vars_list):
        try:
            self.default_cursor.executemany(query, vars_list)
            return self.default_cursor
        except error_util.all_errors:
            with error_util.before_raising():
                if DEBUG_WRAPPER:
                    print "conn " + str(id(self)) + ": error detected"
                self._on_error()

    def fetchall(self):
        result = self.default_cursor.fetchall()
        if result is None:
            return []
        return result

    def fetchone(self):
        return self.default_cursor.fetchone()

    def fetchval(self):
        return self.default_cursor.fetchone()[0]

    def commit(self):
        if self._conn is None:
            return
        if DEBUG_WRAPPER:
            print "conn " + str(id(self)) + ": commit"
        self.conn.commit()

    @property
    def autocommit(self):
        return self.conn.autocommit

    @autocommit.setter
    def autocommit(self, value):
        if DEBUG_WRAPPER:
            print "conn " + str(id(self)) + ": autocommit set to "+repr(value)
        self.conn.autocommit = value

    @property
    def status(self):
        return self.conn.status

    def get_transaction_status(self):
        return self.conn.get_transaction_status()

    def __del__(self):
        try:
            self.close()
        except StandardError:
            pass


class OpenConnectionWrapper(ConnectionWrapper):
    def __init__(self, connection, skip_close=False):
        super(OpenConnectionWrapper, self).__init__()
        if DEBUG_WRAPPER:
            print "conn " + str(id(self)) + ": created with fixed connection"
        self._conn = connection
        self._skip_close = skip_close

    def close(self):
        if self._skip_close:
            return
        if self._cursor:
            if DEBUG_WRAPPER:
                print "conn " + str(id(self)) + ": closing default cursor"
            self._cursor.close()
            self._cursor = None
        if self._conn:
            if not self._conn.autocommit and self._conn.get_transaction_status() in ConnectionWrapper.IN_TRANS:
                if DEBUG_WRAPPER:
                    print "conn " + str(id(self)) + ": commit because of close"
                self._conn.commit()
            if DEBUG_WRAPPER:
                print "conn " + str(id(self)) + ": closing connection"
            self._conn.close()
            self._conn = None

    @property
    def conn(self):
        return self._conn

    def _on_error(self):
        pass


class CursorWrapper(object):
    def __init__(self, conn, *args, **kwargs):
        super(CursorWrapper, self).__init__()
        self._conn = conn
        self._raw_cursor = None
        self._cursor_args = args
        self._cursor_kwargs = kwargs

    def execute(self, query, vars=None):
        try:
            if DEBUG_WRAPPER:
                print "conn " + str(id(self._conn)) + " cursor: executing "+repr(query) + ", with args "+repr(vars)
            self._cursor.execute(query, encode_vars(vars))
            return self
        except error_util.all_errors:
            with error_util.before_raising():
                self._raw_cursor = None
                self._conn._on_error()

    def executemany(self, query, vars_list):
        try:
            if DEBUG_WRAPPER:
                print "conn " + str(id(self._conn)) + " cursor: executing "+repr(query) + ", with args "+repr(vars_list)
            self._cursor.executemany(query, [encode_vars(vars) for vars in vars_list])
            return self
        except error_util.all_errors:
            with error_util.before_raising():
                self._raw_cursor = None
                self._conn._on_error()

    @property
    def _cursor(self):
        if self._raw_cursor and id(self._raw_cursor.connection) != id(self._conn.conn):
            self._raw_cursor = None
        if not self._raw_cursor:
            if DEBUG_WRAPPER:
                print "conn " + str(id(self._conn)) + " cursor: creating internal cursor"
            self._raw_cursor = self._conn.conn.cursor(*self._cursor_args, **self._cursor_kwargs)
        return self._raw_cursor

    def fetchall(self):
        result = self._raw_cursor.fetchall()
        if result is None:
            return []
        return result

    def fetchval(self):
        return self._raw_cursor.fetchone()[0]

    def close(self):
        if not self._raw_cursor:
            return
        if DEBUG_WRAPPER:
            print "conn " + str(id(self._conn)) + " cursor: closing internal cursor"
        self._raw_cursor.close()
        self._raw_cursor = None

    def __getattr__(self, item):
        return getattr(self._cursor, item)

    def __enter__(self):
        self._cursor.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._cursor.__exit__(exc_type, exc_val, exc_tb)

    def __iter__(self):
        return self._cursor.__iter__()


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

    def __init__(self, conn):
        """
        :param conn:        An already opened ConnectionWrapper
        :type conn:         ConnectionWrapper
        """
        if not isinstance(conn, ConnectionWrapper):
            raise RuntimeError("You pass a ConnectionWrapper to this constructor")
        self._conn = conn
        self._level = -1
        self._previous_autocommit = None
        self._now = datetime.datetime.utcnow()

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
        if len(self._trans_stack) <= self._level:
            return True
        if not self._trans_stack[self._level]:
            return True
        return False

    @property
    def level(self):
        """ Get the level of transaction of this
        :rtype:     The level of nested transaction
        """
        return self._level

    @property
    def _trans_stack(self):
        # I known i's a little ugly
        return self._conn._trans_stack

    def _begin(self):
        self._now = datetime.datetime.utcnow()
        self._level = len(self._trans_stack)
        if self._level == 0:
            self._previous_autocommit = self._conn.autocommit
            self._conn.commit()
            self._conn.autocommit = True
            self._conn.execute("BEGIN")
        else:
            self._conn.execute("SAVEPOINT trans_level_" + str(self._level))
        self._trans_stack.append(True)

    def _rollback(self):
        if datetime.datetime.utcnow() - self._now > datetime.timedelta(milliseconds=500):
            elapsed = datetime.datetime.utcnow() - self._now
            elapsed_str = str(elapsed.seconds + float(elapsed.microseconds/1000)/1000)
            log.warning("Transaction took "+elapsed_str+"s here:\n"+util.get_stack_str())
        for i in range(self._level, len(self._trans_stack)):
            self._trans_stack[i] = False
        trans_status = self._conn.get_transaction_status()
        if trans_status not in (psycopg2.extensions.TRANSACTION_STATUS_IDLE,):
            if self._level == 0:
                self._conn.execute("ROLLBACK")
            else:
                self._conn.execute("ROLLBACK TO SAVEPOINT trans_level_" + str(self._level))

    def _commit(self):
        if datetime.datetime.utcnow() - self._now > datetime.timedelta(milliseconds=500):
            elapsed = datetime.datetime.utcnow() - self._now
            elapsed_str = str(elapsed.seconds + float(elapsed.microseconds/1000)/1000)
            log.warning("Transaction took "+elapsed_str+"s here:\n"+util.get_stack_str())
        trans_status = self._conn.get_transaction_status()
        if trans_status not in (psycopg2.extensions.TRANSACTION_STATUS_IDLE,):
            if self._level == 0:
                self._conn.execute("COMMIT")
            else:
                self._conn.execute("RELEASE SAVEPOINT trans_level_" + str(self._level))

    def _finally(self):
        if self._level == 0:
            self._conn.autocommit = self._previous_autocommit
        for i in range(self._level, len(self._trans_stack)):
            self._trans_stack.pop(i)

    def __enter__(self):
        self._begin()
        return self

    def __exit__(self, exception_type, exception_value, stacktrace):
        try:
            if not self.is_canceled():
                trans_status = self._conn.get_transaction_status()

                if exception_type or trans_status == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
                    self._rollback()
                else:
                    self._commit()
        finally:
            self._finally()
        self._conn = None
        return False


def get_now(conn, without_tz=True):
    with conn.cursor() as cur:
        cur.execute("SELECT now()")
        result = cur.fetchone()[0]
        if without_tz:
            result = result.replace(tzinfo=None)
        return result


def delete_with_date(conn, table, element_id, id_field="id"):
    """
    Mark a row as deleted when it use delete_date and delete_random fields

    :param conn:            The database connection
    :type conn:             ConnectionWrapper
    :param table:           The table to change
    :type table:            str
    :param element_id:      The id of the row
    :type element_id:       int
    :param id_field:        The id field name. Optional, default 'id'
    :type id_field:         str
    """
    with conn.cursor() as cur:
        cur.execute("""UPDATE """ + table + """
                          SET delete_date = now()
                        WHERE """ + id_field + """ = %s """, [element_id])


def hist_insert(conn, table, values, now=None, id_field="id"):
    """
    Insert or update a line in database which use the history pattern

    :param conn:                The database connection
    :type conn:                 ConnectionWrapper
    :param table:               The table to change
    :type table:                str
    :param values:              The new value to apply
    :type values:               dict[str, any]
    :param now:                 The time of change. Optional, default None
    :type now:                  int|None|datetime
    :param id_field:            The name of the primary key field for given table. Optional, default "id"
    :type id_field:             str
    :return:                    A list of filtered row after modification
    :rtype:                     Row
    """

    with Transaction(conn):
        if now is None:
            now = get_now(conn)

        fields = values.keys()
        conn.execute(""" INSERT INTO """ + table + """_history
                               ( """ + ', '.join(fields) + """, start_time, end_time)
                         VALUES (""" + ', '.join(['%s'] * len(fields)) + """, %s, NULL)
                         RETURNING """+id_field, [values[f] for f in fields] + [now])
        line_id = conn.fetchval()
        cursor = conn.execute(""" SELECT * FROM """ + table + """_history LIMIT 0""")
        all_fields = [d[0] for d in cursor.description if d[0] not in ('start_time', 'end_time')]
        conn.execute(""" INSERT INTO """ + table + """
                         SELECT """ + ', '.join(all_fields) + """
                           FROM """ + table + """_history
                          WHERE """+id_field+""" = %s""", [line_id])
        return conn.execute("SELECT * FROM " + table + " WHERE "+id_field+" = %s", [line_id]).fetchone()


def hist_update(conn, table, values, where, now=None, id_field="id"):
    """
    Update several lines in database which use the history pattern

    :param conn:                The database connection
    :type conn:                 ConnectionWrapper
    :param table:               The table to change
    :type table:                str
    :param values:              The new value to apply
    :type values:               dict[str, any]
    :param where:               The "WHERE" keys and values to select elements to update
    :type where:                list[tuple[str, str, any]|str]
    :param now:                 The time of change. Optional, default None
    :type now:                  int|None|datetime
    :param id_field:            The name of the primary key field for given table. Optional, default "id"
    :type id_field:             str
    :return:                    A list of filtered row after modification
    :rtype:                     list[Row]
    """

    with Transaction(conn):
        if now is None:
            now = get_now(conn)

        query = "SELECT * FROM " + table + "_history WHERE end_time IS NULL "
        query_conditions, query_args = parse_conditions(where)
        if query_conditions:
            query += " AND "+" AND ".join(query_conditions)
        cursor = conn.execute(query, query_args)
        current_lines = cursor.fetchall()
        fields = [d[0] for d in cursor.description if d[0] not in (id_field, 'start_time', 'end_time')]

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
            fields_with_id = fields[:]
            fields_with_id.insert(0, id_field)

            # Do the job if change is detected
            if not changes_detected:
                results.append(line)
            else:
                conn.execute("UPDATE " + table + "_history SET end_time = %s WHERE """+id_field+""" = %s""",
                             [now, line[id_field]])
                query = """INSERT INTO """ + table + """_history
                                       ( """ + ', '.join(fields) + """, start_time, end_time)
                                VALUES (""" + ', '.join(['%s'] * len(fields)) + """, %s, NULL)
                             RETURNING """+id_field
                conn.execute(query, [final_values[f] for f in fields] + [now])
                new_hist_id = conn.fetchval()
                new_line = conn.execute("SELECT * FROM " + table + "_history WHERE """+id_field+""" = %s""",
                                        [new_hist_id]).fetchone()
                results.append(new_line)
                conn.execute("DELETE FROM " + table + " WHERE """+id_field+" = %s", [line[id_field]])
                conn.execute(""" INSERT INTO """ + table + """ (""" + ", ".join(fields_with_id) + """)
                                      SELECT """ + ", ".join(fields_with_id) + """
                                        FROM  """ + table + """_history
                                        WHERE """ + table + """_history."""+id_field+" = %s """, [new_line[id_field]])
        return results


def hist_upsert(conn, table, values, where, default_values=None, now=None, id_field="id"):
    """
    Insert or update a line in database which use the history pattern

    :param conn:                The database connection
    :type conn:                 ConnectionWrapper
    :param table:               The table to change
    :type table:                str
    :param values:              The new value to apply
    :type values:               dict[str, any]
    :param where:               The "WHERE" values to select one to insert or update
    :type where:                list[tuple[str, str, any]|str]
    :param default_values:      Default values, overridden by existing values. Optional, default None
    :type default_values:       dict[str, any]|None
    :param now:                 The time of change. Optional, default None
    :type now:                  int|None|datetime
    :param id_field:            The name of the primary key field for given table. Optional, default "id"
    :type id_field:             str
    :return:                    A list of filtered row after modification
    :rtype:                     Row
    """

    with Transaction(conn):
        if now is None:
            now = get_now(conn)
        if default_values is None:
            default_values = {}

        query = "SELECT * FROM " + table + "_history WHERE end_time IS NULL "
        query_conditions, query_args = parse_conditions(where)
        if query_conditions:
            query += " AND "+" AND ".join(query_conditions)
        query += " LIMIT 2"

        cursor = conn.execute(query, query_args)
        current_lines = cursor.fetchall()
        if len(current_lines) > 1:
            raise RuntimeError("Too many lines corresponding to the provided where clauses")
        fields = [d[0] for d in cursor.description if d[0] not in (id_field, 'start_time', 'end_time')]
        fields_with_id = fields[:]
        fields_with_id.insert(0, id_field)

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
            conn.execute(""" INSERT INTO """ + table + """_history
                                         ( """ + ', '.join(known_fields) + """, start_time, end_time)
                                  VALUES (""" + ', '.join(['%s'] * len(known_fields)) + """, %s, NULL)
                               RETURNING """+id_field, [known_values[f] for f in known_fields] + [now])
            result_id = conn.fetchval()
            conn.execute("DELETE FROM " + table + " WHERE " + id_field + " = %s", [result_id])
            query = """ INSERT INTO """ + table + """ ("""+', '.join(fields_with_id)+""")
                                  SELECT """ + ', '.join(fields_with_id) + """
                                    FROM """ + table + """_history
                                   WHERE """ + id_field + """ = %s"""
            conn.execute(query, [result_id])
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
                conn.execute("UPDATE " + table + "_history SET end_time = %s WHERE id = %s", [now, line[id_field]])
                query = """INSERT INTO """ + table + """_history
                                     ( """ + ', '.join(fields) + """, start_time, end_time)
                             VALUES (""" + ', '.join(['%s'] * len(fields)) + """, %s, NULL)
                          RETURNING """+id_field
                conn.execute(query, [final_values[f] for f in fields] + [now])
                result_id = conn.fetchval()
                conn.execute(""" DELETE FROM """ + table + """ WHERE """+id_field+""" = %s""", [line[id_field]])
                conn.execute(""" INSERT INTO """ + table + """ (""" + ", ".join(fields_with_id) + """)
                                      SELECT """ + ", ".join(fields_with_id) + """
                                        FROM """ + table + """_history
                                       WHERE """ + id_field+ " = %s", [result_id])
        return conn.execute("SELECT * FROM " + table + " WHERE "+id_field+" = %s", [result_id]).fetchone()


def hist_remove(conn, table, where, now=None):
    if now is None:
        now = get_now(conn)
    with Transaction(conn):
        query = """UPDATE """+table+"""_history
                      SET end_time = %s
                    WHERE end_time IS NULL """
        query_conditions, query_args = parse_conditions(where)
        if query_conditions:
            query += " AND "+" AND ".join(query_conditions)
        conn.execute(query, [now] + query_args)
        query = "DELETE FROM "+table+" "
        if query_conditions:
            query += " WHERE " + " AND ".join(query_conditions)
        conn.execute(query, query_args)


class PgList(list):
    @staticmethod
    def from_result(db_result, count_key=None):
        result = PgList(all_to_dict(db_result, False, count_key))
        if len(result) == 0:
            return result
        if count_key:
            result.set_full_count(db_result[0][count_key])
        return result

    def __init__(self, *args, **kargs):
        super(PgList, self).__init__(*args, **kargs)
        self._full_count = None

    def set_full_count(self, full_count):
        self._full_count = int(full_count)

    @property
    def full_count(self):
        if self._full_count is None:
            return len(self)
        else:
            return self._full_count


def all_to_dict(obj, datetime_to_int=False, keys_to_ignore=None):
    """
    Transform a psycopg2 request result into a dict or a list of dict

    :param obj:                 The psycopg2 request result
    :type obj:                  list[Row]|None
    :param datetime_to_int:     Do you want to transform datetime object into int ? Optional, default False
    :type datetime_to_int:      bool
    :param keys_to_ignore:      Keys to not load. Optional, default None
    :type keys_to_ignore:       None|list[str]
    :return:                    A readable representation of the results
    :rtype:                     list[dict[str, any]]
    """
    if obj is None:
        return []
    return [row_to_dict(line, datetime_to_int, keys_to_ignore) for line in obj]


def row_to_dict(row, datetime_to_int=False, keys_to_ignore=None):
    """
    Transform a psycopg2 row into a dict or a list of dict

    :param row:                 The psycopg2 row
    :type row:                  Row
    :param datetime_to_int:     Do you want to transform datetime object into int ? Optional, default False
    :type datetime_to_int:      bool
    :param keys_to_ignore:      Keys to not load. Optional, default None
    :type keys_to_ignore:       None|list[str]
    :return:                    A readable representation of the results
    :rtype:                     dict[str, any]
    """
    if row is None:
        return None
    result = {}
    for k in row.keys():
        if datetime_to_int and isinstance(row[k], datetime.datetime):
            result[k] = date_util.dt_to_timestamp(row[k])
        else:
            result[k] = row[k]
    return result


def parse_conditions(where):
    query_str = []
    query_args = []
    for cond in where:
        if type_util.is_string(cond):
            query_str.append(str(cond))
        elif len(cond) == 2:
            query_str.append(str(cond[0]) + " " + str(cond[1]))
        elif len(cond) == 3:
            if is_pg_native(cond[2]):
                query_str.append(str(cond[0]) + " " + str(cond[1]) + " %s ")
                query_args.append(cond[2])
            elif isinstance(cond[2], collections.Iterable) and not isinstance(cond[2], collections.Mapping):
                query_str.append(str(cond[0]) + " " + str(cond[1]) + " (" + ", ".join(["%s"] * len(cond[2])) + ")")
                query_args.extend(cond[2])
            else:
                query_str.append(str(cond[0]) + " " + str(cond[1]) + " %s ")
                query_args.append(cond[2])
        else:
            raise RuntimeError("Unable to understand sql condition "+repr(cond))
    return query_str, query_args


def is_pg_native(val):
    if isinstance(val, datetime.datetime) or isinstance(val, uuid.UUID):
        return True
    if isinstance(val, decimal.Decimal) or type_util.is_primitive(val):
        return True
    return False


def encode_vars(values):
    if DEBUG_WRAPPER:
        print "input: "+repr(values)
        if values is None:
            print "output: None"
        else:
            print "output: " + repr([val if is_pg_native(val) else json_encode(val) for val in values])
    if values is None:
        return None
    return [val if is_pg_native(val) else json_encode(val) for val in values]


def json_encode(val, **kwargs):
    if val is None:
        return None
    return json.dumps(cast_for_json(val), **kwargs)


def cast_for_json(val):
    if val is None:
        return None
    if type_util.is_primitive(val):
        return val
    if isinstance(val, collections.Mapping):
        return {cast_for_json(key): cast_for_json(subval) for key, subval in val.items()}
    elif isinstance(val, collections.Iterable):
        return [cast_for_json(subval) for subval in val]
    elif isinstance(val, datetime.datetime):
        return date_util.dt_to_timestamp(val)
    elif isinstance(val, decimal.Decimal):
        return float(val)
    elif isinstance(val, uuid.UUID):
        return str(val)
    else:
        return str(val)
