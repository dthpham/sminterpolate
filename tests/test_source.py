import unittest
from butterflow.media.source import OpenCvFrameSource
import os
import subprocess
import cv2
import numpy as np


class BaseFrameSourceTestCase(unittest.TestCase):
  def setUp(self):
    DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'samples')
    self.test_vid = os.path.join(DIR, 'vid-5s-640x360-30fps.mp4')
    self.test_img = os.path.join(DIR, 'img.png')
    if not os.path.exists(self.test_vid):
      mk_test_proc = subprocess.call([
          'ffmpeg',
          '-loglevel', 'info',
          '-y',
          '-f', 'lavfi',
          '-i', 'testsrc=duration=5:size=640x360:rate=30:decimals=3',
          '-pix_fmt', 'yuv420p',
          '-c:v', 'libx264',
          '-crf', '0',
          self.test_vid
      ])
      if mk_test_proc == 1:
        raise RuntimeError('failed to make test vid')
    self.remove_temp_files()

  def tearDown(self):
    self.remove_temp_files()

  def remove_temp_files(self):
    if os.path.exists(self.test_img):
      os.remove(self.test_img)

  def av_frame_at_idx(self, idx):
    '''extract image using libav, read image using opencv'''
    get_fr_proc = subprocess.call([
        'ffmpeg',
        '-loglevel', 'fatal',
        '-y',
        '-i', self.test_vid,
        '-vf', 'select=gte(n\,{})'.format(idx),
        '-vframes', '1',
        self.test_img
    ])
    if get_fr_proc == 1:
      raise RuntimeError('failed to extract frame at idx: {}'.format(idx))
    return cv2.imread(self.test_img)

  def av_frame_at_time(self, time):
    '''extract image using libav, read image using opencv'''
    secs = time/1000.0
    get_fr_proc = subprocess.call([
        'ffmpeg',
        '-loglevel', 'fatal',
        '-y',
        '-ss', str(secs),
        '-i', self.test_vid,
        '-vframes', '1',
        self.test_img
    ])
    if get_fr_proc == 1:
      raise RuntimeError('failed to extract frame at time: {}s'.format(secs))
    return cv2.imread(self.test_img)

  def do_seek_to_frame(self, src):
    self.assertEqual(src.curr_frame_idx, 0)
    src.seek_to_frame(149)
    self.assertEqual(src.curr_frame_idx, 149)
    src.seek_to_frame(1)
    self.assertEqual(src.curr_frame_idx, 1)

  def do_seek_to_frame_outside(self, src):
    with self.assertRaises(IndexError):
      src.seek_to_frame(-1)
    with self.assertRaises(IndexError):
      src.seek_to_frame(150)

  def do_seek_to_time(self, src):
    self.assertEqual(src.curr_time_pos, 0)
    src.seek_to_time(5*1000)
    self.assertEqual(src.curr_time_pos, 5*1000)
    src.seek_to_time(1*1000)
    self.assertEqual(src.curr_time_pos, 1*1000)

  def do_seek_to_time_outside(self, src):
    with self.assertRaises(IndexError):
      src.seek_to_time(-1*1000)
    with self.assertRaises(IndexError):
      src.seek_to_time(5.1*1000)

  def do_seek_mix_time_and_frame(self, src):
    src.seek_to_frame(120)
    self.assertEqual(src.curr_frame_idx, 120)
    self.assertEqual(src.curr_time_pos, 4*1000)
    src.seek_to_time(1*1000)
    self.assertEqual(src.curr_frame_idx, 30)
    self.assertEqual(src.curr_time_pos, 1*1000)
    src.seek_to_frame(0)
    self.assertEqual(src.curr_frame_idx, 0)
    self.assertEqual(src.curr_time_pos, 0)

  def do_read_frame_after_seek_by_frame(self, src):
    src.seek_to_frame(30)
    f1 = src.read_frame()
    f2 = self.av_frame_at_idx(30)
    self.assertTrue(np.array_equal(f1,f2))

  def do_read_frame_after_seek_by_frame_at_edges(self, src):
    src.seek_to_frame(0)
    f1 = src.read_frame()
    f2 = self.av_frame_at_idx(0)
    self.assertTrue(np.array_equal(f1,f2))
    src.seek_to_frame(149)
    f1 = src.read_frame()
    f2 = self.av_frame_at_idx(149)
    self.assertTrue(np.array_equal(f1,f2))

  def do_read_frame_after_seek_by_time(self, src):
    src.seek_to_time(1*1000)
    f1 = src.read_frame()
    f2 = self.av_frame_at_time(1*1000)
    self.assertTrue(np.array_equal(f1,f2))

  def do_read_frame_after_seek_by_time_at_edges(self, src):
    src.seek_to_time(0)
    f1 = src.read_frame()
    f2 = self.av_frame_at_time(0)
    self.assertTrue(np.array_equal(f1,f2))
    src.seek_to_time(149/30*1000)
    f1 = src.read_frame()
    f2 = self.av_frame_at_time(149/30*1000)
    self.assertTrue(np.array_equal(f1,f2))

  def do_get_frame_at_idx(self, src):
    f1 = src.frame_at_idx(50)
    f2 = self.av_frame_at_idx(50)
    self.assertTrue(np.array_equal(f1,f2))

  def do_get_frame_at_time(self, src):
    f1 = src.frame_at_time(2.5*1000)
    f2 = self.av_frame_at_time(2.5*1000)
    self.assertTrue(np.array_equal(f1,f2))

  @unittest.skip('todo')
  def do_normalize_frame(self, src):pass

  def do_frame_generator(self, src):
    x = 0
    gen = src.frame_generator()
    for fr in gen:
      if x == 0 or x == 149:
        other = self.av_frame_at_idx(x)
        self.assertTrue(np.array_equal(fr, other))
      x += 1
    self.assertEqual(x, 150)


class OpenCvFrameSourceTestCase(BaseFrameSourceTestCase):
  def setUp(self):
    super(OpenCvFrameSourceTestCase, self).setUp()
    self.src = OpenCvFrameSource(self.test_vid)

  def test_seek_to_frame_(self):
    self.do_seek_to_frame(self.src)

  def test_seek_to_frame_outside(self):
    self.do_seek_to_frame_outside(self.src)

  def test_seek_to_time(self):
    self.do_seek_to_time(self.src)

  def test_seek_to_time_outside(self):
    self.do_seek_to_time_outside(self.src)

  def test_seek_mix_time_and_frame(self):
    self.do_seek_mix_time_and_frame(self.src)

  def test_read_frame_after_seek_by_frame(self):
    self.do_read_frame_after_seek_by_frame(self.src)

  def test_read_frame_after_seek_by_frame_at_edges(self):
    self.do_read_frame_after_seek_by_frame_at_edges(self.src)

  def test_read_frame_after_seek_by_time(self):
    self.do_read_frame_after_seek_by_time(self.src)

  def test_read_frame_after_seek_by_time_at_edges(self):
    self.do_read_frame_after_seek_by_time_at_edges(self.src)

  def test_get_frame_at_idx(self):
    self.do_get_frame_at_idx(self.src)

  def test_get_frame_at_time(self):
    self.do_get_frame_at_time(self.src)

  def test_normalize_frame(self):
    self.do_normalize_frame(self.src)

  def test_frame_generator(self):
    self.do_frame_generator(self.src)


if __name__ == '__main__':
  unittest.main()
