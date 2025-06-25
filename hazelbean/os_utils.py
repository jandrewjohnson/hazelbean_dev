import atexit
import datetime
import time
import errno
import pathlib
import os
import random
import shutil
import sys
import distutils
from distutils import dir_util # NEEDED
import pathlib

import hazelbean as hb
import zipfile
import stat
from hazelbean import globals

def make_run_dir(base_folder=hb.config.TEMPORARY_DIR, run_name='', just_return_string=False):
    """Create a directory in a preconfigured location. Does not delete by default. Returns path of dir."""
    run_dir = os.path.join(base_folder, ruri(run_name))
    if not os.path.exists(run_dir):
        if not just_return_string:
            os.makedirs(run_dir)
    else:
        raise Exception('This should not happen as the temp file has a random name.')
    return run_dir

# # TODOO Useful
# def get_last_run_dirs(num_to_get=10, override_default_temp_dir=None):
#     if override_default_temp_dir:
#         temp_dir = override_default_temp_dir
#     else:
#         temp_dir = hb.TEMPORARY_DIR
#     all_run_dirs = [i for i in os.listdir(temp_dir) if os.path.isdir(i)]
#
#     for possible_dir in all_run_dirs:
#         get_time_stamp_from_string(possible_dir)
#
# def check_for_file_path_in_last_n_run_dirs():
#     pass


def temp(ext=None, filename_start=None, remove_at_exit=True, folder=None, suffix='', tag_along_file_extensions=['.aux.xml'], tag_along_file_paths=None):
    """Create a path with extension ext in a temporary dir. Can add filename prefixes or suffixes, and place in a desired folder. Can be removed at exit automatically. 
    Note, this just makes the path string, not the file itself.
    
    tagalong_file_extensions identifies additional files that should also be removed with extra extensions, such as this.tif.aux.xml
    """
    if ext:
        if not ext.startswith('.'):
            ext = '.' + ext

    if filename_start:
        if ext:
            filename = ruri(filename_start + ext)
        else:
            filename = ruri(filename_start + '.tif')
    else:
        if ext:
            filename = ruri('tmp' + ext)
        else:
            filename = ruri('tmp.tif')

    if folder is not None:
        uri = os.path.join(folder, filename)
    else:
        user_home = pathlib.Path.home()
        temp_dir = user_home/'temp'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        # Get the user dir
        uri = os.path.join(temp_dir, filename)

    if remove_at_exit:
        remove_uri_at_exit(uri)
        
    if tag_along_file_extensions is not None:
        if type(tag_along_file_extensions) is str:
            tag_along_file_extensions = [tag_along_file_extensions]
        for tag_along_file_extension in tag_along_file_extensions:
            tag_along_uri = uri + tag_along_file_extension
            if remove_at_exit:
                remove_uri_at_exit(tag_along_uri)
                
    if tag_along_file_paths is not None:
        if type(tag_along_file_paths) is str:
            tag_along_file_paths = [tag_along_file_paths]
        for tag_along_file_path in tag_along_file_paths:
            if remove_at_exit:
                remove_uri_at_exit(tag_along_file_path)

    return uri

# TODOO Get rid of convenience duplications?
def temp_filename(ext=None, filename_start=None, remove_at_exit=True, folder=None, suffix=''):
    return temp(ext=ext, filename_start=filename_start, remove_at_exit=remove_at_exit, folder=folder, suffix=suffix)


def temporary_filename(filename_start=None, ext='', remove_at_exit=True, folder=None, suffix=''):
    return temp(ext=ext, filename_start=filename_start, remove_at_exit=remove_at_exit, folder=folder, suffix=suffix)


def temporary_dir(dir_root=None, dir_name='tmpdir', dirname_prefix=None, dirname_suffix=None, remove_at_exit=True, add_random_string_to_dir_name=True):
    """Get path to new temporary folder that will be deleted on program exit.

    he folder is deleted on exit
    using the atexit register.

    Returns:
        path (string): an absolute, unique and temporary folder path. All underneath will be deleted.
    """
    
    if dir_root is None:
        # Set as users home temp dir
        user_home = pathlib.Path.home()
        dir_root = str(user_home/'temp')

            
    pre_post_string = dir_name
    if dirname_prefix:
        pre_post_string = dirname_prefix + '_' + pre_post_string
    if dirname_suffix:
        pre_post_string += '_' + dirname_suffix

    if add_random_string_to_dir_name:
        path = os.path.join(dir_root, ruri(pre_post_string))
    else:
        path = os.path.join(dir_root, pre_post_string)
    if os.path.exists(path):
        raise FileExistsError()
    else:
        os.mkdir(path)

    def remove_folder(path):
        """Function to remove a folder and handle exceptions encountered.  This
        function will be registered in atexit."""
        shutil.rmtree(path, ignore_errors=True)

    if remove_at_exit:
        atexit.register(remove_folder, path)

    return path

def quad_split_path(input_uri):
    '''
    Splits a path into prior directories path, parent directory, basename (extensionless filename), file extension.
    :return: list of [prior directories path, parent directory, basename (extensionless filename), file extension]
    '''
    a, file_extension = os.path.splitext(input_uri)
    b, file_root = os.path.split(a)
    prior_path, parent_directory = os.path.split(b)

    # TODOO Confusing? Parent directry is cur_dir, no? What happens when you give it a dir?
    return [prior_path, parent_directory, file_root, file_extension]




def random_numerals_string(length=6):
    max_value = int(''.join(['9'] * length))
    to_return = str(random.randint(0, max_value)).zfill(length)
    return to_return

def random_lowercase_string(length=6):
    """Returns randomly chosen, lowercase characters as a string with given length. Uses chr(int) to convert random."""
    random_ints = [random.randint(hb.globals.start_of_lowercase_letters_ascii_int, hb.globals.start_of_lowercase_letters_ascii_int + 26)  for i in range(length)]
    random_chars = [chr(i) for i in random_ints]
    return ''.join(random_chars)

def random_alphanumeric_string(length=6):
    """Returns randomly chosen, lowercase characters as a string with given length. Uses chr(int) to convert random."""
    random_chars = [random.choice(hb.globals.alphanumeric_lowercase_ascii_symbols) for i in range(length)]

    return ''.join(random_chars)


def convert_string_to_implied_type(input_string):
    if input_string in ['TRUE', 'True', 'true', 'T', 't', '1']:
        return True
    if input_string in ['FALSE', 'False', 'false', 'F', 'f', '0']:
        return False

    try:
        floated = float(input_string)
    except:
        floated = False

    try:
        inted = int(input_string)
    except:
        inted = False

    if '.' in input_string and floated:
        return floated

    if inted:
        return inted

    return input_string

def random_string():
    """Return random string of numbers of expected length. Used in uri manipulation."""
    return pretty_time(format='full') + str(random_lowercase_string(3))

def pretty_time(format=None):
    # Returns a nicely formated string of YEAR-MONTH-DAY_HOURS-MIN-SECONDS based on the the linux timestamp
    now = str(datetime.datetime.now())
    day, time = now.split(' ')
    day = day.replace('-', '')
    time = time.replace(':', '')
    if '.' in time:
        time, milliseconds = time.split('.')
        milliseconds = milliseconds[0:3]
    else:
        milliseconds = '000'

    if not format:
        return day + '_' + time
    elif format == 'full':
        return day + '_' + time + '_' + milliseconds
    elif format == 'day':
        return day
    elif format == 'day_hyphens':
        now = str(datetime.datetime.now())
        day, time = now.split(' ')
        return day
    elif format == 'year_month_day_hyphens':
        now = str(datetime.datetime.now())
        day, time = now.split(' ')
        return day


def explode_uri(input_uri):
    return explode_path(input_uri)

