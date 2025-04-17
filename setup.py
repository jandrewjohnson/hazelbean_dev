from distutils.extension import Extension

import numpy
from Cython.Distutils import build_ext
from setuptools import find_packages
from setuptools import setup

setup(
    name='hazelbean',
    packages=find_packages(),
    include_package_data=True,
    description='Geospatial research tools',
    author='Justin Andrew Johnson',
    url='https://github.com/jandrewjohnson/hazelbean',
    # download_url='https://github.com/jandrewjohnson/hazelbean/releases/hazelbean_x64_py3.6.3/dist/hazelbean-0.3.0_x64_py3.6.3.tar.gz',
    keywords=['geospatial', 'raster', 'shapefile'],
    classifiers=[],
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
      "google-cloud",
      "google-cloud-datastore",
      "google-cloud-storage",
      # "libgdal-hdf5",
      "markdown",
      "matplotlib",
      # "matplotlib-base",
      "natcap.invest",
      "netcdf4",
      "numpy",
      "openpyxl",
      "pandas",
      "pandoc",
      "pillow",
      "pygeoprocessing",
      # "pyqt",
      # "python",
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
      "winshell",
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
