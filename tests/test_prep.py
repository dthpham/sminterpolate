import unittest
from butterflow.prep import VideoPrep
from butterflow.media.info import LibAvVideoInfo
from fractions import Fraction
import os
import butterflow.config


class VideoPrepTestCase(unittest.TestCase):
  def setUp(self):
    DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'samples')
    self.src_v = os.path.join(DIR, 'vid-3s-640x360-29.976fps-v.mp4')
    self.src_a = os.path.join(DIR, 'aud-5s.ogg')
    self.src_s = os.path.join(DIR, 'subtitles.srt')
    self.src_va = os.path.join(DIR, 'vid-5s-va.mp4')
    self.src_vs = os.path.join(DIR, 'vid-5s-vs.mp4')
    self.src_vas = os.path.join(DIR, 'vid-5s-vas.mp4')
    self.out_v = os.path.join(DIR, 'out.mp4')
    self.out_a = os.path.join(DIR, 'out.ogg')
    self.out_s = os.path.join(DIR, 'out.srt')
    self.using_avconv = butterflow.config.settings['avutil'] == 'avconv'
    self.remove_temp_files()

  def tearDown(self):
    self.remove_temp_files()

  def remove_temp_files(self):
    for x in [self.out_v, self.out_a, self.out_s]:
      if os.path.exists(x):
        os.remove(x)

  def assertExists(self, path):
    self.assertTrue(os.path.exists(path))

  def test_normalize_video(self):
    p = VideoPrep(LibAvVideoInfo(self.src_v))
    p.normalize_for_interpolation(self.out_v)
    self.assertExists(self.out_v)
    i = LibAvVideoInfo(self.out_v)
    self.assertTrue(i.has_video_stream)
    self.assertFalse(i.has_audio_stream)
    self.assertFalse(i.has_subtitle_stream)

  def test_normalize_video_audio(self):
    p = VideoPrep(LibAvVideoInfo(self.src_va))
    p.normalize_for_interpolation(self.out_v)
    self.assertExists(self.out_v)
    i = LibAvVideoInfo(self.out_v)
    self.assertTrue(i.has_video_stream)
    self.assertTrue(i.has_audio_stream)
    self.assertFalse(i.has_subtitle_stream)

  def test_normalize_video_audio_subtitles(self):
    p = VideoPrep(LibAvVideoInfo(self.src_vas))
    p.normalize_for_interpolation(self.out_v)
    self.assertExists(self.out_v)
    i = LibAvVideoInfo(self.out_v)
    self.assertTrue(i.has_video_stream)
    self.assertTrue(i.has_audio_stream)
    if not self.using_avconv:
      self.assertTrue(i.has_subtitle_stream)

  def test_normalize_no_video(self):
    p = VideoPrep(LibAvVideoInfo(self.src_a))
    with self.assertRaises(RuntimeError):
      p.normalize_for_interpolation(self.src_a)

  @unittest.skip('todo')
  def test_normalize_stream_mapping(self):pass

  def test_extract_audio(self):
    p = VideoPrep(LibAvVideoInfo(self.src_va))
    p.extract_audio(self.out_a)
    self.assertExists(self.out_a)

  def test_extract_audio_no_audio(self):
    p = VideoPrep(LibAvVideoInfo(self.src_v))
    with self.assertRaises(RuntimeError):
      p.extract_audio(self.out_a)

  @unittest.skip('todo')
  def test_extract_audio_multi_stream(self):
    pass

  def test_extract_subtitles(self):
    p = VideoPrep(LibAvVideoInfo(self.src_vs))
    p.extract_subtitles(self.out_s)
    self.assertExists(self.out_s)

  def test_extract_subtitles_no_subtitles(self):
    p = VideoPrep(LibAvVideoInfo(self.src_v))
    with self.assertRaises(RuntimeError):
      p.extract_subtitles(self.out_s)

  @unittest.skip('todo')
  def test_extract_subtitles_multi_stream(self):
    pass

  def test_mux_video(self):
    VideoPrep.mux_video(self.src_v, None, None, self.out_v)
    self.assertExists(self.out_v)
    i = LibAvVideoInfo(self.out_v)
    self.assertTrue(i.has_video_stream)
    self.assertFalse(i.has_audio_stream)
    self.assertFalse(i.has_subtitle_stream)

  def test_mux_video_with_audio(self):
    VideoPrep.mux_video(self.src_v, self.src_a, None, self.out_v)
    i = LibAvVideoInfo(self.out_v)
    self.assertTrue(i.has_video_stream)
    self.assertTrue(i.has_audio_stream)
    self.assertFalse(i.has_subtitle_stream)

  def test_mux_video_with_subtitles(self):
    VideoPrep.mux_video(self.src_v, None, self.src_s, self.out_v)
    i = LibAvVideoInfo(self.out_v)
    self.assertTrue(i.has_video_stream)
    self.assertFalse(i.has_audio_stream)
    if not self.using_avconv:
      self.assertTrue(i.has_subtitle_stream)

  def test_mux_video_with_audio_and_subtitles(self):
    VideoPrep.mux_video(self.src_v, self.src_a, self.src_s, self.out_v)
    i = LibAvVideoInfo(self.out_v)
    self.assertTrue(i.has_video_stream)
    self.assertTrue(i.has_audio_stream)
    if not self.using_avconv:
      self.assertTrue(i.has_subtitle_stream)

if __name__ == '__main__':
  unittest.main()