def explode_path(input_path):
    """
    Returns a dictionary with the following key-value pairs:

        path
        dir_name
        filename
        file_root
        file_extension
        parent_directory
        grandparent_path
        grandparent_directory
        great_grandparent_path
        root_directory
        post_root_directories
        post_root_path
        root_child_directory
        post_root_child_directories
        post_root_child_path
        file_root_no_suffix
        file_root_suffix
        file_root_no_timestamp
        file_root_date
        file_root_time
        file_root_no_timestamp_or_suffix
        parent_directory_no_suffix
        parent_directory_suffix
        parent_directory_no_timestamp
        parent_directory_date
        parent_directory_time
        parent_directory_datetime
        parent_directory_no_timestamp_or_suffix
        drive
        drive_no_slash
        post_drive_path
        post_drive_dir_name_and_file_root
        fragments
        path_directories

    """
    # Uses syntax from path.os
    curdir = '.'
    pardir = '..'
    extsep = '.'
    sep = '\\'
    pathsep = ';'
    altsep = '/'
    defpath = '.;C:\\bin'
    suffixsep = '_'

    # L.debug_deeper_1('Exploding ' + input_path)

    try:
        os.path.split(input_path)
    except:
        raise NameError('Unable to process input_path of ' + input_path + ' with os.path.split().')

    if pathsep in input_path:
        raise NameError('Usage of semicolon for multiple paths is not yet supported.')

    normcase_uri = os.path.normcase(input_path) # Use normpath if you want path optimizations besides case and //. Makes everything ahve the separator '\\'
    drive, post_drive_path = os.path.splitdrive(normcase_uri)
    if drive:
        drive = drive + '\\'

    if post_drive_path.startswith(sep):
        post_drive_path = post_drive_path[1:]

    post_drive_dir_name_and_file_root, file_extension = os.path.splitext(post_drive_path)

    if file_extension:
        post_drive_dir_name = os.path.split(post_drive_path)[0]
        dir_name_and_file_root = os.path.splitext(normcase_uri)[0]
        dir_name, file_root = os.path.split(dir_name_and_file_root)
    else:
        post_drive_dir_name = post_drive_path
        dir_name_and_file_root, file_extension = os.path.splitext(normcase_uri)
        dir_name, file_root = dir_name_and_file_root, ''

    filename = file_root + file_extension
    grandparent_path, parent_directory = os.path.split(dir_name)
    great_grandparent_path, grandparent_directory = os.path.split(grandparent_path)

    if os.path.splitext(post_drive_path):
        post_drive_path_without_files = os.path.split(post_drive_path)[0]
        n_post_drive_directories = len(post_drive_path.split(sep)) - 1
    else:
        n_post_drive_directories = len(post_drive_path.split(sep))

    if n_post_drive_directories == 0:
        root_directory, post_root_directories, root_child_directory, post_root_child_directories = os.path.join(drive, ''), '', '', ''
    elif n_post_drive_directories == 1:
        root_directory = os.path.join(drive, post_drive_path_without_files)
        post_root_directories, root_child_directory, post_root_child_directories = '', '', ''
    elif n_post_drive_directories == 2:
        root_directory, post_root_directories = post_drive_path_without_files.split(sep, 1)
        root_directory = os.path.join(drive, root_directory)
        root_child_directory, post_root_child_directories = post_root_directories, ''
    elif n_post_drive_directories == 3:
        root_directory, post_root_directories = post_drive_path_without_files.split(sep, 1)
        root_directory = os.path.join(drive, root_directory)
        root_child_directory = post_root_directories
        post_root_child_directories = ''
    else:
        root_directory, post_root_directories = post_drive_path_without_files.split(sep, 1)
        root_child_directory, post_root_child_directories = post_root_directories.split(sep, 1)
    post_root_path = os.path.join(post_root_directories, filename)
    post_root_child_path = os.path.join(post_root_child_directories, filename)

    file_root_split = file_root.split(suffixsep)
    split_file_root_reversed = file_root_split[::-1]

    file_root_has_timestamp = False
    file_root_has_suffix = False

    try:
        if len(split_file_root_reversed[0]) == 6 and len(split_file_root_reversed[1]) == 6 and len(split_file_root_reversed[2]) == 8 and split_file_root_reversed[1].isdigit() and split_file_root_reversed[2].isdigit():
            file_root_has_suffix = False
            file_root_has_timestamp = True
            file_root_has_timestamp_but_no_suffix = True
        elif len(split_file_root_reversed[1]) == 6 and len(split_file_root_reversed[2]) == 6 and len(split_file_root_reversed[3]) == 8 and split_file_root_reversed[2].isdigit() and split_file_root_reversed[3].isdigit():
            file_root_has_suffix = True
            file_root_has_timestamp = True
            file_root_has_timestamp_but_no_suffix = False
        else:
            file_root_has_timestamp = False
            file_root_has_suffix = False
            file_root_has_timestamp_but_no_suffix = False
    except:
        file_root_has_timestamp = False
        file_root_has_suffix = False

    if file_root_has_timestamp:
        if file_root_has_timestamp_but_no_suffix:
            a = file_root.rsplit(suffixsep, 3)
            file_root_no_suffix, file_root_suffix = file_root, ''
            file_root_no_timestamp, file_root_date, file_root_time = a[0], a[1], a[2]
            file_root_no_timestamp_or_suffix = a[0]
        else:
            a = file_root.rsplit(suffixsep, 4)
            file_root_no_suffix, file_root_suffix = a[0] + '_' + a[1] +'_' +  a[2] +'_' +  a[3], a[4]
            file_root_no_timestamp, file_root_date, file_root_time = a[0] + '_' + a[4] , a[1], a[2]
            file_root_no_timestamp_or_suffix, file_root_date, file_root_time = a[0], a[1], a[2]
    else:
        if '_' in file_root:
            file_root_no_timestamp_or_suffix, file_root_suffix = file_root.rsplit('_', 1)
            file_root_date, file_root_time = '', ''
            file_root_no_suffix = file_root_no_timestamp_or_suffix
            file_root_no_timestamp = file_root
        else:
            file_root_no_timestamp_or_suffix, file_root_suffix = file_root, ''
            file_root_date, file_root_time = '', ''
            file_root_no_suffix = file_root_no_timestamp_or_suffix
            file_root_no_timestamp = file_root

    parent_directory_split = parent_directory.split(suffixsep)
    split_parent_directory_reversed = parent_directory_split[::-1]

    parent_directory_has_timestamp = False
    parent_directory_has_suffix = False

    try:
        if len(split_parent_directory_reversed[0]) == 6 and len(split_parent_directory_reversed[1]) == 6 and len(split_parent_directory_reversed[2]) == 8 and split_parent_directory_reversed[1].isdigit() and split_parent_directory_reversed[2].isdigit():
            parent_directory_has_suffix = False
            parent_directory_has_timestamp = True
            parent_directory_has_timestamp_but_no_suffix = True
        elif len(split_parent_directory_reversed[1]) == 6 and len(split_parent_directory_reversed[2]) == 6 and len(split_parent_directory_reversed[3]) == 8 and split_parent_directory_reversed[2].isdigit() and split_parent_directory_reversed[3].isdigit():
            parent_directory_has_suffix = True
            parent_directory_has_timestamp = True
            parent_directory_has_timestamp_but_no_suffix = False
        else:
            parent_directory_has_timestamp = False
            parent_directory_has_suffix = False
            parent_directory_has_timestamp_but_no_suffix = False
    except:
        parent_directory_has_timestamp = False
        parent_directory_has_suffix = False

    if parent_directory_has_timestamp:
        if parent_directory_has_timestamp_but_no_suffix:
            a = parent_directory.rsplit(suffixsep, 3)
            parent_directory_no_suffix, parent_directory_suffix = parent_directory, ''
            parent_directory_no_timestamp, parent_directory_date, parent_directory_time = a[0], a[1], a[2]
            parent_directory_no_timestamp_or_suffix = a[0]
        else:
            a = parent_directory.rsplit(suffixsep, 4)
            parent_directory_no_suffix, parent_directory_suffix = a[0] + '_' + a[1] +'_' +  a[2] +'_' +  a[3], a[4]
            parent_directory_no_timestamp, parent_directory_date, parent_directory_time = a[0] + '_' + a[4] , a[1], a[2]
            parent_directory_no_timestamp_or_suffix, parent_directory_date, parent_directory_time = a[0], a[1], a[2]
    else:
        if '_' in parent_directory:
            parent_directory_no_timestamp_or_suffix, parent_directory_suffix = parent_directory.rsplit('_', 1)
            parent_directory_date, parent_directory_time = '', ''
            parent_directory_no_suffix = parent_directory_no_timestamp_or_suffix
            parent_directory_no_timestamp = parent_directory
        else:
            parent_directory_no_timestamp_or_suffix, parent_directory_suffix = parent_directory, ''
            parent_directory_date, parent_directory_time = '', ''
            parent_directory_no_suffix = parent_directory_no_timestamp_or_suffix
            parent_directory_no_timestamp = parent_directory


    # Fragments is a list of all the parts where if it is joined via eg ''.join(fragments) it will recreate the URI.
    fragments = []
    if drive:
        drive_no_slash = drive[0:2]
        fragments.append(drive) # NOTE Because the print method on str of list returns //, this will look different for the drive.
    else:
        drive_no_slash = ''

    split_dirs = post_drive_dir_name.split(sep)
    for i in range(len(split_dirs)):
        if split_dirs[i]:
            fragments.append(split_dirs[i])
    if filename:
        fragments.append(filename)

    path_directories = fragments[1:len(fragments)-1] # NOTE the implicit - 2

    exploded_uri = {}
    exploded_uri['path'] = normcase_uri

    exploded_uri['dir_name'] = dir_name
    exploded_uri['filename'] = filename

    exploded_uri['file_root'] = file_root
    exploded_uri['file_extension'] = file_extension

    exploded_uri['parent_directory'] = parent_directory
    exploded_uri['grandparent_path'] = grandparent_path

    exploded_uri['grandparent_directory'] = grandparent_directory
    exploded_uri['great_grandparent_path'] = great_grandparent_path

    exploded_uri['root_directory'] = root_directory
    exploded_uri['post_root_directories'] = post_root_directories
    exploded_uri['post_root_path'] = post_root_path
    exploded_uri['root_child_directory'] = root_child_directory
    exploded_uri['post_root_child_directories'] = post_root_child_directories
    exploded_uri['post_root_child_path'] = post_root_child_path

    exploded_uri['file_root_no_suffix'] = file_root_no_suffix
    exploded_uri['file_root_suffix'] = file_root_suffix
    exploded_uri['file_root_no_timestamp'] = file_root_no_timestamp
    exploded_uri['file_root_date'] = file_root_date
    exploded_uri['file_root_time'] = file_root_time
    exploded_uri['file_root_no_timestamp_or_suffix'] = file_root_no_timestamp_or_suffix

    exploded_uri['parent_directory_no_suffix'] = parent_directory_no_suffix
    exploded_uri['parent_directory_suffix'] = parent_directory_suffix
    exploded_uri['parent_directory_no_timestamp'] = parent_directory_no_timestamp
    exploded_uri['parent_directory_date'] = parent_directory_date
    exploded_uri['parent_directory_time'] = parent_directory_time
    exploded_uri['parent_directory_datetime'] = parent_directory_date + '_' + parent_directory_time
    exploded_uri['parent_directory_no_timestamp_or_suffix'] = parent_directory_no_timestamp_or_suffix

    exploded_uri['drive'] = drive
    exploded_uri['drive_no_slash'] = drive_no_slash
    exploded_uri['post_drive_path'] = post_drive_path
    exploded_uri['post_drive_dir_name_and_file_root'] = post_drive_dir_name_and_file_root
    exploded_uri['fragments'] = fragments
    exploded_uri['path_directories'] = path_directories

    return exploded_uri


def suri(input_uri, input_string):
    '''Shortcut function to insert_string_before_ext'''
    return insert_string_before_ext(input_uri, input_string)


def insert_string_before_ext(input_uri, input_string):
    # The following helper functions are useful for quickly creating temporary files that resemble but dont overwrite
    # their input. The one confusing point i have so far is that calling this on a folder creates a string representing
    # a subfolder, not an in-situ new folder.

    # split_uri = os.path.splitext(input_uri)
    # return os.path.join(split_uri[0] + '_' + str(input_string) + split_uri[1])

    if input_string:
        split_uri = os.path.splitext(input_uri)
        if split_uri[1]:
            output_uri = split_uri[0] + '_' + str(input_string) + split_uri[1]
        else:
            output_uri = split_uri[0] + str(input_string)
        return output_uri
    else:
        return input_uri


def ruri(input_uri):
    '''Shortcut function to insert_random_string_before_ext'''
    return insert_random_string_before_ext(input_uri)


def insert_random_string_before_ext(input_uri):
    split_uri = os.path.splitext(input_uri)
    if split_uri[1]:
        output_uri = split_uri[0] + '_' + random_string() + split_uri[1]
    else:
        # If it's a folder, just tack it onto the end
        output_uri = split_uri[0] + '_' + random_string()
    return output_uri


def rsuri(input_uri, input_string):
    return insert_string_and_random_string_before_ext(input_uri, input_string)


