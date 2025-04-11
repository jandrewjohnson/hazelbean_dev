from __future__ import division, absolute_import, print_function
import sys, time, os

from hazelbean import json_helper # This enables hb.json_helper.parse_json_with_detailed_error(5)

# Set hb level options
import pandas as pd

# print('hazealbean __init__.py at ' + str(__file__))

# Set pandas maximum width to be 1000
pd.set_option('display.max_columns', 1000)
pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', 500)
            
import_medium_level = 1 # If this is not true, will import all of the HB library on first import, which can take up to 7 seconds.
use_strict_importing = 0 
import_extras = 0
use_strict_importing_for_ui = 0
report_import_times = 0

# Importing GDAL is tricky. Here we use the path of the current python interpretter to guess at the conda env path
# in order to set any missing GDAL environment variables.
conda_env_path = os.path.split(sys.executable)[0]

if 'GDAL_DATA' not in os.environ.__dict__:
    os.environ['GDAL_DATA'] = os.path.join(conda_env_path, 'Library', 'share', 'gdal')
elif not os.isdir(os.environ['GDAL_DATA']):
    os.environ['GDAL_DATA'] = os.path.join(conda_env_path, 'Library', 'share', 'gdal')
    
if 'PROJ_LIB' not in os.environ.__dict__:
    os.environ['PROJ_LIB'] = os.path.join(conda_env_path, 'Library', 'share', 'proj')
elif not os.path.exists(os.path.join(os.environ['PROJ_LIB'], 'proj.db')):
    os.environ['PROJ_LIB'] = os.path.join(conda_env_path, 'Library', 'share', 'proj')


import hazelbean.config # Needs to be imported before core so that hb.config.LAST_TIME_CHECK is set for hb.timer()
from hazelbean.config import *
# The most important and fast-loading things are in core which will be * imported each time.
from hazelbean import core    # Core is imported first so that I can use hb.timer() for import performance assessment.
from hazelbean.core import *

# Start a timer for assessing import performance.
import_start_time = time.time()

if report_import_times:
    hb.timer()

# Define the core features that are not defined in core.py 
from hazelbean.project_flow import ProjectFlow    
from hazelbean.project_flow import Task
if report_import_times:
    hb.timer('project_flow objects')
    
import hazelbean.globals
from hazelbean.globals import *
if report_import_times:
    hb.timer('globals')
    
# Define the core features that are not defined in core.py 
import hazelbean.vector
from hazelbean.vector import *
if report_import_times:
    hb.timer('vector')
    
import hazelbean.os_utils
from hazelbean.os_utils import *
if report_import_times:
    hb.timer('os_utils')
  
import hazelbean.pyramids
from hazelbean.pyramids import *
if report_import_times:
    hb.timer('pyramids')
  
import hazelbean.spatial_projection
from hazelbean.spatial_projection import *
if report_import_times:
    hb.timer('spatial_projection')
  

  
import hazelbean.geoprocessing_extension
from hazelbean.geoprocessing_extension import *
if report_import_times:
    hb.timer('geoprocessing_extension')
  
import hazelbean.spatial_utils
from hazelbean.spatial_utils import *
if report_import_times:
    hb.timer('spatial_utils')
  
import hazelbean.utils
from hazelbean.utils import *
if report_import_times:
    hb.timer('utils')
  
import hazelbean.arrayframe
from hazelbean.arrayframe import *
if report_import_times:
    hb.timer('arrayframe')
  
import hazelbean.arrayframe_functions
from hazelbean.arrayframe_functions import *
if report_import_times:
    hb.timer('arrayframe_functions')
  

import hazelbean.spatial_projection
from hazelbean.spatial_projection import *
if report_import_times:
    hb.timer('spatial_projection')
  
import hazelbean.file_io
from hazelbean.file_io import *
if report_import_times:
    hb.timer('file_io')

import hazelbean.raster_vector_interface
from hazelbean.raster_vector_interface import *
if report_import_times:
    hb.timer('raster_vector_interface')  
    
import hazelbean.cog
from hazelbean.cog import *
if report_import_times:
    hb.timer('cog')
    
import hazelbean.pog
from hazelbean.pog import *
if report_import_times:
    hb.timer('pog')
   
