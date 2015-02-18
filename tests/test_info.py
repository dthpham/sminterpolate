import unittest
from butterflow.media.info import LibAvVideoInfo
import subprocess
import os
from fractions import Fraction
from butterflow.butterflow import config


class LibAvVideoInfoTestCase(unittest.TestCase):
  def setUp(self):
    DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'samples')
    v = os.path.join(DIR, 'vid-3s-640x360-29.976fps.mp4')
    a = os.path.join(DIR, 'vid-10s-va.mp4')
    s = os.path.join(DIR, 'vid-5s-vs.mp4')
    if not os.path.exists(v):
      mk_test_proc = subprocess.call([
          config['avutil'],
          '-loglevel', 'info',
          '-y',
          '-f', 'lavfi',
          '-i', 'testsrc=duration=3:size=640x360:rate=30000/1001:decimals=3',
          '-pix_fmt', 'yuv420p',
          '-c:v', 'libx264',
          '-crf', '0',
          v
      ])
      if mk_test_proc == 1:
        raise RuntimeError('failed to make test vid')
    self.info_v = LibAvVideoInfo(v)
    self.info_a = LibAvVideoInfo(a)
    self.info_s = LibAvVideoInfo(s)

  def test_has_video_stream(self):
    self.assertEquals(self.info_v.has_video_stream, True)
    self.assertEquals(self.info_a.has_video_stream, True)
    self.assertEquals(self.info_s.has_video_stream, True)

  def test_has_audio_stream(self):
    self.assertEquals(self.info_v.has_audio_stream, False)
    self.assertEquals(self.info_a.has_audio_stream, True)
    self.assertEquals(self.info_s.has_audio_stream, False)

  def test_has_sub_stream(self):
    self.assertEquals(self.info_v.has_subtitle_stream, False)
    self.assertEquals(self.info_a.has_subtitle_stream, False)
    self.assertEquals(self.info_s.has_subtitle_stream, True)

  def test_frame_size(self):
    i = self.info_v
    self.assertEquals(i.width, 640)
    self.assertEquals(i.height, 360)

  def test_duration(self):
    i = self.info_v
    d = 3.003*1000
    self.assertEquals(i.duration, d)

  def test_rate(self):
    i = self.info_v
    r = Fraction(30*1000,1001)
    self.assertEquals(i.rate, r)

  def test_min_rate(self):
    i = self.info_v
    r = Fraction(30*1000,1001)
    d = 3.003
    n = float(r)*d
    self.assertEquals(i.min_rate, Fraction(float(n)/d))

  def test_num_frames(self):
    i = self.info_v
    r = Fraction(30*1000,1001)
    d = 3.003
    self.assertEquals(i.num_frames, float(r)*d)

if __name__ == '__main__':
  unittest.main()
