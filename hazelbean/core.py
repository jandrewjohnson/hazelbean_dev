import os, logging, datetime, errno, time
import hazelbean as hb
from hazelbean import os_utils

hb.LAST_TIME_CHECK = 0

def timer(msg=None, silent=False, suppress=False):
    if suppress:
        return
    
    if hb.LAST_TIME_CHECK == 0.0:
        hb.LAST_TIME_CHECK = time.time()
    else:
        if not msg:
            msg = 'Elapsed'
        if not silent:
            print(str(msg) + ': ' + str(time.time() - hb.LAST_TIME_CHECK) + '.')
            
    hb.LAST_TIME_CHECK = time.time()

from hazelbean.config import logging_levels


#### DO NOT USE THIS: it is now in config.
# def get_logger(logger_name=None, logging_level='info', format='full'):
#     """Used to get a custom logger specific to a file other than just susing the config defined one."""
#     if not logger_name:
#         try:
#             logger_name = os.path.basename(main.__file__)
#         except:
#             logger_name = 'unnamed_logger'
#     L = logging.getLogger(logger_name)
#     L.setLevel(logging_levels[logging_level])
#     CL = hb.config.CustomLogger(L, {'msg': 'Custom message: '})
#     # FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     FORMAT = "%(message)s"
#     formatter = logging.Formatter(FORMAT)

#     # handler = logging.StreamHandler()
#     # handler.setFormatter(formatter)
#     # L.addHandler(handler)
#     return CL

# def timer(msg=None, silent=False):
#     if hb.config.LAST_TIME_CHECK == 0.0:
#         hb.config.LAST_TIME_CHECK = time.time()
#     else:
#         if not msg:
#             msg = 'Elapsed'
#         if not silent:
#             print(str(msg) + ': ' + str(time.time() - hb.config.LAST_TIME_CHECK) + ' at time ' + str(hb.pretty_time()))
#         hb.config.LAST_TIME_CHECK = time.time()

def path_split_at_dir(input_path, split_dir):
    input_path_replaced = input_path.replace('\\\\', '/').replace('\\', '/')
    input_list = input_path_replaced.split('/')
    # from more_itertools import split_after

    if not split_dir in input_list:
        raise NameError('Graft dir not in input path and so cannot split: ' + str(input_path) + ', ' + str(split_dir))
    split = input_path.split(split_dir)
    if len(split) != 2:
        raise NameError('Split dir exists more than once in input string: ' + str(input_path) + ', ' + str(split_dir))
    before = split[0]
    split_dir_output = split_dir
    after = split[1]
    
    # split_in_two = list(split_after(input_list, lambda x: x == split_dir))
    # before = os.sep.join(split_in_two[0][0:-1]) # os.path.join(to_join)
    # split_dir_output = split_in_two[0][-1]
    # after = os.sep.join(split_in_two[1])

    return before, split_dir_output, after
    

def get_path_before_dir(input_path, input_dir):
    return path_split_at_dir(input_path, input_dir)[0]

def get_path_after_dir(input_path, input_dir):
    return path_split_at_dir(input_path, input_dir)[2]

def replace_path_with_exsting_in_dir(input_path, src_dir, graft_dir):

    try:
        a, b, c = path_split_at_dir(input_path, graft_dir)
        potential_path = os.path.join(src_dir, c)
        if hb.path_exists(potential_path, verbose=True):
            return potential_path
        else:
            return input_path
    except: 
        return input_path

def split_assume_two(input_string, split_dir):
    # Useful for splitting a string  and always taking the right part, even if it doesn't get split.
    split = input_string.split(split_dir)
    if len(split) == 2:
        return split
    elif len(split) == 1:
        return [split[0], split[0]]
    else:
        raise NameError('Split dir exists more than once in input string: ' + str(input_string) + ', ' + str(split_dir))

