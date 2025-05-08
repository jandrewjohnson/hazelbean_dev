from distutils.extension import Extension

import numpy
from Cython.Distutils import build_ext
from setuptools import find_packages
from setuptools import setup

setup(
    packages=find_packages(include=['hazelbean']),
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
