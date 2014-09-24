import unittest
from fractions import Fraction
from butterflow.region import VideoRegionUtils, VideoSubRegion, RenderingSubRegion


class VideoRegionUtilsTestCase(unittest.TestCase):
  @unittest.skip('todo')
  def test_validate_region_set(self):pass

  def test_time_string_to_ms(self):
    f = VideoRegionUtils.time_string_to_ms
    self.assertEqual(f('00:00:00.001'),1)
    self.assertEqual(f('00:00:00.100'),100)
    self.assertEqual(f('00:17:33.090'),(0*3600+17*60+33.09)*1000)
    self.assertEqual(f('01:30:59.100'),(1*3600+30*60+59.1)*1000)
    self.assertEqual(f('02:09:00.123'),(2*3600+9*60+0.123)*1000)

  def test_time_string_to_ms_fails(self):
    f = VideoRegionUtils.time_string_to_ms
    with self.assertRaises(ValueError):
      f('333:22:22.333')
    with self.assertRaises(ValueError):
      f('22:333:22.333')
    with self.assertRaises(ValueError):
      f('22:22:333.333')
    with self.assertRaises(ValueError):
      f('22:22:22.4444')

class SubRegionTestCase(unittest.TestCase):
  def test_creation(self):
    self.assertIsInstance(VideoSubRegion(0,1), VideoSubRegion)
    self.assertIsInstance(VideoSubRegion(1,2), VideoSubRegion)
    self.assertIsInstance(VideoSubRegion(1,1), VideoSubRegion)

  def test_creation_fails(self):
    with self.assertRaises(ValueError):
      VideoSubRegion(-1,1)
    with self.assertRaises(ValueError):
      VideoSubRegion(1,0)

  def test_setters(self):
    r = VideoSubRegion(0,1)
    r.time_a = 1
    r.time_b = 2
    r.time_b = 3
    self.assertEqual(r.time_a,1)
    self.assertEqual(r.time_b,3)

  def test_setters_fails(self):
    r = VideoSubRegion(2,3)
    with self.assertRaises(ValueError):
      r.time_a = -1
    with self.assertRaises(ValueError):
      r.time_a = 4
    with self.assertRaises(ValueError):
      r.time_b = 1
    self.assertEqual(r.time_a,2)
    self.assertEqual(r.time_b,3)

  def test_intersects_inside(self):
    r1 = VideoSubRegion(1,2)
    r2 = VideoSubRegion(1.5,1.75)
    self.assertTrue(r2.intersects(r1))

  def test_intersect_inside_right_edge(self):
    r1 = VideoSubRegion(1,2)
    r2 = VideoSubRegion(1.5,2)
    self.assertTrue(r2.intersects(r1))

  def test_intersect_inside_left_edge(self):
    r1 = VideoSubRegion(1,2)
    r2 = VideoSubRegion(1,1.5)
    self.assertTrue(r2.intersects(r1))

  def test_intersects_overlap_right(self):
    r1 = VideoSubRegion(1,2)
    r2 = VideoSubRegion(1.75,3)
    self.assertTrue(r2.intersects(r1))

  def test_intersect_borders_right_edge(self):
    r1 = VideoSubRegion(1,2)
    r2 = VideoSubRegion(2,3)
    self.assertFalse(r2.intersects(r1))

  def test_intersects_overlap_left(self):
    r1 = VideoSubRegion(1,2)
    r2 = VideoSubRegion(.5,1.5)
    self.assertTrue(r2.intersects(r1))

  def test_intersect_borders_left_edge(self):
    r1 = VideoSubRegion(1,2)
    r2 = VideoSubRegion(.5,1)
    self.assertFalse(r2.intersects(r1))

  def test_intersects_equal(self):
    r1 = VideoSubRegion(1,2)
    r2 = VideoSubRegion(1,2)
    self.assertTrue(r1.intersects(r2))

  def test_less_than(self):
    r1 = VideoSubRegion(2,3)
    r2 = VideoSubRegion(0,1)
    self.assertLess(r2,r1)
    r3 = VideoSubRegion(1,2)
    self.assertLess(r3,r1)

  def test_greater_than(self):
    r1 = VideoSubRegion(2,3)
    r2 = VideoSubRegion(4,5)
    self.assertGreater(r2,r1)
    r3 = VideoSubRegion(3,4)
    self.assertGreater(r3,r1)

  def test_equal(self):
    r1 = VideoSubRegion(2,3)
    r2 = VideoSubRegion(2,3)
    self.assertEqual(r1,r2)


