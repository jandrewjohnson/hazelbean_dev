"""Detect shared data roots on this machine and write them to machine.env.

A shared data root is a read-only directory mirroring base_data's ref_path layout,
usually a mounted lab drive. ProjectFlow.get_path searches configured roots after
base_data_dir and before the cloud bucket, copying any hit into base_data_dir (see
the get_path section of the EE conventions).

Run once, deliberately:

    hb-setup-machine-env            # scan, show findings, confirm, write
    hb-setup-machine-env --print    # show what would be set, write nothing
    hb-setup-machine-env --yes      # write without prompting (for scripted setup)

Deliberately NOT done at install time or at import time:

  - the conda-forge build of hazelbean never runs this repo's setup.py, so an
    install-time hook would silently skip the most common onboarding path;
  - detection at install time runs before the thing it is looking for exists --
    people install the stack, then get added to the shared drive, then install
    Drive for Desktop;
  - a filesystem probe on every `import hazelbean` is pure waste on a cluster,
    where the mount can never exist, and would make path resolution depend on
    what happens to be mounted rather than on a config file someone can read.

The result is a plain line in ~/.config/hazelbean/machine.env that can be read,
edited, or deleted by hand. This script is a convenience, never a dependency.
"""
import argparse
import glob
import os
import platform
import sys

from hazelbean.machine_env import USER_MACHINE_ENV_PATH

SHARED_DATA_DIRS_KEY = 'HB_SHARED_DATA_DIRS'

# A candidate is only accepted if it looks like base_data. Without this check the
# globs below would happily match any directory that happened to be named right.
BASE_DATA_MARKERS = ('cartographic', 'lulc', 'pyramids', 'crops', 'seals', 'luh2', 'global_invest')
MINIMUM_MARKERS = 2

# Bounded globs, never a walk: walking a cloud-sync tree wakes the sync client and
# materializes placeholder files. Each pattern is anchored so it can only match a
# base_data mirror a few levels inside a known mount point.
def _candidate_patterns():
    """Glob patterns for where a base_data mirror plausibly lives on this OS."""
    home = os.path.expanduser('~')
    system = platform.system()
    patterns = []

    if system == 'Darwin':
        # Drive for Desktop (current) mounts per account under CloudStorage.
        patterns += [
            os.path.join(home, 'Library', 'CloudStorage', 'GoogleDrive-*', 'Shared drives', '*', 'Files', 'base_data'),
            os.path.join(home, 'Library', 'CloudStorage', 'GoogleDrive-*', 'My Drive', 'Files', 'base_data'),
            # Legacy mount point, still present on older installs.
            os.path.join('/Volumes', 'GoogleDrive', 'Shared drives', '*', 'Files', 'base_data'),
            # Other sync clients, same layout contract.
            os.path.join(home, 'Library', 'CloudStorage', 'Dropbox*', 'Files', 'base_data'),
            os.path.join(home, 'Library', 'CloudStorage', 'OneDrive-*', 'Files', 'base_data'),
        ]
    elif system == 'Windows':
        # Drive for Desktop mounts as a drive letter (G: by default, configurable)
        # or as a folder under the user profile.
        patterns += [
            drive + ':\\Shared drives\\*\\Files\\base_data' for drive in 'GHIJKLMNOPQRSTUVWXYZ'
        ]
        patterns += [
            drive + ':\\My Drive\\Files\\base_data' for drive in 'GHIJKLMNOPQRSTUVWXYZ'
        ]
        patterns += [
            os.path.join(home, 'Google Drive', 'Files', 'base_data'),
            os.path.join(home, 'Dropbox', 'Files', 'base_data'),
        ]
    else:
        # No official Google Drive client exists for Linux and none is expected.
        # A shared root on Linux is a group scratch dir or network mount, which
        # has no discoverable convention -- set HB_SHARED_DATA_DIRS by hand.
        pass

    # Any platform: a plain sync folder in the home dir.
    patterns.append(os.path.join(home, 'Dropbox', 'Files', 'base_data'))
    return patterns


def score_candidate(candidate_dir):
    """How many base_data marker directories a candidate contains (higher is better)."""
    try:
        children = set(os.listdir(candidate_dir))
    except OSError:
        # An unmounted or unauthenticated cloud dir can raise rather than be empty.
        return 0
    return len([i for i in BASE_DATA_MARKERS if i in children])


def find_shared_data_root_candidates(verbose=False):
    """Return [(path, marker_score), ...] for plausible base_data mirrors, best first.

    Only directories that actually look like base_data are returned, so a stray
    folder with the right name is never proposed.
    """
    found = {}
    for pattern in _candidate_patterns():
        try:
            matches = glob.glob(pattern)
        except OSError:
            continue
        for candidate_dir in matches:
            if not os.path.isdir(candidate_dir) or candidate_dir in found:
                continue
            score = score_candidate(candidate_dir)
            if verbose:
                print('  checked (%d markers): %s' % (score, candidate_dir))
            if score >= MINIMUM_MARKERS:
                found[candidate_dir] = score
    return sorted(found.items(), key=lambda i: (-i[1], i[0]))


