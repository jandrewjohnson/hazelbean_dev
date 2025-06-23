import os, sys, types, inspect, logging, collections, time, copy
# import nose
from collections import OrderedDict

import hazelbean as hb
from hazelbean import cloud_utils, os_utils
import multiprocessing
import importlib
import ast
import os
import importlib.util
import sys
import inspect
import pandas as pd

# try:
#     import anytree    
# except:
#     'anytree is probably not needed except for project flow.'
import anytree
import platform

L = hb.get_logger('project_flow')
L.setLevel(logging.INFO)
initial_logging_level = L.getEffectiveLevel()

# module level get_path. Usually you want to use the project_level version
def get_path(relative_path, *join_path_args, possible_dirs='default', prepend_possible_dirs=None, create_shortcut=False, download_destination_dir=None, strip_relative_paths_for_output=False, leave_ref_path_if_fail=False, verbose=False):
    # SUPER DANGEROUS TO USE IF YOU ACTUALLY WANT TO USE A PROJECT FLOW OBJECT.
    p = ProjectFlow()
    got_path = p.get_path(relative_path, *join_path_args, possible_dirs=possible_dirs, prepend_possible_dirs=prepend_possible_dirs, create_shortcut=create_shortcut, download_destination_dir=download_destination_dir, strip_relative_paths_for_output=strip_relative_paths_for_output, leave_ref_path_if_fail=leave_ref_path_if_fail, verbose=verbose)
    return got_path 
    
def op():
    pass

def run_iterator(p, task, iteration_counter):
    things_returned = []
    for child in task.children:
        L.info('non-parallel iter ' + str(iteration_counter) + ': Running task ' + str(child.name) + ' with iterator parent ' + child.parent.name + ' in dir ' + str(p.cur_dir))
        r = p.run_task(child)
        things_returned.append(r)

    return things_returned
def run_iterator_in_parallel(p, task, iteration_counter):
    things_returned = []
    for child in task.children:

        if child.run:
            L.info('iter ' + str(iteration_counter) + ': Running task ' + str(child.name) + ' with iterator parent ' + child.parent.name + ' in dir ' + str(p.cur_dir))
            r = p.run_task(child)
            things_returned.append(r)

    return things_returned


class InputPath(object):
    """Defines a path where an object can be calculated, but also alternate file locations that if they exist, mean that the calculation should not be done and the
    existing object should be used instead. Checks first base_data (defined a the Project creation), then model_base_data, then project_base_data, then recalculates into calculation_path
    if none exist.

    base_data_extension_dirs allows the file to have a different root directory structure if it is in a base data dir such that it is BASE_DATA_DIR + base_data_extension_dirs + file_name

    """
    def __init__(self, calculation_dir, file_name, projectflow_object, base_data_extension_dirs=None):
        self.calculation_dir = calculation_dir
        self.file_name = file_name
        self.p = projectflow_object

        self.path = None
        self.dir = None

        if base_data_extension_dirs is None:
            base_data_extension_dirs = hb.file_root(self.calculation_dir)

        self.calculation_path = os.path.join(self.calculation_dir, self.file_name)

        self.project_base_data_dir = os.path.join(self.p.project_base_data_dir, base_data_extension_dirs)
        self.model_base_data_dir = os.path.join(self.p.model_base_data_dir, base_data_extension_dirs)
        self.base_data_dir = os.path.join(self.p.project_base_data_dir, base_data_extension_dirs)

    def __repr__(self):
        return self.get_path(self.file_name)

    def __str__(self):
        return self.get_path(self.file_name)

    def BORK_get_path(self, file_name=None):
        if file_name is None:
            file_name = self.file_name

        if file_name is not None:
            if hb.path_exists(os.path.join(self.project_base_data_dir, file_name)) > 0:
                return os.path.join(self.project_base_data_dir, file_name)
            elif hb.path_exists(os.path.join(self.model_base_data_dir, file_name)) > 0:
                return os.path.join(self.model_base_data_dir, file_name)
            elif hb.path_exists(os.path.join(self.base_data_dir, file_name)) > 0:
                return os.path.join(self.base_data_dir, file_name)
            else:
                return os.path.join(self.calculation_dir, file_name)
        else:
            return os.path.join(self.calculation_dir, file_name)

    def get_dir(self, file_name=None):
        if file_name is not None:
            if hb.path_exists(os.path.join(self.project_base_data_dir, file_name)) > 0:
                return self.project_base_data_dir
            elif hb.path_exists(os.path.join(self.model_base_data_dir, file_name)) > 0:
                return self.model_base_data_dir
            elif hb.path_exists(os.path.join(self.base_data_dir, file_name)) > 0:
                return self.base_data_dir
            else:
                return self.calculation_dir
        else:
            return self.calculation_dir

class InputDir(object):
    # TODOO Started making this, but ran out of time. Also couldnt figure out how to have it inherit from string.
    def __init__(self, calculation_dir, projectflow_object):
        self.calculation_dir = calculation_dir
        self.p = projectflow_object

        self.project_base_data_dir = self.p.project_base_data_dir
        self.model_base_data_dir = self.p.model_base_data_dir
        self.base_data_dir = self.p.project_base_data_dir

    def __repr__(self):
        return self.get_dir()

    def __str__(self):
        return self.get_dir()

    def get_dir(self, file_name=None):
        if file_name is not None:
            if hb.path_exists(os.path.join(self.project_base_data_dir, file_name)) > 0:
                return self.project_base_data_dir
            elif hb.path_exists(os.path.join(self.model_base_data_dir, file_name)) > 0:
                return self.model_base_data_dir
            elif hb.path_exists(os.path.join(self.base_data_dir, file_name)) > 0:
                return self.base_data_dir
            else:
                return self.calculation_dir
        else:
            return self.calculation_dir

class Task(anytree.NodeMixin):
    def __init__(self, function, project=None, parent=None, type='task', run=1, skip_existing=0, **kwargs):
        """
        There are TWO basic types of parallelizataion. Tasks that aren't dependent sequentially,
        or tasks that are defined in a different, unrelated extent, but possibly with sequential tasks.
        This Iterator object is fo the latter type, iterating over some zonal definition.
        """

        self.function = function
        self.p = project
        self.type = type
        self.let_children_skip = False # This didn't seem to change anything in testing gtap_invest zones for skipping iterator children.

        # Note that parent here is defined by anytree and it is not possible to set it to None, as parent has to be a Node
        if parent:
            self.parent = parent

        self.task_dir = kwargs.get('task_dir', None)

        self.name = self.function.__name__
        self.creates_dir = kwargs.get('creates_dir', True)
        self.logging_level = None  # Will be inherited from project flow or set explicitly
        self.report_time_elapsed_when_task_completed = True  # Will be inherited from project flow or set explicitly
        self.documentation = None 
        self.note = None 

        if self.function.__name__ == 'execute':
            self.run = 1
            self.skip_existing = 1

        else:
            self.run = run
            self.skip_existing = skip_existing

    def __str__(self):
        return '<ProjectFlow task ' + self.name + '>'

    def __repr__(self):
        return '<ProjectFlow task ' + self.name + '>'