if import_medium_level:
    
    import hazelbean.geoprocessing
    from hazelbean.geoprocessing import *
    if report_import_times:
        hb.timer('geoprocessing')
        

    
    
    # FOR FUTURE: add init import option for load all into hb namespace., then, reconfigure hazelbean into stats, spatial, parallel, and other TOP LEVEL categories that I will make as subdirectories (i think)
    # from hazelbean.pyramids import *
    
    import hazelbean.geoprocessing_extension
    if report_import_times:
        hb.timer('geoprocessing_extension')

    import hazelbean.spatial_projection
    if report_import_times:
        hb.timer('spatial_projection')

    from hazelbean.globals import *
    from hazelbean.config import *
    if report_import_times:
        hb.timer('config')        
    import hazelbean.arrayframe
    from hazelbean.arrayframe import *
    if report_import_times:
        hb.timer('arrayframe')

    import hazelbean.arrayframe_functions
    from hazelbean.arrayframe_functions import *
    if report_import_times:
        hb.timer('arrayframe_functions')
    import hazelbean.cat_ears
    from hazelbean.cat_ears import *
    if report_import_times:
        hb.timer('cat_ears')
    import hazelbean.file_io
    from hazelbean.file_io import *
    if report_import_times:
        hb.timer('file_io')
    import hazelbean.geoprocessing_extension
    from hazelbean.geoprocessing_extension import *
    if report_import_times:
        hb.timer('geoprocessing_extension')
    import hazelbean.os_utils
    from hazelbean.os_utils import *
    if report_import_times:
        hb.timer('os_utils')
    import hazelbean.project_flow
    from hazelbean.project_flow import *
    if report_import_times:
        hb.timer('project_flow')
    import hazelbean.pyramids
    from hazelbean.pyramids import *
    if report_import_times:
        hb.timer('pyramids')
    import hazelbean.spatial_projection
    from hazelbean.spatial_projection import *
    if report_import_times:
        hb.timer('spatial_projection')
    import hazelbean.spatial_utils
    from hazelbean.spatial_utils import *
    if report_import_times:
        hb.timer('spatial_utils')
    import hazelbean.stats
    from hazelbean.stats import *
    if report_import_times:
        hb.timer('stats')
    import hazelbean.utils
    from hazelbean.utils import *
    if report_import_times:
        hb.timer('utils')
    import hazelbean.raster_vector_interface
    from hazelbean.raster_vector_interface import *
    if report_import_times:
        hb.timer('raster_vector_interface')

    if use_strict_importing: # Protect cython imports so that a user without compiled files can still use the rest of hb
        import hazelbean.calculation_core
        from hazelbean.calculation_core import *
        if report_import_times:
            hb.timer('calculation_core')

        
        import hazelbean.calculation_core.cython_functions
        from hazelbean.calculation_core.cython_functions import *
        if report_import_times:
            hb.timer('cython_functions')
    
    
        import hazelbean.calculation_core.aspect_ratio_array_functions
        from hazelbean.calculation_core.aspect_ratio_array_functions import *
        if report_import_times:
            hb.timer('aspect_ratio_array_functions')

        import hazelbean.visualization
        from hazelbean.visualization import *
        if report_import_times:
            hb.timer('visualization')        

    else:
        try:
            import hazelbean.calculation_core.cython_functions
            from hazelbean.calculation_core.cython_functions import *
            if report_import_times:
                hb.timer('cython_functions')

            import hazelbean.calculation_core.aspect_ratio_array_functions
            from hazelbean.calculation_core.aspect_ratio_array_functions import *
            if report_import_times:
                hb.timer('aspect_ratio_array_functions')

            import hazelbean.visualization
            from hazelbean.visualization import *
            if report_import_times:
                hb.timer('visualization')            

        except:
            print('Unable to import cython-based functions, but this may not be a problem.')

# Optional imports for performance
if import_extras:
    if use_strict_importing_for_ui:

        import hazelbean.ui
        from hazelbean.ui import *

        import hazelbean.ui.auto_ui
        from hazelbean.ui.auto_ui import *

        import hazelbean.watershed_processing
        from hazelbean.watershed_processing import *

    else:
        try:

            
            import hazelbean.ui
            from hazelbean.ui import *

            import hazelbean.ui.auto_ui
            from hazelbean.ui.auto_ui import *

            import hazelbean.watershed_processing
            from hazelbean.watershed_processing import *

        except:
            pass
        
if report_import_times:
    print('Total Hazelbean import time: ' + str(time.time() - import_start_time))






