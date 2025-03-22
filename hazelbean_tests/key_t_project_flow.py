# NOTE Test is manual because uses CWD directly and inspeciton

import os, sys, time

import numpy as np
import hazelbean as hb

# DEVELOPMENT STATE:
# This includes a good idea, having a Path object that is defined as a global in the research script but then is used conditionally based on what is run
# but it isn't finished

p = hb.ProjectFlow('test_project')

# NOTE, for the task-level logging differentiation to happen, the logger must be assigned to the projectflow object.
p.L = hb.get_logger('manual_t_project_flow')





# print(af1)
def calculation_1(p):
    # global path1
    p.path1 = p.DataRef('data/global_1deg_floats.tif')

    hb.debug('Debug 1')
    hb.log('Info 1')
    p.L.warning('warning 1')
    # p.L.critical('critical 1')

    p.temp_path = hb.temp('.tif', remove_at_exit=True)
    if p.run_this:
        4

def calculation_2(p):
    hb.debug('Debug 2')
    hb.log('Info 2')
    p.L.warning('warning 2')
    if p.run_this:
        hb.log(p.temp_path)
        af1 = hb.ArrayFrame(p.path1)
        hb.log(af1)



p.add_task(calculation_1, logging_level=10)
p.add_task(calculation_2)



p.execute()

hb.remove_dirs('test_project', safety_check='delete')