class InputTask(anytree.NodeMixin):
    def __init__(self, function, project=None, parent=None, type='input_task', **kwargs):
        """
        Input Tasks are like Tasks but assume that you will not rerun anything whose file exists (and this, skip_existing is differently implemented).
        Input Tasks also check to see if a file of the same name already exists in p.project_base_data, p.model_base_data, or p.base_data
        """

        self.function = function
        self.p = project
        self.type = type

        # Note that parent here is defined by anytree and it is not possible to set it to None, as parent has to be a Node
        if parent:
            self.parent = parent

        self.task_dir = kwargs.get('task_dir', None)

        self.name = self.function.__name__
        self.creates_dir = kwargs.get('creates_dir', True)
        self.logging_level = None  # Will be inherited from project flow or set explicitly

        self.run = 1
        self.skip_existing = 1  # Will thus overwrite by default.

class OutputTask(anytree.NodeMixin):
    def __init__(self, function, project=None, parent=None, type='output_task', **kwargs):
        """
        Input Tasks are like Tasks but assume that you will not rerun anything whose file exists (and this, skip_existing is differently implemented).
        """

        self.function = function
        self.p = project
        self.type = type

        # Note that parent here is defined by anytree and it is not possible to set it to None, as parent has to be a Node
        if parent:
            self.parent = parent

        self.task_dir = kwargs.get('task_dir', None)

        self.name = self.function.__name__
        self.creates_dir = kwargs.get('creates_dir', True)
        self.logging_level = None  # Will be inherited from project flow or set explicitly

        self.run = 1
        self.skip_existing = 0  # Will thus overwrite by default.