def read_existing_value(machine_env_path=None, key=SHARED_DATA_DIRS_KEY):
    """The value already set for key in machine.env, or None. Never parses the wider env."""
    if machine_env_path is None:
        machine_env_path = USER_MACHINE_ENV_PATH
    if not os.path.isfile(machine_env_path):
        return None
    with open(machine_env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith('export '):
                line = line[len('export '):].strip()
            if line.startswith(key + '='):
                return line.split('=', 1)[1].strip()
    return None


def write_machine_env_value(value, machine_env_path=None, key=SHARED_DATA_DIRS_KEY):
    """Append key=value to machine.env, creating the file and its directory if needed.

    Never rewrites an existing key -- the caller checks read_existing_value first and
    reports rather than clobbering, so a hand-edited config is always safe.
    """
    if machine_env_path is None:
        machine_env_path = USER_MACHINE_ENV_PATH
    config_dir = os.path.dirname(machine_env_path)
    if config_dir and not os.path.isdir(config_dir):
        os.makedirs(config_dir)

    needs_newline = False
    if os.path.isfile(machine_env_path) and os.path.getsize(machine_env_path) > 0:
        with open(machine_env_path, 'rb') as f:
            f.seek(-1, os.SEEK_END)
            needs_newline = f.read(1) != b'\n'

    with open(machine_env_path, 'a') as f:
        if needs_newline:
            f.write('\n')
        f.write('\n# Shared data roots searched by ProjectFlow.get_path, after base_data_dir\n')
        f.write('# and before the cloud bucket. Read-only; hits are cached into base_data.\n')
        f.write('# Written by hb-setup-machine-env; edit or delete freely.\n')
        f.write(key + '=' + value + '\n')
    return machine_env_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='hb-setup-machine-env',
        description='Detect shared data roots (a mounted lab drive mirroring base_data) '
                    'and record them in ~/.config/hazelbean/machine.env.')
    parser.add_argument('--print', dest='print_only', action='store_true',
                        help='show what would be set and exit without writing')
    parser.add_argument('--yes', action='store_true',
                        help='write the detected roots without prompting')
    parser.add_argument('--verbose', action='store_true',
                        help='show every candidate considered, including rejected ones')
    args = parser.parse_args(argv)

    machine_env_path = USER_MACHINE_ENV_PATH
    print('Looking for shared data roots (a directory mirroring base_data)...')

    existing = read_existing_value(machine_env_path)
    candidates = find_shared_data_root_candidates(verbose=args.verbose)

    if not candidates:
        print('\nNo shared data root found on this machine.')
        if platform.system() not in ('Darwin', 'Windows'):
            print('Google Drive for Desktop has no Linux client, so nothing is detectable here.')
            print('If a shared root exists (a group scratch dir, a network mount), set it by hand:')
        else:
            print('If your lab drive is mounted, it may not mirror base_data at')
            print('<drive>/Files/base_data. Set it by hand:')
        print('  %s=/path/to/base_data' % SHARED_DATA_DIRS_KEY)
        print('  in %s' % machine_env_path)
        print('\nThis is not a problem: with no shared root, get_path falls through to the')
        print('cloud bucket, which works everywhere and needs no configuration.')
        return 0

    print('\nFound %d:' % len(candidates))
    for candidate_dir, score in candidates:
        print('  [%d/%d markers] %s' % (score, len(BASE_DATA_MARKERS), candidate_dir))

    value = os.pathsep.join([i for i, _ in candidates])
    line = SHARED_DATA_DIRS_KEY + '=' + value

    if existing is not None:
        print('\n%s is already set in %s:' % (SHARED_DATA_DIRS_KEY, machine_env_path))
        print('  ' + existing)
        print('\nLeaving it alone. To use what was detected instead, replace that line with:')
        print('  ' + line)
        return 0

    if args.print_only:
        print('\nWould add to %s:' % machine_env_path)
        print('  ' + line)
        return 0

    if not args.yes:
        print('\nAdd to %s:' % machine_env_path)
        print('  ' + line)
        try:
            answer = input('\nWrite it? [y/N] ').strip().lower()
        except EOFError:
            answer = ''
        if answer not in ('y', 'yes'):
            print('Nothing written.')
            return 1

    write_machine_env_value(value, machine_env_path)
    print('\nWrote %s' % machine_env_path)
    print('New Python processes will pick it up; hazelbean loads machine.env on import.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
