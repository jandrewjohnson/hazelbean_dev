import xarray as xr
import intake
import numpy as np
from scipy import optimize
from numba import njit, vectorize
import fsspec
xr.set_options(display_style='html') # make the display_style of xarray more user friendlymamba install numbamamba
import dask