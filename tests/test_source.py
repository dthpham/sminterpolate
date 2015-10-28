import unittest
import os
import subprocess
import fractions
import cv2
import numpy as np

# importing settings will make temp directories if they don't exist
from butterflow.settings import default as settings
from butterflow import avinfo
from butterflow.source import FrameSource

def mk_sample_video(dst_path, duration, w, h, rate):
    if os.path.exists(dst_path):
        return
    call = [
        settings['avutil'],
        '-loglevel', 'error',
        '-y',
        '-f', 'lavfi',
        '-i', 'testsrc=duration={}:size={}x{}:rate={}:decimals=2'.format(
            duration, w, h, str(rate)),
        '-pix_fmt', 'yuv420p']
    call.append(dst_path)
    if subprocess.call(call) == 1:
        raise RuntimeError

def av_frame_at_idx(video, dst_path, idx):
    # extract image using avutil and return a cvimage
    get_fr_proc = subprocess.call([
        settings['avutil'],
        '-loglevel', 'fatal',
        '-y',
        '-i', video,
        '-vf', 'select=gte(n\,{})'.format(idx),
        '-vframes', '1',
        dst_path])
    if get_fr_proc == 1:
        raise RuntimeError('failed to extract frame at idx={}'.format(idx))
    return cv2.imread(dst_path)


class FrameSourceTestCase(unittest.TestCase):
    def setUp(self):
        self.videofile_fr1 = os.path.join(settings['tmp_dir'],
                                     '~test_av_frame_source_test_case_fr_1.mp4')
        self.videofile_fr3 = os.path.join(settings['tmp_dir'],
                                     '~test_av_frame_source_test_case_fr_3.mp4')
        # make a 1fr and 3fr video
        mk_sample_video(self.videofile_fr1, 1, 320, 240, fractions.Fraction(1))
        mk_sample_video(self.videofile_fr3, 1, 320, 240, fractions.Fraction(3))
        # path to avutil fr to compare with
        self.imagefile = os.path.join(settings['tmp_dir'],
                                      '~test_av_frame_source_test_case.png')
        self.src_1 = FrameSource(self.videofile_fr1)
        self.src_3 = FrameSource(self.videofile_fr3)
        self.src_3.open()

    def tearDown(self):
        self.src_3.close()

    def test_seek_to_frame_initial_index_zero(self):
        self.assertEqual(self.src_3.idx, 0)

    def test_seek_to_frame_inside(self):
        self.src_3.seek_to_frame(1)
        self.assertEqual(self.src_3.idx, 1)

    def test_seek_to_frame_inside_same_frame_back_to_back(self):
        self.assertEqual(self.src_3.idx, 0)
        self.src_3.seek_to_frame(1)
        self.assertEqual(self.src_3.idx, 1)
        self.src_3.seek_to_frame(1)
        self.assertEqual(self.src_3.idx, 1)

    def test_seek_to_frame_at_edges(self):
        self.src_3.seek_to_frame(0)
        self.assertEqual(self.src_3.idx, 0)
        self.src_3.seek_to_frame(2)
        self.assertEqual(self.src_3.idx, 2)

    def test_seek_to_frame_outside_fails(self):
        with self.assertRaises(IndexError):
            self.src_3.seek_to_frame(-1)
        with self.assertRaises(IndexError):
            self.src_3.seek_to_frame(3)

    def test_read_frame_after_seek_to_frame_inside(self):
        self.src_3.seek_to_frame(1)
        f1 = self.src_3.read()
        f2 = av_frame_at_idx(self.src_3.path, self.imagefile, 1)
        self.assertTrue(np.array_equal(f1,f2))

    def test_read_frame_after_seek_to_frame_at_edges(self):
        self.src_3.seek_to_frame(0)
        f1 = self.src_3.read()
        f2 = av_frame_at_idx(self.src_3.path, self.imagefile, 0)
        self.assertTrue(np.array_equal(f1,f2))
        self.src_3.seek_to_frame(2)
        f1 = self.src_3.read()
        f2 = av_frame_at_idx(self.src_3.path, self.imagefile, 2)
        self.assertTrue(np.array_equal(f1,f2))

    def test_seek_forward_then_backward(self):
        self.src_3.seek_to_frame(2)
        f1 = self.src_3.read()
        f2 = av_frame_at_idx(self.src_3.path, self.imagefile, 2)
        self.assertTrue(np.array_equal(f1,f2))
        self.src_3.seek_to_frame(1)
        f1 = self.src_3.read()
        f2 = av_frame_at_idx(self.src_3.path, self.imagefile, 1)
        self.assertTrue(np.array_equal(f1,f2))
        self.src_3.seek_to_frame(0)
        f1 = self.src_3.read()
        f2 = av_frame_at_idx(self.src_3.path, self.imagefile, 0)
        self.assertTrue(np.array_equal(f1,f2))

    def test_n_frames_same_as_avinfo(self):
        av = avinfo.get_av_info(self.src_3.path)
        self.assertEqual(self.src_3.frames, av['frames'])

    def test_open_close(self):
        self.assertIsNone(self.src_1.src)
        self.src_1.open()
        self.assertIsNotNone(self.src_1.src)
        self.src_1.close()
        self.assertIsNone(self.src_1.src)
        self.src_1.open()
        self.assertIsNotNone(self.src_1.src)
        self.src_1.close()

    def test_open_twice(self):
        self.assertIsNone(self.src_1.src)
        self.src_1.open()
        self.src_1.open()
        self.assertIsNotNone(self.src_1.src)
        self.src_1.close()

    def test_close_twice(self):
        self.assertIsNone(self.src_1.src)
        self.src_1.open()
        self.src_1.close()
        self.assertIsNone(self.src_1.src)
        self.src_1.close()
        self.assertIsNone(self.src_1.src)


if __name__ == '__main__':
    unittest.main()