class ProjectFlow(object):
    def __init__(self, project_dir=None):
        try:
            self.calling_script = inspect.stack()[1][1]
            self.script_dir = os.path.split(self.calling_script)[0]
        except:
            L.debug('Could not identify a calling script.')

        # self.calling_globals = inspect.stack()[1][0].f_globals
        user_dir = os.path.expanduser('~')
        default_extra_dirs = ['Files']
        
        ## PROJECT LEVEL ATTRIBUTES
        # Set the project-level logging level. Individual tasks can overwrite this.
        self.logging_level = logging.INFO

        # # WARNING, although this seems logical, it can mess up multiprocessing if L has a handler. Move back outside.
        # self.L = hb.get_logger('project_flow')

        # TODOO Renable run_dir separation.
        # If true, generates a random dirname and creates it in the folder determined by the following options.
        self.make_run_dir = False



        # If project_dir is not defined, use CWD.
        if project_dir:
            self.project_dir = project_dir
        else:
            self.project_dir = os.getcwd() # This may be temporary though because it may be overwritten by UI

        if not os.path.isdir(self.project_dir):
            try:
                hb.create_directories(self.project_dir)
            except:
                raise NotADirectoryError('A Project Flow object is based on defining a project_dir as its base, but we were unable to create the dir at the given path: ' + self.project_dir + '. It is possible that you do not have write access to this directory or that you are working on a virtual machine with some weird setup.')

        self.ui_agnostic_project_dir = self.project_dir # The project_dir can be overwritten by a UI but it can be useful to know where it would have been for eg decing project_base_data_dir

        self.model_base_data_dir = os.path.abspath(os.path.join(self.ui_agnostic_project_dir, '../../base_data'))  # Data that must be redistributed with this project for it to work. Do not put actual base data here that might be used across many projects.

        if hb.path_exists(hb.config.BASE_DATA_DIR):
            self.base_data_dir = hb.config.BASE_DATA_DIR
        else:
            self.base_data_dir = os.path.join(user_dir, os.sep.join(default_extra_dirs), 'base_data')


        if hb.path_exists(hb.config.EXTERNAL_BULK_DATA_DIR):
            self.external_bulk_data_dir = hb.config.EXTERNAL_BULK_DATA_DIR
        else:
            self.external_bulk_data_dir = None

        self.project_name = hb.file_root(self.project_dir)
        self.project_base_data_dir = os.path.join(self.project_dir, 'base_data')


        # args is used by UI elements.
        self.args = {}

        self.task_paths = {}

        self.prepend = '' # for logging

        # Functions are called via their position within a tree data structure.
        # The logic of the project is defined via the flow_tree to which tasks, batches, secenarios etc. are added and run top-to-bottom
        # The tree itself here is initialized by setting the function to be execute
        self.task_tree = Task(self.execute, 'Task tree') # NOTICE that this Task() has no parent. It is the root node.

        self.jobs = [] # Allow only 1 jobs pipeline

        # State variables that are passed into the task's funciton via p. attribtues
        self.cur_task = None
        self.cur_dir = self.project_dir
        self.run_this = None
        self.skip_existing = None

        self.task_names_defined = [] # Store a list of tasks defined somewhere in the target script. For convenience, e.g., when setting runtime conditionals based on function names existence.

        # TODO FIX get rid of inputs dir, but it's used a lot, including in putting scenarios.csv files in the right place....
        self.inputs_dir = getattr(self, 'inputs_dir', os.path.join(self.project_dir, 'inputs'))
        self.input_dir = getattr(self, 'input_dir', os.path.join(self.project_dir, 'input'))
        self.intermediate_dir = getattr(self, 'intermediate_dir', os.path.join(self.project_dir, 'intermediate'))
        self.output_dir = getattr(self, 'output_dir', os.path.join(self.project_dir, 'output'))
        self.documentation = None 
        self.note = None 
        #
        self.registered_dirs = ['.', self.input_dir]
        
        self.L = hb.get_logger('project_flow')
        # self.registered_dirs = ['.', self.input_dir, self.project_base_data_dir, self.model_base_data_dir, self.base_data_dir]


    def __str__(self):
        return 'Hazelbean ProjectFlow object. ' + hb.pp(self.__dict__, return_as_string=True)

    def __repr__(self):
        return 'Hazelbean ProjectFlow object. ' # +  hb.pp(self.__dict__, return_as_string=True)

    def set_project_dir(self, input_dir):
        self.project_dir = input_dir
        self.project_name = hb.file_root(self.project_dir)

        try:
            hb.create_directories(self.project_dir)
        except:
            raise NotADirectoryError('A Project Flow object is based on defining a project_dir as its base, but we were unable to create the dir at the given path: ' + self.project_dir)

        # BIG ASS-MISTAKE here, repeating inputs
        self.input_dir = os.path.join(self.project_dir, 'inputs')
        self.inputs_dir = os.path.join(self.project_dir, 'inputs')
        self.intermediate_dir = os.path.join(self.project_dir, 'intermediate')
        self.output_dir = os.path.join(self.project_dir, 'outputs')


    def get_path(self, relative_path, *join_path_args, possible_dirs='default', prepend_possible_dirs=None, create_shortcut=False, download_destination_dir=None, strip_relative_paths_for_output=False, leave_ref_path_if_fail=False, verbose=False):
        ### NOTE: This is a PROJECT METHOD. There is currently no hb level function cause then you'd just have to pass the project.
        
        # This is tricky cause there are four possible cases
        # 1. relative path has no directories, join path args is empty
        # 2. relative path has directories, join path args is empty
        # 3. relative path has no directories, join path args is not empty
        # 4. relative path has directories, join path args is not empty
        if hb.has_cat_ears(relative_path):
            if verbose:
                hb.log("A refpath with catears was given. You probably want to replace the variables wrapped in catears. Returning the original path intact: " + str(relative_path))
            return relative_path
        
        if relative_path is None:
            hb.log('WARNING: You gave None to hb.get_path(). This is not recommended but returning None Nonetheless, lol.')
            return None
        
        path_as_inputted = relative_path
        
        if download_destination_dir is None:
            download_destination_dir = self.base_data_dir
        
        
        # first get the length of the relative_path after splitting

        split_relative_path = hb.path_trisplit(relative_path)
        
        if len(split_relative_path) == 1:
            # Check if it has an extension
            if len(join_path_args) == 0:
                # hb.path_standardize_separators(self.intermediate_dir)
                if len(self.cur_dir.split(self.intermediate_dir)) > 1:
                    split1 = self.cur_dir.split(self.intermediate_dir)[1]
                else:
                    split1 = self.cur_dir
                split2 = split1.split(os.sep)
                paths_from_cur_dir = [i for i in split2 if i]
                
                relative_path = os.path.join(os.sep.join(paths_from_cur_dir), relative_path)
                
                
            else:
                relative_path = os.path.join(relative_path, os.sep.join(join_path_args))
                
        else:
            if len(join_path_args) == 0:
                relative_path = os.sep.join(split_relative_path)
            else:
                raise NameError('You gave both extra dirs i relative_path and join_path_args')
        
        default_bucket = 'gtap_invest_seals_2023_04_21'

        # # For convenience, p.get_path will assume that any list of strings should be joined to gether to make the relative path
        # if len(join_path_args) > 0:
        #     hb.debug("Joining relative paths from args list.")
        #     for i in join_path_args:
        #         if type(i) is not str:
        #             raise NameError('get_path was given non-string args to the *join_path_args. This is not allowed!')
        #     relative_path = os.path.join(relative_path, *join_path_args)
        #     relative_joined_path = relative_path
        #     # elif os.path.exists(self.cur_dir):
        #     paths_to_right_of_intermediate_dir = relative_path.split(self.intermediate_dir)[0]
        #     extra_dirs = [relative_path] + [i for i in join_path_args[:-1]]
        # else:
        #     relative_joined_path = relative_path
        #     paths_to_right_of_intermediate_dir = self.cur_dir.split(self.intermediate_dir)[0]
        #     extra_dirs = [relative_path] + [i for i in paths_to_right_of_intermediate_dir]
        # if type(relative_path) is not str:
        #     raise NameError('relative_path must be a string. You gave ' + str(relative_path))
        relative_joined_path = relative_path

        if possible_dirs == 'default':
            possible_dirs = [self.cur_dir, self.intermediate_dir, self.input_dir, self.base_data_dir]
            # possible_dirs = [self.cur_dir, self.input_dir, self.base_data_dir]
            
            # I Just changed this to be cur_dir instead of intermeiate_dir for base_data_promotion to work
            # possible_dirs = [self.intermediate_dir, self.input_dir, self.base_data_dir]
        
        intermediate_path_override = os.path.join(self.intermediate_dir, relative_path)
            
        # if len(join_path_args) > 1:
        #     to_insert = os.path.join(self.intermediate_dir, os.sep.join([path_as_inputted] + list(join_path_args)[:-1]))
        #     possible_dirs.insert(0, to_insert)
        
            # Check if self has google_drive_path attribute and if so, add it to the possible_dirs

        if not hasattr(self, 'input_bucket_name'):
            self.input_bucket_name = default_bucket
        if not hasattr(self, 'data_credentials_path'):
            self.data_credentials_path = None
        
        if self.input_bucket_name is None:
            self.input_bucket_name = default_bucket
            
        if hasattr(self, 'input_bucket_name'):
            possible_dirs.append('input_bucket_name')
                
        if prepend_possible_dirs is not None:
            if type(prepend_possible_dirs) is str:
                prepend_possible_dirs = [prepend_possible_dirs]

            possible_dirs = prepend_possible_dirs + possible_dirs
            


        # It is releative, so search the possible dirs
        for possible_dir in possible_dirs:
            if type(possible_dir) is str:
                if strip_relative_paths_for_output:
                    destination_file_name = os.path.join(download_destination_dir, relative_path.split(os.sep)[-1])
                else:
                    destination_file_name = os.path.join(download_destination_dir, relative_path)
                
                if possible_dir == 'input_bucket_name':
                    source_blob_name =  relative_path.replace('\\', '/')

                    if verbose:
                            hb.log('p.get_path looking online at: ' + str(self.input_bucket_name) + ' ' + str(source_blob_name) + ' ' + str(self.data_credentials_path) + ' ' + str(destination_file_name))

                    if hasattr(self, 'data_credentials_path') and cloud_utils.is_internet_available(1):
                        if self.data_credentials_path is not None:
                            try: # If the file is in the cload, download it.
                                if verbose:
                                    hb.log('Downloading ' + str(source_blob_name) + ' from ' + str(self.input_bucket_name) + ' to ' + str(destination_file_name) + ' in ' + str(self.cur_dir))
                                cloud_utils.download_google_cloud_blob(self.input_bucket_name, source_blob_name, self.data_credentials_path, destination_file_name, chunk_size=262144*5, verbose=verbose)
                                if create_shortcut:
                                    os_utils.create_shortcut(destination_file_name, intermediate_path_override)
                                return path
                            except: # If it wasn't there, assume it is a local file that needs to be created.
                                pass 
                        else:
                            try:
                                url = "https://storage.googleapis.com" + '/' + self.input_bucket_name + '/' + source_blob_name
                                cloud_utils.download_google_cloud_blob(self.input_bucket_name, source_blob_name, self.data_credentials_path, destination_file_name, chunk_size=262144*5, verbose=verbose)
                                if create_shortcut:
                                    os_utils.create_shortcut(destination_file_name, intermediate_path_override)                            
                                
                                return path
                            except:  # If it wasn't there, assume it is a local file that needs to be created.
                                pass 
                    else:
                        if cloud_utils.is_internet_available(1):
                            self.data_credentials_path = None
                            try:
                                url = "https://storage.googleapis.com" + '/' + self.input_bucket_name + '/' + source_blob_name
                                cloud_utils.download_google_cloud_blob(self.input_bucket_name, source_blob_name, self.data_credentials_path, destination_file_name, chunk_size=262144*5, verbose=verbose)
                                if create_shortcut:
                                    os_utils.create_shortcut(destination_file_name, intermediate_path_override)                            
                                
                                return path
                            except:  # If it wasn't there, assume it is a local file that needs to be created.
                                pass   
                        else:
                            pass

                else:

                    path = os.path.join(possible_dir, relative_path)


                    
                    

                    if hb.path_exists(path, verbose=verbose):
                        if create_shortcut:
                            os_utils.create_shortcut(destination_file_name, intermediate_path_override)

                        return path
                    
                    # HACK IUCN RUSH. Also check filepath against possible dir
                    # Though maybe it's not a bad ahck? Basically, what we need to consider is that
                    # sometimes you need to have the cur_dir define the post twist path but sometimes not and you just want to ignore any post twith paths
                    # incorrectly impli9ed by the cur_dir structure.
                    split_path = os.path.join(possible_dir, os.path.split(path)[1])
                    if hb.path_exists(split_path, verbose=verbose):
                        return split_path
                    


        # It wasnt found anywhere, so do some final checks and then use the default
        if os.path.isabs(relative_path):
            # Check that it has one of the possible_dirs already embedded in it
            found_possible_dir_in_input = False
            for possible_dir in possible_dirs:
                if possible_dir in relative_path:
                    relative_path = relative_path.replace(possible_dir, '')
                    if relative_path[1] == '/' or relative_path[1] == '\\':
                        relative_path = relative_path[1:]
                    elif relative_path[0] == '/' or relative_path[0] == '\\':
                        relative_path = relative_path[1:]
                        
                    found_possible_dir_in_input = True
                    
                    break
            
            # First just check if it's found at the unmodified abs path. 
            if hb.path_exists(relative_joined_path): 
                return relative_joined_path # This is the one case where it's okay
                
            
            if not found_possible_dir_in_input:       
                if leave_ref_path_if_fail:
                    return path_as_inputted
                
                elif hb.path_exists(relative_path):
                    hb.log('WARNING: You gave an absolute path to hb.get_path. It still might work if it found the possible_dirs in the path and removed them, but this is not good practice. Inputted path: ', relative_path, 'Possible dirs: ', possible_dirs, include_script_location=True)
                    return relative_path
                else:
                    raise NameError('The path given to hb.get_path() does not appear to be relative, is not relative to one of the possible dirs, does not exist at the unmodified path, and or is not available for download on your selected cloud bucket): ' + str(relative_path) + ', ' + str(possible_dirs))
                            
        if leave_ref_path_if_fail:
            return path_as_inputted
                                            
                            
                            
                            # If it was neither found nor None, THEN return the path constructed from the first element in possible_dirs
        # Get the first non None element in possible_dirs
        possible_dirs = [i for i in possible_dirs if i is not None]
        path = os.path.join(possible_dirs[0], relative_path)
        return path

    def write_args_to_project(self, args):
        L.debug('write_args_to_project.')
        for k, v in args.items():
            if k in self.__dict__:
                L.debug('Arg given to P via UI was already in P. Overwritting: ' + str(k) + ', ' + str(v) +', Original value: ' + str(self.__dict__[k]))
            self.__setattr__(k, v)

    def show_tasks(self):
        for pre, fill, task in anytree.RenderTree(self.task_tree):
            if task.name == 'ProjectFlow':
                L.info(pre + task.name)
            else:
                L.info(pre + task.name + ', running: ' + str(task.run) + ', skip if dir exists: ' + str(task.skip_existing))

    def add_task(self, function, project=None, parent=None, type='task', run=1, skip_existing=0, **kwargs):
        """KWARGS: task_dir sets where this task will have as its cur_dir, overwritting the default logic"""
        if not project:
            project = self
        if not parent:
            parent = self.task_tree
        if not hasattr(function, '__call__'):
        # if not isinstance(function, collections.Callable):
            raise TypeError(
                'Fuction passed to add_task() must be callable. ' + str(function.__name__) + ' was not.')
        task = Task(function, self, parent=parent, type=type, run=run, skip_existing=skip_existing, **kwargs)

        self.task_names_defined.append(function.__name__)

        # Add attribute to the parent object (the ProjectFlow object) referencing the iterator_object
        setattr(self, task.name, task)

        # Tasks inherit by default the projects' logging level.
        task.logging_level = kwargs.get('logging_level', self.logging_level)



        # If the function being used to initialize the task has local variables set with the names task_note or task_documentation, add those as attributes
        # to the task. These will optionally be written to the task_dir.
        if 'task_note' in function.__code__.co_varnames:
            found_index = function.__code__.co_varnames.index('task_note')
            task.note = function.__code__.co_consts[found_index]
        else:
            task.note = None
        
        if 'task_documentation' in function.__code__.co_varnames:
            found_index = function.__code__.co_varnames.index('task_documentation')
            task.documentation = function.__code__.co_consts[found_index]   
        else:
            task.documentation = None       

        
        return task

    def add_input_task(self, function, project=None, parent=None, type='input_task', **kwargs):
        """Input tasks by default save to the projects' input dir and are assumed to always check for file existence to skip anything slow."""
        if not project:
            project = self
        if not parent:
            parent = self.task_tree
        if not hasattr(function, '__call__'):
            raise TypeError(
                'Function passed to add_task() must be callable. ' + str(function.__name__) + ' was not.')

        task_dir = kwargs.get('task_dir', os.path.join(self.input_dir, function.__name__))

        task = InputTask(function, self, parent=parent, type=type, task_dir=task_dir, **kwargs)

        self.task_names_defined.append(function.__name__)

        # Add attribute to the parent object (the ProjectFlow object) referencing the iterator_object
        setattr(self, task.name, task)

        # Tasks inherit by default the projects' logging level.
        task.logging_level = kwargs.get('logging_level', self.logging_level)

        # If the function being used to initialize the task has local variables set with the names task_note or task_documentation, add those as attributes
        # to the task. These will optionally be written to the task_dir.
        if 'task_note' in function.__code__.co_varnames:
            found_index = function.__code__.co_varnames.index('task_note')
            task.note = function.__code__.co_consts[found_index]
        else:
            task.note = None
        
        if 'task_documentation' in function.__code__.co_varnames:
            found_index = function.__code__.co_varnames.index('task_documentation')
            task.documentation = function.__code__.co_consts[found_index]   
        else:
            task.documentation = None   
            
        return task

    def add_output_task(self, function, project=None, parent=None, type='output_task', **kwargs):
        """Input tasks by default save to the projects' input dir and are assumed to always check for file existence to skip anything slow."""
        if not project:
            project = self
        if not parent:
            parent = self.task_tree
        if not hasattr(function, '__call__'):
            raise TypeError(
                'Fuction passed to add_task() must be callable. ' + str(function.__name__) + ' was not.')

        task_dir = kwargs.get('task_dir', os.path.join(self.output_dir, function.__name__))

        task = OutputTask(function, self, parent=parent, type=type, task_dir=task_dir, **kwargs)

        self.task_names_defined.append(function.__name__)

        # Add attribute to the parent object (the ProjectFlow object) referencing the iterator_object
        setattr(self, task.name, task)

        # Tasks inherit by default the projects' logging level.
        task.logging_level = kwargs.get('logging_level', self.logging_level)

        # If the function being used to initialize the task has local variables set with the names task_note or task_documentation, add those as attributes
        # to the task. These will optionally be written to the task_dir.
        if 'task_note' in function.__code__.co_varnames:
            found_index = function.__code__.co_varnames.index('task_note')
            task.note = function.__code__.co_consts[found_index]
        else:
            task.note = None
        
        if 'task_documentation' in function.__code__.co_varnames:
            found_index = function.__code__.co_varnames.index('task_documentation')
            task.documentation = function.__code__.co_consts[found_index]   
        else:
            task.documentation = None   
            

        return task

    def add_iterator(self, function, project=None, parent=None, run_in_parallel=False, type='iterator', **kwargs):
        if not project:
            project = self
        if not parent:
            parent = self.task_tree

        if not hasattr(function, '__call__'):
            raise TypeError('Fuction passed to add_iterator() must be callable. ' + str(function.__name__) + ' was not.')

        # Create the iterator object
        iterator = Task(function, self, parent=parent, type=type, **kwargs)
        iterator.run_in_parallel = run_in_parallel
        # Add attribute to the parent object (the ProjectFlow object) referencing the iterator_object
        setattr(self, iterator.name, iterator)

        # Tasks inherit by default the projects' logging level.
        iterator.logging_level = self.logging_level

        # If the function being used to initialize the task has local variables set with the names task_note or task_documentation, add those as attributes
        # to the task. These will optionally be written to the task_dir.
        if 'task_note' in function.__code__.co_varnames:
            found_index = function.__code__.co_varnames.index('task_note')
            iterator.note = function.__code__.co_consts[found_index]
        else:
            iterator.note = None
        
        if 'task_documentation' in function.__code__.co_varnames:
            found_index = function.__code__.co_varnames.index('task_documentation')
            iterator.documentation = function.__code__.co_consts[found_index]   
        else:
            iterator.documentation = None   
            
        return iterator

    def add_all_functions_from_script_to_task_tree(self, script_path):
        module_name = os.path.splitext(os.path.basename(script_path))[0]

        # Load the module from the given script path
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Parse the file to get the function definitions in the order they appear
        with open(script_path, "r") as file:
            file_contents = file.read()

        parsed_ast = ast.parse(file_contents)
        functions_list = [node.name for node in parsed_ast.body if isinstance(node, ast.FunctionDef)]

        # Print the function names and add them to the task tree
        print("Functions in the script:")
        for func_name in functions_list:
            func = getattr(module, func_name)
            if func_name not in self.task_names_defined:
                self.add_task(func)       
        
        # for name, obj in inspect.getmembers(sys.modules[self.calling_script]):
        #     if inspect.isfunction(obj):
        #         if name not in self.task_names_defined:
        #             self.add_task(obj)        
        
        # module_name = os.path.splitext(os.path.basename(script_path))[0]

        # # Load the module from the given script path
        # spec = importlib.util.spec_from_file_location(module_name, script_path)
        # module = importlib.util.module_from_spec(spec)
        # sys.modules[module_name] = module
        # spec.loader.exec_module(module)

        # # List all functions in the module
        # functions_list = [func for func in dir(module) if inspect.isfunction(getattr(module, func))]

        # # Print the function names and add them to the task tree
        # print("Functions in the script:")
        # for func in functions_list:
        #     print(func)
        #     self.add_task(getattr(module, func))        
            
        
        # # Get the current module (i.e., your script)
        # hb.print_iterable(sys.modules)
        # current_module = sys.modules[script_path]

        # # List all functions in the current module
        # functions_list = [func for func in dir(current_module) if inspect.isfunction(getattr(current_module, func))]

        # # Print the function names
        # print("Functions in the current script:")
        # for func in functions_list:
        #     print(func)
        #     self.add_task(getattr(current_module, func))



        # for name, obj in inspect.getmembers(sys.modules[self.calling_script]):
        #     if inspect.isfunction(obj):
        #         if name not in self.task_names_defined:
        #             self.add_task(obj)

    def run_task(self, current_task):

        for task in anytree.LevelOrderIter(current_task, maxlevel=1): # We ALWAYS have maxlevel = 1 even if there are nested things because it handles all nested children recursively and we don't want the tree iterator to find them. This is sorta stupid instead of just giving the tree itself at the top  node.
            # If the function is not the root execute function, go ahead and run it. Can't run execute this way because it doesn't have a parent.
            # if current_task.report_time_elapsed_when_task_completed:
            #     hb.timer('Starting task: ' + task.function.__name__)
            if not task.function.__name__ == 'execute':

                # Set task level logging
                if task.logging_level is not None:
                    task_logging_level = task.logging_level
                else:
                    task_logging_level = initial_logging_level

                # Set task_dirs and cur_dirs based on tree position
                if task.parent.type == 'task':
                    if task.parent is not None and getattr(task.parent, 'task_dir', None):
                        if getattr(task, 'task_dir', None):
                            L.critical('Logic of task_dirs does not make sense here. In particular, a parent was given an explicit task_dir AND its child task was too instead of being derived')
                        else:
                            task.task_dir = os.path.join(task.parent.task_dir, task.function.__name__)
                    elif isinstance(task, (InputTask, OutputTask)):
                        # task.task_dir = hb.InputDir(task.task_dir, self)
                        pass
                    else:
                        if getattr(task, 'task_dir_override', None):
                            pass # Expected outcome if given an override. This case is for when you want to specify a task look somewhere else. Though note it is hard then to make the override programatically determined.
                        else:
                            task.task_dir = os.path.join(self.intermediate_dir, task.function.__name__)
                    self.cur_dir = task.task_dir
                elif task.parent.type == 'iterator':
                    task.task_dir = os.path.join(self.cur_dir_parent_dir, task.name)
                    self.cur_dir = task.task_dir
                else:
                    raise NameError('Unknown Node type')

                # Set the project level task_dirs object to have an attribute equal to the current name. This makes it possible for functions later in the analysis  script to have access to
                # previous task_dir locations.
                setattr(self, task.name + '_dir', task.task_dir)

                # In addition to self.cur_dir, there are also these two project-level convenience funcitons.
                self.cur_task = task
                self.run_this = task.run # NYI, task skipping enabled here.

                if isinstance(task, InputTask):#, GeneratedInputTask)):
                    self.skip_existing = 0  # Don't want to skip InputTasks because these have internal logig for what to skip.
                else:
                    self.skip_existing = task.skip_existing

                if self.skip_existing:
                    if os.path.exists(self.cur_dir):
                        self.run_this = 0

                if not os.path.exists(self.cur_dir.__str__()) and task.creates_dir and task.run and task.type != 'input_task':
                    pass
                    hb.create_directories(str(self.cur_dir))

                # # TODOO NYI, but I want to implement task-level logging conditionals.
                # L.setLevel(task.logging_level)


                if task.type in ['task', 'input_task', 'output_task']:
                    if self.run_this:
                        if task.creates_dir:
                            pass # NYI
                            # hb.create_directories(self.cur_dir)
                            # assert os.path.exists(self.cur_dir)

                        # If the task's parent is an iterator, we want to report different info, otherwise these are the same.
                        if task.parent.type == 'iterator':
                            if task.parent.let_children_skip:

                                try:
                                    self.L.setLevel(task_logging_level)
                                    r = task.function(self)
                                    self.L.setLevel(initial_logging_level)
                                except:
                                    L.critical('FAILED TO RUN task with iterator parent: ' + str(task.name) + ' and loading from ' + str(self.cur_dir))
                            else:
                                self.L.setLevel(task_logging_level)
                                r = task.function(self)
                                self.L.setLevel(initial_logging_level)
                        elif isinstance(task, InputTask):
                            self.prepend = ''
                            L.info(self.prepend + 'Running InputTask ' + str(task.name) + ' in dir ' + str(self.cur_dir))
                            self.L.setLevel(task_logging_level)
                            task.function(self)  # Running the Task including anyting in p.run_this
                            self.L.setLevel(initial_logging_level)
                        elif isinstance(task, OutputTask):
                            self.prepend = ''
                            L.info(self.prepend + 'Running OutputTask ' + str(task.name) + ' in dir ' + str(self.cur_dir))
                            self.L.setLevel(task_logging_level)
                            task.function(self)  # Running the Task including anyting in p.run_this
                            self.L.setLevel(initial_logging_level)
                        else:
                            self.prepend = ''
                            L.info(self.prepend + 'Running Task ' + str(task.name) + ' in dir ' + str(self.cur_dir))
                            current_level = L.getEffectiveLevel()

                            self.L.setLevel(task_logging_level)
                            task.function(self)  # Running the Task including anyting in p.run_this
                            self.L.setLevel(initial_logging_level)



                    # NYI, task skipping enabled here.
                    else:
                        if os.path.isdir(self.cur_dir):
                            if task.run:
                                if task.parent.type == 'iterator':
                                    L.info('Skipping task (with iterator parent) ' + str(task.name) + ' because the task_dir already existsed. Dir: ' + str(self.cur_dir))
                                    # task.run = 0
                                    self.L.setLevel(task_logging_level)
                                    r = task.function(self)
                                    self.L.setLevel(initial_logging_level)
                                elif isinstance(task, InputTask):
                                    self.prepend = ''
                                    L.info(self.prepend + 'Running InputTask ' + str(task.name) + ' in dir ' + str(self.cur_dir))
                                    self.L.setLevel(task_logging_level)
                                    task.function(self)  # Running the Task including anyting in p.run_this
                                    self.L.setLevel(initial_logging_level)
                                else:
                                    self.prepend = ''
                                    L.info('Skipping task ' + str(task.name) + ' because the task_dir already existsed. Dir: ' + str(self.cur_dir))
                                    self.L.setLevel(task_logging_level)
                                    task.function(self)  # Running the Task including anyting in p.run_this
                                    self.L.setLevel(initial_logging_level)

                            else:
                                # L.info('Instructed to skip task ' + str(task.name) + ' and loading from ' + str(self.cur_dir))
                                if task.parent.type == 'iterator':
                                    self.L.setLevel(task_logging_level)
                                    r = task.function(self)
                                    self.L.setLevel(initial_logging_level)
                                    #try:
                                    #    r = task.function(self)
                                    #except:
                                    #    L.critical('FAILED TO RUN task with iterator parent: ' + str(task.name) + ' and loading from ' + str(self.cur_dir))
                                else:
                                    self.prepend = ''
                                    task.function(self)  # Running the Task including anyting in p.run_this

                            # # CALL THE TASK FUNCTION
                            # task.function(p)  # Running the Task EXCLUDING anyting in p.run_this

                        # CONFUSED HERE, I think that I should have had this type of task not run. # Perhaps need to add multiple levels of _run_this, including silent, verbose, all, quick, indexing, etc.
                        else:
                            L.info('Skipping task ' + str(task.name) + ' because task.run was False')
                            if task.parent.type == 'iterator':
                                self.L.setLevel(task_logging_level)
                                r = task.function(self)
                                self.L.setLevel(initial_logging_level)
                            elif isinstance(task, InputTask):
                                self.prepend = ''
                                # L.info(self.prepend + 'Running InputTask ' + str(task.name) + ' in dir ' + str(self.cur_dir))
                                self.L.setLevel(task_logging_level)
                                task.function(self)  # Running the Task including anyting in p.run_this
                                self.L.setLevel(initial_logging_level)

                            else:
                                self.prepend = ''
                                self.L.setLevel(task_logging_level)
                                task.function(self)  # Running the Task including anyting in p.run_this
                                self.L.setLevel(initial_logging_level)


                elif task.type == 'iterator':

                    # Run the function for defining the iterator
                    if task.run:
                        self.prepend += '    '
                        L.info('Creating iterator ' + str(task.name))
                        # HACK, I failed to understand why sometiems the dirs weren't created in time. Thus I force it here.
                        hb.create_directories(self.cur_dir)
                        assert os.path.exists(self.cur_dir)
                        self.L.setLevel(task_logging_level)
                        task.function(self)
                        self.L.setLevel(initial_logging_level)
                        # task.function(self)

                    else:
                        # NYI, task skipping enabled here.
                        # L.info('Skipping running Iterator.')
                        self.L.setLevel(task_logging_level)
                        task.function(self)
                        self.L.setLevel(initial_logging_level)

            # Currently in this version of the code, if the parent is not run, none of the children run.
            if len(task.children) > 0 and self.run_this:
                # Whether run or not, search for children
                # if len(task.children) > 0: ORIGINAL

                # If the current task is an iterator, then check for replacements before calling the child task.
                # Definition of the projects' self.iterator_replacements is the one part of ProjectFlow that the analysis script needs to be aware of,
                # creating a dict of key-value pairs that are replaced with each step in the iterator.
                if task.type == 'iterator' and task.run:

                    # First check dimensions of iterator_replacements:
                    replacement_lengths = []
                    for replacement_attribute_name, replacement_attribute_value in self.iterator_replacements.items():
                        replacement_lengths.append(len(replacement_attribute_value))
                        assert(len(set(replacement_lengths))==1) # Check that all of the same size.
                    num_iterations = replacement_lengths[0]

                    # self.run_in_parallel = True # TODOO Connect to UI
                    MAX_WINDOWS_WORKERS = 58
                    if not getattr(self, 'num_workers', None):
                        self.num_workers = multiprocessing.cpu_count() - 1
                        #check which os
                        if platform.system() == 'Windows' and self.num_workers > MAX_WINDOWS_WORKERS:
                            self.num_workers = MAX_WINDOWS_WORKERS
                            
                    results = []

                    if task.run_in_parallel:
                        # OPTIMIZATION NOTE: It's slow to spawn 460 processes when they are just going to be skipped, thus run_this for iterators needs to be improved.
                        worker_pool = multiprocessing.Pool(self.num_workers) # NOTE, worker pool and results are LOCAL variabes so that they aren't pickled when we pass the project object.

                    # Once all the iterations are done, iterate through the stored results and call their get functions, which blocks running past this point until all are done.
                    # SUPER CONFUSING POINT. the project object will be modified independently by all tasks. Cant think of a good way ro rejoin them
                    returns_from_parallel_tasks = []

                    parsed_iterable = []
                    for iteration_counter in range(num_iterations):
                        to_append = []

                        # NOTICE strange dimensionality here: even within a single iteration, we have to iterate through self.iterator_replacements because we might have more than 1 var that needs replacing
                        replacements = OrderedDict()
                        for replacement_attribute_name, replacement_attribute_values in self.iterator_replacements.items():
                            current_replacement_value = self.iterator_replacements[replacement_attribute_name][iteration_counter]
                            replacements[replacement_attribute_name] = replacement_attribute_values
                            setattr(self, replacement_attribute_name, current_replacement_value)
                            if replacement_attribute_name == 'cur_dir_parent_dir':
                                setattr(self, 'cur_dir', current_replacement_value)
                            project_copy = copy.copy(self)# Freeze it in place (necessary for parallelizing)

                        # For multiprocessing, you cannot pickle a Gdal DS or Band, so I manually unset them here. For some reason, using the k.close_data corrupted the geotiff headers
                        for i, k in project_copy.__dict__.items():
                            if type(k) in [hb.GlobalPyramidFrame, hb.ArrayFrame]:
                                k.band = None
                                k.ds = None
                                # k.close_data()

                        to_append.append(project_copy)
                        to_append.append(task)
                        to_append.append(iteration_counter)
                        parsed_iterable.append(tuple(to_append))



                    if task.run_in_parallel:
                        try:
                            L.info('Initializing PARALLEL tasks with iterable length: ' + str(len(parsed_iterable)))
                        except Exception as e:
                            L.info('Initializing PARALLEL task but failed or something\nException raised: ' + str(e))

                        # We use apply_async, which immediately lets the next line calculate. It is blocked below with results.get()
                        # result = worker_pool.apply_async(func=run_iterator_in_parallel, args=(project_copy, task, iteration_counter))

                        result = worker_pool.starmap(run_iterator_in_parallel, parsed_iterable)

                        # Not sure if needed, but note that I don't actually ever iterate over result to get the results.

                    else:
                        things_returned = []
                        for child in task.children:
                            for project_copy, task, iteration_counter in parsed_iterable:
                                L.info('non-parallel iter ' + str(iteration_counter) + ': Running task ' + str(
                                    child.name) + ' with iterator parent ' + child.parent.name + ' in dir ' + str(
                                    project_copy.cur_dir))

                                r = project_copy.run_task(child)
                                things_returned.append(r)

                        # run_iterator(self, task, iteration_counter)




                # Task is an iterator's child
                else:
                    if task.run:
                         for child in task.children:
                            self.run_task(child)  # Run the child found by iterating the task-node's children

            # Task is not an iterator, thus we just call it's child directly
            elif task.parent is not None:
                if task.parent.type == 'iterator':
                    for child in task.children:
                        self.run_task(child)# Run the child found by iterating the task-node's children
            else:
                for child in task.children:
                     self.run_task(child)  # Run the child found by iterating the task-node's children

                    # raise NameError('wtf')
        if current_task.report_time_elapsed_when_task_completed:
            hb.timer('Finished task: ' + task.function.__name__) 

        if 1:           
            if task.note is not None:
                # TODOOO, finish writing the CODE to documentation. econ_lcovercom isn't writing for some reason.
                # Notes are just quick text written whereas documentation also includes the full script used in the function.
                hb.create_directories(task.task_dir)
                hb.write_to_file(task.note, os.path.join(task.task_dir, task.name + '_note.md'))
            if task.documentation is not None:    
                to_write = task.documentation + '\n\n\nCode Used:\n\n' + str(task.function.__code__.co_consts)
                hb.create_directories(task.task_dir)
                hb.write_to_file(to_write, os.path.join(task.task_dir, task.name + '_documentation.md'))
        else:
            print('TRIED AND FAILED TO WRITE TDOCUMENTATION')
        
        try:
            if(len(r)) > 0:
                return r
        except:
            'nothing needed returning'

    def DataRef(self, input_path, graft_dir=None, verbose=False):
        """Thin wrapper so that InputPath calls itself with a reference to the ProjectFlow object, even if not given."""
        return DataRef(input_path, p=self, graft_dir=graft_dir, verbose=verbose)

    def InputPath(self, dir, file_name, base_data_extension_dirs=None):
        """Thin wrapper so that InputPath calls itself with a reference to the ProjectFlow object, even if not given."""
        return hb.InputPath(dir, file_name, projectflow_object=self, base_data_extension_dirs=base_data_extension_dirs)

    # OPTIONAL START: Cool advance towards project-level logger management. Extent.
    def log(self, log_input):
        if self.cur_task.logging_level == 'debug':
            L.debug(log_input)
        if self.cur_task.logging_level == 'info':
            L.info(log_input)
        if self.cur_task.logging_level == 'warn':
            L.warn(log_input)
        if self.cur_task.logging_level == 'critical':
            L.critical(log_input)

    def execute(self, args=None):

        # These are registered at execute time because the user may specify overrides.
        self.registered_dirs = ['.', self.input_dir, self.project_base_data_dir, self.model_base_data_dir, self.base_data_dir]
        
        if len(self.task_tree.children) == 0:
            # Add all functions from the script to the task tree
            self.add_all_functions_from_script_to_task_tree(self.calling_script)

        self.show_tasks()

        if not isinstance(self.task_tree, hb.Task):
            raise NameError('Execute was called in ProjectFlow but no tasks were in task_tree.')

        # Execute can be passed an args dict that can be, for instance, generated by a UI. If args exists, write each
        # key value pair as project object level attributes.
        if args:
            self.write_args_to_project(args)


        # Check to see if any args have been set that change runtime conditionals.
        if args:
            for k, v in args.items():
                if k.startswith('run_') and k.split('_', 1)[1] in self.task_names_defined:
                    a = getattr(self, k.split('_', 1)[1], None)
                    if a:
                        a.run = v


        # TRICKY NOTE: Workspace_dir and project_dir are often but not always the same. Project dir is defined by the model code while workspace dir is defined by the script or UI that is calling the model code.
        # If workspace_dir is defined, it will overwrite project_dir? Is this right?
        self.workspace_dir = getattr(self, 'workspace_dir', None)
        if self.workspace_dir: # Then there IS a UI, so use itz
            self.project_dir = self.workspace_dir
        # If no additional dirs are specified, assume inputs, intermediates and outputs all go in CWD
        # These are the DEFAULT LOCATIONS, but they could be changed by the UI or script calling it for example to make batch runs happen.

        self.intermediate_dir =  getattr(self, 'intermediate_dir', os.path.join(self.project_dir, 'intermediate'))

        # Because the UI will give '', need to overwrite this manually.
        # ALSO, this messed me up when I went to API calls as it wasnt properly being rewritten to based on the new worskpace dir. I'm thinking
        # I need to ditch the basis, intermediate etc setup for now to hone the existing. THEN add them back in
        # if self.intermediate_dir == '':
        #     self.intermediate_dir = os.path.join(self.project_dir, 'intermediate')

        self.output_dir = getattr(self, 'output_dir', os.path.join(self.project_dir, 'outputs'))


        L.debug('self.model_base_data_dir set to ' + str(self.model_base_data_dir))
        self.model_dir = os.path.join(self.ui_agnostic_project_dir, '..\\') # Model is the name of the application being developed. THis is referred to confusingly as a Project (in the reseracher's storage), and the model has its own projects, which are defined in this code

        L.debug('self.model_dir set to ' + str(self.model_dir))
        self.model_base_data_dir = os.path.abspath(os.path.join(self.ui_agnostic_project_dir, '..\\..\\base_data'))  # Data that must be redistributed with this project for it to work. Do not put actual base data here that might be used across many projects.

        self.project_base_data_dir = os.path.join(self.project_dir, 'project_base_data')  # Data that must be redistributed with this project for it to work. Do not put actual base data here that might be used across many projects.

        L.debug('self.project_base_data_dir set to ' + str(self.project_base_data_dir))
        self.temporary_dir = getattr(self, 'temporary_dir', os.path.join(hb.config.PRIMARY_DRIVE, 'temp'))  # Generates new run_dirs here. Useful also to set the numdal temporary_dir to here for the run.

        self.run_string = hb.pretty_time()  # unique string with time-stamp. To be used on run_specific identifications.
        self.basis_name = ''  # Specify a manually-created dir that contains a subset of results that you want to use. For any input that is not created fresh this run, it will instead take the equivilent file from here. Default is '' because you may not want any subsetting.
        self.basis_dir = os.path.join(self.intermediate_dir, self.basis_name)  # Specify a manually-created dir that contains a subset of results that you want to use. For any input that is not created fresh this run, it will instead take the equivilent file from here. Default is '' because you may not want any subsetting.

        # if self.make_run_dir:
        #     self.run_dir = getattr(self, 'run_dir', hb.make_run_dir(self.intermediate_dir))
        # else:
        #     self.run_dir = self.intermediate_dir

        # hb.create_directories([self.input_dir, self.intermediate_dir, self.output_dir])


        #### WARNING This was a decent idea (mayyybe), but it put a module in the global scope which meant that it couldn't be pickled in multiprocessing.
        # # Get all globally defined variables of type Path and add as project attributes
        # for k, v in self.calling_globals.items():
        #     if isinstance(v, hb.project_flow.Path):
        #         self.__setattr__(k, v)


        L.info('\nRunning Project Flow')
        self.run_task(self.task_tree) # LAUNCH the task tree. Everything else will be called via recursive task calls.

        L.info('Script complete.')


