import argparse
import asyncio
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from migration_runner import DEFAULT_MIGRATIONS_DIR, apply_migrations, discover_migrations, format_migration_list


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fibaro10 database migrations.")
    parser.add_argument("--database-url", default="", help="Override DATABASE_URL.")
    parser.add_argument("--versions-dir", default=str(DEFAULT_MIGRATIONS_DIR), help="Directory with SQL migrations.")
    parser.add_argument("--list", action="store_true", help="List migrations and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Show pending migrations without applying SQL.")
    return parser.parse_args()


async def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    args = parse_args()
    versions_dir = Path(args.versions_dir)
    if args.list:
        print(format_migration_list(discover_migrations(versions_dir)))
        return 0

    database_url = args.database_url or os.getenv("DATABASE_URL", "")
    if not database_url:
        print("DATABASE_URL mangler.", file=sys.stderr)
        return 2

    applied = await apply_migrations(database_url, versions_dir=versions_dir, dry_run=args.dry_run)
    if applied:
        prefix = "Ville kjørt" if args.dry_run else "Kjørte"
        print(f"{prefix} {len(applied)} migrasjoner:")
        for migration_id in applied:
            print(f"- {migration_id}")
    else:
        print("Ingen ventende migrasjoner.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
