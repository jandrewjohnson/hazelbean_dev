from distutils.extension import Extension

import numpy
from Cython.Distutils import build_ext
from setuptools import find_packages
from setuptools import setup

setup(
    packages=find_packages(include=['hazelbean']),
    install_requires=[
      "Pyro4",
      "aenum",
      "anytree",
      "cython",
      "dask",
      "descartes",
      "gdal",
      "geopandas",
      "google-api-python-client",
      "google-auth",
      "google-auth-oauthlib",
      "google-cloud-datastore",
      "google-cloud-storage",
      "markdown",
      "matplotlib",
      "natcap.invest",
      "netcdf4",
      "numpy",
      "openpyxl",
      "pandas",
      "pillow",
      "pygeoprocessing",
      "python-pptx",
      "pyyaml",
      "qtawesome",
      "qtpy",
      "rioxarray",
      "scikit-learn",
      "scipy",
      "seaborn",
      "setuptools>=70.0.0",
      "setuptools_scm",
      "shapely",
      "sip",
      "six",
      "statsmodels",
      "taskgraph",
      "tqdm",
      "xarray",
      "xlrd",
    ],
    include_dirs=[numpy.get_include()],
    cmdclass={'build_ext': build_ext},
    ext_modules=[
        Extension(
          "hazelbean.calculation_core.cython_functions",
          ["hazelbean/calculation_core/cython_functions.pyx"]),
        Extension(
          "hazelbean.calculation_core.aspect_ratio_array_functions",
          ["hazelbean/calculation_core/aspect_ratio_array_functions.pyx"]),
      ]
)
