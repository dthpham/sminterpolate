import unittest
from butterflow.media.info import LibAvVideoInfo
import subprocess
import os
from fractions import Fraction


class BaseVideoInfoTestCase(unittest.TestCase):
  def setUp(self):
    DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'samples')
    self.test_vid = os.path.join(DIR, 'vid-3s-640x360-29.976fps.mp4')
    self.test_aud = os.path.join(DIR, 'vid-10s-va.mp4')
    self.test_sub = os.path.join(DIR, 'vid-5s-vs.mp4')
    if not os.path.exists(self.test_vid):
      mk_test_proc = subprocess.call([
          'ffmpeg',
          '-loglevel', 'info',
          '-y',
          '-f', 'lavfi',
          '-i', 'testsrc=duration=3:size=640x360:rate=30000/1001:decimals=3',
          '-pix_fmt', 'yuv420p',
          '-c:v', 'libx264',
          '-crf', '0',
          self.test_vid
      ])
      if mk_test_proc == 1:
        raise RuntimeError('failed to make test vid')

  def calc_min_rate(self, frames, duration):
    return Fraction(float(frames)/duration)

  def calc_frames(self, rate, duration):
    return float(rate)*duration

  def do_test_has_video_stream(self, info, b):
    self.assertEquals(info.has_video_stream, b)

  def do_test_has_audio_stream(self, info, b):
    self.assertEquals(info.has_audio_stream, b)

  def do_test_has_sub_stream(self, info, b):
    self.assertEquals(info.has_subtitle_stream, b)

  def do_test_frame_size(self, info, w, h):
    self.assertEquals(info.width, w)
    self.assertEquals(info.height, h)

  def do_test_duration(self, info, d):
    self.assertEquals(info.duration, d)

  def do_test_min_rate(self, info, r):
    self.assertEquals(info.min_rate, r)

  def do_test_num_frames(self, info, n):
    self.assertEquals(info.num_frames, n)


class LibAvVideoInfoTestCase(BaseVideoInfoTestCase):

  def test_has_video_stream(self):
    self.do_test_has_video_stream(LibAvVideoInfo(self.test_vid), True)
    self.do_test_has_video_stream(LibAvVideoInfo(self.test_aud), True)
    self.do_test_has_video_stream(LibAvVideoInfo(self.test_sub), True)

  def test_has_audio_stream(self):
    self.do_test_has_audio_stream(LibAvVideoInfo(self.test_vid), False)
    self.do_test_has_audio_stream(LibAvVideoInfo(self.test_aud), True)
    self.do_test_has_audio_stream(LibAvVideoInfo(self.test_sub), False)

  def test_has_sub_stream(self):
    self.do_test_has_sub_stream(LibAvVideoInfo(self.test_vid), False)
    self.do_test_has_sub_stream(LibAvVideoInfo(self.test_aud), False)
    self.do_test_has_sub_stream(LibAvVideoInfo(self.test_sub), True)

  def test_frame_size(self):
    i = LibAvVideoInfo(self.test_vid)
    self.do_test_frame_size(i, 640, 360)

  def test_duration(self):
    i = LibAvVideoInfo(self.test_vid)
    d = 3.003*1000
    self.do_test_duration(i, d)

  def test_min_rate(self):
    i = LibAvVideoInfo(self.test_vid)
    r = Fraction(30*1000,1001)
    d = 3.003
    n = self.calc_frames(r,d)
    self.do_test_min_rate(i, self.calc_min_rate(n,d))

  def test_num_frames(self):
    i = LibAvVideoInfo(self.test_vid)
    r = Fraction(30*1000,1001)
    d = 3.003
    self.do_test_num_frames(i, self.calc_frames(r,d))

if __name__ == '__main__':
  unittest.main()
