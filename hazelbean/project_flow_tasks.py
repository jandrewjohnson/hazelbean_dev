""" Contains project agnostic tasks for the project flow. """

import os
import sys
import hazelbean as hb
import shutil



def test_cleanup_preparation(p):
    # This is a test function that will be used to clean up the project directory before running the project flow. It will delete all files in the project directory that are not in the list of allowed files. This is useful for testing purposes to ensure that the project flow is working correctly and that there are no leftover files from previous runs that could interfere with the current run.
    is_mac = sys.platform == 'darwin'
    use_elementwise_deletion = False
    if use_elementwise_deletion:
        hb.log("Using elementwise deletion of files in intermediate directory for testing purposes.")
        if is_mac:
            hb.log("Running on Mac - skipping file deletion of GEMPACK FILES for testing purposes.")
            if p.run_this:
                allowed_files = ['har', 'sl4', 'upd', 'slc', 'log']
                for root, dirs, files in os.walk(p.intermediate_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if not any(file.endswith(ext) for ext in allowed_files):
                            print(f"Deleting file: {file_path}")
                            os.remove(file_path)
                        else:
                            print(f"Keeping file: {file_path}")
        else:
            hb.log("Running on non-Mac - deleting all files in intermediate directory for testing purposes.")
            if p.run_this:
                for root, dirs, files in os.walk(p.intermediate_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        print(f"Deleting file: {file_path}")
                        os.remove(file_path)
    else:
        hb.log("Using directory-level deletion of intermediate directory for testing purposes.")
        if p.run_this:
            dirs_to_keep_if_mac = ['initial_gtap_runs', 'gtap_runs']
            if is_mac:
                hb.log("Running on Mac - deleting top-level directories not in keep list for testing purposes.")
                if os.path.exists(p.intermediate_dir):
                    for dirname in os.listdir(p.intermediate_dir):
                        dirpath = os.path.join(p.intermediate_dir, dirname)
                        if os.path.isdir(dirpath):
                            if dirname not in dirs_to_keep_if_mac:
                                print(f"Deleting directory: {dirpath}")
                                shutil.rmtree(dirpath)
                            else:
                                print(f"Keeping directory: {dirpath}")
            else:
                hb.log("Running on non-Mac - deleting all contents of intermediate directory for testing purposes.")
                if os.path.exists(p.intermediate_dir):
                    for name in os.listdir(p.intermediate_dir):
                        path = os.path.join(p.intermediate_dir, name)
                        if os.path.isdir(path):
                            print(f"Deleting directory: {path}")
                            shutil.rmtree(path)
                        else:
                            print(f"Deleting file: {path}")
                            os.remove(path)
