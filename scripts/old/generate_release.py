import os, sys, shutil

import os

import hazelbean as hb

# DEPRECATED FOR relase_hazelbean_to_pypi
package_name = 'hazelbean'
version_number = '0.3.3'
release_name = package_name + '-' + version_number # dont include py version etc. that comes from wheels.
release_dir = os.path.join('..\\releases', release_name)

module_root_dir = '..'
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
    '../releases/default_setup_files/.pypirc',
    '../releases/default_setup_files/setup.cfg',
    '../releases/default_setup_files/README.md',
    # '../releases/default_setup_files/setup.py',
    '../releases/default_setup_files/LICENSE.txt',
    '../releases/default_setup_files/MANIFEST',
]
for filename in setup_files:
    file_root = os.path.split(filename)[1]
    new_filename = os.path.join(release_dir, file_root)
    print('Copying to ', new_filename)
    shutil.copy(filename, new_filename)


# Generate new setup.py file according to new release
setup_str = """from setuptools import setup, find_packages

packages=find_packages()
include_package_data=True

setup(
  name = '""" + str(package_name) + """',
  packages = packages,
  version = '""" + str(version_number) + """',
  description = 'Geospatial research tools',
  author = 'Justin Andrew Johnson',
  url = 'https://github.com/jandrewjohnson/""" + str(package_name) + """',
  download_url = 'https://github.com/jandrewjohnson/""" + str(package_name) + """/releases/""" + str(release_name) + """/dist/""" + str(release_name) + """.tar.gz',
  keywords = ['geospatial', 'raster', 'shapefile'],
  classifiers = [],
)
"""
setup_path = os.path.join(release_dir, 'setup.py')
with open(setup_path, "w") as text_file:
    text_file.write(setup_str)

# After running this, CD to the new dir and run the following commands:


os.chdir(release_dir)
# print(os.getcwd())

os.system('python setup.py sdist')

os.system('python setup.py bdist_wheel --universal')

os.system('twine upload dist/* --skip-existing')

## Creaete tar.gz of the source files.
# python setup.py sdist

## Creaete wheel. assumes pure python that works in all versions of python.
# python setup.py bdist_wheel --universal

## Upload with TWINE
# twine upload dist/* --skip-existing







