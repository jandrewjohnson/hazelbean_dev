import os
import hazelbean as hb
user_dir = os.path.expanduser("~")

float32_path = os.path.join(user_dir, 'Files', 'base_data', 'seals', 'static_regressors', 'change_dtype_20250508_090616_710nmt.tif')
float64_path = os.path.join(user_dir, 'Files', 'base_data', 'seals', 'static_regressors', 'change_dtype_20250508_095614_091wbw.tif')

hb.timer()

a = hb.as_array(float64_path, verbose=True)
hb.timer('float64')
a = None

b = hb.as_array(float32_path, verbose=True)
hb.timer('float32')
b = None