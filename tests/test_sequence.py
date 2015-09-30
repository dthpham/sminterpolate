# Author: Duong Pham
# Copyright 2015

import unittest
from butterflow.sequence import VideoSequence, Subregion


class VideoSequenceTestcase(unittest.TestCase):
    def test_add_subregion(self):
        vs = VideoSequence(1,1)
        self.assertEqual(len(vs.subregions), 0)
        vs.add_subregion(Subregion(0,0.1))
        self.assertEqual(len(vs.subregions), 1)
        vs.add_subregion(Subregion(0.2,0.3))
        self.assertEqual(len(vs.subregions), 2)
        vs.add_subregion(Subregion(0.9,1.0))
        self.assertEqual(len(vs.subregions), 3)

    def test_add_subregion_ordering(self):
        vs = VideoSequence(1,1)
        s1 = Subregion(0, 0.1)
        s2 = Subregion(0.2, 0.3)
        s3 = Subregion(0.4, 0.5)
        s4 = Subregion(0.9, 1.0)
        vs.add_subregion(s4)
        vs.add_subregion(s2)
        vs.add_subregion(s3)
        vs.add_subregion(s1)
        self.assertEqual(vs.subregions[0], s1)
        self.assertEqual(vs.subregions[1], s2)
        self.assertEqual(vs.subregions[2], s3)
        self.assertEqual(vs.subregions[3], s4)

    def test_get_rel_position(self):
        vs = VideoSequence(1,1)
        self.assertEqual(vs.get_rel_position(0), 0.0)
        self.assertEqual(vs.get_rel_position(0.5), 0.5)
        self.assertEqual(vs.get_rel_position(1), 1.0)
        vs = VideoSequence(5,5)
        self.assertEqual(vs.get_rel_position(0), 0.0)
        self.assertEqual(vs.get_rel_position(2.5), 0.5)
        self.assertEqual(vs.get_rel_position(5), 1.0)

    def test_get_rel_position_min_max(self):
        vs = VideoSequence(1,1)
        self.assertEqual(vs.get_rel_position(1.1), 1.0)
        self.assertEqual(vs.get_rel_position(-1), 0.0)

    def test_get_nearest_frame(self):
        vs = VideoSequence(1,1)
        self.assertEqual(vs.get_nearest_frame(0), 1)
        self.assertEqual(vs.get_nearest_frame(0.5), 1)
        self.assertEqual(vs.get_nearest_frame(1), 1)
        vs = VideoSequence(1,10)
        self.assertEqual(vs.get_nearest_frame(0.0), 1)
        self.assertEqual(vs.get_nearest_frame(0.1), 1)
        self.assertEqual(vs.get_nearest_frame(0.15), 2)
        vs = VideoSequence(5,5)
        self.assertEqual(vs.get_nearest_frame(2), 2)
        self.assertEqual(vs.get_nearest_frame(2.4), 2)
        self.assertEqual(vs.get_nearest_frame(2.5), 3)
        self.assertEqual(vs.get_nearest_frame(2.6), 3)
        vs = VideoSequence(1,3)
        self.assertEqual(vs.get_nearest_frame(0.4), 1)
        self.assertEqual(vs.get_nearest_frame(0.5), 2)
        self.assertEqual(vs.get_nearest_frame(0.8), 2)
        self.assertEqual(vs.get_nearest_frame(0.83), 2)
        self.assertEqual(vs.get_nearest_frame(0.84), 3)
        self.assertEqual(vs.get_nearest_frame(0.9), 3)
        self.assertEqual(vs.get_nearest_frame(1), 3)

    def test_get_nearest_frame_min_max(self):
        vs = VideoSequence(1,1)
        self.assertEqual(vs.get_nearest_frame(-1), 1)
        self.assertEqual(vs.get_nearest_frame(1.1), 1)
        vs = VideoSequence(1,3)
        self.assertEqual(vs.get_nearest_frame(-1), 1)
        self.assertEqual(vs.get_nearest_frame(1.1), 3)

    def test_validate(self):
        vs = VideoSequence(1,10)
        s1 = Subregion(0, 0.1)
        vs.add_subregion(s1)
        self.assertTrue(vs.validate(Subregion(0.2, 0.3)))
        self.assertTrue(vs.validate(Subregion(0.4, 0.8)))
        self.assertTrue(vs.validate(Subregion(0.9, 1.0)))

    def test_validate_fails_out_of_bounds(self):
        vs = VideoSequence(1,1)
        s = Subregion(0,1.1)
        with self.assertRaises(RuntimeError):
            vs.add_subregion(s)
        s = Subregion(0,2)
        s.fa = 1
        s.fb = 2
        with self.assertRaises(RuntimeError):
            vs.add_subregion(s)

    def test_validate_fails_intersects(self):
        vs = VideoSequence(1,10)
        s1 = Subregion(0.1,0.2)
        s2 = Subregion(0.15,0.25)
        vs.add_subregion(s1)
        with self.assertRaises(RuntimeError):
            vs.add_subregion(s2)
        vs = VideoSequence(5,1)
        s1 = Subregion(1,1)
        s2 = Subregion(0,5)
        with self.assertRaises(RuntimeError):
            vs.add_subregion(s1)
            vs.add_subregion(s2)
        with self.assertRaises(RuntimeError):
            vs.add_subregion(s2)
            vs.add_subregion(s1)