def path_join(*args, sep='slash'):
    # Even tho backslash is the default separator in windows, slash also works in windows. Thus, 
    # i've chosen to always use it.
    if sep == 'slash':
        sep = '/'
    elif sep == 'backslash':
        sep = '\\' 
    args_as_list = list(args)
    output_path = sep.join(args_as_list)
    return output_path

def path_needs_rerender(render_src_path, render_dst_path, minimum_size_check=0, verbose=False):
    # Checks if check_path has been changed more recently than reference path    
            
    if not hb.path_exists(render_src_path, minimum_size_check=minimum_size_check, verbose=verbose):
        if verbose:
            hb.log('render_src_path ' + str(render_src_path) + ' does not exist, so it doesnt need rerendering.')
        return False
    elif not hb.path_exists(render_dst_path, minimum_size_check=minimum_size_check, verbose=verbose):
        if verbose:
            hb.log('render_dst_path ' + str(render_dst_path) + ' was not found, so yes the src needs rerendering.')
        return True
    else:
        render_src_path_mtime = os.path.getmtime(render_src_path)
        render_dst_path_mtime = os.path.getmtime(render_dst_path)
        if render_src_path_mtime > render_dst_path_mtime:
            if verbose:
                hb.log('Path changed: ' + str(render_src_path_mtime) + ' was changed more recently than ' + str(render_dst_path_mtime) + '.')
            return True
        else:
            if verbose:
                hb.log('Path did not change: ' + str(render_src_path_mtime) + ' was NOT changed more recently than ' + str(render_dst_path_mtime) + '.')
            return False

def path_assert_exists(path, minimum_size_check=0, verbose=False):
    path_exists(path, minimum_size_check=minimum_size_check, verbose=verbose, assert_true=True)

