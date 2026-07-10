import os
import sys

import pytest

from hazelbean.machine_env import load_user_machine_env


def write_env_file(tmp_path, text):
    p = tmp_path / "machine.env"
    p.write_text(text)
    return str(p)


def test_missing_file_returns_empty(tmp_path):
    assert load_user_machine_env(str(tmp_path / "nope.env")) == {}


def test_plain_key_value(tmp_path, monkeypatch):
    monkeypatch.delenv("HB_TEST_PLAIN", raising=False)
    path = write_env_file(tmp_path, "HB_TEST_PLAIN=hello\n")
    supplied = load_user_machine_env(path)
    assert supplied == {"HB_TEST_PLAIN": "hello"}
    assert os.environ["HB_TEST_PLAIN"] == "hello"


def test_real_environment_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("HB_TEST_WINS", "from_real_env")
    path = write_env_file(tmp_path, "HB_TEST_WINS=from_file\n")
    supplied = load_user_machine_env(path)
    assert supplied == {"HB_TEST_WINS": "from_file"}
    assert os.environ["HB_TEST_WINS"] == "from_real_env"


def test_shell_template_format(tmp_path, monkeypatch):
    # The gtappy modality_env template verbatim: export prefix, quotes,
    # inline comments, blank lines, comment-only lines, backslash paths.
    for k in ("GTAP_VM_SSH_HOST", "GTAP_VM_DISK_PREFIX", "GTAP_GEMPACK_DIR"):
        monkeypatch.delenv(k, raising=False)
    text = (
        "# GTAP modality dispatch -- per-machine connection config\n"
        "\n"
        "export GTAP_VM_SSH_HOST='me@192.168.64.2'         # e.g. Chiara@192.168.64.4\n"
        'export GTAP_VM_DISK_PREFIX="C:/Users/me/Files"  # the VM Files dir\n'
        "export GTAP_GEMPACK_DIR='C:\\GP'\n"
        "# export GTAP_SC_SSH_HOST='<user>@<cluster>'\n"
    )
    path = write_env_file(tmp_path, text)
    supplied = load_user_machine_env(path)
    assert supplied == {
        "GTAP_VM_SSH_HOST": "me@192.168.64.2",
        "GTAP_VM_DISK_PREFIX": "C:/Users/me/Files",
        "GTAP_GEMPACK_DIR": "C:\\GP",
    }
    assert os.environ["GTAP_VM_SSH_HOST"] == "me@192.168.64.2"
    assert os.environ["GTAP_GEMPACK_DIR"] == "C:\\GP"


def test_unquoted_inline_comment_stripped(tmp_path, monkeypatch):
    monkeypatch.delenv("HB_TEST_COMMENT", raising=False)
    path = write_env_file(tmp_path, "HB_TEST_COMMENT=bare_value # trailing note\n")
    supplied = load_user_machine_env(path)
    assert supplied == {"HB_TEST_COMMENT": "bare_value"}


def test_malformed_lines_skipped(tmp_path, monkeypatch):
    monkeypatch.delenv("HB_TEST_OK", raising=False)
    text = (
        "no_equals_sign_here\n"
        "two words=bad_key_skipped\n"
        "HB_TEST_OK=fine\n"
    )
    path = write_env_file(tmp_path, text)
    supplied = load_user_machine_env(path)
    assert supplied == {"HB_TEST_OK": "fine"}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
