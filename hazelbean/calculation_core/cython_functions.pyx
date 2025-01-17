# cython: cdivision=True
# define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#cython: boundscheck=True, wraparound=False
from libc.math cimport log
from libc.stdlib cimport malloc, free
import time
from collections import OrderedDict
from xarray import DataArray
from cython.parallel cimport prange

import cython
cimport cython

from osgeo import gdal, osr, ogr

# NOTE, both imports are required. cimport adds extra information to the pyd while the import actually defines numppy
import numpy as np
cimport numpy as np
from numpy cimport ndarray 

from libc.math cimport sin
from libc.math cimport fabs
import math, time

from cython.view cimport array as cvarray

DTYPEUINT8 = np.uint8

DTYPEBYTE = np.byte
# DTYPEINT = np.int
DTYPEINT32 = np.int32
DTYPEINT64 = np.int64
# DTYPELONG = np.long
DTYPEFLOAT32 = np.float32
DTYPEFLOAT64 = np.float64
ctypedef np.uint8_t DTYPEUINT8_t
# ctypedef np.int_t DTYPEINT_t
ctypedef np.int32_t DTYPEINT32_t
ctypedef np.int64_t DTYPEINT64_t
ctypedef np.float32_t DTYPEFLOAT32_t
ctypedef np.float64_t DTYPEFLOAT64_t


from libc.stdlib cimport rand
cdef extern from "limits.h":
    int INT_MAX

