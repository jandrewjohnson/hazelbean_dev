import os, sys, time

start = time.time()
import hazelbean as hb
print('initial import hazelbean took ' + str(time.time() - start))

hb.timer('Starting internal timer')


from  hazelbean.geoprocessing import warp_raster

hb.timer('1')

from hazelbean.calculation_core import aspect_ratio_array_functions
from hazelbean.calculation_core.aspect_ratio_array_functions import cython_calc_proportion_of_coarse_res_with_valid_fine_res

hb.timer('2')
print(cython_calc_proportion_of_coarse_res_with_valid_fine_res)

from hazelbean.calculation_core.cython_functions import angle_to_radians

hb.timer('3')

print('Test complete.')