class SubregionTestCase(unittest.TestCase):
    def setUp(self):
        self.t_intersects = lambda x, y, z, w: \
            self.x_intersects('time', x, y, z, w)
        self.f_intersects = lambda x, y, z, w: \
            self.x_intersects('frame', x, y, z, w)

    def test_init(self):
        self.assertIsInstance(Subregion(0,1), Subregion)
        self.assertIsInstance(Subregion(1,1), Subregion)
        self.assertIsInstance(Subregion(1,2), Subregion)

    def test_init_fails(self):
        with self.assertRaises(ValueError):
            Subregion(-1,0)
        with self.assertRaises(ValueError):
            Subregion(0,-1)
        with self.assertRaises(ValueError):
            Subregion(2,1)

    def x_intersects(self, x, s1_a, s1_b, s2_a, s2_b):
        s1 = Subregion(0,0)
        s2 = Subregion(0,0)
        if x == 'time':
            setattr(s1, 'ta', s1_a)
            setattr(s1, 'tb', s1_b)
            setattr(s2, 'ta', s2_a)
            setattr(s2, 'tb', s2_b)
        elif x == 'frame':
            setattr(s1, 'fa', s1_a)
            setattr(s1, 'fb', s1_b)
            setattr(s2, 'fa', s2_a)
            setattr(s2, 'fb', s2_b)
        else:
            return
        intersect_method = getattr(s2, '{}_intersects'.format(x))
        return(intersect_method(s1))

    def test_intersects_inside(self):
        args = [1,2,1.5,1.75]
        self.assertTrue(self.t_intersects(*args))
        self.assertTrue(self.f_intersects(*args))

    def test_intersects_inside_right_edge(self):
        args = [1,2,1.5,1.75]
        self.assertTrue(self.t_intersects(*args))
        self.assertTrue(self.f_intersects(*args))

    def test_intersects_inside_left_edge(self):
        args = [1,2,1,1.5]
        self.assertTrue(self.t_intersects(*args))
        self.assertTrue(self.f_intersects(*args))

    def test_intersects_overlap_right(self):
        args = [1,2,1.75,3]
        self.assertTrue(self.t_intersects(*args))
        self.assertTrue(self.f_intersects(*args))

    def test_intersects_borders_right_edge(self):
        args = [1,2,2,3]
        self.assertFalse(self.t_intersects(*args))
        self.assertFalse(self.f_intersects(*args))

    def test_intersects_overlap_left(self):
        args = [1,2,0.5,1.5]
        self.assertTrue(self.t_intersects(*args))
        self.assertTrue(self.f_intersects(*args))

    def test_intersects_borders_left_edge(self):
        args = [1,2,0.5,1]
        self.assertFalse(self.t_intersects(*args))
        self.assertFalse(self.f_intersects(*args))

    def test_intersects_equal(self):
        args = [1,2,1,2]
        self.assertTrue(self.t_intersects(*args))
        self.assertTrue(self.f_intersects(*args))

    def test_intersects_envelops(self):
        args = [1,1,0,2]
        self.assertTrue(self.t_intersects(*args))
        self.assertTrue(self.f_intersects(*args))


if __name__ == '__main__':
    unittest.main()
