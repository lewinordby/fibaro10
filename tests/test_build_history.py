import hashlib
import json
from pathlib import Path

from build_log import BUILD_LOG, build_log_entry_by_build, normalized_build_log_entry


def test_all_836_original_history_entries_are_preserved():
    historical = [row for row in BUILD_LOG if int(row['build']) <= 1836]
    assert len(historical) == 836
    canonical = json.dumps(historical, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    assert hashlib.sha256(canonical).hexdigest() == 'c425f72ef7cea412626e83bbb0b286958f13b7ba982895d08e5f29bc145a0bed'


def test_history_remains_a_list_with_compatible_lookup_and_payload():
    assert isinstance(BUILD_LOG, list)
    row = build_log_entry_by_build('1836')
    assert normalized_build_log_entry(row)['build'] == '1836'
    assert build_log_entry_by_build('missing') is None


def test_core_image_excludes_archives_without_changing_collector_contexts():
    root = Path(__file__).resolve().parents[1]
    shared = set((root / '.dockerignore').read_text().splitlines()) - {''}
    core = set((root / 'Dockerfile.dockerignore').read_text().splitlines())
    assert shared <= core
    assert {'*.tar.gz', '*.zip', 'tests', '.pytest_cache'} <= core
