from __future__ import with_statement
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import os
import sys
import flask
import sqlite3
import platform
import re

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# Allow server source code imports
cfg_src_path = config.get_main_option("api_src_path")
if os.path.isabs(cfg_src_path):
    project_src_path = cfg_src_path
else:  # assume unix like file path format
    if platform.system().lower() == "windows":
        cfg_src_path_parts = re.split(r'[\\/]+', cfg_src_path)
    else:
        cfg_src_path_parts = cfg_src_path.split("/")
    alembic_current_dir = os.path.dirname(config.config_file_name)
    project_src_path = os.path.abspath(os.path.join(alembic_current_dir, *cfg_src_path_parts))
sys.path.append(project_src_path)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        connection.detach()
        connection.connection.detach()

        try:
            app = flask.Flask(__name__)
            with app.app_context():
                connection.connection.connection.row_factory = sqlite3.Row
                flask.g.get_db = lambda: connection.connection.connection

                with context.begin_transaction():
                    context.run_migrations()
        finally:
            connection.close()


if context.is_offline_mode():
    raise NotImplementedError("Offline mode is not allowed")
else:
    run_migrations_online()