def path_exists(path, minimum_size_check=0, dir_must_have_content=False, verbose=False, assert_true=False):
    # os.path.exists throws an exception rather than False if given None. This version resolves None as False.
    # set minimum_size_check to None if 0 size is okay.
    # if verbose:
    #     L.info('  Checking to see if ' + str(path) + ' exists.')
    path = str(path)
    # If verbose is a Logger object, use it. Otherwise create it.
    if verbose is not False:
        if verbose is not True:
            L = verbose
        else:
            L = hb.get_logger('hb.core')
            
    if path is None:
        if verbose:
            hb.log('Path given to hazelbean.path_exists() was None.')
        if assert_true:
            raise AssertionError('Path given to hazelbean.path_exists() was None.')
        return False
    if os.path.isdir(path):
        if dir_must_have_content:
            if len(os.listdir(path)) == 0:
                if verbose:
                    hb.log('Path exists: ' + str(path) + ' exists but it is a directory with no content. Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                return False
            else:
                if verbose:
                    hb.log('Path exists: ' + str(path) + ' exists and it is a directory with content. Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                return True
        else:
            if verbose:
                hb.log('Path exists: ' + str(path) + ' exists but it is a directory. Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
            return True

    # if isinstance(path, hb.InputPath):
    #     path = path.get_path(hb.path_filename(path))
    if not path:
        if verbose:
            hb.log('Path DOES NOT exist: ' + str(path) +  ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
        if assert_true:
            raise NameError('Path is not true:' + str(path)  + ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
        return False
    else:
        if minimum_size_check is not None:
            try:
                if os.path.exists(path):
                    if os.path.getsize(path) > minimum_size_check:
                        abs_path = os.path.abspath(path)
                        if verbose:
                            
                            hb.log('Path exists: ' + str(path) + ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                        return True
                    else:
                        if verbose:
                            hb.log('Path DOES NOT exist: ' + str(path) + ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                        if assert_true:
                            raise NameError('Path does not exist: ' + str(path) + ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                        return False     
                else:
                    if verbose:
                        hb.log('Path DOES NOT exist: ' + str(path) + ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                    
                    return False                
                
                
                
            except:
                if verbose:
                    L.info('Path DOES NOT exist: ' + str(path) + ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                if assert_true:
                    raise NameError('Path does not exist: ' + str(path))
                return False
        else:
            try:
                if os.path.exists(path):
                    if verbose:
                        L.info('Path exists: ' + str(path))
                    return True
                else:
                    if verbose:
                        L.info('Path DOES NOT exist: ' + str(path) +  ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                    if assert_true:
                        raise NameError('Path does not exist: ' + str(path))
                    return False
            except:
                if verbose:
                    L.info('Path DOES NOT exist: ' + str(path) +  ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                if assert_true:
                    raise NameError('Path does not exist: ' + str(path) + ', Absolute path is: ' + str(os.path.abspath(path)) + ', Normalized path is: ' + str(os.path.normpath(path)))
                return False

def path_has_content(path):
    path_exists(path, minimum_size_check=0, verbose=False, assert_true=False)

def path_all_exist(*args, verbose=False):
    for i in args:
        if type(i) == list:
            for j in i:
                if not path_exists(j, verbose=verbose):
                    return False
        else:
            if not path_exists(i, verbose=verbose):
                return False
            
    return True

def path_standardize_separators(input_path):
    if input_path is None:
        return None
    r1 = input_path.replace(os.sep, '/')
    r2 = r1.replace('\\', '/')
    return r2
    
    
    
def path_trisplit(input_path):
    if input_path is None:
        
        return None
    clean_path = path_standardize_separators(input_path)
    split_path = clean_path.split('/')
    return split_path
    
    
def path_file_root(input_path):
    # if isinstance(input_path, hb.InputPath):
    #     input_path = str(input_path)
    return os.path.splitext(os.path.split(input_path)[1])[0]

def file_root(input_path):
    return path_file_root(input_path)

def path_print(input_path):
    return_path = input_path
    exists = path_exists(input_path, verbose=False)
    is_dir = os.path.isdir(input_path)
    
    return_path += ' Abspath: ' + str(os.path.abspath(input_path)) + ' Exists: ' + str(exists) + ' Is dir: ' + str(is_dir)
    if is_dir:
        # n objects
        return_path += ' Number of objects: ' + str(len(os.listdir(input_path)))
    return return_path 


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



def create_directories(directory_list, ignore_dots_in_dirname=False):
    """Make directories provided in list of path strings.

    This function will create any of the directories in the directory list
    if possible and raise exceptions if something exception other than
    the directory previously existing occurs.

    Args:
        directory_list (list/string): a list of string uri paths

    Returns:
        None
    """
    if ignore_dots_in_dirname is False:
        # if there are more than two dots in the directory name, raise an error
        for dir_name in directory_list:
            if dir_name.count('.') > 2:
                hb.log("Directory given to create_directories has more than two dots in it: " + str(dir_name) + " but ignore_dots_in_dirname is False. Riiiiisky.")
    if isinstance(directory_list, str):
        directory_list = [directory_list]
    elif not isinstance(directory_list, list):
        raise TypeError('Must give create_directories either a string or a list.')

    for dir_name in directory_list:
        split_dir_name = None
        
        # NYI
        if ignore_dots_in_dirname:
            has_extension = []
        else:
            has_extension = os.path.splitext(dir_name)[1]
        if len(has_extension) > 0:
            split_dir_name = os.path.split(dir_name)[0]
        else:
            split_dir_name = dir_name
        # try:
        #     os.makedirs(dir_name)
        # except:
        #     split_dir_name = os.path.split(dir_name)[0]
        if split_dir_name is not None:
            if not hb.path_exists(split_dir_name):
                try:
                    os.makedirs(split_dir_name)
                except OSError as exception:
                    #It's okay if the directory already exists, if it fails for
                    #some other reason, raise that exception
                    if (exception.errno != errno.EEXIST and
                            exception.errno != errno.ENOENT):
                        raise



