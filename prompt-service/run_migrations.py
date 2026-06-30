import os

from alembic import command
from alembic.config import Config


def run_migrations() -> None:
    """
    Runs `alembic upgrade head` programmatically, the same thing you'd
    type on a terminal -- just callable from Python instead.

    Why this exists: in a real deployment (a server, a container, a
    cloud platform), there usually isn't an interactive terminal to
    manually run alembic commands before the app starts. The standard
    fix is to have the application apply its own migrations as part of
    startup, so "deploy the code" and "the schema is up to date" become
    the same event instead of two separate manual steps.

    Important distinction this does NOT remove: a human still has to
    run `alembic revision --autogenerate` locally and review the
    generated file before committing it -- autogenerate's guesses
    aren't always perfect, and that step genuinely needs a person to
    look at the diff. What this automates is only the safe, mechanical
    second half: applying migration files that have ALREADY been
    written and committed to git. By the time this function runs, the
    migration files in alembic/versions/ are fixed, reviewed code --
    this just makes sure the database actually has them applied.
    """
    config_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    alembic_cfg = Config(config_path)

    # alembic/env.py already reads DATABASE_URL from our own
    # core.config.settings and overrides alembic.ini's placeholder
    # connection string with it -- so calling upgrade() here uses the
    # exact same real database connection the rest of the app uses.
    command.upgrade(alembic_cfg, "head")
