# -*- coding: utf-8 -*-

import unittest
import os
import subprocess
import fractions
import cv2
import numpy as np

from butterflow.settings import default as settings  # will make temp dirs
from butterflow import avinfo
from butterflow.source import OpenCvFrameSource

def mk_sample_video(dest, duration, w, h, rate):
    if os.path.exists(dest):
        return
    call = [
        settings['avutil'],
        '-loglevel', 'error',
        '-y',
        '-f', 'lavfi',
        '-i', 'testsrc=duration={}:size={}x{}:rate={}:decimals=2'.format(
            duration, w, h, str(rate)),
        '-pix_fmt', 'yuv420p',
        dest]
    if subprocess.call(call) == 1:
        raise RuntimeError

def avutil_fr_at_idx(src, dest, idx):
    # extract image using avutil and return a cvimage
    get_fr_proc = subprocess.call([
        settings['avutil'],
        '-loglevel', 'fatal',
        '-y',
        '-i', src,
        '-vf', 'select=gte(n\,{})'.format(idx),
        '-vframes', '1',
        dest])
    if get_fr_proc == 1:
        raise RuntimeError
    return cv2.imread(dest)

class OpenCvFrameSourceTestCase(unittest.TestCase):
    def setUp(self):
        self.videofile_fr1 = os.path.join(settings['tempdir'],
                                     'test_av_frame_source_test_case_fr_1.mp4')
        self.videofile_fr3 = os.path.join(settings['tempdir'],
                                     'test_av_frame_source_test_case_fr_3.mp4')
        # make a 1fr and 3fr video
        mk_sample_video(self.videofile_fr1, 1, 320, 240, fractions.Fraction(1))
        mk_sample_video(self.videofile_fr3, 1, 320, 240, fractions.Fraction(3))
        # path to avutil fr to compare with
        self.imagefile = os.path.join(settings['tempdir'],
                                      'test_av_frame_source_test_case.png')
        self.src_1 = OpenCvFrameSource(self.videofile_fr1)
        self.src_3 = OpenCvFrameSource(self.videofile_fr3)
        self.src_3.open()

    def tearDown(self):
        self.src_3.close()

    def test_seek_to_fr_initial_index_zero(self):
        self.assertEqual(self.src_3.idx, 0)

    def test_seek_to_fr_inside(self):
        self.src_3.seek_to_fr(1)
        self.assertEqual(self.src_3.idx, 1)

    def test_seek_to_fr_inside_same_fr_back_to_back(self):
        self.assertEqual(self.src_3.idx, 0)
        self.src_3.seek_to_fr(1)
        self.assertEqual(self.src_3.idx, 1)
        self.src_3.seek_to_fr(1)
        self.assertEqual(self.src_3.idx, 1)

    def test_seek_to_fr_at_edges(self):
        self.src_3.seek_to_fr(0)
        self.assertEqual(self.src_3.idx, 0)
        self.src_3.seek_to_fr(2)
        self.assertEqual(self.src_3.idx, 2)

    def test_seek_to_fr_outside_fails(self):
        with self.assertRaises(IndexError):
            self.src_3.seek_to_fr(-1)
        with self.assertRaises(IndexError):
            self.src_3.seek_to_fr(3)

    def test_read_after_seek_to_fr_inside(self):
        self.src_3.seek_to_fr(1)
        f1 = self.src_3.read()
        f2 = avutil_fr_at_idx(self.src_3.src, self.imagefile, 1)
        self.assertTrue(np.array_equal(f1,f2))

    def test_read_after_seek_to_fr_at_edges(self):
        self.src_3.seek_to_fr(0)
        f1 = self.src_3.read()
        f2 = avutil_fr_at_idx(self.src_3.src, self.imagefile, 0)
        self.assertTrue(np.array_equal(f1,f2))
        self.src_3.seek_to_fr(2)
        f1 = self.src_3.read()
        f2 = avutil_fr_at_idx(self.src_3.src, self.imagefile, 2)
        self.assertTrue(np.array_equal(f1,f2))

    def test_seek_forward_then_backward(self):
        self.src_3.seek_to_fr(2)
        f1 = self.src_3.read()
        f2 = avutil_fr_at_idx(self.src_3.src, self.imagefile, 2)
        self.assertTrue(np.array_equal(f1,f2))
        self.src_3.seek_to_fr(1)
        f1 = self.src_3.read()
        f2 = avutil_fr_at_idx(self.src_3.src, self.imagefile, 1)
        self.assertTrue(np.array_equal(f1,f2))
        self.src_3.seek_to_fr(0)
        f1 = self.src_3.read()
        f2 = avutil_fr_at_idx(self.src_3.src, self.imagefile, 0)
        self.assertTrue(np.array_equal(f1,f2))

    def test_frames_equal_to_avinfo_frames(self):
        av = avinfo.get_av_info(self.src_3.src)
        self.assertEqual(self.src_3.frames, av['frames'])

    def test_open_close(self):
        self.assertIsNone(self.src_1.capture)
        self.src_1.open()
        self.assertIsNotNone(self.src_1.capture)
        self.src_1.close()
        self.assertIsNone(self.src_1.capture)
        self.src_1.open()
        self.assertIsNotNone(self.src_1.capture)
        self.src_1.close()

    def test_open_2x(self):
        self.assertIsNone(self.src_1.capture)
        self.src_1.open()
        self.src_1.open()
        self.assertIsNotNone(self.src_1.capture)
        self.src_1.close()

    def test_close_2x(self):
        self.assertIsNone(self.src_1.capture)
        self.src_1.open()
        self.src_1.close()
        self.assertIsNone(self.src_1.capture)
        self.src_1.close()
        self.assertIsNone(self.src_1.capture)

if __name__ == '__main__':
    unittest.main()
