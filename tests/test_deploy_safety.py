import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")


def test_deployment_is_non_destructive_and_has_no_collector_side_effects():
    source = "\n".join((ROOT / "scripts" / name).read_text(encoding="utf-8") for name in (
        "deploy-qnap.ps1", "deploy-release.sh", "deploy-core-qnap.sh",
    ))
    for forbidden in ("git reset --hard", "git clean", "set_env_value", "/sync-now", "compose down", "rm -rf"):
        assert forbidden not in source
    assert "git merge --ff-only" in source
    assert "trap rollback EXIT" in source


def test_test_entrypoints_are_cross_platform_and_cover_easypark():
    source = (ROOT / "scripts/check-affected.ps1").read_text(encoding="utf-8")
    assert 'if ($EasyPark)' in source
    assert 'tests/test_easypark_downloader.py' in source
    for name in ("check-local.ps1", "check-affected.ps1", "smoke-affected.ps1", "deploy-qnap.ps1"):
        content = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert 'Run "powershell"' not in content
        assert '& powershell ' not in content


FAKE_DOCKER = r'''#!/bin/sh
set -eu
echo "$*" >> "$TEST_STATE/commands"
last=""; for arg in "$@"; do last=$arg; done
case "$1" in
 inspect)
    case "$3" in
      *Config.Image*) echo caddy:2-alpine ;;
      *State.Running*) if [ -f "$TEST_STATE/run-$last" ]; then echo true; else echo false; fi ;;
      *State.Health*) if [ -f "$TEST_STATE/healthy-$last" ]; then echo healthy; else echo unhealthy; fi ;;
      *.Image*) echo sha256:previous ;;
    esac ;;
 tag) printf '%s' "$2" > "$TEST_STATE/image" ;;
 start) touch "$TEST_STATE/run-$2" "$TEST_STATE/healthy-$2" ;;
 exec)
    case "$*" in
      *"print(json.load"*) cat "$TEST_STATE/build-$2" ;;
      *"assert str"*) test "$(cat "$TEST_STATE/build-$2")" = "$APP_BUILD" ;;
    esac ;;
 compose)
    case " $* " in
      *" build "*) echo new > "$TEST_STATE/image" ;;
      *" stop "*) rm -f "$TEST_STATE/run-$last" ;;
      *" up "*)
        touch "$TEST_STATE/run-$last"
        echo "$APP_BUILD" > "$TEST_STATE/build-$last"
        fail=0
        if [ "$(cat "$TEST_STATE/image")" = new ]; then
          if [ "${TEST_FAIL:-}" = worker ] && [ "$last" = fibaro10_worker ]; then fail=1; fi
          if [ "${TEST_FAIL:-}" = candidate ] && [ "$last" != fibaro10_worker ]; then fail=1; fi
        fi
        if [ "$fail" = 1 ]; then rm -f "$TEST_STATE/healthy-$last"; else touch "$TEST_STATE/healthy-$last"; fi ;;
    esac ;;
esac
'''
FAKE_CURL = r'''#!/bin/sh
for slot in blue green; do
    name=fibaro10_$slot
    if [ -f "$TEST_STATE/run-$name" ] && [ -f "$TEST_STATE/healthy-$name" ]; then
        printf '{"app":{"build":"%s"}}\n' "$(cat "$TEST_STATE/build-$name")"
        exit 0
    fi
done
exit 1
'''


