from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from argparse import ArgumentParser
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path


EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "output",
    "tmp",
    "v1_reference",
}


def requirement_groups(repo_root: Path) -> list[list[Path]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(repo_root.rglob("requirements*.txt")):
        if EXCLUDED_PARTS.intersection(path.parts):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        groups[digest].append(path)
    return sorted(groups.values(), key=lambda paths: str(paths[0]))


def requirements_digest(repo_root: Path, groups: list[list[Path]]) -> str:
    digest = hashlib.sha256()
    for path in sorted(path for group in groups for path in group):
        digest.update(str(path.relative_to(repo_root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def cache_is_fresh(cache_path: Path, digest: str) -> bool:
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        checked_at = datetime.fromisoformat(payload["checked_at"])
        return (
            payload.get("requirements_digest") == digest
            and datetime.now(UTC) - checked_at <= timedelta(hours=24)
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def main() -> int:
    parser = ArgumentParser(description="Audit all active Python requirement sets.")
    parser.add_argument("--force", action="store_true", help="Ignore a fresh successful cache.")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    groups = requirement_groups(repo_root)
    if not groups:
        print("No active Python requirement files found.", file=sys.stderr)
        return 1

    digest = requirements_digest(repo_root, groups)
    cache_path = repo_root / ".audit-cache" / "python-dependencies.json"
    if not args.force and cache_is_fresh(cache_path, digest):
        print("Python dependency audit OK (cached; requirements unchanged)")
        return 0

    print(f"Auditing {len(groups)} unique dependency sets from "
          f"{sum(len(group) for group in groups)} requirement files.")
    for group in groups:
        representative = group[0]
        relative_names = ", ".join(str(path.relative_to(repo_root)) for path in group)
        print(f"\n[{relative_names}]")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--requirement",
                str(representative),
                "--progress-spinner",
                "off",
                "--strict",
                "--timeout",
                "30",
            ],
            cwd=representative.parent,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "checked_at": datetime.now(UTC).isoformat(),
                "requirements_digest": digest,
                "unique_sets": len(groups),
                "requirement_files": sum(len(group) for group in groups),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("\nPython dependency audit OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
