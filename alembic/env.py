from __future__ import annotations

import os
import re
import sys
from logging.config import fileConfig
from typing import Optional

from alembic import context  # type: ignore[attr-defined]
from alembic.script import ScriptDirectory
from sqlalchemy import engine_from_config, pool

# Add project path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.infrastructure.models import Base  # noqa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _slugify(message: Optional[str]) -> str:
    if not message:
        return "revision"
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", message).strip("_").lower()
    return slug or "revision"


def _next_revision_id(slug: str) -> str:
    script_directory = ScriptDirectory.from_config(config)
    max_index = 0
    for revision in script_directory.walk_revisions():
        match = re.match(r"^(\d+)", revision.revision or "")
        if match:
            max_index = max(max_index, int(match.group(1)))
    return f"{max_index + 1:04d}_{slug}"


def _process_revision_directives(context, revision, directives):  # type: ignore[unused-argument]
    cmd_opts = getattr(config, "cmd_opts", None)
    if cmd_opts and getattr(cmd_opts, "rev_id", None):
        return
    if not directives:
        return
    script = directives[0]
    script.rev_id = _next_revision_id(_slugify(getattr(script, "message", None)))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=_process_revision_directives,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=_process_revision_directives,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