cdef extern from "math.h" nogil:
    double M_E
    double M_LOG2E
    double M_LOG10E
    double M_LN2
    double M_LN10
    double M_PI
    double M_PI_2
    double M_PI_4
    double M_1_PI
    double M_2_PI
    double M_2_SQRTPI
    double M_SQRT2
    double M_SQRT1_2

    # C99 constants
    float INFINITY
    float NAN
    double HUGE_VAL
    float HUGE_VALF
    long double HUGE_VALL

    double acos(double x)
    double asin(double x)
    double atan(double x)
    double atan2(double y, double x)
    double cos(double x)
    double sin(double x)
    double tan(double x)

    double cosh(double x)
    double sinh(double x)
    double tanh(double x)
    double acosh(double x)
    double asinh(double x)
    double atanh(double x)

    double hypot(double x, double y)

    double exp(double x)
    double exp2(double x)
    double expm1(double x)
    double log(double x)
    double logb(double x)
    double log2(double x)
    double log10(double x)
    double log1p(double x)
    int ilogb(double x)

    double lgamma(double x)
    double tgamma(double x)

    double frexp(double x, int* exponent)
    double ldexp(double x, int exponent)

    double modf(double x, double* iptr)
    double fmod(double x, double y)
    double remainder(double x, double y)
    double remquo(double x, double y, int *quot)
    double pow(double x, double y)
    double sqrt(double x)
    double cbrt(double x)

    double fabs(double x)
    double ceil(double x)
    double floor(double x)
    double trunc(double x)
    double rint(double x)
    double round(double x)
    double nearbyint(double x)
    double nextafter(double, double)
    double nexttoward(double, long double)

    long long llrint(double)
    long lrint(double)
    long long llround(double)
    long lround(double)

    double copysign(double, double)
    float copysignf(float, float)
    long double copysignl(long double, long double)

    double erf(double)
    float erff(float)
    long double erfl(long double)
    double erfc(double)
    float erfcf(float)
    long double erfcl(long double)

    double fdim(double x, double y)
    double fma(double x, double y)
    double fmax(double x, double y)
    double fmin(double x, double y)
    double scalbln(double x, long n)
    double scalbn(double x, int n)

    double nan(const char*)

    bint isfinite(long double)
    bint isnormal(long double)
    bint isnan(long double)
    bint isinf(long double)

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_uint8_to_uint8_by_dict(unsigned char[::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEUINT8)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_uint8_to_uint8_by_array(unsigned char[::, ::1] input_array, unsigned char[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEUINT8)
    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array


@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef long[::, ::1] reclassify_uint8_to_int_by_dict(unsigned char[::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef long[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEINT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(True)
@cython.wraparound(False)
cpdef long[::, ::1] reclassify_uint8_to_int_by_array(unsigned char[::, ::1] input_array, long[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef long[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEINT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array


@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef long[::, ::1] reclassify_int_to_int_by_dict(long[::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef long[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEINT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef long[::, ::1] reclassify_int_to_int_by_array(long[::, ::1] input_array, long[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef long[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEINT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array


@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_int_to_uint8_by_dict(long[::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEUINT8)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_int_to_uint8_by_array(long[::, ::1] input_array, unsigned char[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEUINT8)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array


@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float[::, ::1] reclassify_uint8_to_float32_by_dict(unsigned char[::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef float[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float[::, ::1] reclassify_uint8_to_float32_by_array(unsigned char[::, ::1] input_array, float[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef float[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef double[::, ::1] reclassify_uint8_to_float64_by_dict(unsigned char [::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef double[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT64)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef double[::, ::1] reclassify_uint8_to_float64_by_array(unsigned char[::, ::1] input_array, double[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef double[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT64)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float[::, ::1] reclassify_int_to_float32_by_dict(long[::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef float[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float[::, ::1] reclassify_int_to_float32_by_array(long[::, ::1] input_array, float[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef float[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef double[::, ::1] reclassify_int_to_float64_by_dict(long [::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef double[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT64)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef double[::, ::1] reclassify_int_to_float64_by_array(long[::, ::1] input_array, double[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef double[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT64)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float[::, ::1] reclassify_int64_to_float32_by_dict(long long [::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef float[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float[::, ::1] reclassify_int64_to_float32_by_array(long long [::, ::1] input_array, float[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef float[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef double[::, ::1] reclassify_int64_to_float64_by_dict(long long [::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef double[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT64)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef double[::, ::1] reclassify_int64_to_float64_by_array(long long[::, ::1] input_array, double[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef double[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEFLOAT64)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_int64_to_uint8_by_dict(long long[::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEUINT8)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]

    return output_array

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_int64_to_uint8_by_array(long long[::, ::1] input_array, unsigned char[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEUINT8)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]


@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_int64_to_int_by_dict(long long[::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEINT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]


@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_int64_to_int_by_array(long long[::, ::1] input_array, unsigned char[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEINT32)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_int64_to_int64_by_dict(long long[::, ::1] input_array, dict rules):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEINT64)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules[input_array[r, c]]


@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cpdef unsigned char[::, ::1] reclassify_int64_to_int64_by_array(long long[::, ::1] input_array, unsigned char[::1] rules_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c
    cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEINT64)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = rules_array[input_array[r, c]]

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(True)
@cython.wraparound(False)
def reclassify_uint8_to_uint8_by_dict_with_dask(unsigned char[::, ::, ::1] input_array):
    cdef long n_rows = input_array.shape[0]
    cdef long n_cols = input_array.shape[1]
    cdef long r, c, a
    #cdef unsigned char[::, ::1] output_array = np.empty([n_rows, n_cols], dtype=DTYPEUINT8)
    cdef np.ndarray[np.uint8_t, ndim=2] output_array = np.zeros([n_rows, n_cols], dtype=DTYPEUINT8)

    for r in range(n_rows):
        for c in range(n_cols):
            output_array[r, c] = input_array[1, r, c] + 1
    return output_array

def array_plus_one(const double [:,:,:] input_array):
    cdef const double[:, :, ::1] input_view = input_array.copy()

    cdef Py_ssize_t i, j, k, x_max, y_max, z_max
    x_max = input_view.shape[0]
    y_max = input_view.shape[1]
    z_max = input_view.shape[2]  
    result = np.zeros((x_max, y_max, z_max), dtype=np.float64)
    cdef double[:, :, ::1] result_view = result

 
    for i in prange(x_max,nogil=True):
        for j in range(y_max):
            for k in range(z_max):
                result_view[i,j,k] = 1
                #result_view[i,j,k] = 2 + input_view[i,j,k]
    return result
    
    


def dist(int start_row, int start_col, int end_row, int end_col):
    return pow(pow((start_row - end_row),2)+pow((start_col - end_col),2),.5)

def angle_between_coords(int start_row, int start_col, int end_row, int end_col): #returns degree or -1 if start=end
    if end_col - start_col != 0:
        return atan2((end_row - start_row),(end_col - start_col)) * 180 / M_PI
    else:
        if end_row > start_row:
            return 90
        elif start_row > end_row:
            return -90
        else:
            return -1 #indicates end location IS start location

def angle_to_radians(double angle):
    cdef double radians
    radians = angle * M_PI/180
    return radians

def get_array_neighborhood_by_radius(np.ndarray[DTYPEFLOAT32_t, ndim=2] input_array, int point_x, int point_y, int radius, double fill_value = -255):
    cdef int num_input_rows = input_array.shape[0]
    cdef int num_input_cols = input_array.shape[1]
    cdef int diameter = 2 * radius + 1
    cdef int neighborhood_r,neighborhood_c, offset_r, offset_c

    cdef int offset_start = -1 * radius

    cdef np.ndarray[DTYPEINT32_t, ndim=2] offset_r_array = np.empty([diameter, diameter], dtype=DTYPEINT32)
    cdef np.ndarray[DTYPEINT32_t, ndim=2] offset_c_array = np.empty([diameter, diameter], dtype=DTYPEINT32)
    for offset_r in range(diameter):
        for offset_c in range(diameter):
            offset_r_array[offset_r, offset_c] = offset_start + offset_r
            offset_c_array[offset_r, offset_c] = offset_start + offset_c


    cdef np.ndarray[DTYPEFLOAT32_t, ndim=2] output_array = np.zeros([diameter, diameter], dtype=DTYPEFLOAT32)

    for neighborhood_r in range(diameter):
        for neighborhood_c in range(diameter):
            if 0 <= point_y + (offset_r_array[neighborhood_r, neighborhood_c]) < num_input_rows and  0 <= point_x + (offset_c_array[neighborhood_r, neighborhood_c]) < num_input_cols:
                output_array[neighborhood_r, neighborhood_c] = input_array[point_y + offset_r_array[neighborhood_r, neighborhood_c], point_x + offset_c_array[neighborhood_r, neighborhood_c]]
            else:
                output_array[neighborhood_r, neighborhood_c] = fill_value
    return output_array

def get_rc_of_max_in_array(np.ndarray[DTYPEFLOAT32_t, ndim=2] input_array, str heuristic='default'):
    cdef int n_rows = input_array.shape[0]
    cdef int n_cols = input_array.shape[1]
    cdef int test_row, test_col
    cdef float heuristic_value
    cdef int center_r = (n_rows - 1)/2
    cdef int center_c = (n_cols - 1)/2



    cdef int max_row = 0
    cdef int max_col = 0
    cdef double max_value = 0.0

    if heuristic == 'default':
        heuristic_value = 0.0
    elif heuristic == 'euclidean':
        heuristic_value = .5

    for test_row in range(n_rows):
        for test_col in range(n_cols):
            if input_array[test_row, test_col] > max_value:
                max_value = input_array[test_row, test_col] - dist(center_r, center_c, test_row, test_col) * input_array[test_row, test_col] * heuristic_value
                max_row = test_row
                max_col = test_col

    return max_row, max_col


@cython.boundscheck(False)
def build_julia_set(int N):
    cdef np.ndarray[np.uint8_t, ndim=2] T = np.empty((N, 2*N), dtype=np.uint8)
    cdef double complex c = -0.835 - 0.2321j
    cdef double complex z
    cdef int J, I
    cdef double h = 2.0/N
    cdef double x, y
    for J in range(N):
        for I in range(2*N):
            y = -1.0 + J*h
            x = -2.0 + I*h
            T[J,I] = 0
            z = x + 1j * y
            while z.imag**2 + z.real**2 <= 4:
                z = z**2 + c
                T[J,I] += 1
    return T




# NOTE By specifying value and no_data_value as np.float32_t, this avoids the error conversion of double to np and might be faster,
@cython.boundscheck(False)
def multiply_by_float_where_not_float_32(ndarray[np.float32_t, ndim=2] a not None, np.float32_t value, np.float32_t no_data_value):
    cdef Py_ssize_t r
    cdef Py_ssize_t c
    cdef Py_ssize_t nr = a.shape[0]
    cdef Py_ssize_t nc = a.shape[1]
    cdef np.float32_t v

    for r in range(nr):
        for c in range(nc):
            v = a[r, c]
            if v != no_data_value:
                a[r, c] = v * value

    return a


@cython.boundscheck(False)
def divide_by_float_where_not_float_32(ndarray[np.float32_t, ndim=2] a not None, np.float32_t value, np.float32_t no_data_value):
    cdef Py_ssize_t r
    cdef Py_ssize_t c
    cdef Py_ssize_t nr = a.shape[0]
    cdef Py_ssize_t nc = a.shape[1]
    cdef np.float32_t v

    for r in range(nr):
        for c in range(nc):
            v = a[r, c]
            if v != no_data_value:
                a[r, c] = v / value

    return a


@cython.boundscheck(False)
def add_by_float_where_not_float_32(ndarray[np.float32_t, ndim=2] a not None, np.float32_t value, np.float32_t no_data_value):
    cdef Py_ssize_t r
    cdef Py_ssize_t c
    cdef Py_ssize_t nr = a.shape[0]
    cdef Py_ssize_t nc = a.shape[1]
    cdef np.float32_t v

    for r in range(nr):
        for c in range(nc):
            v = a[r, c]
            if v != no_data_value:
                a[r, c] = v + value
    return a

@cython.boundscheck(False)
def subtract_by_float_where_not_float_32(ndarray[np.float32_t, ndim=2] a not None, np.float32_t value, np.float32_t no_data_value):
    cdef Py_ssize_t r
    cdef Py_ssize_t c
    cdef Py_ssize_t nr = a.shape[0]
    cdef Py_ssize_t nc = a.shape[1]
    cdef np.float32_t v

    for r in range(nr):
        for c in range(nc):
            v = a[r, c]
            if v != no_data_value:
                a[r, c] = v - value
    return a




@cython.boundscheck(False)
def multiply_by_array_where_not_float_32(ndarray[np.float32_t, ndim=2] a not None, ndarray[np.float32_t, ndim=2] b not None, np.float32_t no_data_value_a, np.float32_t no_data_value_b=-9999.0):
    cdef Py_ssize_t r
    cdef Py_ssize_t c
    cdef Py_ssize_t nr = a.shape[0]
    cdef Py_ssize_t nc = a.shape[1]
    cdef np.float32_t va
    cdef np.float32_t vb

    if no_data_value_b == -9999.0:
        for r in range(nr):
            for c in range(nc):
                va = a[r, c]
                vb = b[r, c]
                if va != no_data_value_a and vb != no_data_value_b:
                    a[r, c] = va * vb
    else:
        for r in range(nr):
            for c in range(nc):
                va = a[r, c]
                vb = b[r, c]
                if va != no_data_value_a and vb != no_data_value_b:
                    a[r, c] = va * vb

    return a


@cython.boundscheck(False)
def multiply_by_array_32(ndarray[np.float32_t, ndim=2] a not None, ndarray[np.float32_t, ndim=2] b not None, np.float32_t no_data_value_a=False, np.float32_t no_data_value_b=False):
    cdef Py_ssize_t r
    cdef Py_ssize_t c
    cdef Py_ssize_t nr = a.shape[0]
    cdef Py_ssize_t nc = a.shape[1]
    cdef np.float32_t va
    cdef np.float32_t vb

    if no_data_value_a and no_data_value_b:
        for r in range(nr):
            for c in range(nc):
                va = a[r, c]
                vb = b[r, c]
                if va != no_data_value_a and vb != no_data_value_b:
                    a[r, c] = va * vb
    elif no_data_value_a and not no_data_value_b:
        for r in range(nr):
            for c in range(nc):
                va = a[r, c]
                vb = b[r, c]
                if va != no_data_value_a:
                    a[r, c] = va * vb
    elif not no_data_value_a and no_data_value_b:
        for r in range(nr):
            for c in range(nc):
                va = a[r, c]
                vb = b[r, c]
                if vb != no_data_value_b:
                    a[r, c] = va * vb
    else:
        for r in range(nr):
            for c in range(nc):
                va = a[r, c]
                vb = b[r, c]
                a[r, c] = va * vb

    return a



@cython.boundscheck(False)
def allocate_among_rank_arrays(ndarray[DTYPEINT32_t, ndim=2] initial_classes not None,
                                ndarray[DTYPEFLOAT64_t, ndim=3] rank_array not None,
                                ndarray[DTYPEFLOAT64_t, ndim=3] ranked_keys not None,
                                ndarray[DTYPEINT32_t, ndim=1] input_class_counters not None,
                                ndarray[DTYPEINT32_t, ndim=1] input_class_ids not None,
                                ndarray[DTYPEINT32_t, ndim=1] all_class_counters not None,
                                ndarray[DTYPEINT32_t, ndim=1] all_class_ids not None,
                                ndarray[DTYPEINT32_t, ndim=1] net_change_ids not None,
                                ndarray[DTYPEFLOAT64_t, ndim=1] net_change_values not None,
                                ndarray[DTYPEINT32_t, ndim=1] cells_per_step_by_class not None,
                                ndarray[DTYPEINT32_t, ndim=1] count_of_all_classes not None,
                                DTYPEINT32_t report_threshold=100,
                                DTYPEINT32_t report_each_conversion=0,
                                DTYPEINT32_t report_replacement_class_logic=0,
                                DTYPEFLOAT32_t ndv=False):

    # initial classes: int array r by c
    # rank_array Rank array, integer raster of r by c shape with 1 indiating first cell to allocate
    # ranked_keys Keys of the ranked array, in orderof first to allocate to last.
    # net_change_values 1 dim array indicating net changes for each class.
    # cells_per_step_by_class 1 dim array indicating allocations per step for each class. Will be 1 for whichever classes have the least nonzero to allocate.
    # ndv = no data value

    # LEARNING POINT: I used float64s even though int64s would be intuitive because numpy doesnt have that type.

    # Challenging point: I need to make it so the 3dim arrays are as compact as possible, representing only things that have convolution arrays.
    # I also want to be flexible for when there is an lulc map with a type not specified in the 3dim array. I
    # think i will create an input ordered dict that is then just check and fail if exists an unknown value.

    cdef int n_input_classes = rank_array.shape[0]
    cdef int n_all_classes = all_class_ids.shape[0]
    cdef int n_rows = rank_array.shape[1]
    cdef int n_cols = rank_array.shape[2]


    # Only have non-zero where the is a change
    cdef np.ndarray[np.uint8_t, ndim=2] changed_cells = np.zeros((n_rows, n_cols), dtype=np.uint8)

    # 1 by n_input_classes array that records the current position within the keys_rank for each class
    cdef np.ndarray[np.float64_t, ndim=1] positions = np.zeros((n_input_classes), dtype=np.float64)

    # 1 by n_input_classes array that records the current position within the keys_rank for each class
    cdef np.ndarray[np.float64_t, ndim=1] initial_net_change_values = np.copy(net_change_values)


    #cdef np.ndarray[np.float64_t, ndim=1] class_counters_from_class_ids = np.copy(net_change_values)


    # If all values in this are 0, then the allocation is done.
    cdef np.ndarray[np.uint8_t, ndim=1] continue_test = np.ones((n_input_classes), dtype=np.uint8)


    # counters
    cdef int class_counter, r, c, initial_position_set_counter, replacement_class, replacement_class_counter, class_to_be_replaced
    cdef double w, step_pos, test_key_r, test_key_c, best_replacement_score, replacement_score, gamma

    cdef int cont = 1
    cdef int ticks = 1
    cdef int cont_sum = 0
    cdef int n_cells = n_rows * n_cols



    cdef double step_counter = 0.0

    # TODO This was a horibly confusing thing. How could I have kept this all parallel. One downside it idoes is make the reported outputs no in the same order.
    # Create a lookup dict to go from counter to class id
    #cdef dict class_counters_from_class_ids = {}
    #for i in range(n_classes):
    #    class_counters_from_class_ids[class_ids[i]] = i
    #for j,i in enumerate(all_class_ids_possible):
    #    if i not in class_counters_from_class_ids:
    #        class_counters_from_class_ids[i] = j + len(class_ids)

    # Get class counts (for later scoring)
    #class_counts = []
    #for class_counter in range(n_classes):
    #    class_counts.append(np.sum(np.where(initial_classes == class_ids[class_counter], 1.0, 0.0)))

    # Set the position of any negative net_change cells manually because the lowest ranked will be No_data otw.
    for class_counter in range(n_all_classes):
        if net_change_values[class_counter] < 0:
            initial_position_set_counter = n_cells - 1
            while 1:
                test_key_r = ranked_keys[class_counter, initial_position_set_counter, 0]
                test_key_c = ranked_keys[class_counter, initial_position_set_counter, 1]

                if rank_array[class_counter, test_key_r, test_key_c] > 0:
                    positions[class_counter] = initial_position_set_counter
                    break
                else:
                    initial_position_set_counter -= 1

    print ('Iterating net changes ' + str(list(net_change_values)) + '\nwith per-class step sizes of ' + str(list(cells_per_step_by_class)))
    while cont == 1:
        if ticks >= report_threshold:
            print (str(report_threshold) + ' iter run. Remaining: ' + str(list(net_change_values)))
            ticks = 0

        for class_counter in range(n_all_classes):

            # POSITIVE
            # If the net change is positive, we want to allocate towards this class.
            if net_change_values[class_counter] > 0 and initial_net_change_values[class_counter] != 0:
                # If the net change is bigger than the cells per step, allocate all of the cells per step
                if net_change_values[class_counter] > cells_per_step_by_class[class_counter]:
                    w = 0.0
                    step_counter = cells_per_step_by_class[class_counter]
                    while w < step_counter:
                        step_pos = positions[class_counter]
                        # Determine class that will be replaced based on initial class.
                        class_to_be_replaced = initial_classes[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]]
                        if changed_cells[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] == 0 \
                                    and class_to_be_replaced != all_class_ids[class_counter]:
                            class_counter_to_be_replaced = [i for i, _ in enumerate(all_class_counters) if all_class_ids[i] == class_to_be_replaced][0]
                            # Check if that class is both not pre-specified and still has conversion increases left
                            if net_change_values[class_counter_to_be_replaced] < 0 or initial_net_change_values[class_counter_to_be_replaced] == 0:
                                # Key line, pull the keys out of the ranked_keys array and rewrite it as the new class.
                                changed_cells[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] = all_class_ids[class_counter]
                                if report_each_conversion:
                                    print ('In expansion of ' + str(all_class_ids[class_counter]) + ', ' + str(class_to_be_replaced) + ' converted to ' + str(all_class_ids[class_counter]) + ' Remaining net_changes: ' + str(list(net_change_values)))
                                # Lower the net_change_values by the amount allocated.
                                net_change_values[class_counter] -= 1.0
                                net_change_values[class_counter_to_be_replaced] += 1
                                positions[class_counter_to_be_replaced] -= 1.0
                            else:
                                #step_counter += 1.0
                                pass
                        else:
                            # If we dont make the allocation, move the goal posts.
                            # TODO I deactivated this cause caused endless looping. update algorithm description in manuscript.
                            #step_counter += 1.0
                            pass
                        positions[class_counter] += 1.0
                        w += 1.0

                # Otherwise, allocate only the number left.
                else:
                    # I used WHILE instead of for i in range so that I could use 64 bit floats.
                    w = 0.0
                    step_counter = net_change_values[class_counter]
                    while w < step_counter:
                        step_pos = positions[class_counter]
                        class_to_be_replaced = initial_classes[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]]
                        if changed_cells[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] == 0 \
                                    and class_to_be_replaced != all_class_ids[class_counter]:
                            class_counter_to_be_replaced =  [i for i, _ in enumerate(all_class_counters) if all_class_ids[i] == class_to_be_replaced][0]
                            # Check if that class is both not pre-specified and still has conversion increases left
                            if net_change_values[class_counter_to_be_replaced] < 0 or initial_net_change_values[class_counter_to_be_replaced] == 0:
                                # Key line, pull the keys out of the ranked_keys array and rewrite it as the new class.
                                changed_cells[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] = all_class_ids[class_counter]
                                if report_each_conversion:
                                    print ('In cells_per_step_by_class CONSTRAINED expansion of ' + str(all_class_ids[class_counter]) + ', ' + str(class_to_be_replaced) + ' converted to ' + str(all_class_ids[class_counter]) + ' Remaining net_changes: ' + str(list(net_change_values)))
                                # Lower the net_change_values by the amount allocated.
                                net_change_values[class_counter] -= 1.0
                                net_change_values[class_counter_to_be_replaced] += 1
                                positions[class_counter_to_be_replaced] -= 1.0
                            else:
                                # step_counter += 1.0
                                pass
                        else:
                            # step_counter += 1.0
                            pass
                        positions[class_counter] += 1.0
                        w += 1.0

            # NEGATIVE
            # if the net change is negative, we want to take cells out of this class. To do this, find the worst cells of the class, and flip them to
            # whatever on that cell has the highest suitability? or rank? or perhaps some composite that is based on the actual presence?
            elif net_change_values[class_counter] < 0  and initial_net_change_values[class_counter] != 0:
                if net_change_values[class_counter] < cells_per_step_by_class[class_counter]:
                    w = 0.0
                    step_counter = -1 * cells_per_step_by_class[class_counter]
                    while w < step_counter:
                        step_pos = positions[class_counter]
                        if changed_cells[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] == 0 \
                                    and initial_classes[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] == all_class_ids[class_counter]:
                            replacement_class = 0
                            best_replacement_score = 0.0
                            for replacement_class_counter in range(n_all_classes):
                                # To ensure we dont calc a score for something that wasn't an input, check that the rank_array  is an array
                                if type(rank_array[replacement_class_counter]) is np.ndarray:
                                    if rank_array[replacement_class_counter, ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] != 0:
                                        if initial_net_change_values[replacement_class_counter] > 0:
                                            gamma = initial_net_change_values[replacement_class_counter]
                                        elif initial_net_change_values[replacement_class_counter] == 0:
                                            gamma = count_of_all_classes[replacement_class_counter]
                                        else:
                                            gamma = 0.0
                                        replacement_score = gamma * (1.0 / rank_array[replacement_class_counter, ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]])
                                    else:
                                        replacement_score = 0.0
                                    if report_replacement_class_logic:
                                        print ('Class ' + str(replacement_class_counter) + ' had score ' + str(replacement_score))
                                    if replacement_score > best_replacement_score and replacement_class_counter != class_counter:
                                        # Test for if the change was explicitly stated
                                        if initial_net_change_values[replacement_class_counter] != 0:
                                            if net_change_values[replacement_class_counter] > 0:
                                                best_replacement_score = replacement_score
                                                replacement_class = replacement_class_counter
                                        # If it wasn't explicitly stated in net_change_values, we don't limit ourselves to a budget.
                                        else:
                                            best_replacement_score = replacement_score
                                            replacement_class = replacement_class_counter
                            changed_cells[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] = all_class_ids[replacement_class]
                            if report_each_conversion:
                                print ('In contraction of ' + str(all_class_ids[class_counter]) + ', ' + str(all_class_ids[class_counter]) + ' converted to ' + str(all_class_ids[replacement_class]) + ' Remaining net_changes: ' + str(list(net_change_values)))
                            net_change_values[class_counter] += 1.0
                            # If the replacement class is one that is explicitly stated in the net_change_values, decrement it here.
                            # if it isn't in the net changes, we just dont record it.
                            if net_change_values[replacement_class] > 0:
                                net_change_values[replacement_class] -= 1.0
                        else:
                            pass
                            # step_counter += 1
                        w += 1.0
                        positions[class_counter] -= 1.0
                # Otherwise, allocate only the number remaining.
                else:
                    w = 0.0
                    step_counter = -1 * net_change_values[class_counter]
                    while w < step_counter:
                        step_pos = positions[class_counter]
                        # if changed_cells[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] == 0:
                        if changed_cells[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] == 0 \
                                    and initial_classes[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] == all_class_ids[class_counter]:
                            replacement_class = 0
                            best_replacement_score = 0.0
                            for replacement_class_counter in range(n_all_classes):
                                if type(rank_array[replacement_class_counter]) is np.ndarray:
                                    if rank_array[replacement_class_counter, ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] != 0:
                                        replacement_score = initial_net_change_values[replacement_class_counter] * (1.0 / rank_array[replacement_class_counter, ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]])
                                    else:
                                        replacement_score = 0.0
                                    if replacement_score > best_replacement_score and replacement_class_counter != class_counter:
                                        if initial_net_change_values[replacement_class_counter] > 0 or initial_net_change_values[replacement_class_counter] < 0:
                                            if net_change_values[replacement_class_counter] > 0:
                                                best_replacement_score = replacement_score
                                                replacement_class = replacement_class_counter
                                        # If it wasn't explicitly stated in net_change_values, we don't limit ourselves to a budget.
                                        else:
                                            best_replacement_score = replacement_score
                                            replacement_class = replacement_class_counter
                            changed_cells[ranked_keys[class_counter, step_pos, 0], ranked_keys[class_counter, step_pos, 1]] = all_class_ids[replacement_class]
                            if report_each_conversion:
                                print ('In cells_per_step_by_class CONSTRAINED contraction of ' + str(all_class_ids[replacement_class]) + ', ' + str(all_class_ids[replacement_class]) + ' converted to ' + str(all_class_ids[replacement_class]) + ' Remaining net_changes: ' + str(list(net_change_values)))
                            net_change_values[class_counter] += 1.0
                            if net_change_values[replacement_class] > 0.0:
                                net_change_values[replacement_class] -= 1.0
                        else:
                            pass
                            # step_counter += 1.0
                        w += 1.0
                        positions[class_counter] -= 1.0
            # If the net change is or has become zero, this class no longer needs consideration
            else:
                continue_test[class_counter] = 0

        cont_sum = 0
        for class_counter in range(n_all_classes):
            if net_change_values[class_counter] != 0 and initial_net_change_values[class_counter] != 0: # The ending only requires that stated changes be filled.
                cont_sum += 1

        if cont_sum == 0:
            cont = 0
        ticks += 1

    return changed_cells


# def factor_convolution_value_to_suitability(
#                 ndarray[DTYPEFLOAT64_t, ndim=2] x not None,
#                 double direct_suitability,
#                 double a,
#                 double b,
#                 double c):
# 
#     cdef int r_counter, c_counter
# 
#     cdef int n_rows = x.shape[0]
#     cdef int n_cols = x.shape[1]
# 
#     cdef np.ndarray[np.float64_t, ndim=2] output_array = np.zeros((n_rows, n_cols), dtype=np.float64)
# 
#     for r_counter in range (n_rows):
#         for c_counter in range(n_cols):
#             # output_array[r_counter, c_counter] = direct_suitability * (a + b * x + c * x ** 2 + d * x ** 3 + e * x ** 4)
#             output_array[r_counter, c_counter] = (a + (x[r_counter, c_counter] ** b * (2 - a - (1 - c) - x[r_counter, c_counter])))
# 
# 
#     return output_array


def calc_change_matrix_of_two_int_arrays(ndarray[DTYPEINT32_t, ndim=2] a1 not None, ndarray[DTYPEINT32_t, ndim=2] a2 not None):
    unique1, count1 = np.unique(a1, return_counts=True)
    unique2, count2 = np.unique(a2, return_counts=True)

    cdef int i, j
    cdef int n_rows = a1.shape[0]
    cdef int n_cols = a1.shape[1]
    cdef int m_n_rows = len(count1)

    # Create lookup from lulc class to lulc counter
    #cdef np.ndarray[np.int32_t, ndim=1] lulc_counters = np.zeros((m_n_rows), dtype=np.int64)

    lulc_counters = {}

    for i in range(m_n_rows):
        lulc_counters[unique1[i]] = i

    cdef np.ndarray[np.int32_t, ndim=2] a3 = np.zeros((m_n_rows, m_n_rows), dtype=np.int64)

    for i in range(n_rows):
        for j in range(n_cols):
            a3[lulc_counters[a1[i, j]], lulc_counters[a2[i, j]]] += 1

    return a3



def get_rank_array_and_keys_from_sorted_keys_no_nan_mask(ndarray[DTYPEINT64_t, ndim=2] keys not None,
                                                         DTYPEINT64_t n_rows,
                                                         DTYPEINT64_t n_cols):

    cdef long long i, j
    cdef long long n_keys = keys.shape[1]
    cdef long long counter = 1

    cdef np.ndarray[np.int64_t, ndim=2] rank_array = np.zeros((n_rows, n_cols), dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=2] output_keys = np.zeros((2, n_keys), dtype=np.int64)


    for i in range(n_keys):
        rank_array[keys[0, i], keys[1, i]] = counter
        output_keys[0, counter-1] = keys[0, i]
        output_keys[1, counter-1] = keys[1, i]
        counter += 1

    return rank_array, output_keys

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(True)
@cython.wraparound(True)
def get_rank_array_and_keys_from_sorted_keys_with_nan_mask(ndarray[DTYPEINT64_t, ndim=2] keys not None,
                                              ndarray[DTYPEINT64_t, ndim=2] nan_mask not None,
                                                           DTYPEINT64_t ndv_int=-9999):

    cdef long long i, j
    cdef long long n_keys = keys.shape[1]
    cdef long long n_rows = nan_mask.shape[0]
    cdef long long n_cols = nan_mask.shape[1]
    cdef long long counter = 1

    cdef np.ndarray[np.int64_t, ndim=2] rank_array = np.zeros((n_rows, n_cols), dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=2] output_keys_pre = np.zeros((2, n_keys), dtype=np.int64)


    for i in range(n_keys):
        if nan_mask[keys[0, i], keys[1, i]] != 1:
            rank_array[keys[0, i], keys[1, i]] = counter
            output_keys_pre[0, counter-1] = keys[0, i]
            output_keys_pre[1, counter-1] = keys[1, i]
            counter += 1
        else:
            rank_array[keys[0, i], keys[1, i]] = ndv_int

    # Now trip the output_keys so it dont have the ndvs
    cdef np.ndarray[np.int64_t, ndim=2] output_keys = np.zeros((2, counter - 1), dtype=np.int64)

    output_keys[0] = output_keys_pre[0][0: counter-1]
    output_keys[1] = output_keys_pre[1][0: counter-1]

    return rank_array, output_keys

def get_rank_array_from_sorted_keys_cython(ndarray[DTYPEINT64_t, ndim=1] ranked_keys_rows not None,
                                    ndarray[DTYPEINT64_t, ndim=1] ranked_keys_cols not None,
                                    ndarray[DTYPEINT32_t, ndim=2] nan_mask not None,
                                    DTYPEINT64_t ndv_int=-9999,
                                    ):

    cdef long long i, j
    cdef long long n_rows = len(ranked_keys_rows)
    cdef long long n_cols = len(ranked_keys_cols)
    cdef long long n_keys = n_rows
    cdef long long counter = 1
    # cdef np.ndarray[np.int64_t, ndim=2] order_array = np.zeros((n_rows, n_cols), dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=2] output_keys_pre = np.zeros((2, n_keys), dtype=np.int64)
    # cdef np.ndarray[np.float64_t, ndim=1] values_1d = np.zeros(n_keys, dtype=np.float64)

    for i in range(n_keys):
        if nan_mask[ranked_keys_rows[i], ranked_keys_cols[i]] != 1:
            # order_array[ranked_keys_rows[i], ranked_keys_cols[i]] = counter
            output_keys_pre[0, counter-1] = ranked_keys_rows[i]
            output_keys_pre[1, counter-1] = ranked_keys_cols[i]
            counter += 1
        # else:
        #     order_array[ranked_keys_rows[i], ranked_keys_cols[i]] = ndv_int

    # Now trim the output_keys so it dont have the ndvs
    cdef np.ndarray[DTYPEINT64_t, ndim=2] ranked_keys = np.zeros((2, counter - 1), dtype=np.int64)

    ranked_keys[0] = output_keys_pre[0][0: counter-1]
    ranked_keys[1] = output_keys_pre[1][0: counter-1]

    # if return_order_array:
    #     if return_values_1dim_array:
    #         return ranked_keys, order_array, values_1d
    #     else:
    #         return ranked_keys, order_array
    # else:
    #     if return_values_1dim_array:
    #         return ranked_keys, values_1d
    #     else:
    return ranked_keys




def allocate_from_sorted_keys(ndarray[DTYPEINT64_t, ndim=2] keys not None,
                              ndarray[DTYPEFLOAT64_t, ndim=2] value not None,
                              DTYPEFLOAT64_t goal
                              ):

    cdef long long n_keys = len(keys[0])
    cdef long long n_rows = value.shape[0]
    cdef long long n_cols = value.shape[1]
    cdef long long i, j

    cdef float obtained_value = 0.0

    cdef np.ndarray[np.int64_t, ndim=2] allocations = np.zeros((n_rows, n_cols), dtype=np.int64)

    for i in range(n_keys):
        obtained_value = obtained_value + value[keys[0, i], keys[1, i]]
        if obtained_value >= goal:
            break
        else:
            allocations[keys[0, i], keys[1, i]] = 1

    return allocations



def allocate_from_sorted_keys_with_eligibility_mask(ndarray[DTYPEINT64_t, ndim=2] keys not None,
                              ndarray[DTYPEFLOAT64_t, ndim=2] value_per_proportion not None,
                              DTYPEFLOAT64_t goal,
                              ndarray[DTYPEFLOAT64_t, ndim=2] eligibile_proportion not None
                              ):

    cdef int n_keys = len(keys[0])
    cdef int n_rows = value_per_proportion.shape[0]
    cdef int n_cols = value_per_proportion.shape[1]
    cdef int i, j

    cdef float obtained_value = 0.0

    cdef np.ndarray[DTYPEFLOAT64_t, ndim=2] allocations = np.zeros((n_rows, n_cols), dtype=DTYPEFLOAT64)

    for i in range(n_keys):
        if eligibile_proportion[keys[0, i], keys[1, i]] > 0:
            obtained_value = obtained_value + value_per_proportion[keys[0, i], keys[1, i]] * eligibile_proportion[keys[0, i], keys[1, i]]
            allocations[keys[0, i], keys[1, i]] = eligibile_proportion[keys[0, i], keys[1, i]]
        if obtained_value >= goal:
            # TODOO Never dealth with the small over production here on the very last iteration.
            break

    return allocations


@cython.cdivision(True)
@cython.boundscheck(True)
@cython.wraparound(False)
# LEARNING POINT ,typing defs like below might be important if I call cythong functions within cython functions
# cpdef double[::1] zonal_stats_cythonized(long long[::, ::1] zones_array,
def zonal_stats_cythonized(long long[::, ::1] zones_array,
                                         double[::, ::1] values_array,
                                         long long[::1] unique_zone_ids,
                                         long long zones_ndv,
                                         double values_ndv,
                                         str stats_to_retrieve = 'sums',
                                         long long reporting_frequency = 1000,
                                         long long[::1] enumeration_classes = np.asarray([1], dtype=np.int64),
                                         double[::, ::1] multiply_raster = np.asarray([[1]], dtype=np.float64),

                                         ):
    cdef long long i, j, z
    cdef double v
    cdef long long n_rows = values_array.shape[0]
    cdef long long n_cols = values_array.shape[1]
    cdef long long min_zone_id = np.min(unique_zone_ids)
    cdef long long max_zone_id = np.max(unique_zone_ids)
    cdef long long output_range = max_zone_id + 1
    cdef long long n_unique_zones = len(unique_zone_ids)
    cdef ndarray[DTYPEINT64_t, ndim = 1] enumeration_classes_array = np.asarray(enumeration_classes, dtype=np.int64, order='C')
    cdef long long max_enumeration_class = np.max(enumeration_classes_array[enumeration_classes_array != values_ndv])
    cdef long long num_enumeration_classes = len(enumeration_classes)
    cdef double enumeration_multiplier
    cdef double multiply_value
    # Output var
    # cdef ndarray[DTYPEFLOAT64_t, ndim=1] sums = np.zeros(output_range, dtype=np.float64)
    cdef double[::1] sums = np.zeros(output_range, dtype=np.float64)
    cdef long long[::1] counts = np.zeros(output_range, dtype=np.int64)
    cdef long long[::, ::1] enumeration = np.zeros((output_range, max_enumeration_class + 1), dtype=np.int64)
    cdef double[::, ::1] enumeration_multiplied = np.zeros((output_range, max_enumeration_class + 1), dtype=np.float64)
    cdef ndarray[DTYPEINT64_t, ndim = 2] enumeration_out = np.zeros((output_range, num_enumeration_classes + 1), dtype=np.int64)
    cdef ndarray[DTYPEFLOAT64_t, ndim = 2] enumeration_multiplied_out = np.zeros((output_range, num_enumeration_classes + 1), dtype=np.float64)

    if stats_to_retrieve == 'sums':
        for i in range(n_rows):
            if i % reporting_frequency == 0:
                if i > 0:
                    print ('Cython call: ' + str((float(i) / float(n_rows)) * 100) + ' percent complete.')
            for j in range(n_cols):
                # PERFORMANCE NOTE: assigning once and then using the values was sigficantly faster rather than having it in the key lookup.
                z = zones_array[i, j]
                if z != zones_ndv:
                    v = values_array[i, j]
                    if v != values_ndv:
                    # LEARNING POINT, the following line added to cython was 400x slower than dropping the np.isnan(v)
                    # if v != values_ndv and z != zones_ndv and not np.isnan(v):

                        sums[z] += v
                        # counts[z] += 1  #removing one of the stats types to calculate gave a 20% speedup

        return sums
    elif stats_to_retrieve == 'sums_counts':

        for i in range(n_rows):
            if i % 1000 == 0:
                if i > 0:
                    print ('Cython call: ' + str((float(i) / float(n_rows)) * 100) + ' percent complete.')
            for j in range(n_cols):
                # PERFORMANCE NOTE: assigning once and then using the values was sigficantly faster rather than having it in the key lookup.
                z = zones_array[i, j]
                if z != zones_ndv:
                    v = values_array[i, j]
                    if v != values_ndv:
                        # LEARNING POINT, the following line added to cython was 400x slower than dropping the np.isnan(v)
                        # if v != values_ndv and z != zones_ndv and not np.isnan(v):

                        sums[z] += v
                        counts[z] += 1  #removing one of the stats types to calculate gave a 20% speedup

        return sums, counts
    elif stats_to_retrieve == 'enumeration':

        # Enumeration has the option of applying a multiplication raster before the zonal enumeration. If not desired, multiply_raster has the default 1 by 1 array of 1 to keep vectorized.
        if len(multiply_raster) > 1:

            # If it's only 1 column, this means it's a vertical stripe, such as for ha_per_cell, and so needs a different multiplication index.
            if multiply_raster.shape[1] == 1:
                for i in range(n_rows):

                    if i % 1000 == 0:
                        if i > 0:
                            print ('Cython call:: ' + str((float(i) / float(n_rows)) * 100) + ' percent complete.')
                    # multiply_value = multiply_raster[i, 1] #Only difference from 2dim version is this line, which has also been moved outer for optimization and only has a single index. Lol!
                    for j in range(n_cols):
                        # PERFORMANCE NOTE: assigning once and then using the values was sigficantly faster rather than having it in the key lookup.
                        z = zones_array[i, j]
                        if z != zones_ndv:
                            v = values_array[i, j]
                            if v != values_ndv:
                                enumeration_multiplied[z, <int>(v)] += multiply_raster[i, 0]
            # The shape is not a vertical stripe and is a i by j 2dim matrix
            else:
                for i in range(n_rows):

                    if i % 1000 == 0:
                        if i > 0:
                            print ('Cython call: ' + str((float(i) / float(n_rows)) * 100) + ' percent complete.')
                    for j in range(n_cols):
                        # PERFORMANCE NOTE: assigning once and then using the values was sigficantly faster rather than having it in the key lookup.
                        z = zones_array[i, j]
                        if z != zones_ndv:
                            v = values_array[i, j]
                            if v != values_ndv:

                                # LEARNING POINT, the following line added to cython was 400x slower than dropping the np.isnan(v)
                                # if v != values_ndv and z != zones_ndv and not np.isnan(v):

                                enumeration_multiplied[z, <int>(v)] += multiply_raster[i, j]

            # Fun line: slices can be irregular, so using the enumaration classes as a raw input to column headers works.
            enumeration_multiplied_out = enumeration_multiplied.base[:, enumeration_classes.base]

            return enumeration_multiplied_out

        else:
            for i in range(n_rows):
                if i % 1000 == 0:
                    if i > 0:
                        print ('Cython call: ' + str((float(i) / float(n_rows)) * 100) + ' percent complete.')
                for j in range(n_cols):
                    # PERFORMANCE NOTE: assigning once and then using the values was sigficantly faster rather than having it in the key lookup.
                    z = zones_array[i, j]
                    if z != zones_ndv:
                        v = values_array[i, j]
                        if v != values_ndv:
                            # LEARNING POINT, the following line added to cython was 400x slower than dropping the np.isnan(v)
                            # if v != values_ndv and z != zones_ndv and not np.isnan(v):
                            enumeration[z, <int> (v)] += 1

            # Fun line: slices can be irregular, so using the enumaration classes as a raw input to column headers works.
            enumeration_out = enumeration.base[:, enumeration_classes.base]

            return enumeration_out

@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def allocate_all_sectors(ndarray[np.float64_t, ndim=2] projections_array not None, # n_sectors by n_countries float array of demand to allocate, will also be used to count down what is left and when a country/sector has finished.
                         list country_iso3 not None, #iso3 code for each country as a list
                         list sector_names not None, #sector names a list
                         ndarray[np.float64_t, ndim=1] sector_min_viable_proportions not None, # 1 by n_sectors array of the minimum proportion of the grid-cell is taken when that sector expands there
                         ndarray[np.float64_t, ndim=1] sector_max_viable_proportions not None, # 1 by n_sectors array of maximum proportion of the grid-cell is taken when that sector expands there
                         ndarray[np.float64_t, ndim=1] sector_footprint_requirements not None, # 1 by n_sectors array of the minimum proportion of the grid-cell is taken when that sector expands there
                         ndarray[np.float64_t, ndim=1] sector_yield_notes not None, # 1 by n_sectors array of maximum proportion of the grid-cell is taken when that sector expands there
                         ndarray[np.int64_t, ndim=3] ranked_keys not None, # n_sector by [r,c] by n_conversions array containing each sectors row and column (separate) ranked arrays
                         ndarray[np.float64_t, ndim=2] sector_yields not None, # n_sectors by [r, c] yields per km ranked in same order as sector_dpi_ranked_keys_3d_array
                         ndarray[np.int64_t, ndim=1] sector_num_changes not None, # 1 by n_sectors array of how many changes total occur in that sector, according to length of that sectors ranked_keys
                         ndarray[np.float64_t, ndim=2] available_land not None, # n_rows by n_cols spatial array of 0-1 land availability. Is based on human modification index.
                         ndarray[np.int32_t, ndim=2] country_ids not None, # n_rows by n_-cols spatial array of 1-252 integers denoting ISO3 country code.
                         # ndarray[np.int64_t, ndim=2] protected_areas_array not None,
                         # np.int64_t max_to_allocate,
                         ):

    cdef double current_yield
    cdef long long n_pads
    cdef long long current_row_id, current_col_id

    cdef long long adjacent_cell_ul_row_id, adjacent_cell_u_row_id, adjacent_cell_ur_row_id, adjacent_cell_r_row_id, adjacent_cell_dr_row_id, adjacent_cell_d_row_id, adjacent_cell_dl_row_id, adjacent_cell_l_row_id
    cdef long long adjacent_cell_ul_col_id, adjacent_cell_u_col_id, adjacent_cell_ur_col_id, adjacent_cell_r_col_id, adjacent_cell_dr_col_id, adjacent_cell_d_col_id, adjacent_cell_dl_col_id, adjacent_cell_l_col_id

    cdef long long max_to_allocate = max(sector_num_changes)
    cdef long long i, j, k, l, m
    cdef long long sector_counter = 0
    cdef long long num_countries = len(country_iso3)
    cdef long long cell_counter = 0
    cdef long long continue_sum = 0
    cdef double current_sector_min_viable_proportions = 0.0
    cdef double current_sector_max_viable_proportions = 0.0
    cdef double current_sector_proportion_to_allocate = 0.0
    cdef double current_yield_obtained = 0.0
    cdef long long continue_algorithm = 1
    cdef long long num_iteration_steps = int(2.6e+07) #Chosen to e slightly larger than the max_change. This is a hackaround to ensure that the largest yield-lenghts have a stepsize of 1.
    cdef long long current_country_id = 0
    cdef double current_sector_current_country_demand = 0
    cdef long long num_sectors = len(sector_names)
    cdef np.ndarray[np.int64_t, ndim=1] sector_step_sizes = np.zeros(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] sector_current_step_location = np.zeros(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] sector_current_allocation_location = np.zeros(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] sector_successful_steps_taken = np.zeros(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.float64_t, ndim=1] projection_sums = np.zeros(num_sectors, dtype=np.float64)

    # PERFORMANCE NOTE: If I only write to these ocasionally, NBD, but if constant writing, the fact that it has to reallocate a longer string memory block would lsow this down.
    report = ''
    warning_message = ''

    start = time.time()
    print ('Cython funciton running for sectors ' + str(sector_names))

    # Get length of each sectors' list. This is somewhat redundant because i calculate the same thing in the py code.
    for sector_counter in range(num_sectors):
        print ('Calculating step sizes for sector ' + str(sector_counter) + ': ' + sector_names[sector_counter])
        sector_step_sizes[sector_counter] = (len(sector_yields[sector_counter]) / num_iteration_steps) + 1 # Plus one to ensure always at least 1 cell taken
        print ('    ' + sector_names[sector_counter] + ' step size: ' + str(sector_step_sizes[sector_counter]))

    # Define 3dim vector to hold each sectors, rc, ranked list of change cells along with their proportion converted in that cell and the yield obtained (total cell yield times proportion)
    cdef np.ndarray[np.int64_t, ndim=3] sector_change_keys_lists = np.zeros((num_sectors, 2, max_to_allocate), dtype=np.int64)
    cdef np.ndarray[np.float64_t, ndim=2] sector_proportion_allocated_lists = np.zeros((num_sectors, max_to_allocate), dtype=np.float64)
    cdef np.ndarray[np.float64_t, ndim=2] sector_yield_obtained_lists = np.zeros((num_sectors, max_to_allocate), dtype=np.float64)

    # Keep track of if specific sector/country pairs need continuing and also separately (to avoid recomputation).
    cdef np.ndarray[np.int64_t, ndim=2] country_sector_continue_array = np.ones((num_countries, num_sectors), dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] sector_continue_array = np.ones(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] country_continue_array = np.ones(num_countries, dtype=np.int64)

    # During computation, keep track of how much has been allocated for each country by sector
    cdef np.ndarray[np.float64_t, ndim=2] country_sector_production = np.zeros((num_countries, num_sectors), dtype=np.float64)

    # Get the number of conversions from projections
    for sector_counter in range(num_sectors):
        for country_counter in range(num_countries):
            to_add = projections_array[country_counter, sector_counter]
            projection_sums[sector_counter] += to_add
            print ('    Country ' + str(country_counter) + ' ' + str(country_iso3[country_counter]) + ' for sector ' + str(sector_counter) + ' ' + str(sector_names[sector_counter]) + ' needs to allocate ' + str(projections_array[sector_counter, country_counter]))
        print ('Over all countries, need to allocate ' + str(projection_sums[sector_counter]))

    # Algorithm runs until a set of conditions are met, which sets continue_algorithm to 0
    while continue_algorithm == 1:

        # Iterate through sectors
        for sector_counter in range(num_sectors):

            # Continue only if that sector still has allocation.
            if sector_continue_array[sector_counter] == 1:

                # Consider ranges of length sector_step_size of cell-counter from the sector's current location within ranked_keys
                for cell_counter in range(sector_current_step_location[sector_counter], sector_current_step_location[sector_counter] + sector_step_sizes[sector_counter]):
                    warning_message = ''

                    # Get the row and col id of the focal cell.
                    current_row_id = ranked_keys[sector_counter, 0, cell_counter]
                    current_col_id = ranked_keys[sector_counter, 1, cell_counter]
                    current_sector_min_viable_proportions = sector_min_viable_proportions[sector_counter]
                    current_sector_max_viable_proportions = sector_max_viable_proportions[sector_counter]

                    # Get the country who owns the focal cell
                    current_country_id = country_ids[current_row_id, current_col_id] # NOTE, IDs in country raster start at 1. The projections array is defined starting at zero.

                    # Get the demand for that country
                    current_sector_current_country_demand = projections_array[current_country_id - 1, sector_counter]

                    # If available land > min_viable, keep considering the focal cell
                    if available_land[current_row_id, current_col_id] >= current_sector_min_viable_proportions:

                        # If this country is not done WITHIN THIS SECTOR, keep considdering it.
                        if country_sector_continue_array[current_country_id - 1, sector_counter] == 1:

                            if sector_yield_notes[sector_counter] == 0:
                                # Use yield raster value directly
                                current_yield = sector_yields[sector_counter, cell_counter]

                            elif sector_yield_notes[sector_counter] == 1:
                                # Requirement is expressed in areal terms, so the yield is equal to the amount to be allocated.
                                current_yield = 1.0
                            elif sector_yield_notes[sector_counter] == 2:
                                # Use raster yield AND the yield in a different cell.
                                # SHORTCUT, currently assuming same yield in adjacent cell. STILL NEED TO HAVE THAT OTHER CELL BE FLIPPED.
                                current_yield = sector_yields[sector_counter, cell_counter] * 2
                            elif sector_yield_notes[sector_counter] == 9:
                                # Use raster yield AND the yield in a different cell.
                                # SHORTCUT, currently assuming same yield in adjacent cell. STILL NEED TO HAVE THAT OTHER CELL BE FLIPPED.
                                current_yield = sector_yields[sector_counter, cell_counter] * 9
                            elif sector_yield_notes[sector_counter] > 9:
                                # Use the fixed value given.
                                current_yield = sector_yield_notes[sector_counter]
                            else:
                                raise NameError('WTF, shouldnt get here. 923910')

                            # Determine how much land will be converted this step
                            if available_land[current_row_id, current_col_id] > current_sector_max_viable_proportions:
                                current_sector_proportion_to_allocate = current_sector_max_viable_proportions
                            else:
                                current_sector_proportion_to_allocate = available_land[current_row_id, current_col_id]

                            if sector_footprint_requirements[sector_counter] == 0: # NO footprint requirement
                                current_yield_obtained = current_sector_proportion_to_allocate * current_yield

                            elif sector_footprint_requirements[sector_counter] == 1:
                                current_yield_obtained = current_sector_proportion_to_allocate * current_yield # Yield will be 1 for areal

                            elif sector_footprint_requirements[sector_counter] == 2:

                                # Tricky lines here, first I use int casting to see how many times higher the allocated amount was than the minimum. this gets the number of wells.
                                # then, i reassign the current allocation based on the yield times pads
                                n_pads = <int>(current_sector_proportion_to_allocate /  current_sector_min_viable_proportions) # 6 was the unmber of pads
                                current_sector_proportion_to_allocate = n_pads * current_sector_min_viable_proportions
                                current_yield_obtained = n_pads * current_yield

                            elif sector_footprint_requirements[sector_counter] == 3:
                                current_yield_obtained = current_sector_proportion_to_allocate * current_yield # Yield will be 1 for areal

                            elif sector_footprint_requirements[sector_counter] == 4:
                                current_yield_obtained = current_sector_proportion_to_allocate * current_yield # Yield will be 1 for areal

                            elif sector_footprint_requirements[sector_counter] == 5:
                                current_yield_obtained = current_yield # NOTE That current yield here is not multiplied by area for this type of conversion.

                            if current_sector_current_country_demand >= current_yield:
                                if current_yield > 0:

                                    # Record row-col of all cells that change in a 3dim npy array
                                    sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = current_row_id
                                    sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = current_col_id

                                    # Record proportion allocated and yield obtained in 2dim arrays
                                    sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = current_sector_proportion_to_allocate
                                    available_land[current_row_id, current_col_id] -= current_sector_proportion_to_allocate

                                    # For hydro, have to consider spatial adjacency
                                    # MANUSCRIPT NOTE: We made the assumption that if the 9cell availability was greater than country demand, the hydro plant would not be made. (THUS, this code is not replicated in the conditional below).
                                    if sector_yield_notes[sector_counter] == 9:

                                        adjacent_cell_ul_row_id = current_row_id - 1
                                        adjacent_cell_u_row_id = current_row_id - 1
                                        adjacent_cell_ur_row_id = current_row_id - 1
                                        adjacent_cell_r_row_id = current_row_id
                                        adjacent_cell_dr_row_id = current_row_id + 1
                                        adjacent_cell_d_row_id = current_row_id + 1
                                        adjacent_cell_dl_row_id = current_row_id + 1
                                        adjacent_cell_l_row_id = current_row_id

                                        adjacent_cell_ul_col_id = current_col_id - 1
                                        adjacent_cell_u_col_id = current_col_id
                                        adjacent_cell_ur_col_id = current_col_id + 1
                                        adjacent_cell_r_col_id = current_col_id + 1
                                        adjacent_cell_dr_col_id = current_col_id + 1
                                        adjacent_cell_d_col_id = current_col_id
                                        adjacent_cell_dl_col_id = current_col_id - 1
                                        adjacent_cell_l_col_id = current_col_id - 1

                                        # check that one of the adjacent cells has not been taken. write if so
                                        if available_land[adjacent_cell_ul_row_id, adjacent_cell_ul_col_id] > 0.0:
                                            sector_current_allocation_location[sector_counter] += 1
                                            sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_ul_row_id
                                            sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_ul_col_id
                                            sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_ul_row_id, adjacent_cell_ul_col_id]
                                            available_land[adjacent_cell_ul_row_id, adjacent_cell_ul_col_id] = 0.0

                                        if available_land[adjacent_cell_u_row_id, adjacent_cell_u_col_id] > 0.0:
                                            sector_current_allocation_location[sector_counter] += 1
                                            sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_u_row_id
                                            sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_u_col_id
                                            sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_u_row_id, adjacent_cell_u_col_id]
                                            available_land[adjacent_cell_u_row_id, adjacent_cell_u_col_id] = 0.0

                                        if available_land[adjacent_cell_ur_row_id, adjacent_cell_ur_col_id] > 0.0:
                                            sector_current_allocation_location[sector_counter] += 1
                                            sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_ur_row_id
                                            sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_ur_col_id
                                            sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_ur_row_id, adjacent_cell_ur_col_id]
                                            available_land[adjacent_cell_ur_row_id, adjacent_cell_ur_col_id] = 0.0

                                        if available_land[adjacent_cell_r_row_id, adjacent_cell_r_col_id] > 0.0:
                                            sector_current_allocation_location[sector_counter] += 1
                                            sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_r_row_id
                                            sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_r_col_id
                                            sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_r_row_id, adjacent_cell_r_col_id]
                                            available_land[adjacent_cell_r_row_id, adjacent_cell_r_col_id] = 0.0

                                        if available_land[adjacent_cell_dr_row_id, adjacent_cell_dr_col_id] > 0.0:
                                            sector_current_allocation_location[sector_counter] += 1
                                            sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_dr_row_id
                                            sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_dr_col_id
                                            sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_dr_row_id, adjacent_cell_dr_col_id]
                                            available_land[adjacent_cell_dr_row_id, adjacent_cell_dr_col_id] = 0.0

                                        if available_land[adjacent_cell_d_row_id, adjacent_cell_d_col_id] > 0.0:
                                            sector_current_allocation_location[sector_counter] += 1
                                            sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_d_row_id
                                            sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_d_col_id
                                            sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_d_row_id, adjacent_cell_d_col_id]
                                            available_land[adjacent_cell_d_row_id, adjacent_cell_d_col_id] = 0.0

                                        if available_land[adjacent_cell_dl_row_id, adjacent_cell_dl_col_id] > 0.0:
                                            sector_current_allocation_location[sector_counter] += 1
                                            sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_dl_row_id
                                            sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_dl_col_id
                                            sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_dl_row_id, adjacent_cell_dl_col_id]
                                            available_land[adjacent_cell_dl_row_id, adjacent_cell_dl_col_id] = 0.0

                                        if available_land[adjacent_cell_l_row_id, adjacent_cell_l_col_id] > 0.0:
                                            sector_current_allocation_location[sector_counter] += 1
                                            sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_l_row_id
                                            sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_l_col_id
                                            sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_l_row_id, adjacent_cell_l_col_id]
                                            available_land[adjacent_cell_l_row_id, adjacent_cell_l_col_id] = 0.0

                                        sector_successful_steps_taken[sector_counter] += 8 # Not nine cause hit again below as with other sectors.

                                    # Record yield obtained in 2dim arrays
                                    sector_yield_obtained_lists[sector_counter, sector_current_allocation_location[sector_counter]] = current_yield_obtained

                                    # Record country-specific changes too
                                    country_sector_production[current_country_id - 1, sector_counter] += current_yield_obtained

                                    # Decrease the projections_array by how much yield was obtained
                                    projections_array[current_country_id - 1, sector_counter] -= current_yield_obtained

                                    # For ending conditions, record this
                                    sector_successful_steps_taken[sector_counter] += 1


                                else:
                                    pass
                                    # warning_message += ' WARNING!! went to a cell that had no yield'
                            # If country  demand is less  than the gridcell's yield, then only part of it is allocated.
                            elif current_sector_current_country_demand > 0:
                                if current_yield > 0:

                                    # Record row-col of all cells that change in a 3dim npy array
                                    sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = current_row_id
                                    sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = current_col_id

                                    # Record proportion allocated and yield obtained in 2dim arrays
                                    sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = current_sector_proportion_to_allocate

                                    # Record yield obtained in 2dim arrays
                                    sector_yield_obtained_lists[sector_counter, sector_current_allocation_location[sector_counter]] = current_sector_proportion_to_allocate * current_yield_obtained

                                    # Record country-specific changes too
                                    country_sector_production[current_country_id - 1, sector_counter] += current_sector_current_country_demand

                                    # Decrease the projections_array by how much yield was obtained
                                    projections_array[current_country_id - 1, sector_counter] -= current_sector_current_country_demand

                                    if sector_yield_notes[sector_counter] == 9:
                                        sector_successful_steps_taken[sector_counter] += 9
                                    else:
                                        sector_successful_steps_taken[sector_counter] += 1


                                    available_land[current_row_id, current_col_id] -= current_sector_proportion_to_allocate * (current_sector_current_country_demand / current_yield)

                                    country_sector_continue_array[current_country_id - 1, sector_counter] = 0

                                    # Upon finishing a country_sector, check to see if the whole sector is done by running through each country.
                                    l = 0
                                    for k in range(num_countries):
                                        l += country_sector_continue_array[k, sector_counter]
                                    if l == 0:
                                        country_sector_continue_array[current_country_id - 1, sector_counter] = 0
                                        sector_continue_array[sector_counter] = 0


                                    continue_sum = 0
                                    for m in range(num_sectors):
                                        continue_sum += sector_continue_array[m]
                                    if continue_sum == 0:
                                        continue_algorithm = 0
                                else:
                                    warning_message += ' WARNING!! sector demand was less than yield  AND yield was zero?'
                                    raise NameError(warning_message)
                            else:
                                country_sector_continue_array[current_country_id - 1, sector_counter] = 0

                                # Upon finishing a country_sector, check to see if the whole sector is done by running through each country.
                                l = 0
                                for k in range(num_countries):
                                    l += country_sector_continue_array[k, sector_counter]
                                if l == 0:
                                    country_sector_continue_array[current_country_id - 1, sector_counter] = 0
                                    sector_continue_array[sector_counter] = 0

                                continue_sum = 0
                                for m in range(num_sectors):
                                    continue_sum += sector_continue_array[m]
                                if continue_sum == 0:
                                    continue_algorithm = 0
                        else:
                            pass
                            # Didnt consider this celll because country_sector_continue_array was 0 for this country, this sector.
                    else:
                        pass
                        # available land  was not > min_viable, stopped considering the focal cell
                    sector_current_allocation_location[sector_counter] += 1
                    sector_current_step_location[sector_counter] += 1



                    if True:
                        if warning_message != '' or cell_counter % 1012300 == 0  or cell_counter % 1012301 == 0 or cell_counter < 5 or (1000 < cell_counter < 1005) or (100000 < cell_counter < 100005) or (10000000 < cell_counter < 10000005):
                            print (cell_counter)
                            if country_sector_continue_array[current_country_id - 1, sector_counter]:
                                report += warning_message + '\n'
                                report_message = 'id: ' + str(cell_counter) + ', sector: ' + sector_names[sector_counter] + ', country: ' + str(country_iso3[current_country_id-1]) + ', sector-country remaining demand: ' + str(current_sector_current_country_demand) + ', proportion to be allocated: ' + str(current_sector_proportion_to_allocate)  + ' available land after allocation: ' + str(available_land[current_row_id, current_col_id])+ ', sector_successful_steps_taken: ' + str(sector_successful_steps_taken[sector_counter])  + ', sector_current_step_location: ' + str(sector_current_step_location[sector_counter]) + ', total to change: ' + str(sector_num_changes[sector_counter]) +  ', current cell row: ' + str(current_row_id) + ', current cell col: ' + str(current_col_id) + ', current_sector_min_viable_proportions: ' + str(current_sector_min_viable_proportions) + ', current_sector_max_viable_proportions: ' + str(current_sector_max_viable_proportions) + ', sector_continue: ' + str(sector_continue_array[sector_counter]) + ', country_sector_continue: ' + str(country_sector_continue_array[current_country_id - 1, sector_counter])
                                print (report_message)
                                report += report_message + '\n'

                # if sector_current_step_location[sector_counter] + sector_step_sizes[sector_counter] >= sector_num_changes[sector_counter]:
                if sector_successful_steps_taken[sector_counter] + sector_step_sizes[sector_counter] >= sector_num_changes[sector_counter] or sector_current_step_location[sector_counter] + sector_step_sizes[sector_counter] >= max_to_allocate:
                    # if sector_yields[sector_counter, cell_counter] > 0:
                    #     report += 'WARNING !!!!! Shouldnt get here either, because this means the goal wasnt met AND the yield was still >0\n'

                    sector_continue_array[sector_counter] = 0
            else: # Skipped sector because sector_continue_array was 0 for this sector
                pass

        # Upon finishing a country_sector, check to see if the whole sector is done by running through each country.
        l = 0
        for k in range(num_countries):
            l += country_sector_continue_array[k, sector_counter]
        if l == 0:
            country_sector_continue_array[current_country_id - 1, sector_counter] = 0
            sector_continue_array[sector_counter] = 0

        continue_sum = 0
        for m in range(num_sectors):
            continue_sum += sector_continue_array[m]
        if continue_sum == 0:
            print ('YAYAYAYAY! Allocation algorithm has zero values for all in sector_continue_array.')

            projection_sums = np.zeros(num_sectors, dtype=np.float64)
            for sector_counter in range(num_sectors):
                for country_counter in range(num_countries):
                    to_add = projections_array[country_counter, sector_counter]
                    projection_sums[sector_counter] += to_add

            continue_algorithm = 0

    print ('cython time: ' + str(time.time() - start))

    return sector_change_keys_lists, sector_proportion_allocated_lists, sector_yield_obtained_lists, country_sector_production, report



@cython.cdivision(False)
@cython.boundscheck(True)
@cython.wraparound(True)
def read_1d_npy_chunk(input_path, start_entry, num_entries):
    """
    Reads a SUBSET of a npy file at path where you can specify a starting point and number of entries.
    :param input_path:
    :param start_entry:
    :param num_entries:
    :return:
    """
    with open(input_path, 'rb') as fhandle:
        major, minor = np.lib.format.read_magic(fhandle)
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(fhandle)
        assert not fortran, "Fortran order arrays not supported"
        # Make sure the offsets aren't invalid.
        assert start_entry < shape[0], (
            'start_entry is beyond end of file'
        )
        assert start_entry + num_entries <= shape[0], (
            'start_row + num_rows > shape[0]'
        )
        # Get the number of elements in one 'row' by taking
        # a product over all other dimensions.
        # row_size = np.prod(shape[1:])
        start_byte = start_entry * dtype.itemsize

        # start_byte = start_entry

        fhandle.seek(start_byte, 1)
        # n_items = row_size * num_rows
        flat = np.fromfile(fhandle, count=num_entries, dtype=dtype)
        return flat.reshape((-1,) + shape[1:])

@cython.cdivision(False)
@cython.boundscheck(True)
@cython.wraparound(True)
def read_2d_npy_chunk(input_path, start_row, num_rows, start_entry=None, max_entries=None):
    """
    Reads a SUBSET of a 2 dimensional npy file at path where you can specify a starting row and number of subsequent rows
    :param input_path:
    :param start_row:
    :param num_rows:
    :param max_entries:
    :return:
    """
    # assert start_row >= 0 and num_rows > 0
    with open(input_path, 'rb') as fhandle:
        major, minor = np.lib.format.read_magic(fhandle)
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(fhandle)
        # assert not fortran, "Fortran order arrays not supported"
        # # Make sure the offsets aren't invalid.
        # assert start_row < shape[0], (
        #     'start_row is beyond end of file'
        # )
        # assert start_row + num_rows <= shape[0], (
        #     'start_row + num_rows > shape[0]'
        # )
        # Get the number of elements in one 'row' by taking
        # a product over all other dimensions.
        if start_entry is None:
            start_entry = 0
        row_size = np.prod(shape[1:])
        start_byte = start_entry * dtype.itemsize + start_row * row_size * dtype.itemsize
        fhandle.seek(start_byte, 1)
        n_items = row_size * num_rows
        if n_items > max_entries:
            n_items = max_entries
        flat = np.fromfile(fhandle, count=n_items, dtype=dtype)

        # NOTE: Reshaping was a bit funny  here because the 2d version of this funciton is purpose built for the gdra project. Need to generalize.
        return flat.reshape((1,) + (-1,))
        # return flat.reshape((-1,) + (1,))
        # return flat.reshape((-1,) + shape[1:])




@cython.cdivision(False)
@cython.boundscheck(True)
@cython.wraparound(True)
def read_3d_npy_chunk(input_path, d1_index, d2_index, d3_start, d3_end):
    """
    Reads a SUBSET of a 3-dimensional npy file at path where you can specify the index for dimensions 1 and 2,
    and then give a range of values for d3. This works well when, for instance, you have multiple lists of 2-dim
    coordinates, where each list is ranked by value.

    :param input_path:
    :param d1_index:
    :param d2_index:
    :param d3_start:
    :param d3_end:
    :return:
    """
    with open(input_path, 'rb') as fhandle:
        major, minor = np.lib.format.read_magic(fhandle)
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(fhandle)

        row_size = shape[2]
        n_items = d3_end - d3_start
        start_byte = ((d1_index) * 2 + d2_index) * row_size * dtype.itemsize
        fhandle.seek(start_byte, 1)


        flat = np.fromfile(fhandle, count=n_items, dtype=dtype)

        return flat.reshape(1, 1, n_items)



# @cython.cdivision(True)
# @cython.boundscheck(False)
# @cython.wraparound(False)


@cython.cdivision(False)
@cython.boundscheck(True)
@cython.wraparound(True)
def allocate_all_sectors_paged(ndarray[np.float64_t, ndim=2] projections_array not None, # n_sectors by n_countries float array of demand to allocate, will also be used to count down what is left and when a country/sector has finished.
                         list country_iso3 not None, #iso3 code for each country as a list
                         list sector_names not None, #sector names a list
                         ndarray[np.float64_t, ndim=1] sector_min_viable_proportions not None, # 1 by n_sectors array of the minimum proportion of the grid-cell is taken when that sector expands there
                         ndarray[np.float64_t, ndim=1] sector_max_viable_proportions not None, # 1 by n_sectors array of maximum proportion of the grid-cell is taken when that sector expands there
                         ndarray[np.float64_t, ndim=1] sector_footprint_requirements not None, # 1 by n_sectors array of the minimum proportion of the grid-cell is taken when that sector expands there
                         ndarray[np.float64_t, ndim=1] sector_yield_notes not None, # 1 by n_sectors array of maximum proportion of the grid-cell is taken when that sector expands there
                         list ranked_keys_paths not None, # n_sector by [r,c] by n_conversions array containing each sectors row and column (separate) ranked arrays
                         list sector_yield_paths not None, # n_sectors by [r, c] yields per km ranked in same order as sector_dpi_ranked_keys_3d_array
                         # ndarray[np.int64_t, ndim=1] sector_num_changes not None, # 1 by n_sectors array of how many changes total occur in that sector, according to length of that sectors ranked_keys
                         ndarray[np.float64_t, ndim=2] available_land not None, # n_rows by n_cols spatial array of 0-1 land availability. Is based on human modification index.
                         ndarray[np.int32_t, ndim=2] country_ids not None, # n_rows by n_-cols spatial array of 1-252 integers denoting ISO3 country code.
                         # ndarray[np.int64_t, ndim=2] protected_areas_array not None,
                         # np.int64_t max_to_allocate,
                         ):

    cdef double current_yield
    cdef long long n_pads
    cdef long long current_row_id, current_col_id

    cdef long long adjacent_cell_ul_row_id, adjacent_cell_u_row_id, adjacent_cell_ur_row_id, adjacent_cell_r_row_id, adjacent_cell_dr_row_id, adjacent_cell_d_row_id, adjacent_cell_dl_row_id, adjacent_cell_l_row_id
    cdef long long adjacent_cell_ul_col_id, adjacent_cell_u_col_id, adjacent_cell_ur_col_id, adjacent_cell_r_col_id, adjacent_cell_dr_col_id, adjacent_cell_d_col_id, adjacent_cell_dl_col_id, adjacent_cell_l_col_id

    # cdef long long max_to_allocate = max(sector_num_changes)
    cdef long long i, j, k, l, m
    cdef long long sector_counter = 0
    cdef long long paged_counter = 0
    cdef long long num_countries = len(country_iso3)
    cdef long long cell_counter = 0
    cdef long long continue_sum = 0
    cdef long long num_to_load_per_chunk = 500000
    cdef double current_sector_min_viable_proportions = 0.0
    cdef double current_sector_max_viable_proportions = 0.0
    cdef double current_sector_proportion_to_allocate = 0.0
    cdef double current_yield_obtained = 0.0
    cdef long long continue_algorithm = 1
    cdef long long num_iteration_steps = np.int64(2.6e+07) #Chosen to e slightly larger than the max_change. This is a hackaround to ensure that the largest yield-lenghts have a stepsize of 1.
    cdef long long current_country_id = 0
    cdef double current_sector_current_country_demand = 0
    cdef long long num_sectors = len(sector_names)
    cdef np.ndarray[np.int64_t, ndim=1] sector_step_sizes = np.zeros(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] sector_current_step_location = np.zeros(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] sector_current_allocation_location = np.zeros(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] sector_successful_steps_taken = np.zeros(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.float64_t, ndim=1] projection_sums = np.zeros(num_sectors, dtype=np.float64)

    # PERFORMANCE NOTE: If I only write to these ocasionally, NBD, but if constant writing, the fact that it has to reallocate a longer string memory block would lsow this down.
    report = ''
    warning_message = ''

    start = time.time()
    print ('Cython funciton running for sectors ' + str(sector_names))


    cdef long long max_to_allocate = 45000000
    # Define 3dim vector to hold each sectors, rc, ranked list of change cells along with their proportion converted in that cell and the yield obtained (total cell yield times proportion)
    cdef np.ndarray[np.int64_t, ndim=3] sector_change_keys_lists = np.zeros((num_sectors, 2, max_to_allocate), dtype=np.int64)
    cdef np.ndarray[np.float64_t, ndim=2] sector_proportion_allocated_lists = np.zeros((num_sectors, max_to_allocate), dtype=np.float64)
    cdef np.ndarray[np.float64_t, ndim=2] sector_yield_obtained_lists = np.zeros((num_sectors, max_to_allocate), dtype=np.float64)

    # Keep track of if specific sector/country pairs need continuing and also separately (to avoid recomputation).
    cdef np.ndarray[np.int64_t, ndim=2] country_sector_continue_array = np.ones((num_countries, num_sectors), dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] sector_continue_array = np.ones(num_sectors, dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=1] country_continue_array = np.ones(num_countries, dtype=np.int64)



    # During computation, keep track of how much has been allocated for each country by sector
    cdef np.ndarray[np.float64_t, ndim=2] country_sector_production = np.zeros((num_countries, num_sectors), dtype=np.float64)

    # Get the number of conversions from projections
    for sector_counter in range(num_sectors):
        for country_counter in range(num_countries):
            to_add = projections_array[country_counter, sector_counter]
            projection_sums[sector_counter] += to_add

    # Set up memory block to store chunks of input data     cdef np.ndarray[np.int64_t, ndim=3] sector_change_keys_lists = np.zeros((num_sectors, 2, num_to_load_per_chunk), dtype=np.int64)
    cdef np.ndarray[np.int64_t, ndim=3] ranked_keys = np.zeros((num_sectors, 2, num_to_load_per_chunk), dtype=np.int64)
    cdef np.ndarray[np.float64_t, ndim=2] sector_yields = np.zeros((num_sectors, num_to_load_per_chunk))


    # Make update?
    cdef long long start_row = 0
    cdef long long num_to_load_this_chunk = 0 # What about when this is LONGER than the input?
    cdef long long row_size = 0

    # Load first chunk of ranked and yield data
    cdef np.ndarray[np.int64_t, ndim=1] sector_num_steps_loaded = np.full(num_sectors, num_to_load_this_chunk, dtype=np.int64)
    for sector_counter, sector_name in enumerate(sector_names):

        a = read_2d_npy_chunk(ranked_keys_paths[sector_counter], 0, 1, 0, num_to_load_this_chunk)
        ranked_keys[sector_counter, 0, 0: num_to_load_this_chunk] = a
        b = read_2d_npy_chunk(ranked_keys_paths[sector_counter], 1, 1, 0, num_to_load_this_chunk)
        ranked_keys[sector_counter, 1, 0: num_to_load_this_chunk] = b

        sector_num_steps_loaded[sector_counter] += num_to_load_this_chunk

        if sector_yield_paths[sector_counter] is not None:
            with open(sector_yield_paths[sector_counter], 'rb') as fhandle:
                print ('Loading initial chunk for sector ', sector_name)

                major, minor = np.lib.format.read_magic(fhandle)
                shape, fortran, dtype = np.lib.format.read_array_header_1_0(fhandle)

                if shape[0] < num_to_load_per_chunk:
                    num_to_load_this_chunk = shape[0]
                else:
                    num_to_load_this_chunk = num_to_load_per_chunk

                start_byte = 0
                fhandle.seek(start_byte, 1) # 0 is absolute, 1 is relative, 2 is from end
                sector_yields[sector_counter, 0: num_to_load_this_chunk] = np.fromfile(fhandle, count=num_to_load_this_chunk, dtype=dtype)


    # Get length of each sectors' list. This is somewhat redundant because i calculate the same thing in the py code.
    for sector_counter in range(num_sectors):
        print ('Calculating step sizes for sector ' + str(sector_counter) + ': ' + sector_names[sector_counter])
        ### disabled to allow compiling
        # sector_step_sizes[sector_counter] = (len(sector_yields[sector_counter]) / num_iteration_steps) + 1 # Plus one to ensure always at least 1 cell taken
        print ('    ' + sector_names[sector_counter] + ' step size: ' + str(sector_step_sizes[sector_counter]))

    # Algorithm runs until a set of conditions are met, which sets continue_algorithm to 0
    while continue_algorithm == 1:

        # Iterate through sectors
        for sector_counter in range(num_sectors):

            # Continue only if that sector still has allocation.
            if sector_continue_array[sector_counter] == 1:

                # Consider ranges of length sector_step_size of cell-counter from the sector's current location within ranked_keys
                # for cell_counter in range(0, sector_step_sizes[sector_counter]):
                for cell_counter in range(sector_current_step_location[sector_counter], sector_current_step_location[sector_counter] + sector_step_sizes[sector_counter]):
                    warning_message = ''

                    if num_to_load_this_chunk > 0:
                        paged_counter = cell_counter % num_to_load_this_chunk
                    else:
                        paged_counter = 0

                    # Get the row and col id of the focal cell.
                    current_row_id = ranked_keys[sector_counter, 0, paged_counter]
                    current_col_id = ranked_keys[sector_counter, 1, paged_counter]
                    current_sector_min_viable_proportions = sector_min_viable_proportions[sector_counter]
                    current_sector_max_viable_proportions = sector_max_viable_proportions[sector_counter]

                    # Get the country who owns the focal cell
                    current_country_id = country_ids[current_row_id, current_col_id] # NOTE, IDs in country raster start at 1. The projections array is defined starting at zero.

                    # Get the demand for that country
                    if current_country_id <= 254:
                        current_sector_current_country_demand = projections_array[current_country_id - 1, sector_counter]

                        # If available land > min_viable, keep considering the focal cell
                        if available_land[current_row_id, current_col_id] > current_sector_min_viable_proportions: # TODO  is all the error here from an incorrect >=
                        # if available_land[current_row_id, current_col_id] >= current_sector_min_viable_proportions:

                            # If this country is not done WITHIN THIS SECTOR, keep considdering it.
                            if country_sector_continue_array[current_country_id - 1, sector_counter] == 1:

                                if sector_yield_notes[sector_counter] == 0:
                                    # Use yield raster value directly
                                    current_yield = sector_yields[sector_counter, paged_counter]
                                elif sector_yield_notes[sector_counter] == 1:
                                    # current_yield = sector_yields[sector_counter, paged_counter]
                                    current_yield = 1.0
                                elif sector_yield_notes[sector_counter] == 9:
                                    current_yield = sector_yields[sector_counter, paged_counter] * 9.0 # OVERRODE comments in last email. If the unit really was ann mw per km2, and the area converted was 9km2, it should reflect that.
                                elif sector_yield_notes[sector_counter] > 9:
                                    current_yield = sector_yield_notes[sector_counter]
                                elif sector_yield_notes[sector_counter] < 0:
                                    current_yield = -1.0 * sector_yield_notes[sector_counter]

                                # Determine how much land will be converted this step
                                if available_land[current_row_id, current_col_id] > current_sector_max_viable_proportions:
                                    current_sector_proportion_to_allocate = current_sector_max_viable_proportions
                                else:
                                    current_sector_proportion_to_allocate = available_land[current_row_id, current_col_id]

                                if sector_footprint_requirements[sector_counter] == 0: # NO footprint requirement
                                    current_yield_obtained = current_sector_proportion_to_allocate * current_yield

                                elif sector_footprint_requirements[sector_counter] == 1:
                                    current_yield_obtained = current_sector_proportion_to_allocate * current_yield # Yield will be 1 for areal

                                elif sector_footprint_requirements[sector_counter] == 2:

                                    # Tricky lines here, first I use int casting to see how many times higher the allocated amount was than the minimum. this gets the number of wells.
                                    # then, i reassign the current allocation based on the yield times pads
                                    n_pads = <int>(current_sector_proportion_to_allocate /  current_sector_min_viable_proportions) # 6 was the unmber of pads
                                    current_sector_proportion_to_allocate = n_pads * current_sector_min_viable_proportions
                                    current_yield_obtained = n_pads * current_yield

                                elif sector_footprint_requirements[sector_counter] == 3:
                                    current_yield_obtained = current_sector_proportion_to_allocate * current_yield # Yield will be 1 for areal

                                elif sector_footprint_requirements[sector_counter] == 4:
                                    current_yield_obtained = current_sector_proportion_to_allocate * current_yield # Yield will be 1 for areal

                                elif sector_footprint_requirements[sector_counter] == 5:
                                    current_yield_obtained = current_yield # NOTE That current yield here is not multiplied by area for this type of conversion.
                                elif sector_footprint_requirements[sector_counter] == 6:
                                    current_yield_obtained = current_yield # NOTE That current yield here is not multiplied by area for this type of conversion.
                                else:
                                    raise NameError('wtf')

                                if current_sector_current_country_demand >= current_yield  and sector_current_allocation_location[sector_counter] < max_to_allocate:
                                    if current_yield > 0:

                                        # Record row-col of all cells that change in a 3dim npy array
                                        sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = current_row_id
                                        sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = current_col_id

                                        # Record proportion allocated and yield obtained in 2dim arrays
                                        sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = current_sector_proportion_to_allocate
                                        available_land[current_row_id, current_col_id] -= current_sector_proportion_to_allocate

                                        # For hydro, have to consider spatial adjacency
                                        # MANUSCRIPT NOTE: We made the assumption that if the 9cell availability was greater than country demand, the hydro plant would not be made. (THUS, this code is not replicated in the conditional below).
                                        if sector_yield_notes[sector_counter] == 9:

                                            adjacent_cell_ul_row_id = current_row_id - 1
                                            adjacent_cell_u_row_id = current_row_id - 1
                                            adjacent_cell_ur_row_id = current_row_id - 1
                                            adjacent_cell_r_row_id = current_row_id
                                            adjacent_cell_dr_row_id = current_row_id + 1
                                            adjacent_cell_d_row_id = current_row_id + 1
                                            adjacent_cell_dl_row_id = current_row_id + 1
                                            adjacent_cell_l_row_id = current_row_id

                                            adjacent_cell_ul_col_id = current_col_id - 1
                                            adjacent_cell_u_col_id = current_col_id
                                            adjacent_cell_ur_col_id = current_col_id + 1
                                            adjacent_cell_r_col_id = current_col_id + 1
                                            adjacent_cell_dr_col_id = current_col_id + 1
                                            adjacent_cell_d_col_id = current_col_id
                                            adjacent_cell_dl_col_id = current_col_id - 1
                                            adjacent_cell_l_col_id = current_col_id - 1

                                            # check that one of the adjacent cells has not been taken. write if so
                                            if available_land[adjacent_cell_ul_row_id, adjacent_cell_ul_col_id] > 0.0:
                                                sector_current_allocation_location[sector_counter] += 1
                                                sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_ul_row_id
                                                sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_ul_col_id
                                                sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_ul_row_id, adjacent_cell_ul_col_id]
                                                available_land[adjacent_cell_ul_row_id, adjacent_cell_ul_col_id] = 0.0

                                            if available_land[adjacent_cell_u_row_id, adjacent_cell_u_col_id] > 0.0:
                                                sector_current_allocation_location[sector_counter] += 1
                                                sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_u_row_id
                                                sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_u_col_id
                                                sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_u_row_id, adjacent_cell_u_col_id]
                                                available_land[adjacent_cell_u_row_id, adjacent_cell_u_col_id] = 0.0

                                            if available_land[adjacent_cell_ur_row_id, adjacent_cell_ur_col_id] > 0.0:
                                                sector_current_allocation_location[sector_counter] += 1
                                                sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_ur_row_id
                                                sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_ur_col_id
                                                sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_ur_row_id, adjacent_cell_ur_col_id]
                                                available_land[adjacent_cell_ur_row_id, adjacent_cell_ur_col_id] = 0.0

                                            if available_land[adjacent_cell_r_row_id, adjacent_cell_r_col_id] > 0.0:
                                                sector_current_allocation_location[sector_counter] += 1
                                                sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_r_row_id
                                                sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_r_col_id
                                                sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_r_row_id, adjacent_cell_r_col_id]
                                                available_land[adjacent_cell_r_row_id, adjacent_cell_r_col_id] = 0.0

                                            if available_land[adjacent_cell_dr_row_id, adjacent_cell_dr_col_id] > 0.0:
                                                sector_current_allocation_location[sector_counter] += 1
                                                sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_dr_row_id
                                                sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_dr_col_id
                                                sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_dr_row_id, adjacent_cell_dr_col_id]
                                                available_land[adjacent_cell_dr_row_id, adjacent_cell_dr_col_id] = 0.0

                                            if available_land[adjacent_cell_d_row_id, adjacent_cell_d_col_id] > 0.0:
                                                sector_current_allocation_location[sector_counter] += 1
                                                sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_d_row_id
                                                sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_d_col_id
                                                sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_d_row_id, adjacent_cell_d_col_id]
                                                available_land[adjacent_cell_d_row_id, adjacent_cell_d_col_id] = 0.0

                                            if available_land[adjacent_cell_dl_row_id, adjacent_cell_dl_col_id] > 0.0:
                                                sector_current_allocation_location[sector_counter] += 1
                                                sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_dl_row_id
                                                sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_dl_col_id
                                                sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_dl_row_id, adjacent_cell_dl_col_id]
                                                available_land[adjacent_cell_dl_row_id, adjacent_cell_dl_col_id] = 0.0

                                            if available_land[adjacent_cell_l_row_id, adjacent_cell_l_col_id] > 0.0:
                                                sector_current_allocation_location[sector_counter] += 1
                                                sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = adjacent_cell_l_row_id
                                                sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = adjacent_cell_l_col_id
                                                sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = available_land[adjacent_cell_l_row_id, adjacent_cell_l_col_id]
                                                available_land[adjacent_cell_l_row_id, adjacent_cell_l_col_id] = 0.0

                                            sector_successful_steps_taken[sector_counter] += 8 # Not nine cause hit again below as with other sectors.

                                        # Record yield obtained in 2dim arrays
                                        sector_yield_obtained_lists[sector_counter, sector_current_allocation_location[sector_counter]] = current_yield_obtained

                                        # Record country-specific changes too
                                        country_sector_production[current_country_id - 1, sector_counter] += current_yield_obtained

                                        # Decrease the projections_array by how much yield was obtained
                                        projections_array[current_country_id - 1, sector_counter] -= current_yield_obtained

                                        # For ending conditions, record this
                                        sector_successful_steps_taken[sector_counter] += 1


                                    else:
                                        pass
                                        # warning_message += ' WARNING!! went to a cell that had no yield'
                                # If country  demand is less  than the gridcell's yield, then only part of it is allocated.
                                elif current_sector_current_country_demand > 0 and sector_current_allocation_location[sector_counter] < max_to_allocate:
                                    if current_yield > 0:

                                        # Record row-col of all cells that change in a 3dim npy array
                                        sector_change_keys_lists[sector_counter, 0, sector_current_allocation_location[sector_counter]] = current_row_id
                                        sector_change_keys_lists[sector_counter, 1, sector_current_allocation_location[sector_counter]] = current_col_id

                                        # Record proportion allocated and yield obtained in 2dim arrays
                                        sector_proportion_allocated_lists[sector_counter, sector_current_allocation_location[sector_counter]] = current_sector_proportion_to_allocate

                                        # Record yield obtained in 2dim arrays
                                        sector_yield_obtained_lists[sector_counter, sector_current_allocation_location[sector_counter]] = current_sector_proportion_to_allocate * current_yield_obtained

                                        # Record country-specific changes too
                                        country_sector_production[current_country_id - 1, sector_counter] += current_sector_current_country_demand

                                        # Decrease the projections_array by how much yield was obtained
                                        projections_array[current_country_id - 1, sector_counter] -= current_sector_current_country_demand

                                        if sector_yield_notes[sector_counter] == 9:
                                            sector_successful_steps_taken[sector_counter] += 9
                                        else:
                                            sector_successful_steps_taken[sector_counter] += 1


                                        available_land[current_row_id, current_col_id] -= current_sector_proportion_to_allocate * (current_sector_current_country_demand / current_yield)

                                        country_sector_continue_array[current_country_id - 1, sector_counter] = 0

                                        # Upon finishing a country_sector, check to see if the whole sector is done by running through each country.
                                        l = 0
                                        for k in range(num_countries):
                                            l += country_sector_continue_array[k, sector_counter]
                                        if l == 0:
                                            country_sector_continue_array[current_country_id - 1, sector_counter] = 0
                                            sector_continue_array[sector_counter] = 0


                                        continue_sum = 0
                                        for m in range(num_sectors):
                                            continue_sum += sector_continue_array[m]
                                        if continue_sum == 0:
                                            continue_algorithm = 0
                                    else:
                                        warning_message += ' WARNING!! sector demand was less than yield  AND yield was zero?'
                                        raise NameError(warning_message)
                                else:
                                    country_sector_continue_array[current_country_id - 1, sector_counter] = 0

                                    # Upon finishing a country_sector, check to see if the whole sector is done by running through each country.
                                    l = 0
                                    for k in range(num_countries):
                                        l += country_sector_continue_array[k, sector_counter]
                                    if l == 0:
                                        country_sector_continue_array[current_country_id - 1, sector_counter] = 0
                                        sector_continue_array[sector_counter] = 0

                                    continue_sum = 0
                                    for m in range(num_sectors):
                                        continue_sum += sector_continue_array[m]
                                    if continue_sum == 0:
                                        continue_algorithm = 0


                            else:
                                pass
                                # Didnt consider this celll because country_sector_continue_array was 0 for this country, this sector.
                        else:
                            pass
                            # available land  was not > min_viable, stopped considering the focal cell

                    # Notice that these increment even if hit a non-country area (255)
                    sector_current_allocation_location[sector_counter] += 1
                    sector_current_step_location[sector_counter] += 1

                    if True:
                        if cell_counter % 1012300 == 0  or cell_counter % 1012301 == 0 or cell_counter < 5 or (1000 < cell_counter < 1005) or (100000 < cell_counter < 100005) or (10000000 < cell_counter < 10000005):
                            report_message = warning_message + ', id: ' + str(cell_counter) + ', sector: ' + sector_names[sector_counter] + ', country: ' + str(
                                current_sector_current_country_demand) + ', proportion to be allocated: ' + str(
                                current_sector_proportion_to_allocate) + ' current_yield: ' + str(
                                current_yield) + ' current_yield_obtained: ' + str(
                                current_yield_obtained) + ' available land after allocation: ' + str(
                                available_land[current_row_id, current_col_id]) + ', sector_successful_steps_taken: ' + str(
                                sector_successful_steps_taken[sector_counter]) + ', sector_current_step_location: ' + str(
                                sector_current_step_location[sector_counter]) + ', current cell row: ' + str(current_row_id) + ', current cell col: ' + str(
                                current_col_id) + ', current_sector_min_viable_proportions: ' + str(
                                current_sector_min_viable_proportions) + ', current_sector_max_viable_proportions: ' + str(
                                current_sector_max_viable_proportions) + ', sector_continue: ' + str(sector_continue_array[sector_counter])
                            print (report_message)
                    if False:
                        if warning_message != '' or cell_counter % 1012300 == 0  or cell_counter % 1012301 == 0 or cell_counter < 5 or (1000 < cell_counter < 1005) or (100000 < cell_counter < 100005) or (10000000 < cell_counter < 10000005):
                            if current_country_id - 1 <= 253 or True:
                                if True:
                                    report += warning_message + '\n'
                                    if warning_message:
                                        report_message = warning_message + ', id: ' + str(cell_counter) + ', sector: ' + sector_names[sector_counter] + ', country: ' + str(country_iso3[current_country_id-1]) + ', sector-country remaining demand: ' + str(current_sector_current_country_demand) + ', proportion to be allocated: ' + str(current_sector_proportion_to_allocate)  + ' available land after allocation: ' + str(available_land[current_row_id, current_col_id])+ ', sector_successful_steps_taken: ' + str(sector_successful_steps_taken[sector_counter])  + ', sector_current_step_location: ' + str(sector_current_step_location[sector_counter]) +  ', current cell row: ' + str(current_row_id) + ', current cell col: ' + str(current_col_id) + ', current_sector_min_viable_proportions: ' + str(current_sector_min_viable_proportions) + ', current_sector_max_viable_proportions: ' + str(current_sector_max_viable_proportions) + ', sector_continue: ' + str(sector_continue_array[sector_counter]) + ', country_sector_continue: ' + str(country_sector_continue_array[current_country_id - 1, sector_counter])

                                    else:
                                        report_message = 'id: ' + str(cell_counter) + ', sector: ' + sector_names[sector_counter] + ', ' +  str(current_yield_obtained) + ',' + str(sector_footprint_requirements) + ', ' + str(sector_yield_notes) + ', ' + str(current_yield) + ', country: ' + str(country_iso3[current_country_id-1]) + ', sector-country remaining demand: ' + str(current_sector_current_country_demand) + ', proportion to be allocated: ' + str(current_sector_proportion_to_allocate)  + ' available land after allocation: ' + str(available_land[current_row_id, current_col_id])+ ', sector_successful_steps_taken: ' + str(sector_successful_steps_taken[sector_counter])  + ', sector_current_step_location: ' + str(sector_current_step_location[sector_counter]) +  ', current cell row: ' + str(current_row_id) + ', current cell col: ' + str(current_col_id) + ', current_sector_min_viable_proportions: ' + str(current_sector_min_viable_proportions) + ', current_sector_max_viable_proportions: ' + str(current_sector_max_viable_proportions) + ', sector_continue: ' + str(sector_continue_array[sector_counter]) + ', country_sector_continue: ' + str(country_sector_continue_array[current_country_id - 1, sector_counter])
                                    print (report_message)

                                    report += report_message + '\n'

                # if sector_current_step_location[sector_counter] + sector_step_sizes[sector_counter] >= 3:
                # if sector_current_step_location[sector_counter] + sector_step_sizes[sector_counter] >= sector_num_changes[sector_counter]:

                    # TODO RECONSIDER how SUCCESSFUL STEPS TAKEN FITS IN
                # if sector_successful_steps_taken[sector_counter] + sector_step_sizes[sector_counter] >= sector_num_steps_loaded[sector_counter]:
                if sector_current_step_location[sector_counter] + sector_step_sizes[sector_counter] >= sector_num_steps_loaded[sector_counter]:
                    print ('Ran out of loaded data for sector ' + sector_names[sector_counter])
                    # if sector_yields[sector_counter, cell_counter] > 0:
                    #     report += 'WARNING !!!!! Shouldnt get here either, because this means the goal wasnt met AND the yield was still >0\n'


                    # Get num total in file
                    with open(ranked_keys_paths[sector_counter], 'rb') as fhandle:
                        print ('Loading NEW ranked_keys for sector ', sector_names[sector_counter])

                        major, minor = np.lib.format.read_magic(fhandle)
                        shape, fortran, dtype = np.lib.format.read_array_header_1_0(fhandle)

                        if shape[1] < sector_num_steps_loaded[sector_counter] + num_to_load_per_chunk:
                            num_to_load_this_chunk = shape[1] - sector_num_steps_loaded[sector_counter]
                        else:
                            num_to_load_this_chunk = num_to_load_per_chunk
                        # sector_num_steps_loaded[sector_counter] += num_to_load_this_chunk



                    if sector_num_steps_loaded[sector_counter] <= shape[1] and not num_to_load_this_chunk == 0:
                        a = read_2d_npy_chunk(ranked_keys_paths[sector_counter], 0, 1, sector_num_steps_loaded[sector_counter], num_to_load_this_chunk)
                        ranked_keys[sector_counter, 0, 0: num_to_load_this_chunk] = a
                        b = read_2d_npy_chunk(ranked_keys_paths[sector_counter], 1, 1, sector_num_steps_loaded[sector_counter], num_to_load_this_chunk)
                        ranked_keys[sector_counter, 1, 0: num_to_load_this_chunk] = b
                    else:
                        print ('Hit end of array for ', sector_names[sector_counter])
                        sector_continue_array[sector_counter] = 0

                    sector_num_steps_loaded[sector_counter] += num_to_load_this_chunk

                    if sector_yield_paths[sector_counter] is not None:
                        with open(sector_yield_paths[sector_counter], 'rb') as fhandle:
                            print ('Loading NEW yield for sector ', sector_names[sector_counter])

                            major, minor = np.lib.format.read_magic(fhandle)
                            shape, fortran, dtype = np.lib.format.read_array_header_1_0(fhandle)

                            if shape[0] < num_to_load_per_chunk:
                                num_to_load_this_chunk = shape[0]
                            else:
                                num_to_load_this_chunk = num_to_load_per_chunk
                            # sector_num_steps_loaded[sector_counter] += num_to_load_this_chunk

                            if sector_num_steps_loaded[sector_counter] < shape[0]:
                                start_byte = sector_current_step_location[sector_counter] * dtype.itemsize
                                fhandle.seek(start_byte, 1) # 0 is absolute, 1 is relative, 2 is from end
                                sector_yields[sector_counter, 0: num_to_load_this_chunk] = np.fromfile(fhandle, count=num_to_load_this_chunk, dtype=dtype)
                            else:
                                print ('Hit end of array for ', sector_names[sector_counter])
                                sector_continue_array[sector_counter] = 0

                else:
                    num_to_load_this_chunk = num_to_load_per_chunk





            else: # Skipped sector because sector_continue_array was 0 for this sector
                pass

        # Upon finishing a country_sector, check to see if the whole sector is done by running through each country.
        l = 0
        for k in range(num_countries):
            l += country_sector_continue_array[k, sector_counter]
        if l == 0:
            country_sector_continue_array[current_country_id - 1, sector_counter] = 0
            sector_continue_array[sector_counter] = 0

        continue_sum = 0
        for m in range(num_sectors):
            continue_sum += sector_continue_array[m]
        if continue_sum == 0:
            print ('YAYAYAYAY! Allocation algorithm has zero values for all in sector_continue_array.')

            projection_sums = np.zeros(num_sectors, dtype=np.float64)
            for sector_counter in range(num_sectors):
                for country_counter in range(num_countries):
                    to_add = projections_array[country_counter, sector_counter]
                    projection_sums[sector_counter] += to_add

            continue_algorithm = 0

    print ('cython time: ' + str(time.time() - start))

    return sector_change_keys_lists, sector_proportion_allocated_lists, sector_yield_obtained_lists, country_sector_production, report


@cython.boundscheck(False)
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def update_float_array_with_discrete_change_list(
        ndarray[np.float64_t, ndim=2] input_array not None,
        ndarray[np.int64_t, ndim=2] change_list not None,
        np.float64_t new_value,
):
    start = time.time()
    cdef long long change_list_counter = 0
    cdef long long num_changes = change_list.shape[1]
    # cdef np.ndarray[np.float64_t, ndim=2] output_array = np.copy(input_array)

    for change_list_counter in range(num_changes):
        input_array[change_list[0, change_list_counter], change_list[1, change_list_counter]] = new_value

    print ('cython time: ' + str(time.time() - start))

    return input_array


@cython.boundscheck(False)
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def add_to_float_array_with_discrete_change_list(
        ndarray[np.float64_t, ndim=2] input_array not None,
        ndarray[np.int64_t, ndim=2] change_list not None,
        np.float64_t value_to_add,
):
    start = time.time()
    cdef long long change_list_counter = 0
    cdef long long num_changes = change_list.shape[1]
    # cdef np.ndarray[np.float64_t, ndim=2] output_array = np.copy(input_array)

    for change_list_counter in range(num_changes):
        input_array[change_list[0, change_list_counter], change_list[1, change_list_counter]] += value_to_add

    print ('cython time: ' + str(time.time() - start))

    return input_array


@cython.boundscheck(False)
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def add_to_int_array_with_discrete_change_list(
        ndarray[np.int64_t, ndim=2] input_array not None,
        ndarray[np.int64_t, ndim=2] change_list not None,
        np.int64_t value_to_add,
):
    start = time.time()
    cdef long long change_list_counter = 0
    cdef long long num_changes = change_list.shape[1]
    # cdef np.ndarray[np.float64_t, ndim=2] output_array = np.copy(input_array)

    for change_list_counter in range(num_changes):
        input_array[change_list[0, change_list_counter], change_list[1, change_list_counter]] += value_to_add

    print ('cython time: ' + str(time.time() - start))

    return input_array


@cython.boundscheck(False)
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def update_float_array_with_change_list_and_value_list(
                         ndarray[np.float64_t, ndim=2] input_array not None,
                         ndarray[np.int64_t, ndim=2] change_list not None,
                         ndarray[np.float64_t, ndim=1] values_list not None,
        ):
    start = time.time()
    cdef long long change_list_counter = 0
    cdef long long num_changes = change_list.shape[1]
    # cdef np.ndarray[np.float64_t, ndim=2] output_array = np.copy(input_array)

    if len(values_list) < num_changes:
        num_changes = len(values_list)

    for change_list_counter in range(num_changes):
        if change_list_counter % 10000000 == 0:
            print ('change_list_counter', change_list_counter, values_list[change_list_counter])
        input_array[change_list[0, change_list_counter], change_list[1, change_list_counter]] = values_list[change_list_counter]

    print ('cython time:  ' + str(time.time() - start))

    return input_array

@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def create_order_array_from_ranked_keys(
                         ndarray[np.int64_t, ndim=2] ranked_keys not None,
                         np.int64_t output_n_rows,
                         np.int64_t output_n_cols,
):
    start = time.time()
    print ('Creating order array from ranked_keys.')
    cdef np.int64_t change_list_counter = 0
    cdef np.int64_t num_changes = ranked_keys.shape[1]

    cdef np.ndarray[np.int64_t, ndim=2] output_array = np.zeros((output_n_rows, output_n_cols), dtype=np.int64)

    for change_list_counter in range(num_changes):
        output_array[ranked_keys[0, change_list_counter], ranked_keys[1, change_list_counter]] = change_list_counter
    print ('  cython time: ' + str(time.time() - start))
    return output_array


@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def create_values_1dim_array_from_ranked_keys(
                         ndarray[np.int64_t, ndim=2] ranked_keys not None,
                         ndarray[np.float64_t, ndim=2] values_array not None,
):
    start = time.time()
    print ('Cythoning create_values_1dim_array_from_ranked_keys etc.')
    cdef np.int64_t change_list_counter = 0
    cdef np.int64_t num_changes = ranked_keys.shape[1]

    cdef np.ndarray[np.float64_t, ndim=1] output_array = np.zeros(num_changes, dtype=np.float64)
    for change_list_counter in range(num_changes):
        output_array[change_list_counter] = values_array[ranked_keys[0, change_list_counter], ranked_keys[1, change_list_counter]]

    print ('  cython time: ' + str(time.time() - start))
    return output_array

@cython.cdivision(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def get_2d_keys_from_sorted_keys_1d(
                         ndarray[np.int64_t, ndim=2] sorted_keys_1dim not None,
                         np.int64_t n_rows,
                         np.int64_t n_cols,
):
    start = time.time()
    print ('Cython get_2d_keys_from_sorted_keys_1d.')
    cdef long long num_sorted_keys = len(sorted_keys_1dim[0])
    cdef np.int64_t num_total_keys = n_rows * n_cols

    cdef np.int64_t k, l
    cdef np.ndarray[np.int64_t, ndim=2] output_keys = np.zeros((2, num_sorted_keys), dtype=np.int64)

    for k in range(num_sorted_keys):
        if k % 1000000 == 0:
            print (k, sorted_keys_1dim[k], <int>(sorted_keys_1dim[k] / n_cols))

        output_keys[0, k] = <int>(sorted_keys_1dim[k] / n_cols)
        output_keys[1, k] = sorted_keys_1dim[k] - <int>(n_cols * output_keys[0, k] )


    return output_keys

# def factor_convolution_value_to_suitability(
#         ndarray[DTYPEFLOAT64_t, ndim=2] x not None,
#         double direct_suitability,
#         double a,
#         double b,
#         double c):
#     cdef int r_counter, c_counter
# 
#     cdef int n_rows = x.shape[0]
#     cdef int n_cols = x.shape[1]
# 
#     cdef np.ndarray[np.float64_t, ndim=2] output_array = np.zeros((n_rows, n_cols), dtype=np.float64)
# 
#     for r_counter in range(n_rows):
#         for c_counter in range(n_cols):
#             # output_array[r_counter, c_counter] = direct_suitability * (a + b * x + c * x ** 2 + d * x ** 3 + e * x ** 4)
#             output_array[r_counter, c_counter] = (a + (x[r_counter, c_counter] ** b * (2 - a - (1 - c) - x[r_counter, c_counter])))
# 
#     return output_array

def calc_change_matrix_of_two_int_arrays(ndarray[DTYPEINT32_t, ndim=2] a1 not None, ndarray[DTYPEINT32_t, ndim=2] a2 not None, list classes not None):
# def calc_change_matrix_of_two_int_arrays(ndarray[DTYPEINT32_t, ndim=2] a1 not None, ndarray[DTYPEINT32_t, ndim=2] a2 not None, ndarray[DTYPEINT32_t, ndim=1] classes not None):
    """NOTE WARNING, does not currently take into account case where value is not included in either."""
    unique1, count1 = np.unique(a1, return_counts=True)
    unique2, count2 = np.unique(a2, return_counts=True)

    cdef int i, j
    cdef int n_rows = a1.shape[0]
    cdef int n_cols = a1.shape[1]
    cdef int m_n_rows = len(classes)

    # Create lookup from lulc class to lulc counter
    #cdef np.ndarray[np.int32_t, ndim=1] lulc_counters = np.zeros((m_n_rows), dtype=np.int32)

    lulc_counters = {}

    for i in range(m_n_rows):
        lulc_counters[classes[i]] = i

    cdef np.ndarray[np.int32_t, ndim=2] a3 = np.zeros((m_n_rows, m_n_rows), dtype=np.int32)

    if m_n_rows > 0:
        for i in range(n_rows):
            for j in range(n_cols):
                if a1[i, j] in lulc_counters and a2[i, j] in lulc_counters:
                    a3[lulc_counters[a1[i, j]], lulc_counters[a2[i, j]]] += 1

    return a3, lulc_counters

@cython.cdivision(True)
@cython.embedsignature(True)
@cython.boundscheck(True)
@cython.wraparound(False)
def calculate_coarse_state_stack_from_fine_classified(ndarray[DTYPEINT32_t, ndim=2] fine_input_array,
                                                       ndarray[DTYPEFLOAT32_t, ndim=2] coarse_match_array,
                                                       ndarray[DTYPEINT32_t, ndim=1] values_to_summarize,
                                                       long coarse_reporting_row_frequency = 10):
    """
    Return a 3d numpy array with the number of values_to_summarize in the fine array present in each coarse-sized grid-cell.

    :param fine_input_array: Input to be array to be summarized. Assumes type np.int32
    :param coarse_match_array: Sets the shape of the chunk used on fine to sumarize the fine. Assumes type np.float32
    :param values_to_summarize: The specific values to be counted. This will determine the size of the first dimention in the output.
    :param max_value_to_summarize: TRICKY OPTIMIZATION: It is much faster to have a long 1dim array to index the value_to_summarize into the right place
    in the output 3dim array. Internally, this creates an array as long as the max value and then assigns a position to that lookup.
    :param coarse_reporting_row_frequency: Controls how frequently the algorithm prints updates, based on the number of coarse rows that have been processed.
    :return:
    """

    cdef int fine_n_rows = fine_input_array.shape[0]
    cdef int fine_n_cols = fine_input_array.shape[1]
    cdef int coarse_n_rows = coarse_match_array.shape[0]
    cdef int coarse_n_cols = coarse_match_array.shape[1]
    cdef int n_values_to_summarize = len(values_to_summarize) + 1
    cdef int implied_chunk_size = <int>(fine_n_rows / coarse_n_rows)
    cdef np.ndarray[np.int32_t, ndim=3] output_3d = np.zeros((n_values_to_summarize, coarse_n_rows, coarse_n_cols), dtype=np.int32)

    # TRICKY Optimization: create a 1dim array where the value from the fine array is the index into this
    # lookup array, which is zero throughout except where it is used as a lookup value
    cdef int max_value_to_include = np.max(values_to_summarize).astype(np.int32)
    cdef np.ndarray[np.int32_t, ndim=1] value_to_position = np.full(max_value_to_include + 1, max_value_to_include + 1, dtype=np.int32)
    cdef int current_value
    cdef int c = 0
    for current_value in range(max_value_to_include + 1):
        if current_value in values_to_summarize:
            value_to_position[current_value] = c
            c += 1

    cdef int chunk_fine_r, chunk_fine_c, fine_r, fine_c, current_r, current_c, coarse_r, coarse_c

    # Iterate through coarse chunks
    for coarse_r in range(coarse_n_rows):
        if coarse_r % coarse_reporting_row_frequency == 0:
            print ('calculate_coarse_state_stack_from_fine_classified on row ' + str(coarse_r) + ' out of ' + str(coarse_n_rows))
        for coarse_c in range(coarse_n_cols):

            # Within a coarse chunk, iterate through the fine cells but write to a non-chunk fine output.
            for chunk_fine_r in range(implied_chunk_size):
                fine_r = coarse_r * implied_chunk_size + chunk_fine_r
                for chunk_fine_c in range(implied_chunk_size):
                    fine_c = coarse_c * implied_chunk_size + chunk_fine_c
                    current_value = fine_input_array[fine_r, fine_c]
                    if current_value <= max_value_to_include:
                        output_3d[value_to_position[current_value], coarse_r, coarse_c] += 1

    return output_3d



def calculate_zone_to_chunk_list_lookup_dict(ndarray[DTYPEINT32_t, ndim=2] input_array):
    """For every unique id in input_array, return two row, column arrays that store for each id-th column set of RC indices that are in that id. """

    cdef int n_rows = input_array.shape[0]
    cdef int n_cols = input_array.shape[1]
    cdef int r, c

    cdef dict output_dict = {}
    cdef list current_list = []

    values, counts = np.unique(input_array, return_counts=True)

    cdef int n_values = np.max(values) + 1

    cdef int max_n_in_zone = np.max(counts[0: ]) # Skip the first one which is -9999

    cdef output_r_array = np.zeros((n_values, max_n_in_zone), dtype=np.int32)
    cdef output_c_array = np.zeros((n_values, max_n_in_zone), dtype=np.int32)

    cdef row_counter = np.zeros(max_n_in_zone, dtype=np.int32)
    cdef int current_row_counter = 0


    for r in range(n_rows):
        for c in range(n_cols):
            if input_array[r, c] != -9999:
                output_r_array[input_array[r, c], row_counter[input_array[r, c]]] = r
                output_c_array[input_array[r, c], row_counter[input_array[r, c]]] = c
                row_counter[input_array[r, c]] += 1

    return output_r_array, output_c_array










