import os, sys, warnings, logging, shutil
from osgeo import gdal
# gdal.SetConfigOption("IGNORE_COG_LAYOUT_BREAK", "YES") 
# gdal.PushErrorHandler('CPLQuietErrorHandler')
from osgeo import gdal, osr, ogr
import numpy as np
import hazelbean as hb

L = hb.get_logger('arrayframe', logging_level='warning') # hb.arrayframe.L.setLevel(logging.DEBUG)


class ArrayFrame(object):

    """DESIRED Functinality to add: starting with an array, save as AF."""
    def __init__(self, path, **kwargs):
        if path is not None:
            try:
                assert os.path.exists(path) is True
            except:
                raise NameError('Path ' + str(path) + ' does not exist. Attempting to make an ArrayFrame out of it thus failed.')
        else:
            L.debug('Loading an arrayframe with path=None, which means it will be an in-memory ds.')
        self.load_data_on_init = kwargs.get('load_data_on_init', False)

        self.path = path

        if self.path is None:
            # If path is none, the it's a memory only array frame, which doesn't have access to ANYTHING yet until the array is loaded via load_data()
            self.ds = None
            self.band = None
            self.num_cols = None
            self.n_cols = None
            self.num_rows = None
            self.n_rows = None
            self.shape = None
            self.size = None
            self.ndv = None
            self.datatype = None


        else:
            # If path is set, then we can get all attributes from the DS
            a = hb.path_exists(path)

            self.ds = gdal.OpenEx(path, gdal.GA_Update, open_options=["IGNORE_COG_LAYOUT_BREAK=YES"])
            self.band = self.ds.GetRasterBand(1)
            self.num_cols = self.ds.RasterXSize
            self.n_cols = self.num_cols
            self.num_rows = self.ds.RasterYSize
            self.n_rows = self.num_rows
            self.shape = (self.num_rows, self.num_cols)
            self.size = self.num_cols * self.num_rows

            self.projection = self.ds.GetProjection()
            self.geotransform = self.ds.GetGeoTransform()
            self.cell_size = self.geotransform[1]
            self.info_as_string = gdal.Info(self.ds)
            self.res = self.cell_size
            self.resolution = self.cell_size
            self.x_res = self.res
            self.y_res = self.geotransform[5]
            if self.x_res != abs(self.y_res):
                L.warning('Warning, x_res not same as abs(y_res). This may be possible to use correctly, but if you dont know exactly why you are doing it and still do it, you\'re probably a Sith.')



            # From here on it's starting to get bloated and might affect performance in the way a Frame idea doesnt make sense.
            self.raster_info = hb.get_raster_info_hb(self.path)
            self.old_bounding_box = hb.get_bounding_box(self.path, return_in_old_order=True)
            self.bounding_box = self.raster_info['bounding_box']  # projected coordinates as [minx, miny, maxx, maxy]
            self.bb = self.bounding_box
            self.left_lat = self.bb[0]
            self.bottom_lon = self.bb[1]
            self.right_lat = self.bb[2]
            self.top_lon = self.bb[3]
            self.lat_size = self.left_lat - self.right_lat
            self.lon_size = self.top_lon - self.bottom_lon

            # Note that by definition of being an Arrayframe (rather than a block of one), this will always have 0 for first two entries and the second two will (should
            # be equivilent to n_rows, n_cols
            self.cr_widthheight = hb.bb_path_to_cr_size(self.path, self.bb)

            self.ndv = self.band.GetNoDataValue()

            # TODOO Consider eliminating data_type
            self.data_type = self.band.DataType
            self.datatype = self.data_type

            if self.ndv is None:
                L.info('NDV for raster at ' + self.path + ' was not set. ')

            if not self.geotransform:
                L.critical('Geotransform not set for arrayframe at ' + self.path + '. Forcing to WGS84 global.')

            if not self.projection:
                L.critical('Projection not set for arrayframe at ' + self.path + '')

        self._data = None
        self.data_loaded = False

        self.stats = None # Time consuming, but can load from set_stats() method.

        # Set when self.stats is set via set_stats()
        self.min = None
        self.max = None
        self.median = None
        self.mean = None

        # Save these so that they don't need to be often recomputed.
        self._valid_mask = None
        self.valid_mask_set = False
        self.num_valid = None

        self._ndv_mask = None
        self.ndv_mask_set = False
        self.num_ndv = None

        self._nonzero_mask = None
        self.nonzero_mask_set = False
        self.num_nonzero = None

        self._zero_mask = None
        self.zero_mask_set = False
        self.num_zero = None

        if self.load_data_on_init:
            self.load_data()

        if self.ndv is None:
            L.info('NDV for raster at ' + str(self.path) + ' was not set. ')

        # if not self.geotransform:
        #     L.critical('Geotransform not set for arrayframe at ' + self.path + '. Forcing to WGS84 global.')
        #
        # if not self.projection:
        #     L.critical('Projection not set for arrayframe at ' + self.path + '')

    def reload_ds_and_band(self):
        # After attributes have been changed on dataset of band, this needs to be called or the actual  attribute will not be updated
        self.band = None
        self.ds = None
        self.ds = gdal.Open(self.path, gdal.GA_Update)
        self.band = self.ds.GetRasterBand(1)


    def set_geotransform_to_global_wgs84_from_num_cols(self):
        res = 360 / self.num_cols
        self.set_geotransform(hb.get_global_geotransform_from_resolution(res))

    def set_geotransform(self, input_geotransform):
        self.ds.SetGeotransform(input_geotransform)
        self.reload_ds_and_band()
        self.geotransform = self.ds.GetGeoTransform()

    def set_projection_to_wgs84(self):
        self.set_projection(hb.wgs_84_wkt)

    def set_projection(self, input_wkt):
        self.ds.SetProjection(input_wkt)
        self.reload_ds_and_band()
        self.projection = self.ds.GetProjection()

    def set_ndv_without_data_rewrite(self, input_ndv):
        self.band.SetNoDataValue(input_ndv)
        self.reload_ds_and_band()
        self.ndv = input_ndv

    @property
    def data(self):
        if self._data is None:
            self.load_data()
        return self._data

    @data.setter
    def data(self, value):
        raise NameError('Cannot set data directly for ArrayFrames. Use load_data() method.')

    def load_data(self):
        if self.size > hb.MAX_IN_MEMORY_ARRAY_SIZE:
            print ('WARNING! Could not load all of the array in Arrayframe at ' + self.path + '. Instead, loading strided subset.')
            L.warning('WARNING! Could not load all of the array in Arrayframe at ' + self.path + '. Instead, loading strided subset.')
            warnings.warn('WARNING! Could not load all of the array in Arrayframe at ' + self.path + '. Instead, loading strided subset.')
            self._data = hb.as_array_resampled_to_size(self.path, hb.MAX_IN_MEMORY_ARRAY_SIZE)
            self.data_loaded = True
        else:
            self._data = self.band.ReadAsArray()
            self.data_loaded = True

    def load_array_as_data(self, input_array):
        L.info('Called load_array_as_data to ArrayFrame.')
        self._data = input_array
        self.data_loaded = True

        self.set_attributes_from_data()

    def set_attributes_from_data(self):

        # If path is set, then we can get all attributes from the DS
        self.num_cols = self._data.shape[1]
        self.n_cols = self._data.shape[1]
        self.num_rows = self._data.shape[0]
        self.n_rows = self._data.shape[0]
        self.shape = (self.num_rows, self.num_cols)
        self.size = self.num_cols * self.num_rows

        self.numpy_data_type = self._data.dtype
        self.gdal_data_number = hb.numpy_type_to_gdal_number[self.numpy_data_type]
        self.gdal_data_type = hb.gdal_number_to_gdal_type[self.gdal_data_number]
        self.data_type = self.gdal_data_number
        self.ndv = hb.get_correct_ndv_from_dtype_flex[str(self.numpy_data_type)]

    @property
    def valid_mask(self):
        if self._valid_mask is None:
            self.set_valid_mask()
        return self._valid_mask

    @valid_mask.setter
    def valid_mask(self, value):
        raise NameError('Cannot directly set valid_mask. Use set_valid_and_ndv_masks() method.')

    def set_valid_and_ndv_masks(self):
        # For performance reasons, it is faster to set both of these at once.
        # self._valid_mask = np.where(self.data != self.ndv) # NOTE, this method was slower
        self._valid_mask = np.where(self.data != self.ndv, 1, 0).astype(np.ubyte)
        self._ndv_mask = np.invert(self._valid_mask)
        self.num_valid = np.count_nonzero(self.valid_mask)
        self.num_ndv = self.size - self.num_valid
        self.valid_mask_set = True
        self.ndv_mask_set = True
        L.info('Setting valid and NDV masks. ' + str(self.num_valid) + ' valid. ' + str(self.num_ndv) + ' invalid.')

    def set_valid_mask(self):
        # self._valid_mask = np.where(self.data != self.ndv) # NOTE, this method was slower
        self._valid_mask = np.where(self.data != self.ndv, 1, 0).astype(np.ubyte)
        self.num_valid = np.count_nonzero(self.valid_mask)
        self.valid_mask_set = True
        L.info('Setting valid mask. ' + str(self.num_valid) + ' valid.')

    # TODOO Setting these via setters got confusing and may have been overboard.
    @property
    def ndv_mask(self):
        if self._ndv_mask is None:
            self.set_ndv_mask()
        return self._ndv_mask

    @ndv_mask.setter
    def ndv_mask(self, value):
        raise NameError('Cannot directly set ndv_mask. Use set_valid_and_ndv_masks() method.')

    def set_ndv_mask(self):
        self._ndv_mask = np.where(self.data == self.ndv, 1, 0).astype(np.ubyte)
        self.num_ndv = np.count_nonzero(self.ndv_mask)
        self.ndv_mask_set = True
        L.info('Setting ndv mask. ' + str(self.num_ndv) + ' ndv.')

    @property
    def zero_mask(self):
        if self._zero_mask is None:
            self.set_zero_mask()
        return self._zero_mask

    @zero_mask.setter
    def zero_mask(self, value):
        raise NameError('Cannot directly set zero_mask. Use set_zero_mask() method.')

    def set_zero_and_nonzero_masks(self):
        # For performance reasons, it is faster to set both of these at once.
        self._nonzero_mask = np.where(self.data != 0, 1, 0).astype(np.ubyte)
        self._ndv_mask = np.invert(self._nonzero_mask)
        self.num_nonzero = np.count_nonzero(self._nonzero_mask)
        self.num_zero = self.size - self.num_nonzero
        self.zero_mask_set = True
        self.nonzero_mask_set = True
        L.info('Setting zero and nonzero masks. ' + str(self.num_zero) + ' zero. ' + str(self.num_nonzero) + ' nonzero.')


    def set_zero_mask(self):
        self._zero_mask = np.where(self.data == 0, 1, 0).astype(np.ubyte)
        self.num_zero = np.count_nonzero(self._zero_mask)
        self.num_nonzero = self.size - self.num_zero
        self.zero_mask_set = True
        L.info('Setting zero mask. ' + str(self.num_zero) + ' zero, ' + str(self.num_nonzero) + ' nonzero.')


    @property
    def nonzero_mask(self):
        if self._nonzero_mask is None:
            self.set_nonzero_mask()
        return self._nonzero_mask

    @nonzero_mask.setter
    def nonzero_mask(self, value):
        raise NameError('Cannot directly set nonzero_mask. Use set_nonzero_mask() method.')

    def set_nonzero_mask(self):
        self._nonzero_mask = np.where(self.data == 1, 1, 0).astype(np.ubyte)
        self.num_nonzero = np.count_nonzero(self._nonzero_mask)
        self.num_zero = self.size - self.num_nonzero
        self.nonzero_mask_set = True
        L.info('Setting nonzero mask. ' + str(self.num_nonzero) + ' nonzero, ' + str(self.num_zero) + '.')

    def save(self, output_path, overwrite_existing=False):
        """SAVING in this context only means renaming and moving the originnal file."""
        self.close_data()
        if os.path.exists(output_path):
            if overwrite_existing:
                os.remove(output_path)
            else:
                raise NameError('Attempted to save ArrayFrame to ' + output_path + ', but that path exists.  Consider setting overwrite_existing=True')

        os.rename(self.path, output_path)
        self.path = output_path

    def __str__(self):
        return hb.describe_af(self)

    def load_all(self):
        self.load_data()
        self.set_stats()
        self.set_valid_and_ndv_masks()# Faster than calcing separate.
        self.set_zero_and_nonzero_masks()

    def set_stats(self):
        self.stats = self.band.ComputeStatistics(False)
        self.min, self.max, self.median, self.mean = self.stats[0], self.stats[1], self.stats[2], self.stats[3]

    def sum(self):
        return np.sum(self.data)

    def close_data(self):
        # Close and clean up dataset
        self.band = None
        gdal.Dataset.__swig_destroy__(self.ds)
        self.ds = None

    # TODOO consider removing. Overboard?
    def __add__(self, after):
        def op(left, right):
            return left + right
        output_path = hb.temp(filename_start='add', remove_at_exit=True)
        return hb.raster_calculator_flex([self.path, after.path], op, output_path)

    def __sub__(self, after):
        def op(left, right):
            return left - right
        output_path = hb.temp(filename_start='sub', remove_at_exit=True)
        return hb.raster_calculator_flex([self.path, after.path], op, output_path)

    def __mul__(self, after):
        def op(left, right):
            return left + right
        output_path = hb.temp(filename_start='mul', remove_at_exit=True)
        return hb.raster_calculator_flex([self.path, after.path], op, output_path)

    def __truediv__(self, after):
        def op(left, right):
            return left + right
        output_path = hb.temp(filename_start='div', remove_at_exit=True)
        return hb.raster_calculator_flex([self.path, after.path], op, output_path)


class GlobalPyramidFrame(ArrayFrame):
    def __init__(self, path, **kwargs):
        hb.ArrayFrame.__init__(self, path, **kwargs)
        hb.make_path_global_pyramid(path)


def create_af_from_array(input_array, af_path, match_af, compress=False):
    if not os.path.exists(os.path.split(af_path)[0]):
        hb.create_directories(os.path.split(af_path)[0])
    hb.save_array_as_geotiff(input_array, af_path, match_af.path, compress=compress)
    return hb.ArrayFrame(af_path)

def input_flex_as_af(intput_af_or_path):
    if isinstance(intput_af_or_path, str):
        af = hb.ArrayFrame(intput_af_or_path)
    elif isinstance(intput_af_or_path, hb.ArrayFrame):
        af = intput_af_or_path
    else:
        raise NameError('input_flex_as_af unable to interpret intput_af_or_path of ' + str(intput_af_or_path))
    return af


if __name__=='__main__':
    print ('Atttempted to run arrayframe in hazelbean by itself. This doesnt do anything... just sayin.....')