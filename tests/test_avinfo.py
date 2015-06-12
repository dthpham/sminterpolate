import unittest
import os
import subprocess
from butterflow import avinfo, settings

SDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                    'samples')


class AvInfoTestCase(unittest.TestCase):
    def setUp(self):
        fv = os.path.join(SDIR, 'vid-3s-640x360-29.976fps.mp4')
        fa = os.path.join(SDIR, 'vid-10s-va.mp4')
        fs = os.path.join(SDIR, 'vid-5s-vs.mp4')
        if not os.path.exists(fv):
            mk_test_proc = subprocess.call([
                settings.default['avutil'],
                '-loglevel', 'fatal',
                '-y',
                '-f', 'lavfi',
                '-i', 'testsrc=duration=3:size=640x360:rate=30000/1001:'
                      'decimals=3',
                '-pix_fmt', 'yuv420p',
                '-c:v', 'libx264',
                '-crf', '0',
                fv
            ])
            if mk_test_proc == 1:
                raise RuntimeError('failed to make test vid')
        self.v = avinfo.get_info(fv)
        self.a = avinfo.get_info(fa)
        self.s = avinfo.get_info(fs)

    def test_invalid_video_path(self):
        with self.assertRaises(RuntimeError):
            avinfo.get_info(os.path.join(SDIR, 'dne'))

    def test_vid_path(self):
        self.assertEqual(self.v['path'],
                         os.path.join(SDIR, 'vid-3s-640x360-29.976fps.mp4'))

    def test_v_stream_exists(self):
        self.assertTrue(self.v['v_stream_exists'])
        self.assertTrue(self.a['v_stream_exists'])
        self.assertTrue(self.s['v_stream_exists'])

    def test_a_stream_exists(self):
        self.assertFalse(self.v['a_stream_exists'])
        self.assertTrue(self.a['a_stream_exists'])
        self.assertFalse(self.s['a_stream_exists'])

    def test_s_stream_exists(self):
        self.assertFalse(self.v['s_stream_exists'])
        self.assertFalse(self.a['s_stream_exists'])
        self.assertTrue(self.s['s_stream_exists'])

    def test_resolution(self):
        i = self.v
        self.assertEqual(i['width'], 640)
        self.assertEqual(i['height'], 360)

    def test_duration(self):
        self.assertEqual(self.v['duration'], 3.003*1000)

    def test_frames(self):
        r = 30*1000.0/1001
        d = 3.003
        self.assertEqual(self.v['frames'], r*d)

    def test_rate(self):
        self.assertEqual(self.v['rate_num'], 30*1000.0)
        self.assertEqual(self.v['rate_den'], 1001)

    def test_min_rate(self):
        r = 30*1000.0/1001
        d = 3.003
        n = float(r)*d
        self.assertEqual(self.v['min_rate'], n/d)

if __name__ == '__main__':
    unittest.main()
