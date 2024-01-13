
    import os

import hazelbean as hb

target_dir = '../pygeoprocessing3_06'
# target_dir = '../invest'
# target_dir = '../versioner'
# target_dir = '.'
# Print the results
hb.execute_2to3_on_folder(target_dir)

# Actually do it
hb.execute_2to3_on_folder(target_dir, do_write=True)

# Remove backups
baks = hb.list_files_in_dir_recursively(target_dir, filter_extensions='.py.bak')
print(baks)
for path in baks:
    os.remove(path)