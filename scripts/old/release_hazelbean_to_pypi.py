# TO RUN THIS in vscode, make sure to use the run in IntegratedTerminal launch setup so that you can enter your username and password.

import os, sys, shutil, setuptools, subprocess
sys.path.insert(0, 'c:/users/jajohns/Files/Research/hazelbean/hazelbean_dev')
import hazelbean as hb


release_name = 'hazelbean_1.6.0'
version = release_name.split('_')[1]
target_dir = '..'
release_dir = os.path.join('../../', 'hazelbean_stable')
release_dist_dir = os.path.join('../../hazelbean_stable', 'dist')

if not os.path.exists(release_dir):
    os.mkdir(release_dir)

if not os.path.exists(release_dist_dir):
    os.mkdir(release_dist_dir)

dirs_to_copy = ['hazelbean']
# dirs_to_copy = ['hazelbean', 'tests', 'docs']

files_to_copy = [
    "LICENSE",
    # "MANIFEST",
    "MANIFEST.in",
    "README.md",
    "setup.cfg",
    ".pypirc",
    # "requirements.txt",
]

for dir_ in dirs_to_copy:
    src = os.path.join(target_dir, dir_)
    dst = os.path.join(release_dir, dir_)
    print('Copying dir ' + src + ' to ' + dst)
    print('hb', hb)
    hb.copy_shutil_flex(src, dst)


# if os.path.exists(release_dir):
#     print('release_dir', release_dir)
#     hb.remove_dirs(release_dir, safety_check='delete')

if os.path.exists(release_dist_dir):
    for i in os.listdir(release_dist_dir):
        if version in i:
            raise NameError('That version of hb already exists. Increment it up you fool!')


for file in files_to_copy:
    src = os.path.join(target_dir, file)
    dst = os.path.join(release_dir, file)
    hb.copy_shutil_flex(src, dst)

optional_if_want_to_enforce_install_requirements = """

_REQUIREMENTS = [
    x for x in open(os.path.join('requirements.txt')).read().split('\\n')
    if not x.startswith('#') and len(x) > 0]



and then below becofe ext_modules:

install_requires=_REQUIREMENTS,

"""

setup_string = """
from setuptools import setup, find_packages
from distutils.extension import Extension
from Cython.Distutils import build_ext
from Cython.Build import cythonize
import numpy
import os



with open("README.md", "r") as fh:
    long_description = fh.read()

packages=find_packages()
include_package_data=True

setup(
  name = 'hazelbean',
  packages = packages,
  version = '""" + version + """',
  description = 'Geospatial research tools',
  long_description = 'Geospatial research tools for economics and sustainability science.',
  author = 'Justin Andrew Johnson',
  url = 'https://github.com/jandrewjohnson/hazelbean',
  download_url = 'https://github.com/jandrewjohnson/hazelbean',
  keywords = ['geospatial', 'raster', 'shapefile', 'sustainability science'],
  classifiers = ["Programming Language :: Python :: 3"],
  #cmdclass={'build_ext': build_ext},
  #ext_modules=[Extension("cython_functions", ["hazelbean/calculation_core/cython_functions.c"]),
  #             Extension("aspect_ratio_array_functions", ["hazelbean/calculation_core/aspect_ratio_array_functions.c"]),
  #             ]

  ext_modules=cythonize(
    [Extension(
        "hazelbean.calculation_core.cython_functions",
        sources=["hazelbean/calculation_core/cython_functions.pyx"],
        include_dirs=[
            numpy.get_include(),
            'hazelbean/calculation_core/cython_functions'],
        language="c++",
    ),
     Extension(
         "hazelbean.calculation_core.aspect_ratio_array_functions",
         sources=[
             "hazelbean/calculation_core/aspect_ratio_array_functions.pyx"],
         include_dirs=[numpy.get_include()],
         language="c++")],
    )

)
"""


setup_py_file_path = os.path.join(release_dir, 'setup.py')
print('Writing setup to ' + setup_py_file_path)
with open(setup_py_file_path, 'w') as fp:
    fp.write(setup_string)

os.chdir(release_dir)
env_name = 'env2023a'
command = 'conda activate ' + env_name + ' && python setup.py sdist bdist_wheel'
os.system(command)

# Under the Projects Anaconda environment, I installed Twine and Keyring
# Used keyring to authenticate pypi.org account:
# python -m keyring set https://upload.pypi.org/ jandrewjohnson
# This makes the following twine command work.

# IF TWINE FAILS: Run this script, exit out when it hangs on twine. Open comand prompt at the hazelbean_stable/dist dir
# and run the command below. This will allow you to enter your credentials manually.
command = 'conda activate ' + env_name + ' && twine upload dist/* --skip-existing'
os.system(command)
# os.system('twine upload dist/* --skip-existing'



## DO NOT USE THIS, YOU FOOL, JUST DO IT MANUALLY YOU LAZY IDIOT
# print(os.getcwd())
# os.chdir(release_dir)
#
# for dir_ in dirs_to_copy:
#     print('dir_', dir_)
#     os.system('git add .')
#
# for file in files_to_copy:
#     print('file', file)
#     os.system('git add ' + str(file))
#
# os.system('git commit -m "' + release_name + '"')
# # os.system('git tag -a v' + str(version) + ' -m "release ' + release_name + '"')
#
# # subprocess.run('git push --tags')
# subprocess.run('git push -u origin master')





