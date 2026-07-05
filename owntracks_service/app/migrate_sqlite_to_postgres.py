from __future__ import annotations

import argparse
import os
from typing import Any

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine

from app.main import (
    DATA_DIR,
    Base,
    OwnTracksDevice,
    OwnTracksGeocodeCache,
    OwnTracksLocation,
    OwnTracksWaypointEvent,
    OwnTracksWaypointState,
    OwnTracksZoneVisit,
)


TABLE_MODELS = [
    OwnTracksDevice,
    OwnTracksLocation,
    OwnTracksWaypointState,
    OwnTracksGeocodeCache,
    OwnTracksWaypointEvent,
    OwnTracksZoneVisit,
]


def default_source_url() -> str:
    return f"sqlite:///{DATA_DIR / 'owntracks.db'}"


def table_rows(engine: Engine, model: type[Any]) -> list[dict[str, Any]]:
    with engine.begin() as connection:
        return [dict(row._mapping) for row in connection.execute(select(model.__table__))]


def reset_postgres_sequence(engine: Engine, table_name: str, id_column: str = "id") -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        max_id = connection.execute(text(f'SELECT COALESCE(MAX("{id_column}"), 0) FROM "{table_name}"')).scalar_one()
        if int(max_id or 0) > 0:
            connection.execute(
                text("SELECT setval(pg_get_serial_sequence(:table_name, :id_column), :max_id, true)"),
                {"table_name": table_name, "id_column": id_column, "max_id": int(max_id)},
            )


def migrate(source_url: str, target_url: str) -> dict[str, int]:
    if source_url == target_url:
        raise ValueError("Source and target database URL are identical")
    source_engine = create_engine(source_url, future=True, connect_args={"check_same_thread": False} if source_url.startswith("sqlite") else {})
    target_engine = create_engine(target_url, future=True)

    Base.metadata.create_all(target_engine)

    copied: dict[str, int] = {}
    for model in TABLE_MODELS:
        table = model.__table__
        rows = table_rows(source_engine, model)
        with target_engine.begin() as connection:
            connection.execute(table.delete())
            if rows:
                connection.execute(table.insert(), rows)
        reset_postgres_sequence(target_engine, table.name)
        copied[table.name] = len(rows)
    return copied


def count_target_rows(target_url: str) -> dict[str, int]:
    target_engine = create_engine(target_url, future=True)
    result: dict[str, int] = {}
    with target_engine.begin() as connection:
        for model in TABLE_MODELS:
            result[model.__tablename__] = int(connection.execute(select(func.count()).select_from(model.__table__)).scalar_one())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy OwnTracks data from SQLite to PostgreSQL.")
    parser.add_argument("--source", default=os.getenv("OWNTRACKS_SQLITE_SOURCE_URL") or default_source_url())
    parser.add_argument("--target", default=os.getenv("OWNTRACKS_MIGRATE_TARGET_URL") or os.getenv("OWNTRACKS_DATABASE_URL"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.target:
        raise SystemExit("Target database URL is required. Set OWNTRACKS_DATABASE_URL or pass --target.")

    if args.verify_only:
        counts = count_target_rows(args.target)
    else:
        counts = migrate(args.source, args.target)
    for table_name, count in counts.items():
        print(f"{table_name}: {count}")


if __name__ == "__main__":
    main()