class RenderingSubRegionTestCase(unittest.TestCase):
  def test_create_from_rate(self):
    rate = Fraction(24)
    r = RenderingSubRegion.from_rate(0,5,rate)
    self.assertIsInstance(r,RenderingSubRegion)
    self.assertEqual(r.time_a,0)
    self.assertEqual(r.time_b,5)
    self.assertEqual(r.target_rate,rate)
    self.assertEqual(r.target_duration,None)

  def test_create_from_duration(self):
    r = RenderingSubRegion.from_duration(1,20,10)
    self.assertIsInstance(r, RenderingSubRegion)
    self.assertEqual(r.time_a,1)
    self.assertEqual(r.time_b,20)
    self.assertEqual(r.target_rate,None)
    self.assertEqual(r.target_duration,10)

  def test_create_from_factor(self):
    r = RenderingSubRegion.from_factor(1,2,0.5)
    self.assertIsInstance(r, RenderingSubRegion)
    self.assertEqual(r.target_rate,None)
    self.assertEqual(r.target_duration,None)
    self.assertEqual(r.target_factor,0.5)

  def test_create_from_string_fps(self):
    r = RenderingSubRegion.from_string(
        'a=00:05:00.0,b=00:05:30.0,fps=59.94')
    self.assertIsInstance(r, RenderingSubRegion)
    self.assertEqual(r.time_a,(5*60)*1000)
    self.assertEqual(r.time_b,(5*60+30)*1000)
    self.assertEqual(r.target_rate,59.94)

  def test_create_from_string_fps_fraction(self):
    r = RenderingSubRegion.from_string(
        'a=00:00:00.5,b=00:00:01.0,fps=24000/1001')
    self.assertIsInstance(r, RenderingSubRegion)
    self.assertEqual(r.time_a,0.5*1000)
    self.assertEqual(r.time_b,1.0*1000)
    self.assertEqual(r.target_rate,Fraction(24000,1001))

  def test_create_from_string_duration(self):
    r = RenderingSubRegion.from_string(
        'a=01:20:31.59,b=01:21:34.0,duration=3')
    self.assertIsInstance(r, RenderingSubRegion)
    self.assertEqual(r.time_a,(1*3600+20*60+31.59)*1000)
    self.assertEqual(r.time_b,(1*3600+21*60+34.0)*1000)
    self.assertEqual(r.target_duration,3*1000)

  def test_create_from_string_factor(self):
    r = RenderingSubRegion.from_string(
        'a=00:00:01.0,b=00:00:02.0,factor=0.5')
    self.assertIsInstance(r, RenderingSubRegion)
    self.assertEqual(r.time_a,1*1000)
    self.assertEqual(r.time_b,2*1000)
    self.assertEqual(r.target_factor,0.5)

  def test_sync_frame_points_with_fps(self):
    r = RenderingSubRegion.from_string(
        'a=00:00:01.0,b=00:00:02.0,duration=3')
    r.sync_frame_points_with_fps(0)
    self.assertEqual(r.frame_a, 0)
    self.assertEqual(r.frame_b, 0)
    r.sync_frame_points_with_fps(1)
    self.assertEqual(r.frame_a, 1)
    self.assertEqual(r.frame_b, 2)
    r.sync_frame_points_with_fps(1.1)
    self.assertEqual(r.frame_a, 1)
    self.assertEqual(r.frame_b, 2)
    r.sync_frame_points_with_fps(1.5)
    self.assertEqual(r.frame_a, 2)
    self.assertEqual(r.frame_b, 3)
    r.sync_frame_points_with_fps(1.9)
    self.assertEqual(r.frame_a, 2)
    self.assertEqual(r.frame_b, 4)
    r.sync_frame_points_with_fps(29.976)
    self.assertEqual(r.frame_a, 30)
    self.assertEqual(r.frame_b, 60)

  def test_sync_relative_pos_to_frames(self):
    r = RenderingSubRegion.from_string(
        'a=00:00:01.0,b=00:00:02.0,duration=3')
    r.sync_frame_points_with_fps(1.5)
    with self.assertRaises(ValueError):
      r.sync_relative_pos_to_frames(0)
    with self.assertRaises(ValueError):
      r.sync_relative_pos_to_frames(2)
    r.sync_relative_pos_to_frames(10)
    self.assertEqual(r.relative_pos_a,0.2)
    self.assertEqual(r.relative_pos_b,0.3)
    r.sync_relative_pos_to_frames(3)
    self.assertEqual(r.relative_pos_a, 2.0/3)
    self.assertEqual(r.relative_pos_b, 1)

  def test_sync_relative_pos_to_duration(self):
    r = RenderingSubRegion.from_string(
        'a=00:00:01.0,b=00:00:02.0,duration=3')
    r.sync_frame_points_with_fps(29.976)
    with self.assertRaises(ValueError):
      r.sync_relative_pos_to_duration(0)
    with self.assertRaises(ValueError):
      r.sync_relative_pos_to_duration(1)
    r.sync_relative_pos_to_duration(30*1000)
    self.assertEqual(r.relative_pos_a, 1.0/30)
    self.assertEqual(r.relative_pos_b, 2.0/30)

  @unittest.skip('todo')
  def test_resync_points(self):pass

if __name__ == '__main__':
  unittest.main()
