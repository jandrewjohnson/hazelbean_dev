from distutils.core import setup
from distutils.extension import Extension
from setuptools import setup, find_packages

packages=find_packages()
include_package_data=True

setup(
  name = 'hazelbean',
  packages = packages,
  version = '1.5.4',
  description = 'Geospatial research tools',
  author = 'Justin Andrew Johnson',
  url = 'https://github.com/jandrewjohnson/hazelbean',
  # download_url = 'https://github.com/jandrewjohnson/hazelbean/releases/hazelbean_x64_py3.6.3/dist/hazelbean-0.3.0_x64_py3.6.3.tar.gz',
  keywords = ['geospatial', 'raster', 'shapefile'],
  classifiers = [],
  ext_modules=[Extension("cython_functions", ["cython_functions.c"]),
               Extension("aspect_ratio_array_functions", ["aspect_ratio_array_functions.c"]),
               ]
)
