# Author: Duong Pham
# Copyright 2015

import unittest
import numpy as np
from butterflow.mux import atempo_factors_for_spd, ATEMPO_MIN, ATEMPO_MAX


class MuxTestCase(unittest.TestCase):
    def validate_factors_for_spd(self, s):
        f = atempo_factors_for_spd(s)
        return self.array_has_product(f, s) and \
            self.array_items_inside_min_max(f, ATEMPO_MIN, ATEMPO_MAX)

    def array_has_product(self, array, p):
        return np.prod(np.array(array)) == p

    def array_items_inside_min_max(self, array, min, max):
        for i in array:
            if i < min or i > max:
                return False
        return True

    def test_atempo_factors_for_spd_zero_and_one(self):
        with self.assertRaises(ValueError):
            self.assertTrue(self.validate_factors_for_spd(0))
        self.assertTrue(self.validate_factors_for_spd(1))

    def test_atempo_factors_for_spd_min_max_edges(self):
        self.assertTrue(self.validate_factors_for_spd(ATEMPO_MIN))
        self.assertTrue(self.validate_factors_for_spd(ATEMPO_MIN+0.1))
        self.assertTrue(self.validate_factors_for_spd(ATEMPO_MIN-0.1))
        self.assertTrue(self.validate_factors_for_spd(ATEMPO_MAX))
        self.assertTrue(self.validate_factors_for_spd(ATEMPO_MAX-0.1))
        self.assertTrue(self.validate_factors_for_spd(ATEMPO_MAX+0.1))

    def test_atempo_factors_for_spd_near_zero(self):
        self.assertTrue(self.validate_factors_for_spd(0.001))

    def test_atempo_factors_for_spd_extremely_fast(self):
        self.assertTrue(self.validate_factors_for_spd(100.0))

if __name__ == '__main__':
    unittest.main()
