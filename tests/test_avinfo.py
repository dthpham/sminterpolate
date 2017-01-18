# -*- coding: utf-8 -*-

import unittest
import subprocess
import os
import fractions
import struct
import wave
import numpy as np

from butterflow.settings import default as settings  # will mk temp dirs
from butterflow import avinfo

def mk_sample_wav_file(dest, duration):
    if os.path.exists(dest):
        return
    wav = wave.open(dest, 'w')
    wav.setparams((2, 2, 44100, 0, 'NONE', 'un-compressed'))  # 2-ch
    # 44100 random samples between -1 and 1
    data = np.random.uniform(-1, 1, 44100 * duration)  # duration in seconds
    scaled = np.int16(data / np.max(np.abs(data)) * 32767)
    for i in scaled:
        v = struct.pack('h', i)  # short int, 2 bytes or 16 bits
        wav.writeframes(v)
        wav.writeframes(v)
    wav.close()

def mk_sample_video(dest, duration, w, h, rate, sar=None, dar=None):
    if os.path.exists(dest):
        return
    call = [
        settings['avutil'],
        '-loglevel', 'error',
        '-y',
        '-f', 'lavfi',
        '-i', 'smptebars=duration={}:size={}x{}:rate={}'.
        format(duration, w, h, str(rate))]
    vf = []
    if sar is not None:
        vf.append('setsar={}:{}'.format(sar.numerator, sar.denominator))
    if dar is not None:
        vf.append('setdar={}:{}'.format(dar.numerator, dar.denominator))
    if len(vf) > 0:
        call.extend(['-vf', ','.join(vf)])
    call.append(dest)
    if subprocess.call(call) == 1:
        raise RuntimeError

def mux_video_with_files(dest, video, *files):
    if os.path.exists(dest):
        return
    call = [
        settings['avutil'],
        '-loglevel', 'error',
        '-y',
        '-i', video]
    for file in files:
        call.extend(['-i', file])
    call.extend([
        '-strict', '-2',
        '-c:a', 'aac',
        '-c:v', 'copy',
        dest])
    if subprocess.call(call) == 1:
        raise RuntimeError

class AvInfoTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_get_av_info_video_duration_rate_frames_rational_rate(self):
        testfile = os.path.join(settings['tempdir'],
                                'test_get_av_info_video_rational_rate.mp4')
        mk_sample_video(testfile, 2, 640, 360, fractions.Fraction(24, 1))
        av = avinfo.get_av_info(testfile)
        self.assertEqual(av['duration'], 2*1000)
        self.assertEqual(av['rate_n'], 24)
        self.assertEqual(av['rate_d'], 1)
        self.assertEqual(av['frames'], 24*2)

    def test_get_av_info_video_duration_rate_frames_fractional_rate(self):
        testfile = os.path.join(settings['tempdir'],
                                'test_get_av_info_video_fractional_rate.mp4')
        mk_sample_video(testfile, 3, 640, 360, fractions.Fraction(30000, 1001))
        av = avinfo.get_av_info(testfile)
        self.assertEqual(av['duration'], 3.003*1000)
        self.assertEqual(av['rate_n'], 30*1000.0)
        self.assertEqual(av['rate_d'], 1001)
        self.assertEqual(av['frames'], 30*1000.0/1001 * 3.003)

    def test_get_av_info_w_h_sar_unknown(self):
        testfile = os.path.join(settings['tempdir'],
                                'test_get_av_info_w_h_sar_unknown.mp4')
        mk_sample_video(testfile, 1, 640, 360, fractions.Fraction(1, 1))
        av = avinfo.get_av_info(testfile)
        self.assertEqual(av['w'], 640)
        self.assertEqual(av['h'], 360)
        self.assertEqual(av['sar_n'], 1)    # assume sar is 1:1
        self.assertEqual(av['sar_d'], 1)
        w_h = fractions.Fraction(640, 360)  # dar is just the aspect ratio of
        # the pixel aspect ratio if sar is 1:1
        self.assertEqual(av['dar_n'], w_h.numerator)
        self.assertEqual(av['dar_d'], w_h.denominator)

    def test_get_av_info_w_h_sar_known_dar_known(self):
        testfile = os.path.join(settings['tempdir'],
                                'test_get_av_info_w_h_sar_known_dar_known.mp4')
        sar = fractions.Fraction(4, 3)
        dar = fractions.Fraction(16, 9)
        mk_sample_video(testfile, 1, 320, 240, fractions.Fraction(1, 1),
                        sar=sar, dar=dar)
        av = avinfo.get_av_info(testfile)
        self.assertEqual(av['w'], 320)
        self.assertEqual(av['h'], 240)
        self.assertEqual(av['sar_n'], sar.numerator)
        self.assertEqual(av['sar_d'], sar.denominator)
        self.assertEqual(av['dar_n'], dar.numerator)
        self.assertEqual(av['dar_d'], dar.denominator)

    def test_get_av_info_w_h_sar_known_dar_unknown(self):
        testfile = os.path.join(settings['tempdir'],
                              'test_get_av_info_w_h_sar_known_dar_unknown.mp4')
        sar = fractions.Fraction(32, 27)
        mk_sample_video(testfile, 1, 714, 458, fractions.Fraction(1, 1),
                        sar=sar)
        av = avinfo.get_av_info(testfile)
        self.assertEqual(av['w'], 714)
        self.assertEqual(av['h'], 458)
        self.assertEqual(av['sar_n'], sar.numerator)
        self.assertEqual(av['sar_d'], sar.denominator)
        dar = fractions.Fraction(714*32, 458*27)  # use fractions.Fraction to
        # simplify the fraction, if needed
        self.assertEqual(av['dar_n'], dar.numerator)
        self.assertEqual(av['dar_d'], dar.denominator)

    def test_get_av_info_stream_exists(self):
        videofile = os.path.join(settings['tempdir'],
                                 'test_get_av_info_stream_exists.mp4')
        mk_sample_video(videofile, 1, 320, 240, fractions.Fraction(1, 1))
        av = avinfo.get_av_info(videofile)
        self.assertTrue(av['v_stream_exists'])
        self.assertFalse(av['a_stream_exists'])
        self.assertFalse(av['s_stream_exists'])

        wavfile = os.path.join(settings['tempdir'],
                               'test_get_av_info_stream_exists.wav')
        mk_sample_wav_file(wavfile, 1)
        av = avinfo.get_av_info(wavfile)
        self.assertTrue(av['a_stream_exists'])
        self.assertFalse(av['v_stream_exists'])
        self.assertFalse(av['s_stream_exists'])

        muxedfile = os.path.join(settings['tempdir'],
                                 'test_get_av_info_stream_exists.muxed.mp4')
        mux_video_with_files(muxedfile, videofile, wavfile)
        av = avinfo.get_av_info(muxedfile)
        self.assertTrue(av['v_stream_exists'])
        self.assertTrue(av['a_stream_exists'])
        self.assertFalse(av['s_stream_exists'])

    def test_get_av_info_multimedia_file_no_video_stream(self):
        testfile = os.path.join(settings['tempdir'],
                        'test_get_av_info_multimedia_file_no_video_stream.wav')
        mk_sample_wav_file(testfile, 1)
        av = avinfo.get_av_info(testfile)
        self.assertEqual(av['path'], testfile)
        self.assertFalse(av['v_stream_exists'])
        self.assertEqual(av['w'], 0)
        self.assertEqual(av['h'], 0)
        self.assertEqual(av['sar_n'], 0)
        self.assertEqual(av['sar_d'], 0)
        self.assertEqual(av['dar_n'], 0)
        self.assertEqual(av['dar_d'], 0)
        self.assertEqual(av['duration'], 0)
        self.assertEqual(av['rate_n'], 0)
        self.assertEqual(av['rate_d'], 0)
        self.assertEqual(av['frames'], 0)

    def test_get_av_info_path(self):
        testfile = os.path.join(settings['tempdir'],
                                'test_get_av_info_path.mp4')
        mk_sample_video(testfile, 1, 320, 240, fractions.Fraction(1, 1))
        av = avinfo.get_av_info(testfile)
        self.assertEqual(av['path'], testfile)

    def test_no_file_at_path_fails(self):
        with self.assertRaises(RuntimeError):
            avinfo.get_av_info('does_not_exist.mp4')

    def test_get_av_info_non_multimedia_file_fails(self):
        testfile = os.path.join(settings['tempdir'],
                                'test_get_av_info_non_multimedia_file_fails')
        with open(testfile, 'w'):
            pass
        with self.assertRaises(RuntimeError):
            avinfo.get_av_info(testfile)

if __name__ == '__main__':
    unittest.main()