def insert_string_and_random_string_before_ext(input_uri, input_string):
    split_uri = os.path.splitext(input_uri)
    if split_uri[1]:
        output_uri = split_uri[0] + '_' + str(input_string) + '_' + random_string() + split_uri[1]
    else:
        output_uri = split_uri[0] + '_' + str(input_string) + '_' + random_string()
    return output_uri





def create_dirs(list_of_folders):
    print('Deprecated. Use create_directories.')
    if type(list_of_folders) is str:
        list_of_folders = [list_of_folders]

    for folder in list_of_folders:
        try:
            os.makedirs(folder, exist_ok=True)
        except:
            raise NameError('create_dirs() failed to make ' + folder)

def remove_dirs(list_of_folders, safety_check=''):
    if isinstance(list_of_folders, str):
        list_of_folders = [list_of_folders]
    if safety_check == 'delete':
        if list_of_folders is str:
            list_of_folders = list(list_of_folders)
        for folder in list_of_folders:
            if folder == '':
                raise NameError('remove_dirs() told to remove current directory (\'\'). This is not allowed.')
            if folder == '/' or folder == '\\' or folder == '\\\\' or folder == '..' or folder == '.' or '*' in folder:
                raise NameError('remove_dirs() given a protected symbol. This is not allowed.')
            if os.path.exists(folder):
                try:
                    shutil.rmtree(folder, ignore_errors=True)
                except:
                    raise NameError('remove_dirs() failed to remove ' + folder)
    else:
        raise NameError('remove_dirs() called but saftety_check did not equal \"delete\"')

def execute_2to3_on_folder(input_folder, do_write=False):
    python_files = hb.list_filtered_paths_recursively(input_folder, include_extensions='.py')

    print ('execute_2to3_on_folder found ' + str(python_files))

    for file in python_files:
        if do_write:
            command = '2to3 -w ' + file
        else:
            command  = '2to3 ' + file
        system_results = os.system(command)
        print (system_results)

def execute_3to2_on_folder(input_folder, filenames_to_exclude=None, do_write=False):
    print ('filenames_to_exclude', filenames_to_exclude)
    python_files = list_filtered_paths_recursively(input_folder, depth=1, include_extensions='.py', exclude_strings=filenames_to_exclude)

    print (python_files)

    python_3_scripts_dir = 'c:/Anaconda363/scripts'
    sys.path.extend(python_3_scripts_dir)

    for file in python_files:
        if do_write:
            command = '3to2.py -w ' + file
        else:
            command  = '3to2.py ' + file
        system_results = os.system(command)
        print (system_results)





def walklevel(some_dir, level=1):
    some_dir = some_dir.rstrip(os.path.sep)
    assert os.path.isdir(some_dir)
    num_sep = some_dir.count(os.path.sep)
    for root, dirs, files in os.walk(some_dir):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + level <= num_sep_this:
            del dirs[:]

def list_filtered_dirs_recursively(input_dir, include_strings=None, depth=9999):
    if not include_strings:
        include_strings = []
    output_dirs = []

    for cur_dir, dirs_present, files_present in hb.walklevel(input_dir, depth):
        for dir_ in dirs_present:
            if len(include_strings) > 0:
                if any(specific_string in os.path.join(cur_dir, dir_) for specific_string in include_strings):
                    output_dirs.append(dir_)
            else:
                output_dirs.append(dir_)
    return output_dirs

def get_size_of_list_of_file_paths(input_list):
    """Return an ordered dict (no longer OrderedDict from collections cause dicts are not ordered as of 3.6)
     with path-name as key and filesize as value. Return None if file not found."""

    sizes = {}
    for path in input_list:
        try:
            size = os.stat(path).st_size
            sizes[path] = size
        except:
            sizes[path] = None

    return sizes


# TODOO Collapse this with recursive?
def list_filtered_paths_nonrecursively(input_folder, include_strings=None, include_extensions=None, exclude_strings=None, exclude_extensions=None, return_only_filenames=False):
    # NOTE: the filter strings can be anywhere in the path, not just the filename.
    if not hb.path_exists(input_folder):
        raise FileNotFoundError('The input folder does not exist: ' + input_folder)
    # ONLY CHANGE
    depth = 1

    # Convert filters to lists
    if include_strings is None:
        include_strings = []
    elif type(include_strings) == str:
        include_strings = [include_strings]
    elif type(include_strings) != list:
        raise TypeError('Must be string or list.')
    if include_extensions is None:
        include_extensions = []
    elif type(include_extensions) == str:
        include_extensions = [include_extensions]
    elif type(include_extensions) != list:
        raise TypeError('Must be string or list.')

    if exclude_strings is None:
        exclude_strings = []
    elif type(exclude_strings) == str:
        exclude_strings = [exclude_strings]
    elif type(exclude_strings) != list:
        raise TypeError('Must be string or list.')

    if exclude_extensions is None:
        exclude_extensions = []
    elif type(exclude_extensions) == str:
        exclude_extensions = [exclude_extensions]
    elif type(exclude_extensions) != list:
        raise TypeError('Must be string or list.')

    iteration_count = 0
    files = []
    for current_folder, folders_present, files_present in os.walk(input_folder):
        if depth is not None:
            if iteration_count >= depth: # CURRENTLY NOT DEACTIVATED because i messed up the logic where the break would end early.
                # NOTE that this only counts the times os.walk is called. Each call may have tons of files. Iterations here are more similar to search depth.
                # Also note this just terminates the walk, missing things that come later in the call.
                return files
        iteration_count += 1
        for filename in files_present:

            include = False
            if not (include_strings or include_extensions):
                include = True
            else:
                if include_strings:
                    if include_extensions:
                        if any(specific_string in os.path.join(current_folder, filename) for specific_string in include_strings) \
                                and any(filename.endswith(specific_extension) for specific_extension in include_extensions) \
                                and not any(specific_string in os.path.join(current_folder, filename) for specific_string in exclude_strings) \
                                and not any(filename.endswith(specific_extension) for specific_extension in exclude_extensions):
                            include = True
                    else:
                        if any(specific_string in filename for specific_string in include_strings):
                            include = True
                else:
                    if include_extensions:
                        if any(filename.endswith(specific_extension) for specific_extension in include_extensions) \
                                and not any(filename.endswith(specific_extension) for specific_extension in exclude_extensions):
                            include = True

            for exclude_string in exclude_strings:
                if exclude_string in os.path.join(current_folder, filename):
                    include = False

            for exclude_extension in exclude_extensions:
                if exclude_extension == os.path.splitext(filename)[1]:
                    include = False

            if include:
                if return_only_filenames:
                    files.append(filename)
                else:
                    files.append(os.path.join(current_folder, filename))
    return files

def split_path_by_timestamp(input_path):
    """Checks a file for having either a 3-part (long) or 2-part (short) timestamp. If found, returns a tuple of (path_before_timestamp, timestamp, extension
     For a timestamp to be valid, it must end in something of the form either for LONGFORM: 20180101_120415_123asd
     or SHORTFORM 20180101_120415
     """
    parent_dir, last_element_in_path = os.path.split(input_path)
    last_element_split = last_element_in_path.split('_')

    pre_extension, extension = os.path.splitext(last_element_split[-1])

    if extension:
        last_element_split[-1] = pre_extension

    # Generate a list where the last three elements are the timestamp elements and everything before is False
    test_split_elements_shortform_intable = list(range(len(last_element_split)))
    test_split_elements_longform_intable = list(range(len(last_element_split)))

    has_short_timestamp = False
    has_long_timestamp = False

    # Test if the last elements are intable FOR SHORTFORM
    for c, i in enumerate(last_element_split):
        try:
            int(i)
            test_split_elements_shortform_intable[c] = i
        except:
            test_split_elements_shortform_intable[c] = False

    # Test if the last elements are intable FOR LONGFORM
    for c, i in enumerate(last_element_split):
        try:
            int(i)
            test_split_elements_longform_intable[c] = i
        except:
            if len(i) == 6:
                try:
                    int(i[0:3])
                    test_split_elements_longform_intable[c] = i
                except:
                    test_split_elements_longform_intable[c] = False
            else:
                test_split_elements_longform_intable[c] = False

    # Test for shortform validity of last 2 elements
    shortform_final_result = []
    if test_split_elements_shortform_intable[-2] is not False:
        if 18000101 < int(test_split_elements_shortform_intable[-2]) < 30180101:
            shortform_final_result.append(True)
        else:
            shortform_final_result.append(False)
    if test_split_elements_shortform_intable[-1] is not False:
        if 0 <= int(test_split_elements_shortform_intable[-1]) <= 245999:
            shortform_final_result.append(True)
        else:
            shortform_final_result.append(False)

    # Test for longform validity of last 2 elements
    longform_final_result = []
    if test_split_elements_longform_intable[-3] is not False:
        if 18000101 < int(test_split_elements_longform_intable[-3]) < 30180101:
            longform_final_result.append(True)
        else:
            longform_final_result.append(False)
    if test_split_elements_longform_intable[-2] is not False:
        if 0 <= int(test_split_elements_longform_intable[-2]) <= 245999:
            longform_final_result.append(True)
        else:
            longform_final_result.append(False)
    if test_split_elements_longform_intable[-1] is not False:
        if 0 <= int(test_split_elements_longform_intable[-1][0:3]) <= 999:
            longform_final_result.append(True)
        else:
            longform_final_result.append(False)

    if shortform_final_result == [True, True]:
        has_short_timestamp = True
    if longform_final_result == [True, True, True]:
        has_long_timestamp = True

    if has_short_timestamp and has_long_timestamp:
         raise NameError('WTF?')
    if not has_short_timestamp and not has_long_timestamp:
        return None

    if has_short_timestamp:
        timestamp = '_'.join(last_element_split[-2:])
        return os.path.join(parent_dir, '_'.join(last_element_split[0: -2])), timestamp, extension

    if has_long_timestamp:
        timestamp = '_'.join(last_element_split[-3:])
        return os.path.join(parent_dir, '_'.join(last_element_split[0: -3])), timestamp, extension