class DataRef(str):
    """Number of times I have attempted this and failed: 3. Please increment when reattempted and failed.
    
    History: this used to be the p.Path(input_path_string) class but it failed. I tried hard to subclass str so that I could override __str__() etc and give the correct, existant path to other libraries.
    However, I got tripped up by windows backslashing. The first pass would work, but the second pass would re-escape the backslashes and mess up the path.
    Thus I abandoned the idea and instead call it p.Data which has an attribute p.Data.path which is the acutal string."""

    # THIS FAILED MISERABLY when it was included in a multiprocessing loop because that would trigger a copy, which would trigger the __new__ which would then be missing a p argument.
    # I temporarily got around this by not assigning any DataRefs to the p. object. But this is a hack. Consider if I should make this just a function to find it. WRONG!!!!
    # Actually it failed because I originaly called it just Data which was a namespace conflict.

    def __new__(cls, str_input, p, graft_dir=None, verbose=False):
        obj = str.__new__(cls, str_input)
        obj.p = p
        return obj

    def __init__(self, input_path, p, graft_dir=None, verbose=False):
        self.input_path = input_path
        # self.input_path = input_path.replace('\\', '/')
        self.p = p
        self.first_extant_path = None
        self.registered_dirs = self.p.registered_dirs

        if graft_dir is None:
            self.graft_dir = os.path.split(p.cur_dir)[1]
        else:
            self.graft_dir = graft_dir

        if os.path.exists(self.input_path):
            self.path = self.input_path

        else:

            if self.graft_dir is None:
                num_input_graftpoints = 0
            else:
                num_input_graftpoints = input_path.count(self.graft_dir)

            if num_input_graftpoints == 0:
                if verbose:
                    L.info('Graft dir not in input path or no graft_dir set. Graft_dir: ' + str(self.graft_dir) + '. Input path: ' + str(self.input_path))
                lhs, rhs_path = os.path.split(self.input_path)

                self.first_extant_path = self.get_first_extant_path(rhs_path)

                if self.first_extant_path is None:
                    self.path = self.input_path # Then it doesn't exist everywhere, so we will write it to the current dir by default. Could extend this later if needed.
                else:
                    self.path = self.first_extant_path

            elif num_input_graftpoints == 1:
                # NOTE: This is using
                lhs, grafted_rhs_path = self.input_path.split(self.graft_dir)

                if grafted_rhs_path[0:1] == '\\':
                    grafted_rhs_path = grafted_rhs_path[1:]
                if grafted_rhs_path[0:1] == '/':
                    grafted_rhs_path = grafted_rhs_path[1:]





                self.first_extant_path = self.get_first_extant_path(grafted_rhs_path)

                if self.first_extant_path is None:
                    self.path = self.input_path # Then it doesn't exist everywhere, so we will write it to the current dir by default. Could extend this later if needed.
                else:
                    self.path = self.first_extant_path
            else:
                raise NameError('Graft dir repeated in input path. Behavior NYI. Graft_dir: ' + str(self.graft_dir) + '. Input path: ' + str(self.input_path))

        if verbose:
            self.hb.log('Path object created and found the following attributes: \n'
                          '    input_path: ' + str(self.input_path) + '\n'
                          '    graft_dir: ' + str(self.graft_dir) + '\n'
                          '    first_extant_path: ' + str(self.first_extant_path) + '\n'
                          '    path: ' + str(self.path) + '\n'
                          '    registered_dirs: ' + str(self.registered_dirs) + '\n'
                          )

        # As a very last and controversial step, override windows' default backslashes:
        # self.input_path = self.input_path.replace('\\', '/')

    #
    # def __call__(self, *args, **kwargs):
    #     # return p.path
    #     return p.path.encode('unicode_escape')
    #
    # def __str__(self):
    #     # return self.path
    #     return self.path.encode('unicode_escape')
    #
    # def __repr__(self):
    #     return self.path

    def replace(selfs):
        raise NameError('Cannot use string mangling on Path objects. Perhaps you want to use a path-specific method.')

    def exists(self):
        return hb.path_exists(self.path)


    # def get_first_extant_path(self, input_path):
    #     for test_dir in self.registered_dirs:
    #         if test_dir is not None:
    #             current_path = os.path.join(test_dir, input_path)
    #             if os.path.exists(current_path):
    #                 return current_path
    #     # raise NameError('Unable to find path in registered dirs. Registered dirs: ' + str(self.registered_dirs))
    #     return None

    def register_dir(self, input_dirs):
        if isinstance(dirs, str):
            dirs = [dirs]
        for dir in dirs:
            self.registered_dirs.append(dir)



def get_dummy_scenarios_df():
    # Make a dataframe with a single row and a single column named scenario_type with the value 'baseline'
    df = pd.DataFrame(data={'scenario_type': ['baseline'], 'years': [2015]})
    return df



if __name__=='__main__':
    print ('cannot run by itself.')
