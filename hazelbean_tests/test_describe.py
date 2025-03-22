from unittest import TestCase
import numpy as np
import hazelbean as hb

class TestDescribe(TestCase):
    def test_describe(self):
        a = np.random.rand(5, 5)
        tmp_path = hb.temp('.npy', remove_at_exit=True)
        hb.save_array_as_npy(a, tmp_path)
        hb.describe(tmp_path, surpress_print=True, surpress_logger=True)


