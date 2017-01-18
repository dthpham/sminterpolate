# -*- coding: utf-8 -*-

import unittest
from butterflow.sequence import VideoSequence, Subregion

class VideoSequenceTestcase(unittest.TestCase):
    def test_relative_pos(self):
        vs = VideoSequence(1,1)
        self.assertEqual(vs.relative_pos(0), 0.0)
        self.assertEqual(vs.relative_pos(0.4), 0.4)
        self.assertEqual(vs.relative_pos(0.5), 0.5)
        self.assertEqual(vs.relative_pos(0.6), 0.6)
        self.assertEqual(vs.relative_pos(1), 1.0)
        vs = VideoSequence(5,5)
        self.assertEqual(vs.relative_pos(0), 0.0)
        self.assertEqual(vs.relative_pos(2.4), 0.48)
        self.assertEqual(vs.relative_pos(2.5), 0.5)
        self.assertEqual(vs.relative_pos(2.6), 0.52)
        self.assertEqual(vs.relative_pos(5), 1.0)

    def test_relative_pos_min_max(self):
        vs = VideoSequence(1,3)
        self.assertEqual(vs.relative_pos(1.1), 1.0)
        self.assertEqual(vs.relative_pos(0), 0.0)

    def test_nearest_fr(self):
        vs = VideoSequence(1,1)
        self.assertEqual(vs.nearest_fr(0), 1-1)
        self.assertEqual(vs.nearest_fr(0.5), 1-1)
        self.assertEqual(vs.nearest_fr(1), 1-1)
        vs = VideoSequence(1,2)
        self.assertEqual(vs.nearest_fr(0), 1-1)
        self.assertEqual(vs.nearest_fr(0.49), 1-1)
        self.assertEqual(vs.nearest_fr(0.5), 2-1)
        self.assertEqual(vs.nearest_fr(0.51), 2-1)
        self.assertEqual(vs.nearest_fr(1), 2-1)
        vs = VideoSequence(1,4)
        self.assertEqual(vs.nearest_fr(0), 1-1)
        self.assertEqual(vs.nearest_fr(0.24), 1-1)
        self.assertEqual(vs.nearest_fr(0.25), 2-1)
        self.assertEqual(vs.nearest_fr(0.26), 2-1)
        self.assertEqual(vs.nearest_fr(0.49), 2-1)
        self.assertEqual(vs.nearest_fr(0.5), 3-1)
        self.assertEqual(vs.nearest_fr(0.51), 3-1)
        self.assertEqual(vs.nearest_fr(0.74), 3-1)
        self.assertEqual(vs.nearest_fr(0.75), 4-1)
        self.assertEqual(vs.nearest_fr(0.76), 4-1)
        self.assertEqual(vs.nearest_fr(0.9), 4-1)
        self.assertEqual(vs.nearest_fr(1), 4-1)

    def test_nearest_fr_min_max(self):
        vs = VideoSequence(1,1)
        self.assertEqual(vs.nearest_fr(0), 1-1)
        self.assertEqual(vs.nearest_fr(1.1), 1-1)
        vs = VideoSequence(1,3)
        self.assertEqual(vs.nearest_fr(0), 1-1)
        self.assertEqual(vs.nearest_fr(1.1), 3-1)

    def test_add_subregion(self):
        cnt_skip_subs = lambda x: \
            len([s for s in x.subregions if s.skip])
        cnt_usr_subs = lambda x: \
            len(x.subregions) - cnt_skip_subs(x)
        vs = VideoSequence(1,1)
        self.assertEqual(cnt_usr_subs(vs), 0)
        self.assertEqual(cnt_skip_subs(vs), 1)
        vs.add_subregion(Subregion(0,0.1))
        self.assertEqual(cnt_usr_subs(vs), 1)
        self.assertEqual(cnt_skip_subs(vs), 1)
        vs = VideoSequence(1,1)
        vs.add_subregion(Subregion(0.9,1))
        self.assertEqual(cnt_usr_subs(vs), 1)
        self.assertEqual(cnt_skip_subs(vs), 1)
        vs = VideoSequence(1,1)
        vs.add_subregion(Subregion(0,1))
        self.assertEqual(cnt_usr_subs(vs), 1)
        self.assertEqual(cnt_skip_subs(vs), 0)
        vs = VideoSequence(1,2)
        vs.add_subregion(Subregion(0,0.5))
        vs.add_subregion(Subregion(0.5,0.6))
        self.assertEqual(cnt_usr_subs(vs), 2)
        self.assertEqual(cnt_skip_subs(vs), 1)
        vs = VideoSequence(1,2)
        vs.add_subregion(Subregion(0.5,0.6))
        vs.add_subregion(Subregion(0,0.1))
        self.assertEqual(cnt_usr_subs(vs), 2)
        self.assertEqual(cnt_skip_subs(vs), 2)
        vs = VideoSequence(1,3)
        vs.add_subregion(Subregion(0,0.1))
        self.assertEqual(cnt_usr_subs(vs), 1)
        self.assertEqual(cnt_skip_subs(vs), 1)
        vs.add_subregion(Subregion(0.9,1))
        self.assertEqual(cnt_usr_subs(vs), 2)
        self.assertEqual(cnt_skip_subs(vs), 1)
        vs.add_subregion(Subregion(0.66,0.66))
        self.assertEqual(cnt_usr_subs(vs), 3)
        self.assertEqual(cnt_skip_subs(vs), 2)
        vs = VideoSequence(1,3)
        vs.add_subregion(Subregion(0.66,0.66))
        self.assertEqual(cnt_usr_subs(vs), 1)
        self.assertEqual(cnt_skip_subs(vs), 2)
        vs.add_subregion(Subregion(0,0.1))
        self.assertEqual(cnt_usr_subs(vs), 2)
        self.assertEqual(cnt_skip_subs(vs), 2)
        vs.add_subregion(Subregion(0.9,1))
        self.assertEqual(cnt_usr_subs(vs), 3)
        self.assertEqual(cnt_skip_subs(vs), 2)
        vs = VideoSequence(1,4)
        vs.add_subregion(Subregion(0.25,0.5))
        vs.add_subregion(Subregion(0.5,0.75))
        self.assertEqual(cnt_usr_subs(vs), 2)
        self.assertEqual(cnt_skip_subs(vs), 2)
        vs.add_subregion(Subregion(0,0.25))
        self.assertEqual(cnt_usr_subs(vs), 3)
        self.assertEqual(cnt_skip_subs(vs), 1)
        vs.add_subregion(Subregion(0.75,1))
        self.assertEqual(cnt_usr_subs(vs), 4)
        self.assertEqual(cnt_skip_subs(vs), 0)
        vs = VideoSequence(1,5)
        vs.add_subregion(Subregion(0.2,0.4))
        vs.add_subregion(Subregion(0.6,0.8))
        self.assertEqual(cnt_usr_subs(vs), 2)
        self.assertEqual(cnt_skip_subs(vs), 3)
        vs.add_subregion(Subregion(0.4,0.6))
        self.assertEqual(cnt_usr_subs(vs), 3)
        self.assertEqual(cnt_skip_subs(vs), 2)
        vs.add_subregion(Subregion(0.8,1))
        self.assertEqual(cnt_usr_subs(vs), 4)
        self.assertEqual(cnt_skip_subs(vs), 1)
        vs.add_subregion(Subregion(0,0.2))
        self.assertEqual(cnt_usr_subs(vs), 5)
        self.assertEqual(cnt_skip_subs(vs), 0)