def get_most_recent_timestamped_file_in_dir(input_dir, pre_timestamp_string=None, include_extensions=None, recursive=False):
    if recursive:
        paths_list = list_filtered_paths_recursively(input_dir, pre_timestamp_string, include_extensions=include_extensions)
    else:
        paths_list = list_filtered_paths_nonrecursively(input_dir, pre_timestamp_string, include_extensions=include_extensions)

    sorted_paths = {}
    for path in paths_list:
        r = split_path_by_timestamp(path)
        sorted_paths[r[1]] = r[0] + r[1] + r[2]



    print ('NEEDS MINOR FIXING FOR get_most_recent_timestamped_file_in_dir')
    sorted_return_list = sorted(sorted_paths)
    if len(sorted_return_list) > 0:
        most_recent_key = sorted_return_list[-1]
        to_return = sorted_paths[most_recent_key]
    else:
        to_return = []

    to_return = '_'.join(to_return)
    return to_return


def list_filtered_paths_recursively(input_folder, include_strings=None, include_extensions=None, exclude_strings=None, exclude_extensions=None, return_only_filenames=False, depth=50000, only_most_recent=False):
    # NOTE: the filter strings can be anywhere in the path, not just the filename.
    # TODO MASSIVE BUG: depth, even at 50000, will stop well before 50000. 12500 in the seals case and i don't know why.
    """If only_most_recent is True, will analyze time stampes and only return similar-named files with the most recent."""

    # Convert filters to lists
    if include_strings is None:
        include_strings = []
    elif type(include_strings) == str:
        include_strings = [include_strings]
    elif type(include_strings) != list:
        raise TypeError('Must be string or list.')

    if include_extensions is None:
        include_extensions = []
    elif type(include_extensions) == str:
        include_extensions = [include_extensions]
    elif type(include_extensions) != list:
        raise TypeError('Must be string or list.')

    if exclude_strings is None:
        exclude_strings = []
    elif type(exclude_strings) == str:
        exclude_strings = [exclude_strings]
    elif type(exclude_strings) != list:
        raise TypeError('Must be string or list.')

    if exclude_extensions is None:
        exclude_extensions = []
    elif type(exclude_extensions) == str:
        exclude_extensions = [exclude_extensions]
    elif type(exclude_extensions) != list:
        raise TypeError('Must be string or list.')
    iteration_count = 0
    files = []
    for current_folder, folders_present, files_present in os.walk(input_folder):
        if depth is not None:
            if iteration_count >= depth: # CURRENTLY NOT DEACTIVATED because i messed up the logic where the break would end early.
                # NOTE that this only counts the times os.walk is called. Each call may have tons of files. Iterations here are more similar to search depth.
                # Also note this just terminates the walk, missing things that come later in the call.
                return files
        iteration_count += 1
        for filename in files_present:
            include = False
            if not (include_strings or include_extensions):
                include = True
            else:
                if include_strings:
                    if include_extensions:
                        if any(specific_string in os.path.join(current_folder, filename) for specific_string in include_strings) \
                                and any(filename.endswith(specific_extension) for specific_extension in include_extensions) \
                                and not any(specific_string in os.path.join(current_folder, filename) for specific_string in exclude_strings) \
                                and not any(filename.endswith(specific_extension) for specific_extension in exclude_extensions):
                            include = True
                    else:
                        if any(specific_string in filename for specific_string in include_strings):
                            include = True
                else:
                    if include_extensions:
                        if any(filename.endswith(specific_extension) for specific_extension in include_extensions) \
                                and not any(filename.endswith(specific_extension) for specific_extension in exclude_extensions):
                            include = True

            for exclude_string in exclude_strings:
                if exclude_string in os.path.join(current_folder, filename):
                    include = False

            for exclude_extension in exclude_extensions:
                if exclude_extension == os.path.splitext(filename)[1]:
                    include = False

            if include:
                if return_only_filenames:
                    files.append(filename)
                else:
                    files.append(os.path.join(current_folder, filename))

            if only_most_recent is True:
                print ('NYI only_most_recent')
                # final_files = []
                # for file in files:
                #     input_dir = os.path.split(file)[0]
                #     pre_timestamp_string, unused_timestamp = hb.get_pre_timestamp_file_root(file)
                #     most_recent = get_most_recent_timestamped_file_in_dir(input_dir, pre_timestamp_string=pre_timestamp_string, include_extensions=None)
                #     final_files.append(most_recent)
                # files = final_files
    return files
# Example Usage
# input_folder = 'G:\\IONE-Old\\NATCAP\\bulk_data\\worldclim\\baseline\\30s'
# pp(get_list_of_file_uris_recursively(input_folder, '.bil'))



# TODOO get rid of all uris
def unzip_file(input_uri, output_folder=None, verbose=True):
    'Unzip file in place. If no output folder specified, place in input_uris folder'
    if not output_folder:
        output_folder = os.path.join(os.path.split(input_uri)[0], os.path.splitext(input_uri)[0])
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    fh = open(input_uri, 'rb')
    z = zipfile.ZipFile(fh)
    for name in z.namelist():
        if verbose:
            hb.pp(name, output_folder)
        z.extract(name, output_folder)
    fh.close()


def unzip_folder(input_folder, output_folder=None, verbose=True):
    if not output_folder:
        output_folder = input_folder
    input_files = os.listdir(input_folder)
    for i in range(len(input_files)):
        input_uri = os.path.join(input_folder, input_files[i])
        unzip_file(input_uri, output_folder, verbose)


def zip_files_from_dir_by_filter(input_dir, zip_uri, include_strings=None, include_extensions=None, exclude_strings=None, exclude_extensions=None, return_only_filenames=False):

    "FLATTENS into target zip"
    if not os.path.exists(input_dir):
        raise NameError('File not found: ' + str(input_dir))
    if not os.path.splitext(zip_uri)[1] == '.zip':
        raise NameError('zip_uri must end with zip')

    zipf = zipfile.ZipFile(zip_uri, 'w', zipfile.ZIP_DEFLATED)
    for i in hb.list_filtered_paths_recursively(input_dir, include_strings, include_extensions, exclude_strings, exclude_extensions, return_only_filenames):
        zipf.write(i, os.path.basename(i))

    zipf.close()


def copy_files_from_dir_by_filter(input_dir, dst_dir, include_strings=None, include_extensions=None, exclude_strings=None, exclude_extensions=None, return_only_filenames=False):
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)

    for i in hb.list_filtered_paths_recursively(input_dir, include_strings, include_extensions, exclude_strings, exclude_extensions, return_only_filenames):
        filename = os.path.split(i)[1]
        new_uri = os.path.join(dst_dir, filename)

        shutil.copy(i, new_uri)


def copy_files_from_dir_by_filter_preserving_dir_structure(input_dir, dst_dir, include_strings=None, include_extensions=None, exclude_strings=None, exclude_extensions=None, return_only_filenames=False):
    print ('possibly deprecated for copy_file_tree_to_new_root')

    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)

    for uri in hb.list_filtered_paths_recursively(input_dir, include_strings, include_extensions, exclude_strings, exclude_extensions, return_only_filenames):
        modified_uri = uri.replace(input_dir, dst_dir, 1)

        os.makedirs(os.path.split(modified_uri)[0], exist_ok=True)
        shutil.copy(uri, modified_uri)

def zip_files_from_dir_by_filter_preserving_dir_structure(input_dir, zip_dst_uri, include_strings=None, include_extensions=None, exclude_strings=None, exclude_extensions=None, return_only_filenames=False):
    # PRESERVES dir structure inside zip.
    temp_dir = input_dir + '_temp'
    copy_files_from_dir_by_filter_preserving_dir_structure(input_dir, temp_dir, include_strings, include_extensions, exclude_strings, exclude_extensions, return_only_filenames)

    # Because i couldnt figure out how to zip to a non curdir, i had this hack
    new_zip_dst_uri = os.path.split(zip_dst_uri)[1]
    zip_dir(temp_dir, zip_dst_uri)

    # remove temporary dir only, because now it's in a zip
    shutil.rmtree(temp_dir, ignore_errors=True)

