# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Base Schema

Revision ID: 1e54e6f3375f
Revises: e00000000009
Create Date: 2018-05-01 13:42:34.156781

"""

import os
from alembic import op


# Revision identifiers, used by Alembic.
revision = '1e54e6f3375f'
down_revision = 'e00000000009'
branch_labels = None
depends_on = None

data_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db_data'))
bkp_data_file = os.path.join(data_path, os.path.splitext(os.path.basename(__file__))[0]+'.pickle')
dump_file = os.path.join(data_path, str(revision)+"_fulldump.sql")


def upgrade():
    conn = op.get_bind()

    # if we had saved the database, we reload the dump
    if os.path.exists(dump_file):
        with open(dump_file, 'r') as f:
            sql = f.read()
        conn.connection.executescript(sql)
        return

    # ---- users ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `users` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `login`                     TEXT NOT NULL,
                                    `pwd`                       TEXT NOT NULL,
                                    `salt`                      TEXT NOT NULL,
                                    `user_rank`                 INTEGER NOT NULL DEFAULT 1,
                                    `create_date`               DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `delete_date`               DATETIME DEFAULT NULL,
                                    `delete_random`             INTEGER NOT NULL DEFAULT 0
                            )""")
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uidx_u_login_delete ON `users` (
                                    `login`,
                                    IFNULL(`delete_date`, 0),
                                    `delete_random`
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_u_login ON `users`(`login`) """)

    # ---- machines ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `machines` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY,
                                    `uid`                       TEXT NOT NULL,
                                    `machine_code`              TEXT NOT NULL,
                                    `provider_code`             TEXT NOT NULL,
                                    `nbr_cores`                 INTEGER NOT NULL,
                                    `ram_size`                  INTEGER NOT NULL,
                                    `nbr_available`             INTEGER DEFAULT NULL,
                                    UNIQUE(`uid`)
                                    UNIQUE(`machine_code`, `provider_code`)
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_m_machine_code ON `machines`(`machine_code`) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_m_provider_code ON `machines`(`provider_code`) """)

    conn.execute(""" CREATE TABLE IF NOT EXISTS `machines_history` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `uid`                       TEXT NOT NULL,
                                    `machine_code`              TEXT NOT NULL,
                                    `provider_code`             TEXT NOT NULL,
                                    `nbr_cores`                 INTEGER NOT NULL,
                                    `ram_size`                  INTEGER NOT NULL,
                                    `nbr_available`             INTEGER DEFAULT NULL,
                                    `start_time`                DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `end_time`                  DATETIME DEFAULT NULL
                            )""")

    # ---- machine prices ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `machine_prices` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY,
                                    `user_rank`                 INTEGER NOT NULL,
                                    `machine_uid`               TEXT NOT NULL,
                                    `sec_price`                 INTEGER NOT NULL DEFAULT 0,
                                    `sec_granularity`           INTEGER NOT NULL DEFAULT 3600,
                                    `min_sec_granularity`       INTEGER NOT NULL DEFAULT 3600,
                                    UNIQUE(`user_rank`, `machine_uid`)
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_mp_machine_uid ON `machine_prices`(`machine_uid`) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_mp_user_rank ON `machine_prices`(`user_rank`) """)

    conn.execute(""" CREATE TABLE IF NOT EXISTS `machine_prices_history` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `user_rank`                 INTEGER NOT NULL,
                                    `machine_uid`               TEXT NOT NULL,
                                    `sec_price`                 INTEGER NOT NULL DEFAULT 0,
                                    `sec_granularity`           INTEGER NOT NULL DEFAULT 3600,
                                    `min_sec_granularity`       INTEGER NOT NULL DEFAULT 3600,
                                    `start_time`                DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `end_time`                  DATETIME DEFAULT NULL
                            )""")

    # ---- provider costs ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `provider_costs` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY,
                                    `machine_uid`               TEXT NOT NULL,
                                    `cost_per_sec`              INTEGER NOT NULL DEFAULT 0,
                                    `currency`                  TEXT NOT NULL DEFAULT 'dollar',
                                    `sec_granularity`           INTEGER NOT NULL DEFAULT 3600,
                                    `min_sec_granularity`       INTEGER NOT NULL DEFAULT 3600,
                                    UNIQUE(`machine_uid`)
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_pc_machine_uid ON `provider_costs`(`machine_uid`) """)

    conn.execute(""" CREATE TABLE IF NOT EXISTS `provider_costs_history` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY,
                                    `machine_uid`               TEXT NOT NULL,
                                    `cost_per_sec`              INTEGER NOT NULL DEFAULT 0,
                                    `currency`                  TEXT NOT NULL DEFAULT 'dollar',
                                    `sec_granularity`           INTEGER NOT NULL DEFAULT 3600,
                                    `min_sec_granularity`       INTEGER NOT NULL DEFAULT 3600,
                                    `start_time`                DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `end_time`                  DATETIME DEFAULT NULL
                            )""")

    # ---- operations ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `operations` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY,
                                    `operation_name`            TEXT NOT NULL,
                                    `provider_code`             TEXT NOT NULL,
                                    `user_rank`                 INTEGER NOT NULL,
                                    `fixed_cost`                INTEGER NOT NULL DEFAULT 0,
                                    `cluster_limit`             INTEGER NOT NULL DEFAULT 0,
                                    UNIQUE(`operation_name`, `provider_code`, `user_rank`)
                            )""")

    conn.execute(""" CREATE TABLE IF NOT EXISTS `operations_history` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `operation_name`            TEXT NOT NULL,
                                    `provider_code`             TEXT NOT NULL,
                                    `user_rank`                 INTEGER NOT NULL,
                                    `fixed_cost`                INTEGER NOT NULL DEFAULT 0,
                                    `cluster_limit`             INTEGER NOT NULL DEFAULT 0,
                                    `start_time`                DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `end_time`                  DATETIME DEFAULT NULL
                            )""")

    conn.execute(""" CREATE TABLE IF NOT EXISTS `operation_machine` (
                                    `operation_name`            TEXT NOT NULL,
                                    `machine_uid`               TEXT NOT NULL,
                                    UNIQUE(`operation_name`, `machine_uid`)
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_om_operation_name ON `operation_machine`(`operation_name`) """)

    # ---- projects ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `projects` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY,
                                    `uid`                       TEXT NOT NULL,
                                    `user_id`                   INTEGER NOT NULL,
                                    `status`                    INTEGER NOT NULL DEFAULT 1,
                                    `data`                      TEXT NOT NULL DEFAULT '{}',
                                    `storage`                   TEXT NOT NULL,
                                    UNIQUE(`uid`)
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_p_uid ON `projects`(`uid`) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_p_user_id ON `projects`(`user_id`) """)

    conn.execute(""" CREATE TABLE IF NOT EXISTS `projects_history` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `uid`                       TEXT NOT NULL,
                                    `user_id`                   INTEGER NOT NULL,
                                    `status`                    INTEGER NOT NULL DEFAULT 1,
                                    `data`                      TEXT NOT NULL DEFAULT '{}',
                                    `storage`                   TEXT NOT NULL,
                                    `start_time`                DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `end_time`                  DATETIME DEFAULT NULL
                            )""")

    # ---- project files ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `project_files` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `project_uid`               TEXT NOT NULL,
                                    `filename`                  TEXT NOT NULL,
                                    `key`                       TEXT DEFAULT NULL,
                                    `size`                      INTEGER NOT NULL DEFAULT 0,
                                    `data`                      TEXT NOT NULL DEFAULT '{}',
                                    `storage`                   TEXT DEFAULT NULL,
                                    `create_date`               DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `change_date`               DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `delete_date`               DATETIME DEFAULT NULL,
                                    `delete_random`             INTEGER NOT NULL DEFAULT 0
                            )""")
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uidx_pf_1 ON `project_files` (
                                    `project_uid`, 
                                    `key`,
                                    IFNULL(`delete_date`, 0),
                                    `delete_random`
                            )""")
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uidx_pf_2 ON `project_files` (
                                    `project_uid`, 
                                    `filename`,
                                    IFNULL(`delete_date`, 0),
                                    `delete_random`
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_pf_project_uid ON `project_files`(`project_uid`) """)

    # ---- user accounts ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `user_accounts` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `user_id`                   INTEGER NOT NULL,
                                    `amount`                    INTEGER NOT NULL,
                                    `description`               TEXT NOT NULL,
                                    `date`                      DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `job_id`                    INTEGER DEFAULT NULL,
                                    `computing_start`           DATETIME DEFAULT NULL,
                                    `computing_end`             DATETIME DEFAULT NULL,
                                    `price_snapshot`            TEXT NOT NULL DEFAULT '{}'
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_ua_user_id ON `user_accounts`(`user_id`) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_ua_job_id ON `user_accounts`(`job_id`) """)

    # ---- jobs ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `jobs` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `user_id`                   INTEGER NOT NULL,
                                    `project_uid`               TEXT NOT NULL,
                                    `status`                    INTEGER NOT NULL DEFAULT 1,
                                    `progress`                  FLOAT NOT NULL DEFAULT 0.0,
                                    `operation_id`              INTEGER DEFAULT NULL,
                                    `provider_cost_id`          INTEGER DEFAULT NULL,
                                    `machine_price_id`          INTEGER DEFAULT NULL,
                                    `nbr_machines`              INTEGER NOT NULL DEFAULT 1,
                                    `create_date`               DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `start_time`                DATETIME DEFAULT NULL,
                                    `end_time`                  DATETIME DEFAULT NULL,
                                    `logs`                      BLOB DEFAULT NULL
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_j_user_id ON `jobs`(`user_id`) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_j_project_uid ON `jobs`(`project_uid`) """)

    conn.execute(""" CREATE TABLE IF NOT EXISTS `task_queue` (
                                    `job_id`                    INTEGER NOT NULL,
                                    `task`                      TEXT NOT NULL,
                                    `params`                    TEXT NOT NULL DEFAULT '{}',
                                    UNIQUE(`job_id`)
                            )""")

    # ---- Meshes ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `meshes` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `project_uid`               TEXT NOT NULL,
                                    `name`                      TEXT NOT NULL,
                                    `result_file_id`            INTEGER DEFAULT NULL,
                                    `preview_file_id`           INTEGER DEFAULT NULL,
                                    `status`                    INTEGER NOT NULL DEFAULT 1,
                                    `job_id`                    INTEGER DEFAULT NULL,
                                    `create_date`               DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `delete_date`               DATETIME DEFAULT NULL,
                                    `delete_random`             INTEGER NOT NULL DEFAULT 0
                            )""")
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uidx_meshes_1 ON `meshes` (
                                    `project_uid`, 
                                    `name`,
                                    IFNULL(`delete_date`, 0),
                                    `delete_random`
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_meshes_project_uid ON `meshes`(`project_uid`) """)

    # ---- calc ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `calculations` (
                                    `id`                        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                    `project_uid`               TEXT NOT NULL,
                                    `name`                      TEXT NOT NULL,
                                    `mesh_id`                   INTEGER NOT NULL,
                                    `params_file_id`            INTEGER DEFAULT NULL,
                                    `status_file_id`            INTEGER DEFAULT NULL,
                                    `result_file_id`            INTEGER DEFAULT NULL,
                                    `internal_file_id`          INTEGER DEFAULT NULL,
                                    `status`                    INTEGER NOT NULL DEFAULT 1,
                                    `job_id`                    INTEGER DEFAULT NULL,
                                    `last_start_date`           DATETIME DEFAULT NULL,
                                    `last_stop_date`            DATETIME DEFAULT NULL,
                                    `create_date`               DATETIME NOT NULL DEFAULT (CAST(strftime('%s', 'now', 'utc') AS int)),
                                    `delete_date`               DATETIME DEFAULT NULL,
                                    `delete_random`             INTEGER NOT NULL DEFAULT 0
                            )""")
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uidx_calculations_1 ON `calculations` (
                                    `project_uid`, 
                                    `name`,
                                    IFNULL(`delete_date`, 0),
                                    `delete_random`
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_calc_project_uid ON `calculations`(`project_uid`) """)

    # ---- Time metrics ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS `time_metrics` (
                                    `label`                     TEXT NOT NULL,
                                    `start_time`                DATETIME NOT NULL,
                                    `end_time`                  DATETIME NOT NULL,
                                    `job_id`                    INTEGER DEFAULT NULL,
                                    `estimated`                 DATETIME DEFAULT NULL,
                                    `fields`                    TEXT NOT NULL DEFAULT '{}'
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_tm_label ON `time_metrics`(`label`) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_tm_start_time ON `time_metrics`(`start_time`) """)


def downgrade():
    conn = op.get_bind()

    # We dump the full database as backup
    if os.path.exists(dump_file):
        os.remove(dump_file)

    with open(dump_file, 'w') as f:
        for line in conn.connection.iterdump():
            if 'alembic_version' not in line:
                f.write('%s\n' % line)

    # And we remove the full database
    result = conn.execute("""
          SELECT name 
            FROM sqlite_master 
           WHERE type = 'table' 
             AND name NOT IN ('alembic_version', 'sqlite_sequence')""").fetchall()
    for line in result:
        conn.execute("DROP TABLE '"+line[0]+"'")
