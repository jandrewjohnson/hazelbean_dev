"""Per-machine environment config.

Loads KEY=value pairs from a per-user file (default ~/.config/hazelbean/machine.env)
into os.environ when hazelbean is imported, filling gaps only — a variable already
set in the real environment always wins. This is the devstack-wide home for
per-machine, never-committed settings (e.g. gtappy's solve-backend connection vars
GTAP_VM_SSH_HOST / GTAP_GEMPACK_DIR), so they work identically on any OS and inside
IDE debug runs without shell rc files.

The format tolerates a leading 'export ' and trailing '# comment' on each line, so
the same file can also be sourced from a POSIX shell.
"""
import os

USER_MACHINE_ENV_PATH = os.path.join(os.path.expanduser('~'), '.config', 'hazelbean', 'machine.env')


def _parse_value(raw):
    """Strip surrounding quotes (and anything after the closing quote) or, for
    unquoted values, a trailing inline comment."""
    raw = raw.strip()
    if raw[:1] in ('"', "'"):
        quote = raw[0]
        end = raw.find(quote, 1)
        if end != -1:
            return raw[1:end]
    return raw.split('#', 1)[0].strip()


def load_user_machine_env(path=None):
    """Load KEY=value lines from path into os.environ with setdefault semantics.

    Returns a dict of the variables the file supplied (regardless of whether each
    one won over a pre-existing environment variable). Missing file -> empty dict,
    so machines without a config file are unaffected.
    """
    if path is None:
        path = USER_MACHINE_ENV_PATH
    if not os.path.isfile(path):
        return {}
    supplied = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, raw_value = line.split('=', 1)
            key = key.strip()
            if key.startswith('export '):
                key = key[len('export '):].strip()
            if not key or ' ' in key:
                continue
            value = _parse_value(raw_value)
            supplied[key] = value
            os.environ.setdefault(key, value)
    return supplied
