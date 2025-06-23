import os, sys, warnings

import hazelbean as hb
# hazelbean_working_directory = '../hazelbean'
hazelbean_working_directory = hb.config.HAZELBEAN_WORKING_DIRECTORY
"""
TO COMPILE on windows 10, need to install proper Visual Studio tools: See::
https://stackoverflow.com/questions/29846087/microsoft-visual-c-14-0-is-required-unable-to-find-vcvarsall-bat
But basically, need to install 
"Tools for Visual Studio 2017, Build Tools for Visual Studio 2017, These Build Tools allow you to build Visual Studio projects from a command-line interface. Supported projects include: ASP.NET, Azure, C++ desktop, ClickOnce, containers, .NET Core, .NET Desktop, Node.js, Office and SharePoint, Python, TypeScript, Unit Tests, UWP, WCF, and Xamarin"."""


hazelbean_cython_directory = os.path.split(__file__)[0]
hazelbean_working_directory = os.path.split(hazelbean_cython_directory)[0]
CYTHON_FILES = ['compile_cython_functions.py']
recompile_cython = True # NEVER PUSH CODE WITH THIS SET TO TRUE!

if recompile_cython == True:
    # if os.path.exists(hazelbean_working_directory):
    # NOTE: This line will change the working dir of anything that imports it, so I was sure to set it back to original.
    old_cwd = os.getcwd()
    os.chdir(os.path.join(hazelbean_working_directory, 'calculation_core'))
    if sys.version_info[0] == 2:
        python_2_exe_dir = 'C:\\Anaconda2'
        os.chdir(python_2_exe_dir)

        for python_file_uri in CYTHON_FILES:
            python_file_uri = os.path.splitext(python_file_uri)[0] + '_27' + os.path.splitext(python_file_uri)[1]
            cython_command = "python.exe " + os.path.join(hazelbean_working_directory, python_file_uri) + " --quiet build_ext -i clean"  #
            # cython_command = "python " + python_file_uri + " --verbose build_ext -i clean"  #

            returned = os.system(cython_command)
            if returned:
                warnings.warn('Cythonization failed.')

    else:
        python_executable = sys.executable
        for python_file_uri in CYTHON_FILES:
            cython_command = python_executable + " " + python_file_uri + " --verbose build_ext -i clean"  #
            # cython_command = python_executable + " " + python_file_uri + " --quiet build_ext -i clean"  #
            # cython_command = "python " + python_file_uri + " --quiet build_ext -i clean"  #
            # cython_command = "python " + python_file_uri + " --verbose build_ext -i clean"  #
            returned = os.system(cython_command)
            if returned:
                warnings.warn('Cythonization failed.')

    # Set cwd back to original to clean up
    os.chdir(old_cwd)

