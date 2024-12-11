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
        "dask",
        "pygeoprocessing",
        "gdal",
        "rioxarray",
        "gdal",
        "python-pptx",
        "pandas",
        "pillow",
        "anytree",
        "pyyaml",
        "xlrd",
        "shapely",
        "scipy",
        "geopandas",
        "scikit-learn",
        "matplotlib",
        "statsmodels",
        "google-cloud",
        "netcdf4",
        "aenum",
        "descartes",
        "mpl-toolkits",
        "google-auth-oauthlib",
        "google-auth",
        "winshell",
        "qtpy",
        "natcap.invest",
        "six",
        "qtawesome",
        "sip",
        "pyro4",
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
