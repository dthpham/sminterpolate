import unittest
import os
import subprocess
import cv2
import numpy as np
from butterflow import avinfo, settings
from butterflow.source import FrameSource

SDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                    'samples')


class FrameSourceTestCase(unittest.TestCase):
    def setUp(self):
        self.test_vid = os.path.join(SDIR, 'vid-5s-640x360-30fps.mp4')
        self.test_img = os.path.join(SDIR, 'img.png')
        if not os.path.exists(self.test_vid):
            mk_test_proc = subprocess.call([
                settings.default['avutil'],
                '-loglevel', 'fatal',
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
        self.src = FrameSource(self.test_vid)

    def tearDown(self):
        self.remove_temp_files()

    def remove_temp_files(self):
        if os.path.exists(self.test_img):
            os.remove(self.test_img)

    def av_frame_at_idx(self, idx):
        '''extract image using libav, read image using opencv'''
        get_fr_proc = subprocess.call([
            settings.default['avutil'],
            '-loglevel', 'fatal',
            '-y',
            '-i', self.test_vid,
            '-vf', 'select=gte(n\,{})'.format(idx),
            '-vframes', '1',
            self.test_img
        ])
        if get_fr_proc == 1:
            raise RuntimeError(
                'failed to extract frame at idx {}'.format(idx))
        return cv2.imread(self.test_img)

    def av_frame_at_time(self, time):
        '''extract image using libav, read image using opencv'''
        secs = time/1000.0
        get_fr_proc = subprocess.call([
            settings.default['avutil'],
            '-loglevel', 'fatal',
            '-y',
            '-ss', str(secs),
            '-i', self.test_vid,
            '-vframes', '1',
            self.test_img
        ])
        if get_fr_proc == 1:
            raise RuntimeError(
                'failed to extract frame at time {}s'.format(secs))
        return cv2.imread(self.test_img)

    def test_seek_to_frame(self):
        self.assertEqual(self.src.index, 0)
        self.src.seek_to_frame(149)
        self.assertEqual(self.src.index, 149)
        self.src.seek_to_frame(1)
        self.assertEqual(self.src.index, 1)

    def test_seek_to_frame_outside(self):
        with self.assertRaises(IndexError):
            self.src.seek_to_frame(-1)
        with self.assertRaises(IndexError):
            self.src.seek_to_frame(150)

    def test_seek_to_time(self):
        self.assertEqual(self.src.time_position, 0)
        self.src.seek_to_time(5*1000)
        self.assertEqual(self.src.time_position, 5*1000)
        self.src.seek_to_time(1*1000)
        self.assertEqual(self.src.time_position, 1*1000)

    def test_seek_to_time_outside(self):
        with self.assertRaises(IndexError):
            self.src.seek_to_time(-1*1000)
        with self.assertRaises(IndexError):
            self.src.seek_to_time(5.1*1000)

    def test_seek_mix_time_and_frame(self):
        self.src.seek_to_frame(120)
        self.assertEqual(self.src.index, 120)
        self.assertEqual(self.src.time_position, 4*1000)
        self.src.seek_to_time(1*1000)
        self.assertEqual(self.src.index, 30)
        self.assertEqual(self.src.time_position, 1*1000)
        self.src.seek_to_frame(0)
        self.assertEqual(self.src.index, 0)
        self.assertEqual(self.src.time_position, 0)

    def test_read_frame_after_seek_by_frame(self):
        self.src.seek_to_frame(30)
        f1 = self.src.read()
        f2 = self.av_frame_at_idx(30)
        self.assertTrue(np.array_equal(f1,f2))

    def test_read_frame_after_seek_by_frame_at_edges(self):
        self.src.seek_to_frame(0)
        f1 = self.src.read()
        f2 = self.av_frame_at_idx(0)
        self.assertTrue(np.array_equal(f1,f2))
        self.src.seek_to_frame(149)
        f1 = self.src.read()
        f2 = self.av_frame_at_idx(149)
        self.assertTrue(np.array_equal(f1,f2))

    def test_read_frame_after_seek_by_time(self):
        self.src.seek_to_time(1*1000)
        f1 = self.src.read()
        f2 = self.av_frame_at_time(1*1000)
        self.assertTrue(np.array_equal(f1,f2))

    def test_read_frame_after_seek_by_time_at_edges(self):
        self.src.seek_to_time(0)
        f1 = self.src.read()
        f2 = self.av_frame_at_time(0)
        self.assertTrue(np.array_equal(f1,f2))
        self.src.seek_to_time(149/30*1000)
        f1 = self.src.read()
        f2 = self.av_frame_at_time(149/30*1000)
        self.assertTrue(np.array_equal(f1,f2))

    def test_get_frame_at_idx(self):
        f1 = self.src.frame_at_idx(50)
        f2 = self.av_frame_at_idx(50)
        self.assertTrue(np.array_equal(f1,f2))

    def test_get_frame_at_time(self):
        f1 = self.src.frame_at_time(2.5*1000)
        f2 = self.av_frame_at_time(2.5*1000)
        self.assertTrue(np.array_equal(f1,f2))

    def test_frame_and_duration_equal_avinfo(self):
        av = avinfo.get_info(self.test_vid)
        av_frs = av['frames']
        av_dur = av['duration']
        self.assertEqual(self.src.duration, av_dur)
        self.assertEqual(self.src.frames, av_frs)


if __name__ == '__main__':
    unittest.main()
