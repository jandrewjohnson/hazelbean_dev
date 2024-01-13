import os
import hazelbean as hb


input_path = r"C:\Files\Teaching\APEC 8222 - Big Data\Code\python_for_big_data\04_06_ridge_and_lasso.py"
output_path = input_path.replace('.py', '.ipynb')

hb.convert_py_script_to_jupyter(input_path)
