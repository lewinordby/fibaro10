import tempfile
import unittest
from pathlib import Path

from migration_runner import discover_migrations, format_migration_list, migration_id_from_path, pending_migrations, split_sql_statements


class MigrationRunnerTests(unittest.TestCase):
    def test_migration_id_comes_from_file_stem(self) -> None:
        self.assertEqual(migration_id_from_path(Path("20260610_1200_test.sql")), "20260610_1200_test")

    def test_discover_migrations_returns_sorted_sql_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20260610_1201_second.sql").write_text("-- second", encoding="utf-8")
            (root / "20260610_1200_first.sql").write_text("-- first", encoding="utf-8")
            (root / "notes.txt").write_text("ignore", encoding="utf-8")

            migrations = discover_migrations(root)

        self.assertEqual([item.migration_id for item in migrations], ["20260610_1200_first", "20260610_1201_second"])

    def test_pending_migrations_filters_applied_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "20260610_1200_first.sql").write_text("-- first", encoding="utf-8")
            (root / "20260610_1201_second.sql").write_text("-- second", encoding="utf-8")
            migrations = discover_migrations(root)

        pending = pending_migrations(migrations, {"20260610_1200_first"})

        self.assertEqual([item.migration_id for item in pending], ["20260610_1201_second"])

    def test_format_migration_list_handles_empty_list(self) -> None:
        self.assertEqual(format_migration_list([]), "Ingen migrasjoner funnet.")

    def test_split_sql_statements_preserves_semicolon_inside_string(self) -> None:
        sql = "CREATE TABLE test (value TEXT); INSERT INTO test VALUES ('a;b'); -- comment;\nUPDATE test SET value='c';"

        statements = split_sql_statements(sql)

        self.assertEqual(len(statements), 3)
        self.assertIn("'a;b'", statements[1])
