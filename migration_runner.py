from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


DEFAULT_MIGRATIONS_DIR = Path(__file__).parent / "migrations" / "versions"


@dataclass(frozen=True)
class MigrationFile:
    migration_id: str
    path: Path


def migration_id_from_path(path: Path) -> str:
    return path.stem


def discover_migrations(versions_dir: Path = DEFAULT_MIGRATIONS_DIR) -> List[MigrationFile]:
    if not versions_dir.exists():
        return []
    migrations = [
        MigrationFile(migration_id=migration_id_from_path(path), path=path)
        for path in versions_dir.glob("*.sql")
        if path.is_file()
    ]
    migrations.sort(key=lambda item: item.migration_id)
    seen: set[str] = set()
    duplicates: set[str] = set()
    for migration in migrations:
        if migration.migration_id in seen:
            duplicates.add(migration.migration_id)
        seen.add(migration.migration_id)
    if duplicates:
        raise ValueError(f"Duplicate migration ids: {', '.join(sorted(duplicates))}")
    return migrations


def pending_migrations(all_migrations: Iterable[MigrationFile], applied_ids: Iterable[str]) -> List[MigrationFile]:
    applied = set(applied_ids)
    return [migration for migration in all_migrations if migration.migration_id not in applied]


def split_sql_statements(sql: str) -> List[str]:
    statements: List[str] = []
    current: List[str] = []
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    index = 0
    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if in_line_comment:
            current.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            current.append(char)
            if char == "*" and next_char == "/":
                current.append(next_char)
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if not in_single_quote and not in_double_quote and char == "-" and next_char == "-":
            current.append(char)
            current.append(next_char)
            in_line_comment = True
            index += 2
            continue

        if not in_single_quote and not in_double_quote and char == "/" and next_char == "*":
            current.append(char)
            current.append(next_char)
            in_block_comment = True
            index += 2
            continue

        if char == "'" and not in_double_quote:
            current.append(char)
            if in_single_quote and next_char == "'":
                current.append(next_char)
                index += 2
                continue
            in_single_quote = not in_single_quote
            index += 1
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(char)
            index += 1
            continue

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            index += 1
            continue

        current.append(char)
        index += 1

    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


async def applied_migration_ids(database_url: str) -> set[str]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(database_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        migration_id TEXT PRIMARY KEY,
                        applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            result = await conn.execute(text("SELECT migration_id FROM schema_migrations"))
            return {str(row[0]) for row in result.fetchall()}
    finally:
        await engine.dispose()


async def apply_migrations(database_url: str, versions_dir: Path = DEFAULT_MIGRATIONS_DIR, dry_run: bool = False) -> List[str]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    migrations = discover_migrations(versions_dir)
    engine = create_async_engine(database_url, echo=False)
    applied_now: List[str] = []
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        migration_id TEXT PRIMARY KEY,
                        applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            result = await conn.execute(text("SELECT migration_id FROM schema_migrations"))
            applied = {str(row[0]) for row in result.fetchall()}
            for migration in pending_migrations(migrations, applied):
                applied_now.append(migration.migration_id)
                if dry_run:
                    continue
                sql = migration.path.read_text(encoding="utf-8")
                for statement in split_sql_statements(sql):
                    await conn.execute(text(statement))
                await conn.execute(
                    text("INSERT INTO schema_migrations (migration_id) VALUES (:migration_id)"),
                    {"migration_id": migration.migration_id},
                )
    finally:
        await engine.dispose()
    return applied_now


def format_migration_list(migrations: Iterable[MigrationFile]) -> str:
    rows = list(migrations)
    if not rows:
        return "Ingen migrasjoner funnet."
    return "\n".join(f"{migration.migration_id}  {migration.path}" for migration in rows)
