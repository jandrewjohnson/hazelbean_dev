from distutils.extension import Extension

from setuptools import find_packages
from setuptools import setup

setup(
    name='hazelbean',
    packages=find_packages(),
    include_package_data=True,
    version='1.5.4',
    description='Geospatial research tools',
    author='Justin Andrew Johnson',
    url='https://github.com/jandrewjohnson/hazelbean',
    # download_url='https://github.com/jandrewjohnson/hazelbean/releases/hazelbean_x64_py3.6.3/dist/hazelbean-0.3.0_x64_py3.6.3.tar.gz',
    keywords=['geospatial', 'raster', 'shapefile'],
    classifiers=[],
    ext_modules=[
        Extension(
          "hazelbean.calculation_core.cython_functions",
          ["hazelbean/calculation_core/cython_functions.pyx"]),
        Extension(
          "hazelbean.calculation_core.aspect_ratio_array_functions",
          ["hazelbean/calculation_core/aspect_ratio_array_functions.pyx"]),
      ]
)