class SubregionTestCase(unittest.TestCase):
    def setUp(self):
        self.time_intersects = lambda x, y, z, w: \
            self.x_intersects('time', x, y, z, w)
        self.fr_intersects = lambda x, y, z, w: \
            self.x_intersects('fr', x, y, z, w)

    def test_init(self):
        self.assertIsInstance(Subregion(0,1), Subregion)
        self.assertIsInstance(Subregion(1,1), Subregion)
        self.assertIsInstance(Subregion(1,2), Subregion)

    def x_intersects(self, x, s1_a, s1_b, s2_a, s2_b):
        s1 = Subregion(0,0)
        s2 = Subregion(0,0)
        if x == 'time':
            setattr(s1, 'ta', s1_a)
            setattr(s1, 'tb', s1_b)
            setattr(s2, 'ta', s2_a)
            setattr(s2, 'tb', s2_b)
        elif x == 'fr':
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
        self.assertTrue(self.time_intersects(*args))
        self.assertTrue(self.fr_intersects(*args))

    def test_intersects_inside_right_edge(self):
        args = [1,2,1.5,1.75]
        self.assertTrue(self.time_intersects(*args))
        self.assertTrue(self.fr_intersects(*args))

    def test_intersects_inside_left_edge(self):
        args = [1,2,1,1.5]
        self.assertTrue(self.time_intersects(*args))
        self.assertTrue(self.fr_intersects(*args))

    def test_intersects_overlap_right(self):
        args = [1,2,1.75,3]
        self.assertTrue(self.time_intersects(*args))
        self.assertTrue(self.fr_intersects(*args))

    def test_intersects_borders_right_edge(self):
        args = [1,2,2,3]
        self.assertFalse(self.time_intersects(*args))
        self.assertFalse(self.fr_intersects(*args))

    def test_intersects_overlap_left(self):
        args = [1,2,0.5,1.5]
        self.assertTrue(self.time_intersects(*args))
        self.assertTrue(self.fr_intersects(*args))

    def test_intersects_borders_left_edge(self):
        args = [1,2,0.5,1]
        self.assertFalse(self.time_intersects(*args))
        self.assertFalse(self.fr_intersects(*args))

    def test_intersects_equal(self):
        args = [1,2,1,2]
        self.assertTrue(self.time_intersects(*args))
        self.assertTrue(self.fr_intersects(*args))

    def test_intersects_envelops(self):
        args = [1,1,0,2]
        self.assertTrue(self.time_intersects(*args))
        self.assertTrue(self.fr_intersects(*args))

if __name__ == '__main__':
    unittest.main()
