import os, sys, shutil

import os

import hazelbean as hb

# release_name = 'hazelbean_0.3.0_64bit_py3.6.3'
release_name = 'hazelbean_0.3.0_32bit_py2.7'
release_dir = os.path.join('..\\releases', release_name)

module_root_dir = '..'
print('release_dir', release_dir)
dirs_to_include = [module_root_dir, os.path.join(module_root_dir, 'pygeoprocessing3')]
filenames_to_exclude = ['pypi upload method.txt']

# First create the new release dir and copy found files to it
hb.create_directories(release_dir)
dirs_to_convert = []
for curdir in dirs_to_include:
    stripped_dir  = curdir.replace(module_root_dir, '')
    copy_dir = release_dir + '/hazelbean' + stripped_dir
    dirs_to_convert.append(copy_dir)
    hb.create_directories(copy_dir)

    release_files = hb.list_filtered_paths_recursively(curdir, depth=1, include_extensions='.py', exclude_strings=filenames_to_exclude)

    for curfile in release_files:
        copy_path = os.path.join(copy_dir, os.path.split(curfile)[1])

        print('copying ' + curfile + ' to ' + copy_path)
        shutil.copy(curfile, copy_path)

# Now copy setup files
setup_files = [
    '../releases/hazelbean_x64_py3.6.3/.pypirc',
    '../releases/hazelbean_x64_py3.6.3/setup.cfg',
    '../releases/hazelbean_x64_py3.6.3/setup.py',
    '../releases/hazelbean_x64_py3.6.3/LICENSE.txt',
    '../releases/hazelbean_x64_py3.6.3/MANIFEST',
                   ]
for filename in setup_files:
    file_root = os.path.split(filename)[1]
    new_filename = os.path.join(release_dir, file_root)
    print('Copying to ', new_filename)
    shutil.copy(filename, new_filename)

for curdir in dirs_to_convert:
    hb.execute_3to2_on_folder(curdir, filenames_to_exclude, do_write=True)

    # Remove backups
    baks = hb.list_files_in_dir_recursively(curdir, filter_extensions='.py.bak')
    print('Backups being deleted: ' + baks)
    for path in baks:
        os.remove(path)