def zip_dir(input_dir, zip_uri):
    if not os.path.exists(input_dir):
        raise NameError('File not found: ' + str(input_dir))
    if not os.path.splitext(zip_uri)[1] == '.zip':
        raise NameError('zip_uri must end with zip')

    zipf = zipfile.ZipFile(zip_uri, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            destination_relative_to_zip_archive_path = os.path.join(root, file).replace(input_dir, '')
            current_file_to_zip_path = os.path.join(root, file)
            print ('Zipping ' + current_file_to_zip_path + ' to ' + destination_relative_to_zip_archive_path)
            zipf.write(current_file_to_zip_path, destination_relative_to_zip_archive_path)

    zipf.close()


def zip_list_of_paths(paths_list, zip_path):
    if not os.path.splitext(zip_path)[1] == '.zip':
        raise NameError('zip_path must end with zip')

    zipf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
    for i in paths_list:
        print ('Zipping ' + str(i))
        if not os.path.exists(i):
            raise NameError('File not found when zipping: ' + str(i))
        zipf.write(i, os.path.basename(i))

    zipf.close()



















def list_files_in_dir_recursively(input_folder, filter_strings=None, filter_extensions=None, max_folders_analyzed=None, return_only_filenames=False):
    print ('Function deprecated (list_files_in_dir_recursively). Consider using list_filtered_paths_recursively.')
    if type(filter_strings) == str:
        filter_strings = [filter_strings]
    if type(filter_extensions) == str:
        filter_extensions = [filter_extensions]

    iteration_count = 0
    files = []
    for current_folder, folders_present, files_present in os.walk(input_folder):
        iteration_count += 1
        if max_folders_analyzed is not None:
            if iteration_count > max_folders_analyzed:
                # NOTE that this only counts the times os.walk is called. Each call may have tons of files. Iterations here are more similar to search depth.
                return files

        for filename in files_present:
            include = False
            if filter_strings:
                if filter_extensions:
                    if any(specific_string in filename for specific_string in filter_strings) \
                            and any(filename.endswith(specific_extension) for specific_extension in filter_extensions):
                        include = True
                else:
                    if any(specific_string in filename for specific_string in filter_strings):
                        include = True
            else:
                if filter_extensions:
                    if any(filename.endswith(specific_extension) for specific_extension in filter_extensions):
                        include = True
                else:
                    include = True

            if include:
                if return_only_filenames:
                    files.append(filename)
                else:
                    files.append(os.path.join(current_folder, filename))
    return files

# TODOO Consider again removing this, noting that the list_files_in_dir seems more robust.
def list_dirs_in_dir_recursively(input_folder, filter_strings=None, max_folders_analyzed=None, return_only_filenames=False):
    if type(filter_strings) == str:
        filter_strings = [filter_strings]
    if type(filter_strings) == str:
        filter_strings = [filter_strings]

    iteration_count = 0
    folders = []
    for current_folder, folders_present, files_present in os.walk(input_folder):
        iteration_count += 1
        if max_folders_analyzed is not None:
            if iteration_count > max_folders_analyzed:
                # NOTE that this only counts the times os.walk is called. Each call may have tons of files. Iterations here are more similar to search depth.
                return folders

        for current_folder in [current_folder]:
            include = False
            if filter_strings:
                if any(specific_string in current_folder for specific_string in filter_strings):
                    include = True
            else:
                include = True

            folders.append(current_folder)
    return folders

def assert_file_existence(input_path):
    if not os.path.exists(input_path):
        raise FileNotFoundError('hb.assert_file_existence could not find ' + str(input_path))


def swap_filenames(left_uri, right_uri):
    left_temp_uri = suri(left_uri, 'temp')
    os.rename(left_uri, left_temp_uri)
    os.rename(right_uri, left_uri)
    os.rename(left_temp_uri, right_uri)

def displace_file(src_path, to_displace_path, displaced_path=None, displaced_string=None, delete_original=False, raise_on_fails=False):
    # Copies to_displace_path to displaced_path, then moves src_path to to_displace_path, then deletes displaced_path if delete_original is True.
    if displaced_string is None:
        displaced_string = 'displaced'
    if not displaced_path:
        displaced_path = hb.rsuri(to_displace_path, displaced_string)
    
    if raise_on_fails:
        os.rename(to_displace_path, displaced_path)
        os.rename(src_path, to_displace_path)
    else:
        try:
            os.rename(to_displace_path, displaced_path)
        except:
            hb.log('Failed to rename ' + to_displace_path + ' to ' + str(displaced_path))
            
        try:        
            os.rename(src_path, to_displace_path)
        except:
            hb.log('Failed to rename ' + src_path + ' to ' + str(to_displace_path))
        
    if delete_original:
        os.remove(displaced_path)

def path_rename(input_path, new_path, skip_if_exists=False):
    if not skip_if_exists:
        try:
            os.rename(input_path, new_path)
        except:
            raise NameError('Failed to rename ' + input_path + ' to ' + str(new_path))
    else:
        if not os.path.exists(new_path):
            try:
                os.rename(input_path, new_path)
            except:
                raise NameError('Failed to rename ' + input_path + ' to ' + new_path)
        else:
            'we good'
    
def rename_with_overwrite(src_path, dst_path):
    if os.path.exists(dst_path):
        hb.remove_path(dst_path)
    os.rename(src_path, dst_path)

def replace_file(src_uri, dst_uri, delete_original=True):
    if os.path.exists(dst_uri):
        if delete_original:
            os.remove(dst_uri)
        else:
            os.rename(dst_uri, rsuri(hb.quad_split_path(dst_uri[2]), 'replaced_by_' + src_uri))

    try:
        os.rename(src_uri, dst_uri)
    except:
        raise Exception('Failed to rename ' + src_uri + ' to ' + dst_uri)


def replace_ext(input_uri, desired_ext):
    if os.path.splitext(input_uri)[1]:
        if desired_ext.startswith('.'):
            modified_uri = os.path.splitext(input_uri)[0] + desired_ext
        else:
            modified_uri = os.path.splitext(input_uri)[0] + '.' + desired_ext
    else:
        raise NameError('Cannot replace extension on the input_uri given because it did not have an extension.')
    return modified_uri

def copy_shapefile(input_uri, output_uri):
    # Because shapefiles have 4+ separate files, use this to smartly copy all of the ones that exist based on versions of input uri.
    for ext in hb.config.possible_shapefile_extensions:
        potential_uri = hb.replace_ext(input_uri, ext)
        if os.path.exists(potential_uri):
            potential_output_uri = hb.replace_ext(output_uri, ext)
            shutil.copyfile(potential_uri, potential_output_uri)

def rename_shapefile(input_uri, output_uri):
    # Because shapefiles have 4+ separate files, use this to smartly rename all of the ones that exist based on versions of input uri.
    for ext in hb.config.possible_shapefile_extensions:
        potential_uri = hb.replace_ext(input_uri, ext)
        if os.path.exists(potential_uri):
            potential_output_uri = hb.replace_ext(output_uri, ext)
            os.rename(potential_uri, potential_output_uri)

def remove_shapefile(input_uri):
    # Because shapefiles have 4+ separate files, use this to smartly rename all of the ones that exist based on versions of input uri.
    for ext in hb.config.possible_shapefile_extensions:
        potential_uri = hb.replace_ext(input_uri, ext)
        if os.path.exists(potential_uri):
            os.remove(potential_uri)

def replace_shapefile(src_uri, dst_uri):
    for ext in hb.config.possible_shapefile_extensions:
        potential_uri = hb.replace_ext(src_uri, ext)
        if os.path.exists(potential_uri):
            potential_output_uri = hb.replace_ext(dst_uri, ext)
            os.replace(potential_uri, potential_output_uri)

def remove_temporary_files():
    for uri_to_delete in hb.config.uris_to_delete_at_exit:
        try:
            if os.path.splitext(uri_to_delete)[1] == '.shp':
                remove_shapefile(uri_to_delete) 
            elif os.path.isdir(uri_to_delete):
                shutil.rmtree(uri_to_delete, ignore_errors=True)
            else:
                os.remove(uri_to_delete)
            # L.debug('Deleting temporary file: ' + str(uri_to_delete))
        except:
            pass
            # L.debug('Couldn\'t remove temporary file: ' + str(uri_to_delete))
atexit.register(remove_temporary_files)

def remove_uri_at_exit(input):
    if isinstance(input, str):
        hb.config.uris_to_delete_at_exit.append(input)
    elif isinstance(input, hb.ArrayFrame):
        hb.config.uris_to_delete_at_exit.append(input.path)

# TODOO consider if this should be named remove_path or path_remove or path.remove
def path_remove(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    filename = os.path.join(root, name)
                    os.chmod(filename, stat.S_IWRITE)
                    os.remove(filename)
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(path)
        else:
            os.remove(path)
    else:
        'couldnt find path, but no worries, we good.'

def remove_path(path):
    hb.path_remove(path)
        # if os.path.isdir(path):
    #     shutil.rmtree(path, ignore_errors=True)
    # else:
    #     shutil.remove

    # if os.path.isdir(path):
    #     os.rmdir(path)
    # else:
    #     os.remove(path)
    # try:
    #     os.remove(path)
    # except:
    #     'Probably just didnt exist.'

def path_move(src_path, dst_path):
    """
    
    This will follow the shutil approach about moving dirs versus files.
    
     Recursively move a file or directory to another location. This is
    similar to the Unix "mv" command. Return the file or directory's
    destination.

    If the destination is a directory or a symlink to a directory, the source
    is moved inside the directory. The destination path must not already
    exist.

    If the destination already exists but is not a directory, it may be
    overwritten depending on os.rename() semantics.
    
    
    """
    
    hb.move_file(src_path, dst_path)
    
def move_file(source_path, destination_path):
    """
    Move a file from source_path to destination_path CREATING ANY NECESSARY PATHS.

    :param source_path: The original location of the file.
    :param destination_path: The location to move the file to.
    """
    hb.create_directories(destination_path)
    shutil.move(source_path, destination_path)

def remove_at_exit(uri):
    hb.config.uris_to_delete_at_exit.append(uri)

def get_path_to_right_of_dir(input_path, target_dir):
    """Return the path to the right of the target_dir in the input_path. If the target_dir is not in the input_path, return None."""
    if target_dir in input_path:
        with_leading = input_path.split(target_dir)[1]
        
        # remove leading slashes
        while with_leading[0] == '/' or with_leading[0] == '\\':
            with_leading = with_leading[1:]
            
        return with_leading
            
    else:
        return None
    
    
    
# TODOO clarify when have path_<function name>. Should i make it a module?
def path_rename_change_dir(input_path, new_dir):
    """Change the directory of a file given its input path, preserving the name. NOTE does not do anything to the file"""
    return os.path.join(new_dir, os.path.split(input_path)[1])


# TODOO clarify when have path_<function name>. Should i make it a module?
def path_rename_change_dir_at_depth(input_path, new_dir, depth, verbose=False):
    """Change the directory of a file given its input path, preserving the name. NOTE does not do anything to the file.
    Instead of replacing the directory immediately to the left of the path, do it after depth number of directories up the directory tree.
    """
    input_path = pathlib.Path(input_path)


    if depth > 0:
        depth += 1

    new_dir = pathlib.Path(new_dir)

    # LEARNING POINT fun use of pathlib on a pathlib.parts object with the * operator.
    new_path = pathlib.Path(new_dir) / pathlib.Path(*input_path.parts[-depth:])
    if verbose:
        hb.log('  Searched for path ' + str(input_path) + ' and found ' + str(new_path) + ' via path_rename_change_dir_at_depth.')

    # LEARNING POINT, Gdal checks for a string object, so it's got to be return here as a string.
    return str(new_path)


# def file_root(input_path):
#     return path_file_root(input_path)


# def path_file_root(input_path):
#     # if isinstance(input_path, hb.InputPath):
#     #     input_path = str(input_path)
#     return os.path.splitext(os.path.split(input_path)[1])[0]

def path_filename(input_path):
    if isinstance(input_path, hb.InputPath):
        input_path = str(input_path)
    return os.path.split(input_path)[1]

def path_dir(input_):
    """If input is a dir, just return it. if it's a file, return it's parent dir."""

    if os.path.isdir(input_):
        return input_
    else:
        left_split = os.path.split(input_)[0]
        if left_split:
            return left_split
        else:
            raise NameError('Tried to path_dir() on ' + str(input_) + ' but something went wrong.')

def get_flex_as_path(input_flex, raise_file_exists_errors=True):
    """Return a path-string from input_flex. If its an arrayframe it will just return the path attribute, while if its a string it will test for file existence."""
    if isinstance(input_flex, str):
        if os.path.exists(input_flex):
            return input_flex
        else:
            if raise_file_exists_errors:
                 raise NameError('get_flex_as_path given ' + str(input_flex) + ' which was interpreted as a string-path but it doesnt exist in the file system.')
            else:
                return input_flex
    elif isinstance(input_flex, hb.ArrayFrame):
        return input_flex.path

def copy_file_tree_to_new_root(input_dir, root_dir, **kwargs):
    print('Not sure how/if this is different than copy_files_from_dir_by_filter_preserving_dir_structure')

    include_strings = kwargs.get('include_strings', None)
    include_extensions = kwargs.get('include_extensions', None)
    exclude_strings = kwargs.get('exclude_strings', None)
    exclude_extensions = kwargs.get('exclude_extensions', None)
    return_only_filenames = kwargs.get('return_only_filenames', False)
    depth = kwargs.get('depth', 5000)
    only_most_recent = kwargs.get('only_most_recent', False)
    verbose = kwargs.get('verbose', False)

    paths = hb.list_filtered_paths_recursively(input_dir,
        include_strings=include_strings,
        include_extensions=include_extensions,
        exclude_strings=exclude_strings,
        exclude_extensions=exclude_extensions,
        return_only_filenames=return_only_filenames,
        depth=depth,
        only_most_recent=only_most_recent,
    )

    for cur_dir, dirs_in_dir, files_in_dir in os.walk(input_dir):
        extra_dirs = cur_dir.replace(input_dir, '')
        output_dir = root_dir + extra_dirs
        for file in files_in_dir:
            target_path = os.path.join(cur_dir, file)
            output_path = os.path.join(output_dir, file)

            if target_path in paths:
                if verbose:
                    hb.log('copying from ' + str(target_path) + ' to ' + str(output_path))

                hb.copy_shutil_flex(target_path, output_path)
            else:
                if verbose:
                    hb.log('skipped coppying ' + str(target_path) + ' due to exclusion rule.')
def path_abs(input_relative_path):
    try:
        return os.path.abspath(str(input_relative_path))
    except:
        return "Failed path_abs on " + str(input_relative_path)


def path_copy(src, dst, copy_tree=True, displace_overwrites=False, overwrite=True, verbose=False):
    copy_shutil_flex(src, dst, copy_tree=copy_tree, displace_overwrites=displace_overwrites, overwrite=overwrite, verbose=verbose)

def copy_shutil_flex(src, dst, copy_tree=True, displace_overwrites=False, overwrite=True, verbose=False):
    """Helper util that allows copying of files or dirs in same function"""
    if os.path.isdir(src):
        if verbose:
            hb.log('Copying directory ' + str(src) + ' to ' + str(dst))
        if not os.path.exists(dst):
            hb.create_directories(dst)
        if copy_tree:
            copy_shutil_copytree(src, dst)
        else:
            dst = os.path.join(dst, os.path.basename(src))
            shutil.copyfile(src, dst)
    else:
        dst_dir = os.path.split(dst)[0]
        if not os.path.exists(dst_dir):
            hb.create_directories(dst_dir)
        if displace_overwrites:
            if os.path.exists(dst):
                hb.rename_with_overwrite(dst, hb.rsuri(dst, 'displaced'))
            else:
                'meh'
        elif overwrite:
            if os.path.exists(dst):
                os.remove(dst)
        shutil.copyfile(src, dst)
        if verbose:
            hb.log('Copying file ' + str(src) + ' to ' + str(dst))

def copy_shutil_copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            distutils.dir_util.copy_tree(s, d)
            # shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

def replace_in_file_via_dict(input_path, replace_dict, output_path=None):
    """Replace all instances of keys in replace_dict with their values in the input_path file, writing to output_path.
    
    NOTE, that elements in replace_dict will be replaced in order, so is you need to modify something and then replace the modified
    thing, make sure the modification replacement happens first.
    
    """
    
    if not output_path:
        output_path = input_path
    with open(input_path, 'r') as file:
        filedata = file.read()
    for key in replace_dict:
        filedata = filedata.replace(key, replace_dict[key])
    with open(output_path, 'w') as file:
        file.write(filedata)


def replace_in_string_via_dict(input_string, replace_dict):
    for key in replace_dict:
        input_string = input_string.replace(key, replace_dict[key])
    return input_string


def add_lines_to_file(input_file, new_lines):
    with open(input_file, 'a') as file:
        for line in new_lines:
            file.write(line + '\n')

def add_file_to_file(input_file, new_file):
    with open(input_file, 'a') as file:
        with open(new_file, 'r') as new_file:
            file.write(new_file.read())
            
    


def path_replace_extension(input_path, new_extension):
    if not new_extension.startswith('.'):
        new_extension = '.' + new_extension
    return os.path.splitext(input_path)[0] + new_extension


def get_existing_path_from_nested_sources(input_path, project_flow_object=None, depth_to_keep=1, verbose=False):
    """Check the existing path, and then ever deeper nested data sources (And eventually, downloading from buckets) until it is found.
    IMPORTANT: Pass the project flow object if you want to look in project specific stuff, including e.g. model_base_data_dir

    depth_to_keep allows you to keep more than just the path name, but the nested structure
    """
    if hb.path_exists(input_path, verbose=verbose):
        return input_path
    elif project_flow_object is not None:
        if hb.path_exists(hb.path_rename_change_dir_at_depth(input_path, project_flow_object.project_base_data_dir, depth_to_keep, verbose=verbose), verbose=verbose):
            return hb.path_rename_change_dir_at_depth(input_path, project_flow_object.project_base_data_dir, depth_to_keep, verbose=verbose)
        elif hb.path_exists(hb.path_rename_change_dir_at_depth(input_path, project_flow_object.model_base_data_dir, depth_to_keep, verbose=verbose), verbose=verbose):
            return hb.path_rename_change_dir_at_depth(input_path, project_flow_object.model_base_data_dir, depth_to_keep, verbose=verbose)
        elif hb.path_exists(hb.path_rename_change_dir_at_depth(input_path, project_flow_object.model_base_data_dir, depth_to_keep, verbose=verbose), verbose=verbose):
            return hb.path_rename_change_dir_at_depth(input_path, project_flow_object.model_base_data_dir, depth_to_keep, verbose=verbose)
    else:

        if hb.path_exists(hb.path_rename_change_dir_at_depth(input_path, hb.BASE_DATA_DIR, depth_to_keep, verbose=verbose), verbose=verbose):
            return hb.path_rename_change_dir_at_depth(input_path, hb.BASE_DATA_DIR, depth_to_keep, verbose=verbose)
        elif hb.path_exists(hb.path_rename_change_dir_at_depth(input_path, hb.BULK_DATA_DIR, depth_to_keep, verbose=verbose), verbose=verbose):
            return hb.path_rename_change_dir_at_depth(input_path, hb.BULK_DATA_DIR, depth_to_keep, verbose=verbose)
        elif hb.path_exists(hb.path_rename_change_dir_at_depth(input_path, hb.EXTERNAL_BULK_DATA_DIR, depth_to_keep, verbose=verbose), verbose=verbose):
            return hb.path_rename_change_dir_at_depth(input_path, hb.EXTERNAL_BULK_DATA_DIR, depth_to_keep, verbose=verbose)
        # TODOO Here is where to add integration with searching online ecoshards or gdrive.
        raise NameError('Unable to rectify ' + input_path + ' using get_existing_path_from_nested_sources.')


def write_to_file(input_object, output_path):
    # hb.create_directories(output_path)
    s = str(input_object)
    with open(output_path, 'w', encoding="utf8") as fp:
        fp.write(s)

def read_path_as_string(input_path):
    with open(input_path, 'r') as file:
        data = str(file.read())
    return data

def read_path_as_list(input_path):
    with open(input_path, 'r') as file:
        data = file.readlines()
    return data

# def timer(msg=None, silent=False):
#     if hb.LAST_TIME_CHECK == 0.0:
#         hb.LAST_TIME_CHECK = time.time()
#     else:
#         if not msg:
#             msg = 'Elapsed'
#         if not silent:
#             print(str(msg) + ': ' + str(time.time() - hb.LAST_TIME_CHECK) + ' at time ' + str(hb.pretty_time()))
#         hb.LAST_TIME_CHECK = time.time()




# Print iterations progress
def print_progress_bar(iteration, total, prefix = '', suffix = '', decimals = 1, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    length = 20
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()

def convert_file_via_pandoc(input_path, output_path, verbose=False):

    command = f"pandoc -s \"{input_path}\" -o \"{output_path}\" --pdf-engine xelatec"

    if verbose:
        print(f"Running command {command}")

    os.system(command)

def convert_file_via_quarto(input_path, output_path, verbose=False):

    to_arg = str(os.path.splitext(output_path)[1])[1:]

    command = "quarto render \"" + input_path + "\" --output " + output_path + " --to " + to_arg
    # command = "quarto render \"" + input_path + "\" --to " + to_arg
    



    if verbose:
        print(f"Running command {command}")

    os.system(command)


def compile_exam_from_md(exam_template_path, question_bank_dir, output_filename, output_dir, number_of_variations=4, randomize=True, include_unrandomized=True, questions_to_include=None):
    import numpy as np
    if questions_to_include is None:
        questions_to_include = 'all'

    template_dict = hb.parse_template_path_to_dict(exam_template_path)
    hb.log(template_dict)
    header_dict = template_dict['Header']
    
    # Get filenames from header_dict
    test_bank_file_roots = [k for k, v in header_dict.items() if type(v) is dict]
    
    titlepage_dict = template_dict['Titlepage']
    titlepage_md_string = hb.parse_template_dict_to_titlepage_md_string(titlepage_dict)
    
    output_path = os.path.join(output_dir, output_filename)

    output_fileroot, output_filename_extension = os.path.splitext(output_filename)
    hb.create_directories(output_path)

    all_variation_answers = []

    if include_unrandomized:
        for is_key in (False, True):
            question_bank_path = question_bank_dir
            included_questions_md_string, current_answers = hb.make_exam_md_from_dicts(header_dict, question_bank_path, 1, False, is_key=is_key)
            # if len(current_answers) > 0:
            #     all_variation_answers.append(current_answers)
            title_page_variant_md_string = titlepage_md_string.replace('<^-version_number-^>', 'UNRANDOMIZED')
            output_string = title_page_variant_md_string + "<div style=\"page-break-after: always;\"></div>\n\n\\newpage" + included_questions_md_string

            if is_key:
                temp_md_path = output_fileroot + '_version_' + 'UNRANDOMIZED' +'_KEY.md'
                temp_output_path = output_fileroot + '_version_' + 'UNRANDOMIZED' +'_KEY' + output_filename_extension
                final_output_path = os.path.join(output_dir, output_fileroot + '_version_' + 'UNRANDOMIZED' +'_KEY' + output_filename_extension)
            else:
                temp_md_path = output_fileroot + '_version_' + 'UNRANDOMIZED'+'.md'
                temp_output_path = output_fileroot + '_version_' + 'UNRANDOMIZED' + output_filename_extension
                final_output_path = os.path.join(output_dir, output_fileroot + '_version_' + 'UNRANDOMIZED' + output_filename_extension)

            # output_md_path = hb.replace_ext(temp_md_path, '.md')
            hb.write_to_file(output_string, temp_md_path)
            hb.convert_file_via_quarto(temp_md_path, temp_output_path, verbose=True)

            hb.remove_path(temp_md_path)
            hb.rename_with_overwrite(temp_output_path, final_output_path)



    for variation_id in range(number_of_variations):    
        for is_key in (False, True):
            random_seed = variation_id
            included_questions_md_string, current_answers = hb.make_exam_md_from_dicts(header_dict, question_bank_path, random_seed, randomize, is_key=is_key)
            if len(current_answers) > 0:
                all_variation_answers.append(current_answers)
            title_page_variant_md_string = titlepage_md_string.replace('<^-version_number-^>', str(variation_id + 1))
            output_string = title_page_variant_md_string + "<div style=\"page-break-after: always;\"></div>\n\n\\newpage" + included_questions_md_string

            

            # variation_output_path = hb.suri(output_path, 'version_' + str(variation_id+1))

            if is_key:
                temp_md_path = output_fileroot + '_version_' + str(variation_id+1) +'_KEY.md'
                temp_output_path = output_fileroot + '_version_' + str(variation_id+1) +'_KEY' + output_filename_extension
                final_output_path = os.path.join(output_dir, output_fileroot + '_version_' + str(variation_id+1) +'_KEY' + output_filename_extension)
            else:
                temp_md_path = output_fileroot + '_version_' + str(variation_id+1) +'.md'
                temp_output_path = output_fileroot + '_version_' + str(variation_id+1) + output_filename_extension
                final_output_path = os.path.join(output_dir, output_fileroot + '_version_' + str(variation_id+1) + output_filename_extension)

            # output_md_path = hb.replace_ext(temp_md_path, '.md')
            hb.write_to_file(output_string, temp_md_path)
            hb.convert_file_via_quarto(temp_md_path, temp_output_path, verbose=True)

            hb.remove_path(temp_md_path)
            hb.rename_with_overwrite(temp_output_path, final_output_path)
            
    all_variation_answers.insert(0, list(range(1, len(all_variation_answers[0])+1)))
    all_variation_answers_t = np.array(all_variation_answers, dtype=object).T.tolist()
    new_row = np.array([''] + ['Version ' + str(i+1) for i in range(number_of_variations)])
    all_variation_answers_t = np.insert(all_variation_answers_t, 0, new_row, axis=0)
    hb.python_object_to_csv(all_variation_answers_t, os.path.join(output_dir, output_fileroot + '_COMBINED_KEY' + '.csv'), csv_type='2d_list')


def compile_exam_from_md_old(exam_template_path, question_bank_path, output_filename, output_dir, number_of_variations=4, randomize=True, questions_to_include=None):
    
    # TODOOO: Make it also optionally output an unrandomized version for troubleshooting.
    # TODOO: Idea, add boxes around questions that enable smart page breaks
    import numpy as np
    if questions_to_include is None:
        questions_to_include = 'all'

    template_dict = hb.parse_markdown_path_to_dict(exam_template_path)

    header_dict = template_dict['Header']

    titlepage_dict = template_dict['Titlepage']
    titlepage_md_string = hb.parse_dict_to_markdown_string(titlepage_dict)
    
    output_path = os.path.join(output_dir, output_filename)

    output_fileroot, output_filename_extension = os.path.splitext(output_filename)
    hb.create_directories(output_path)

    all_variation_answers = []

    for variation_id in range(number_of_variations):    
        for is_key in (False, True):
            random_seed = variation_id
            included_questions_md_string, current_answers = hb.make_exam_md_from_dicts(header_dict, question_bank_path, random_seed, randomize, is_key=is_key)
            if len(current_answers) > 0:
                all_variation_answers.append(current_answers)
            title_page_variant_md_string = titlepage_md_string.replace('<^-version_number-^>', str(variation_id + 1))
            output_string = title_page_variant_md_string + "<div style=\"page-break-after: always;\"></div>\n\n\\newpage" + included_questions_md_string

            

            # variation_output_path = hb.suri(output_path, 'version_' + str(variation_id+1))

            if is_key:
                temp_md_path = output_fileroot + '_version_' + str(variation_id+1) +'_KEY.md'
                temp_output_path = output_fileroot + '_version_' + str(variation_id+1) +'_KEY' + output_filename_extension
                final_output_path = os.path.join(output_dir, output_fileroot + '_version_' + str(variation_id+1) +'_KEY' + output_filename_extension)
            else:
                temp_md_path = output_fileroot + '_version_' + str(variation_id+1) +'.md'
                temp_output_path = output_fileroot + '_version_' + str(variation_id+1) + output_filename_extension
                final_output_path = os.path.join(output_dir, output_fileroot + '_version_' + str(variation_id+1) + output_filename_extension)

            # output_md_path = hb.replace_ext(temp_md_path, '.md')
            hb.write_to_file(output_string, temp_md_path)
            hb.convert_file_via_quarto(temp_md_path, temp_output_path, verbose=True)

            hb.remove_path(temp_md_path)
            hb.rename_with_overwrite(temp_output_path, final_output_path)
            
    all_variation_answers.insert(0, list(range(1, len(all_variation_answers[0])+1)))
    all_variation_answers_t = np.array(all_variation_answers, dtype=object).T.tolist()
    new_row = np.array([''] + ['Version ' + str(i+1) for i in range(number_of_variations)])
    all_variation_answers_t = np.insert(all_variation_answers_t, 0, new_row, axis=0)
    hb.python_object_to_csv(all_variation_answers_t, os.path.join(output_dir, output_fileroot + '_COMBINED_KEY' + '.csv'), csv_type='2d_list')

def parse_template_path_to_dict(input_path):


# def parse_header_dict_and_question_bank_dir_to_dict(header_dict, input_dir):
# def parse_template_path_to_dict(input_path):
    
    # Check header for filenames
    # filenames = [k for k, v in header_dict.items() if isinstance(v,)]
    
    output_dict = {}
    current_dict = output_dict
    with open(input_path, 'r', encoding="utf8") as fp:
        lines = fp.readlines()
        for line in lines:
            
            # Strip linebreaks at end of each line (is implied by list)
            if line[-1:] == '\n':
                line = line[:-1]
            if line != '':
                
                if line.startswith('#'):
                    in_header = True
                    if line.startswith('# '):
                        header_text = line.split('# ', 1)[1]
                        h1 = header_text                    
                        output_dict[h1] = {}
                        output_dict[h1]['^-text-^'] = []
                        current_dict = output_dict[h1]
                    if line.startswith('## '):
                        header_text = line.split('# ', 1)[1]
                        h2 = header_text                    
                        output_dict[h1][h2] = {} 
                        output_dict[h1][h2]['^-text-^'] = []
                        current_dict = output_dict[h1][h2]
                    if line.startswith('### '):
                        header_text = line.split('# ', 1)[1]
                        h3 = header_text                    
                        output_dict[h1][h2][h3] = {}
                        output_dict[h1][h2][h3]['^-text-^'] = []
                        current_dict = output_dict[h1][h2][h3]
                    if line.startswith('#### '):
                        header_text = line.split('# ', 1)[1]
                        h4 = header_text                    
                        output_dict[h1][h2][h3][h4]= {}
                        output_dict[h1][h2][h3][h4]['^-text-^'] = []
                        current_dict = output_dict[h1][h2][h3][h4]
                    if line.startswith('##### '):
                        header_text = line.split('# ', 1)[1]
                        h5 = header_text                    
                        output_dict[h1][h2][h3][h4][h5] = {}
                        output_dict[h1][h2][h3][h4][h5]['^-text-^'] = []
                        current_dict = output_dict[h1][h1][h2][h3][h4][h5]
                    if line.startswith('###### '):
                        header_text = line.split('# ', 1)[1]
                        h6 = header_text                    
                        output_dict[h1][h2][h3][h4][h5][h6] = {}
                        output_dict[h1][h2][h3][h4][h5][h6]['^-text-^'] = []
                        current_dict = output_dict[h1][h2][h3][h4][h5][h6]     
                else:
                    5
                    a = current_dict['^-text-^']
                    a.append(line)
                    # a = current_dict['^-text-^'].append(line)
                        

                # print(header_text)

    5
    return output_dict
  


def parse_markdown_path_to_dict_old(input_path):
    output_dict = {}
    current_dict = output_dict
    with open(input_path, 'r', encoding="utf8") as fp:
        lines = fp.readlines()
        for line in lines:
            
            # Strip linebreaks at end of each line (is implied by list)
            if line[-1:] == '\n':
                line = line[:-1]
            if line != '':
                
                if line.startswith('#'):
                    in_header = True
                    if line.startswith('# '):
                        header_text = line.split('# ', 1)[1]
                        h1 = header_text                    
                        output_dict[h1] = {}
                        output_dict[h1]['^-text-^'] = []
                        current_dict = output_dict[h1]
                    if line.startswith('## '):
                        header_text = line.split('# ', 1)[1]
                        h2 = header_text                    
                        output_dict[h1][h2] = {} 
                        output_dict[h1][h2]['^-text-^'] = []
                        current_dict = output_dict[h1][h2]
                    if line.startswith('### '):
                        header_text = line.split('# ', 1)[1]
                        h3 = header_text                    
                        output_dict[h1][h2][h3] = {}
                        output_dict[h1][h2][h3]['^-text-^'] = []
                        current_dict = output_dict[h1][h2][h3]
                    if line.startswith('#### '):
                        header_text = line.split('# ', 1)[1]
                        h4 = header_text                    
                        output_dict[h1][h2][h3][h4]= {}
                        output_dict[h1][h2][h3][h4]['^-text-^'] = []
                        current_dict = output_dict[h1][h2][h3][h4]
                    if line.startswith('##### '):
                        header_text = line.split('# ', 1)[1]
                        h5 = header_text                    
                        output_dict[h1][h2][h3][h4][h5] = {}
                        output_dict[h1][h2][h3][h4][h5]['^-text-^'] = []
                        current_dict = output_dict[h1][h1][h2][h3][h4][h5]
                    if line.startswith('###### '):
                        header_text = line.split('# ', 1)[1]
                        h6 = header_text                    
                        output_dict[h1][h2][h3][h4][h5][h6] = {}
                        output_dict[h1][h2][h3][h4][h5][h6]['^-text-^'] = []
                        current_dict = output_dict[h1][h2][h3][h4][h5][h6]     
                else:
                    5
                    a = current_dict['^-text-^']
                    a.append(line)
                    # a = current_dict['^-text-^'].append(line)
                        

                # print(header_text)

    5
    return output_dict
        
def parse_template_dict_to_titlepage_md_string(input_dict):
    current_level = 0
    md_string = ''
    def walk_level(level_dict, md_string, current_level):
        current_level += 1
        for k, v in level_dict.items():
            if isinstance(v, dict):
                header_hashtags = current_level * '#'
                md_string += header_hashtags + ' ' + str(k) + '\n\n'
                
                md_string = walk_level(v, md_string, current_level)
            else:
                if k == '^-text-^':
                    if isinstance(v, str):
                        md_string += str(v) + '\n\n'
                    elif isinstance(v, list):
                        for i in v:
                            md_string += str(i) + '\n\n'
                else:
                    if isinstance(v, str):
                         md_string += str(k) + '\n\n' + str(v) + '\n\n'
                    elif isinstance(v, list):
                        md_strin += str(k) + '\n\n'
                        for i in v:
                            md_string += str(i) + '\n\n'
        current_level -= 1
        return md_string
    to_return = walk_level(input_dict, md_string, current_level)       
    print(to_return)
    return to_return

def make_exam_md_from_dicts(header_dict, question_bank_dir, random_seed, randomize, is_key=False):
    import random
    
    # TODOOO: Fubared the order. How do i do this if i have multiple filesto load?
    print([k for k, v in header_dict.items() if isinstance(v, dict)])
    question_bank_dict = {}
    for k in [k for k, v in header_dict.items() if isinstance(v, dict)]:
        question_bank_path = os.path.join(question_bank_dir, k + '.qmd')
        new_dict = hb.parse_template_path_to_dict(question_bank_path)
        question_bank_dict.update(new_dict)

    output_question_number = 1
    included_questions_md_string = ''
    answers = []
    for h1, v1 in header_dict.items():
        if isinstance(v1, dict):
            for h2, v2 in v1.items():
                if isinstance(v2, dict):
                    for h3, v3 in v2.items():
                        subdict = question_bank_dict[h1][h2]
                        for h4, v4 in subdict.items():
                            if 'Question' in h4:

                                question_label = h4.split('Question ', 1)[1].split(':')[0]
                                if question_label in v3:
                                    
                                    included_questions_md_string += '### Question ' + str(output_question_number) + '\n\n'
                                    output_question_number += 1

                                    if isinstance(v4, dict):
                                        for i in v4['^-text-^']:
                                            
                                            if not i.startswith('Answer:') and not i.startswith('Reference:') and not i.startswith('Explanation:')  and not i.startswith('Type:'): 
                                                included_questions_md_string += str(i) + '\n\n'
                                            elif is_key:
                                                included_questions_md_string += str(i) + '\n\n'
                                            # elif i.startswith('Answer:'): # Then it is the answer line
                                            #     answers.append(i.split('Answer: ')[1])

    included_questions_md_string_randomized = included_questions_md_string.split('Question')[1:]
    included_questions_md_string_randomized = [i.split('\n\n', 1)[1] for i in included_questions_md_string_randomized]

    if randomize:
        random.Random(random_seed).shuffle(included_questions_md_string_randomized)
    
    new_md_string = ''
    for c, i in enumerate(included_questions_md_string_randomized):
        new_md_string += '### Question ' + str(c+1) + ':\n\n' + i + '\n\n'

    if is_key:
        for c, i in enumerate(included_questions_md_string_randomized):
            try:
                answer = i.split('Answer: ')[1].split(' ', 1)[0].replace(' ', '').replace('\n', '')
                answer = answer[0] # lol can't have more than 1 place obptions
                answers.append(answer)
            except:
                hb.log('Unable to add answer')


    return new_md_string, answers
                                                
        

# TODOO I decided that every print-generating function should default to NOT printing but just returning the string,
# which could be overriden by setting return_as_string to False. 
def print_iterable(input_iterable, level = -1, max_length_to_visualize=255, return_as_string=False, input_name=None):
    a = describe_iterable(input_iterable, level=level, max_length_to_visualize=max_length_to_visualize, return_as_string=return_as_string, input_name=input_name)
    if not return_as_string:
        print(a)
    return a
    
def describe_iterable(input_iterable, level=-1, max_length_to_visualize=255, return_as_string=True, input_name=None):
    return_string = ''
    prepend = ''
    if level == -1:
        return_string += '\nIterable contents:\n'           

        # Get the name of the iterable # NOTE that this will only return "input_iterable" so you will need to go up a frame to get the name of the variable.
        if input_name is None:            
            for name, value in locals().items():
                if value is input_iterable:
                    input_name = name            
        
        return_string += input_name + ' = '
        level += 1
        
    if type(input_iterable) is dict:
        return_string += prepend + '{\n'
        level += 1
        prepend = '    ' * level
        
        if len(input_iterable) == 0:
            if level > 1:
                level -= 1                
                prepend = '    ' * level
                return_string = return_string[:-1]
                return_string += '},\n'
            else:
                level -= 1
                prepend = '    ' * level
                return_string = return_string[:-1]
                return_string += '}\n'
        else:       
               
            for k, v in input_iterable.items():
                if type(k) in [str]:
                    k_quotes = '\''
                else:
                    k_quotes = ''
                if type(v) in [str]:
                    quotes = '\''
                else:
                    quotes = ''
                if type(v) in [dict, list, tuple]:
                    return_string += prepend + k_quotes + str(k) + k_quotes + ': ' + describe_iterable(v, level=level, max_length_to_visualize=max_length_to_visualize, return_as_string=return_as_string)
                else:
                    return_string += prepend + k_quotes + str(k) + k_quotes + ': ' + quotes + str(v) + quotes + ',\n'
            if level > 1:
                level -= 1
                prepend = '    ' * level
                return_string += prepend + '},\n'
            else:
                level -= 1
                prepend = '    ' * level
                return_string += prepend + '}\n'
        level -= 1
                    
    elif type(input_iterable) in [list, tuple]:
        return_string += prepend + '[\n'
        level += 1
        prepend = '    ' * level
        if len(input_iterable) == 0:
            if level > 1:
                level -= 1
                prepend = '    ' * level
                return_string = return_string[:-1]
                return_string += '],\n'
            else:
                level -= 1
                prepend = '    ' * level
                return_string = return_string[:-1]
                return_string += ']\n'
        else:
            for i in input_iterable:
                if type(i) in [str]:
                    quotes = '\''
                else:
                    quotes = ''
                                    
                if type(i) in [dict, list, tuple]:
                    return_string += prepend + describe_iterable(i, level=level, max_length_to_visualize=max_length_to_visualize, return_as_string=return_as_string)
                else:
                    return_string += prepend + quotes + str(i) + quotes + ',\n'
            level -= 1
            prepend = '    ' * level
            return_string += prepend + '],\n'
    else:

        prepend = '    ' * level
        return_string += prepend + 'String given to describe_iterable, but okay....: ' + str(input_iterable) + '\n'
    level -= 1     
    if return_string:
        return return_string




def print_dict_old(input_dict, level = -1, max_length_to_visualize=255, return_as_string=True):
    
    return_string = ''
    if level == -1:
        if return_as_string:
            return_string = '\nDictionary contents:\n'
        else:
            print('\nDictionary contents:')
        level += 1
    print_counter = 0
    for k, v in input_dict.items():
        if k == 'Shocks':
            pass
        if isinstance(v, dict):
            prepend = '   ' * level

            if return_as_string:
                return_string += prepend + str(k) + ':\n'
            else:
                print(prepend + str(k) )
                # print_counter = 0'
            level += 1
            return_string += hb.print_dict(v, level, return_as_string=return_as_string)
            level -= 1
        elif isinstance(v, list):

            if len(v) == 0:
                level += 1
                prepend = '   ' * level
                return_string += prepend + str(k) + ': []\n'
            elif v[0] is list or v[0] is dict:
                level += 1
                prepend = '   ' * level

                if return_as_string:
                    return_string += prepend + str(k) + ': [\n'
                else:
                    print(return_string)                
                   
                
                return_string += hb.print_dict(v, level, return_as_string=return_as_string)
            
            else:
                prepend = '   ' * level
                
                return_string += prepend + str(k) + ': [\n'
            
            
            print_counter = 0
            # return_string += '   ' * level + str(k) + ': '
            # level += 1
            if len(v) < 5:
                for c, i in enumerate(v):
                    # c += 1
                    if c < max_length_to_visualize:
                        return_string += prepend + str(i) + ',\n'
            else:
                prepend = '   ' * level
                return_string += '[\n'
                
                for c, i in enumerate(v):

                    if c < max_length_to_visualize:
                        return_string += prepend + str(i) + '\n'
                return_string += ']\n'
            level -= 1    
            if not return_as_string:
                print(return_string)

        else:
            print_counter += 1
            if print_counter < max_length_to_visualize:
                prepend = '   ' * level

                if len(str(v)) > max_length_to_visualize:
                    current_string = prepend + str(k) + ': ' + str(v)[:max_length_to_visualize] + '...\n'
                else:
                    current_string = prepend + str(k) + ': ' + str(v) + '\n'

                if return_as_string:
                    return_string += current_string
                else:
                    print(current_string)
            else:
                if return_as_string:
                    pass
                    return_string += prepend + 'truncated...'
                else:
                    pass
                    print(prepend + 'truncated...')
    if not return_string:
        prepend = '   ' * level
        return_string = prepend + 'Empty Dictionary.\n'
    if return_as_string:
        level -= 1
        return return_string
    else:
        print(return_string)


def print_md_dict(input_dict, level = 0):

    for k, v in input_dict.items():
        if isinstance(v, dict):
            prepend = '   ' * level
            print(prepend + str(k) )

            level += 1
            hb.print_dict(v, level)
        else:
            # level += 1
            prepend = '   ' * level
            for i in v:

                print(prepend + str(i))


def create_shortcut(target_path, shortcut_path, verbose=False):
    if sys.platform == 'win32':
        shortcut_path += '.lnk'
    try:
        os.symlink(target_path, shortcut_path)
        if verbose:
            hb.log(f'Shortcut created at {shortcut_path} pointing to {target_path}')
    except OSError:
        hb.log('Unable to create symlink')
