import unittest
import os
from butterflow import avinfo, settings
from butterflow.render import Renderer

TDIR = settings.default['tmp_dir']
SDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                    'samples')


class RenderTestCase(unittest.TestCase):
    def setUp(self):
        self.src_v   = os.path.join(SDIR, 'vid-3s-640x360-29.976fps.mp4')
        self.src_a   = os.path.join(SDIR, 'aud-5s-beep.ogg')
        self.src_s   = os.path.join(SDIR, 'sub-5s.srt')
        self.src_va  = os.path.join(SDIR, 'vid-5s-va.mp4')
        self.src_vs  = os.path.join(SDIR, 'vid-5s-vs.mp4')
        self.src_vas = os.path.join(SDIR, 'vid-5s-vas.mp4')
        self.out_v   = os.path.join(TDIR, 'rnd.mp4')
        self.out_a   = os.path.join(TDIR, 'aud.ogg')
        self.out_s   = os.path.join(TDIR, 'sub.srt')
        self.make_renderer = lambda x: \
            Renderer(self.out_v, avinfo.get_info(x), None, 24,
                     av_loglevel='fatal')

    def tearDown(self):
        self.remove_temp_files()

    def remove_temp_files(self):
        for x in [self.out_v, self.out_a, self.out_s]:
            if os.path.exists(x):
                os.remove(x)

    def assertExists(self, path):
        self.assertTrue(os.path.exists(path))

    def test_normalize_video(self):
        r = self.make_renderer(self.src_v)
        r.normalize_for_interpolation(self.out_v)
        self.assertExists(self.out_v)
        i = avinfo.get_info(self.out_v)
        self.assertTrue(i['v_stream_exists'])
        self.assertFalse(i['a_stream_exists'])
        self.assertFalse(i['s_stream_exists'])

    def test_normalize_video_audio(self):
        r = self.make_renderer(self.src_va)
        r.normalize_for_interpolation(self.out_v)
        self.assertExists(self.out_v)
        i = avinfo.get_info(self.out_v)
        self.assertTrue(i['v_stream_exists'])
        self.assertTrue(i['a_stream_exists'])
        self.assertFalse(i['s_stream_exists'])

    def test_normalize_video_audio_subtitles(self):
        r = self.make_renderer(self.src_vas)
        r.normalize_for_interpolation(self.out_v)
        self.assertExists(self.out_v)
        i = avinfo.get_info(self.out_v)
        self.assertTrue(i['v_stream_exists'])
        self.assertTrue(i['a_stream_exists'])

    def test_normalize_no_video(self):
        r = self.make_renderer(self.src_a)
        with self.assertRaises(RuntimeError):
            r.normalize_for_interpolation(self.src_a)

    def test_extract_audio(self):
        r = self.make_renderer(self.src_va)
        r.extract_audio(self.out_a)
        self.assertExists(self.out_a)

    def test_extract_audio_no_audio(self):
        r = self.make_renderer(self.src_v)
        with self.assertRaises(RuntimeError):
            r.extract_audio(self.out_a)

    @unittest.skip('todo')
    def test_extract_audio_multi_stream(self):
        pass

    def test_extract_subtitles(self):
        r = self.make_renderer(self.src_vs)
        r.extract_subtitles(self.out_s)
        self.assertExists(self.out_s)

    def test_extract_subtitles_no_subtitles(self):
        r = self.make_renderer(self.src_v)
        with self.assertRaises(RuntimeError):
            r.extract_subtitles(self.out_s)

    @unittest.skip('todo')
    def test_extract_subtitles_multi_stream(self):
        pass

    def test_mux_video(self):
        r = self.make_renderer(self.src_v)
        r.mux_video(self.src_v, None, None, self.out_v,
            cleanup=False)
        self.assertExists(self.out_v)
        i = avinfo.get_info(self.out_v)
        self.assertTrue(i['v_stream_exists'])
        self.assertFalse(i['a_stream_exists'])
        self.assertFalse(i['s_stream_exists'])

    def test_mux_video_with_audio(self):
        r = self.make_renderer(self.src_v)
        r.mux_video(self.src_v, self.src_a, None, self.out_v,
            cleanup=False)
        i = avinfo.get_info(self.out_v)
        self.assertTrue(i['v_stream_exists'])
        self.assertTrue(i['a_stream_exists'])
        self.assertFalse(i['s_stream_exists'])

    def test_mux_video_with_subtitles(self):
        r = self.make_renderer(self.src_v)
        r.mux_video(self.src_v, None, self.src_s, self.out_v,
            cleanup=False)
        i = avinfo.get_info(self.out_v)
        self.assertTrue(i['v_stream_exists'])
        self.assertFalse(i['a_stream_exists'])
        self.assertTrue(i['s_stream_exists'])

    def test_mux_video_with_audio_and_subtitles(self):
        r = self.make_renderer(self.src_v)
        r.mux_video(self.src_v, self.src_a, self.src_s, self.out_v,
            cleanup=False)
        i = avinfo.get_info(self.out_v)
        self.assertTrue(i['v_stream_exists'])
        self.assertTrue(i['a_stream_exists'])
        self.assertTrue(i['s_stream_exists'])


if __name__ == '__main__':
    unittest.main()
