# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

"""Base Schema

Revision ID: a00000000002
Revises: a00000000001
Create Date: 2018-05-01 13:42:34.156781

"""

import os
from alembic import op


# Revision identifiers, used by Alembic.
revision = 'a00000000002'
down_revision = 'a00000000001'
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

    conn.execute(""" CREATE TABLE IF NOT EXISTS users (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    login                     TEXT NOT NULL,
                                    pwd                       TEXT NOT NULL,
                                    salt                      TEXT NOT NULL,
                                    user_rank                 SMALLINT NOT NULL DEFAULT 1,
                                    create_date               TIMESTAMP NOT NULL DEFAULT now(),
                                    delete_date               TIMESTAMP DEFAULT NULL
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_u_login_delete ON users (login)
                     WHERE delete_date IS NULL""")

    # ---- machines ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS machines (
                                    id                        BIGINT NOT NULL PRIMARY KEY,
                                    uid                       UUID NOT NULL,
                                    machine_code              TEXT NOT NULL,
                                    provider_code             TEXT NOT NULL,
                                    nbr_cores                 SMALLINT NOT NULL,
                                    ram_size                  BIGINT NOT NULL,
                                    nbr_available             INTEGER DEFAULT NULL
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_m_uid ON machines (uid) """)
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_m_m_p ON machines (machine_code, provider_code) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_m_machine_code ON machines(machine_code) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_m_provider_code ON machines(provider_code) """)

    conn.execute(""" CREATE TABLE IF NOT EXISTS machines_history (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    uid                       UUID NOT NULL,
                                    machine_code              TEXT NOT NULL,
                                    provider_code             TEXT NOT NULL,
                                    nbr_cores                 SMALLINT NOT NULL,
                                    ram_size                  BIGINT NOT NULL,
                                    nbr_available             INTEGER DEFAULT NULL,
                                    start_time                TIMESTAMP NOT NULL DEFAULT now(),
                                    end_time                  TIMESTAMP DEFAULT NULL
                            )""")

    # ---- machine prices ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS machine_prices (
                                    id                        BIGINT NOT NULL PRIMARY KEY,
                                    user_rank                 SMALLINT NOT NULL,
                                    machine_uid               UUID NOT NULL,
                                    sec_price                 BIGINT NOT NULL DEFAULT 0,
                                    sec_granularity           INTEGER NOT NULL DEFAULT 3600,
                                    min_sec_granularity       INTEGER NOT NULL DEFAULT 3600
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_mp_ur_muid ON machine_prices(user_rank, machine_uid)""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_mp_machine_uid ON machine_prices(machine_uid) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_mp_user_rank ON machine_prices(user_rank) """)

    conn.execute(""" CREATE TABLE IF NOT EXISTS machine_prices_history (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    user_rank                 SMALLINT NOT NULL,
                                    machine_uid               UUID NOT NULL,
                                    sec_price                 BIGINT NOT NULL DEFAULT 0,
                                    sec_granularity           INTEGER NOT NULL DEFAULT 3600,
                                    min_sec_granularity       INTEGER NOT NULL DEFAULT 3600,
                                    start_time                TIMESTAMP NOT NULL DEFAULT now(),
                                    end_time                  TIMESTAMP DEFAULT NULL
                            )""")

    # ---- provider costs ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS provider_costs (
                                    id                        BIGINT NOT NULL PRIMARY KEY,
                                    machine_uid               UUID NOT NULL,
                                    cost_per_sec              BIGINT NOT NULL DEFAULT 0,
                                    currency                  TEXT NOT NULL DEFAULT 'dollar',
                                    sec_granularity           INTEGER NOT NULL DEFAULT 3600,
                                    min_sec_granularity       INTEGER NOT NULL DEFAULT 3600
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_pc_muid ON provider_costs(machine_uid)""")

    conn.execute(""" CREATE TABLE IF NOT EXISTS provider_costs_history (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    machine_uid               UUID NOT NULL,
                                    cost_per_sec              INTEGER NOT NULL DEFAULT 0,
                                    currency                  TEXT NOT NULL DEFAULT 'dollar',
                                    sec_granularity           INTEGER NOT NULL DEFAULT 3600,
                                    min_sec_granularity       INTEGER NOT NULL DEFAULT 3600,
                                    start_time                TIMESTAMP NOT NULL DEFAULT now(),
                                    end_time                  TIMESTAMP DEFAULT NULL
                            )""")

    # ---- operations ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS operations (
                                    id                        BIGINT NOT NULL PRIMARY KEY,
                                    operation_name            TEXT NOT NULL,
                                    provider_code             TEXT NOT NULL,
                                    user_rank                 SMALLINT NOT NULL,
                                    fixed_cost                BIGINT NOT NULL DEFAULT 0,
                                    cluster_limit             INTEGER NOT NULL DEFAULT 0
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_o_muid ON operations(operation_name, provider_code, user_rank)""")

    conn.execute(""" CREATE TABLE IF NOT EXISTS operations_history (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    operation_name            TEXT NOT NULL,
                                    provider_code             TEXT NOT NULL,
                                    user_rank                 SMALLINT NOT NULL,
                                    fixed_cost                BIGINT NOT NULL DEFAULT 0,
                                    cluster_limit             INTEGER NOT NULL DEFAULT 0,
                                    start_time                TIMESTAMP NOT NULL DEFAULT now(),
                                    end_time                  TIMESTAMP DEFAULT NULL
                            )""")

    conn.execute(""" CREATE TABLE IF NOT EXISTS operation_machine (
                                    operation_name            TEXT NOT NULL,
                                    machine_uid               UUID NOT NULL
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_om_idx ON operation_machine(operation_name, machine_uid)""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_om_operation_name ON operation_machine(operation_name)""")

    # ---- projects ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS projects (
                                    id                        BIGINT NOT NULL PRIMARY KEY,
                                    uid                       TEXT NOT NULL,
                                    user_id                   BIGINT NOT NULL,
                                    status                    SMALLINT NOT NULL DEFAULT 1,
                                    data                      JSON NOT NULL DEFAULT '{}',
                                    storage                   TEXT NOT NULL
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_p_uid ON projects(uid)""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_p_user_id ON projects(user_id) """)

    conn.execute(""" CREATE TABLE IF NOT EXISTS projects_history (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    uid                       TEXT NOT NULL,
                                    user_id                   BIGINT NOT NULL,
                                    status                    SMALLINT NOT NULL DEFAULT 1,
                                    data                      JSON NOT NULL DEFAULT '{}',
                                    storage                   TEXT NOT NULL,
                                    start_time                TIMESTAMP NOT NULL DEFAULT now(),
                                    end_time                  TIMESTAMP DEFAULT NULL
                            )""")

    # ---- project files ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS project_files (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    project_uid               TEXT NOT NULL,
                                    filename                  TEXT NOT NULL,
                                    key                       TEXT DEFAULT NULL,
                                    size                      BIGINT NOT NULL DEFAULT 0,
                                    data                      JSON NOT NULL DEFAULT '{}',
                                    storage                   TEXT DEFAULT NULL,
                                    create_date               TIMESTAMP NOT NULL DEFAULT now(),
                                    change_date               TIMESTAMP NOT NULL DEFAULT now(),
                                    delete_date               TIMESTAMP DEFAULT NULL
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_pf_1 ON project_files(project_uid, key)
                     WHERE delete_date IS NULL AND key IS NOT NULL""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_pf_2 ON project_files(project_uid, filename)
                     WHERE delete_date IS NULL AND key IS NULL""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_pf_project_uid ON project_files(project_uid) """)

    # ---- user accounts ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS user_accounts (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    user_id                   BIGINT NOT NULL,
                                    amount                    BIGINT NOT NULL,
                                    description               TEXT NOT NULL,
                                    date                      TIMESTAMP NOT NULL DEFAULT now(),
                                    job_id                    BIGINT DEFAULT NULL,
                                    computing_start           TIMESTAMP DEFAULT NULL,
                                    computing_end             TIMESTAMP DEFAULT NULL,
                                    price_snapshot            JSON NOT NULL DEFAULT '{}'
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_ua_user_id ON user_accounts(user_id) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_ua_job_id ON user_accounts(job_id) """)

    # ---- jobs ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS jobs (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    user_id                   BIGINT NOT NULL,
                                    project_uid               TEXT NOT NULL,
                                    status                    SMALLINT NOT NULL DEFAULT 1,
                                    progress                  FLOAT NOT NULL DEFAULT 0.0,
                                    operation_id              BIGINT DEFAULT NULL,
                                    provider_cost_id          BIGINT DEFAULT NULL,
                                    machine_price_id          BIGINT DEFAULT NULL,
                                    nbr_machines              INTEGER NOT NULL DEFAULT 1,
                                    create_date               TIMESTAMP NOT NULL DEFAULT now(),
                                    start_time                TIMESTAMP DEFAULT NULL,
                                    end_time                  TIMESTAMP DEFAULT NULL,
                                    logs                      TEXT DEFAULT NULL
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_j_user_id ON jobs(user_id) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_j_project_uid ON jobs(project_uid) """)

    conn.execute(""" CREATE TABLE IF NOT EXISTS task_queue (
                                    job_id                    BIGINT NOT NULL,
                                    task                      TEXT NOT NULL,
                                    params                    JSON NOT NULL DEFAULT '{}'
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_tq_j ON task_queue(job_id)""")

    # ---- Meshes ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS meshes (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    project_uid               TEXT NOT NULL,
                                    name                      TEXT NOT NULL,
                                    result_file_id            BIGINT DEFAULT NULL,
                                    preview_file_id           BIGINT DEFAULT NULL,
                                    status                    SMALLINT NOT NULL DEFAULT 1,
                                    job_id                    BIGINT DEFAULT NULL,
                                    create_date               TIMESTAMP NOT NULL DEFAULT now(),
                                    delete_date               TIMESTAMP DEFAULT NULL
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_meshes_1 ON meshes(project_uid, name)
                     WHERE delete_date IS NULL""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_meshes_project_uid ON meshes(project_uid) """)

    # ---- calc ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS calculations (
                                    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                                    project_uid               TEXT NOT NULL,
                                    name                      TEXT NOT NULL,
                                    mesh_id                   BIGINT NOT NULL,
                                    params_file_id            BIGINT DEFAULT NULL,
                                    status_file_id            BIGINT DEFAULT NULL,
                                    result_file_id            BIGINT DEFAULT NULL,
                                    internal_file_id          BIGINT DEFAULT NULL,
                                    status                    SMALLINT NOT NULL DEFAULT 1,
                                    job_id                    BIGINT DEFAULT NULL,
                                    last_start_date           TIMESTAMP DEFAULT NULL,
                                    last_stop_date            TIMESTAMP DEFAULT NULL,
                                    create_date               TIMESTAMP NOT NULL DEFAULT now(),
                                    delete_date               TIMESTAMP DEFAULT NULL
                            )""")
    conn.execute(""" CREATE UNIQUE INDEX IF NOT EXISTS uidx_calculations_1 ON calculations(project_uid, name)
                     WHERE delete_date IS NULL""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_calc_project_uid ON calculations(project_uid) """)

    # ---- Time metrics ----

    conn.execute(""" CREATE TABLE IF NOT EXISTS time_metrics (
                                    label                     TEXT NOT NULL,
                                    start_time                TIMESTAMP NOT NULL,
                                    end_time                  TIMESTAMP NOT NULL,
                                    job_id                    BIGINT DEFAULT NULL,
                                    estimated                 INTERVAL DEFAULT NULL,
                                    fields                    JSON NOT NULL DEFAULT '{}'
                            )""")
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_tm_label ON time_metrics(label) """)
    conn.execute(""" CREATE INDEX IF NOT EXISTS idx_tm_start_time ON time_metrics(start_time) """)


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
