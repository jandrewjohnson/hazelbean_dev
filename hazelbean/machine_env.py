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

# Provenance of the most recent load, so a ProjectFlow can say at construction where
# a per-machine value came from (see describe_source).
LOADED_MACHINE_ENV_PATH = None   # the file that was read, or None when it did not exist
LOADED_MACHINE_ENV = {}          # KEY -> value as supplied by that file


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
    global LOADED_MACHINE_ENV_PATH, LOADED_MACHINE_ENV
    if path is None:
        path = USER_MACHINE_ENV_PATH
    if not os.path.isfile(path):
        LOADED_MACHINE_ENV_PATH, LOADED_MACHINE_ENV = None, {}
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
    LOADED_MACHINE_ENV_PATH, LOADED_MACHINE_ENV = path, dict(supplied)
    return supplied


def describe_source(key):
    """Where the current value of os.environ[key] came from, as a short phrase for a log line.

    One of: 'machine.env (<path>)', 'process environment (overrides <path>)',
    'process environment', or 'unset (...)' naming the file that was or was not read.
    """
    in_env = key in os.environ
    in_file = key in LOADED_MACHINE_ENV
    if in_file and in_env and os.environ[key] == LOADED_MACHINE_ENV[key]:
        return 'machine.env (%s)' % LOADED_MACHINE_ENV_PATH
    if in_file and in_env:
        return 'process environment (overrides %s)' % LOADED_MACHINE_ENV_PATH
    if in_env:
        return 'process environment'
    if LOADED_MACHINE_ENV_PATH is None:
        return 'unset (no %s)' % USER_MACHINE_ENV_PATH
    return 'unset (not in %s)' % LOADED_MACHINE_ENV_PATH