@pytest.mark.parametrize("active", ["blue", "green"])
@pytest.mark.parametrize("failure", ["", "candidate", "worker"])
def test_core_rollout_and_automatic_rollback(tmp_path, active, failure):
    assert BASH, "Bash is required for deploy tests (Git Bash on Windows)"
    state = tmp_path / "state"
    state.mkdir()
    for name in (f"fibaro10_{active}", "fibaro10_worker"):
        (state / f"run-{name}").touch()
        (state / f"healthy-{name}").touch()
        (state / f"build-{name}").write_text("1836")
    (state / "active-slot").write_text(active)
    for name, content in (("docker-fake", FAKE_DOCKER), ("curl", FAKE_CURL)):
        path = tmp_path / name
        path.write_text(content, encoding="utf-8", newline="\n")
        path.chmod(0o755)
    env = {**os.environ, "APP_BUILD": "1837", "TEST_STATE": state.as_posix(), "TEST_FAIL": failure,
           "FIBARO10_DEPLOY_STATE_DIR": state.as_posix(), "DEPLOY_HEALTH_ATTEMPTS": "2", "DEPLOY_POLL_SECONDS": "0"}
    # Set PATH inside bash so Windows drive letters are not interpreted as separators.
    command = 'test_bin=$(cd "$1" && pwd); export PATH="$test_bin:$PATH"; exec sh "$2" "$3"'
    result = subprocess.run([BASH, "-c", command, "test", tmp_path.as_posix(),
                             (ROOT / "scripts/deploy-core-qnap.sh").as_posix(), (tmp_path / "docker-fake").as_posix()],
                            env=env, capture_output=True, text=True, timeout=30)
    candidate = "green" if active == "blue" else "blue"
    expected_slot = active if failure else candidate
    assert (result.returncode != 0) == bool(failure), result.stdout + result.stderr
    assert (state / "active-slot").read_text().strip() == expected_slot
    assert (state / f"run-fibaro10_{expected_slot}").exists()
    assert (state / "healthy-fibaro10_worker").exists()
    assert (state / "build-fibaro10_worker").read_text().strip() == ("1836" if failure else "1837")
    commands = (state / "commands").read_text()
    assert "easypark" not in commands and "roborock" not in commands


@pytest.mark.parametrize('blocked', ['', 'dirty', 'lock', 'wrong-revision'])
def test_release_requires_fast_forward_and_preserves_runtime_files(tmp_path, blocked):
    assert BASH
    origin = tmp_path / 'origin'
    remote = tmp_path / 'remote'
    backups = tmp_path / 'backups'
    origin.mkdir()

    def git(directory, *args):
        result = subprocess.run(['git', '-C', str(directory), *args], capture_output=True, text=True, check=True)
        return result.stdout.strip()

    git(origin, 'init', '-b', 'main')
    git(origin, 'config', 'user.email', 'test@example.invalid')
    git(origin, 'config', 'user.name', 'Deploy test')
    (origin / 'BUILD').write_text('1836')
    (origin / 'unifi_protect_events').mkdir()
    (origin / 'unifi_protect_events/BUILD').write_text('1')
    git(origin, 'add', '.')
    git(origin, 'commit', '-m', 'before')
    previous = git(origin, 'rev-parse', 'HEAD')
    subprocess.run(['git', 'clone', str(origin), str(remote)], check=True, capture_output=True)
    (remote / '.env').write_text('RUNTIME_SECRET=preserve\n')
    (origin / 'BUILD').write_text('1837')
    git(origin, 'add', 'BUILD')
    git(origin, 'commit', '-m', 'after')
    target = git(origin, 'rev-parse', 'HEAD')
    if blocked == 'dirty':
        (remote / 'BUILD').write_text('local change')
    if blocked == 'lock':
        (backups / 'deploy.lock').mkdir(parents=True)
    args = [BASH, str(ROOT / 'scripts/deploy-release.sh'), remote.as_posix(), backups.as_posix(), '/not-used',
            '0' * 40 if blocked == 'wrong-revision' else previous, target, 'main']
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    assert (result.returncode != 0) == bool(blocked), result.stdout + result.stderr
    assert git(remote, 'rev-parse', 'HEAD') == (previous if blocked else target)
    assert (remote / '.env').read_text() == 'RUNTIME_SECRET=preserve\n'
    if not blocked:
        assert not (backups / 'deploy.lock').exists()
        assert len(list(backups.glob('*/previous-source.tar'))) == 1
