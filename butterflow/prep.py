import os
import fractions
import math
import subprocess
import shutil
import pdb


class VideoPrep(object):
  '''applies some ops to video to aid in the creation of the final
  rendered video. takes in a BaseVideoInfo object
  '''
  def __init__(self, video_info, loglevel='fatal'):
    self.video_info = video_info
    self.loglevel = loglevel

  def get_nearest_common_frame_rate(self, rate, tol=25.0):
    '''returns the nearest lowest common frame rate for a given rate.
    `tol` is the largest difference between the closest common rate and
    the given rate that is needed before accepting any newly proposed
    rate. note that it is more desirable to drop frames (going from
    higher to lower). a higher rate means frames will have to be
    duplicated.
    '''
    new_rate = rate
    common = {
        '24': fractions.Fraction(24),
        '23.976': fractions.Fraction(24*1000,1001),
        '23.98': fractions.Fraction(24*1000,1001),
        '25': fractions.Fraction(25),
        '29.97': fractions.Fraction(30*1000,1001),
        '48': fractions.Fraction(48),
        '50': fractions.Fraction(50),
        '59.94': fractions.Fraction(60*1000,1001),
        '60': fractions.Fraction(60),
    }

    key = None
    low_diff = float('inf')
    for r in common.keys():
      diff = math.fabs(float(r) - float(rate))
      if diff < low_diff:
        key = r
        low_diff = diff
    near_rate = common[key]

    if low_diff <= tol:
      new_rate = near_rate
    return new_rate

  def get_telecine_compensated_rate(self, rate):
    '''returns a rate that compensates for videos that may have been
    telecined / pulled down. rate should be in fractional form. this
    doesnt cover the entire range of pulldown patterns we're not trying
    to detect telecined videos here, just indiscriminately going to use
    a pullup filter on all videos later, however this can have a
    negative effect because the videos may not even be pulled down and
    therefore lowering the fps may cause unique frames to be dropped.
    this can be improved by first detecting if a video is telecined
    using a quick and dirty heuritic and only pulling up when necessary
    '''
    if not isinstance(rate, fractions.Fraction):
      raise RuntimeWarning(
          'rate should be in fractional form for best results')
    patterns = {
        fractions.Fraction(25): fractions.Fraction(24*1000, 1001),
        fractions.Fraction(30*1000, 1001): fractions.Fraction(24*1000, 1001)
    }
    new_rate = rate
    if rate in patterns.keys():
      new_rate = patterns[rate]
    return new_rate

  def normalize_for_interpolation(self, dst_path, scale=1.0):
    '''transcode the video to a standard format so that interpolation
    yields the the best results. the main goal is to retranscode to the
    lowest possible constant rate in which all unique frames in the vid
    are retained. this is to avoid having to dupe/drop frames during the
    interpolation process which if done incorrectly may cause video and
    audio sync drift. in the future, the process shouldn't be framerate
    sensitive
    '''
    if not self.video_info.has_video_stream:
      raise RuntimeError('no video stream detected')
    has_sub = self.video_info.has_subtitle_stream
    has_aud = self.video_info.has_audio_stream

    h = int(self.video_info.height * scale * 0.5) * 2
    scaler = 'bilinear' if scale >= 1.0 else 'lanczos'

    new_rate = self.video_info.min_rate
    new_rate = self.get_nearest_common_frame_rate(new_rate)
    new_rate = self.get_telecine_compensated_rate(new_rate)

    tmp_path = os.path.join(
        os.path.dirname(dst_path), '~' + os.path.basename(dst_path))

    call = [
        'ffmpeg',
        '-loglevel', self.loglevel,
        '-y',
        '-threads', '0',
        '-fflags', '+discardcorrupt+genpts+igndts',
        '-i', self.video_info.video_path,
        '-pix_fmt', 'yuv420p',
        '-filter:v', 'fieldmatch,decimate,scale=-2:{}'.format(h),
        # '-r', str(new_rate)
    ]
    if has_aud:
      call.extend([
          '-c:a', 'libvorbis',
          '-ab', '96k'
      ])
    if has_sub:
      call.extend([
          '-c:s', 'mov_text'
      ])
    call.extend([
        '-c:v', 'libx264',
        '-tune', 'film',
        '-preset', 'slow',
        '-crf', '18',
        '-level', '4.0',
        '-sws_flags', scaler
    ])
    call.extend([tmp_path])
    nrm_proc = subprocess.call(call)
    if nrm_proc == 1:
      raise RuntimeError('could not normalize video')
    shutil.move(tmp_path, dst_path)

  def extract_audio(self, dst_path):
    '''extract audio from the file if it exists'''
    if not self.video_info.has_audio_stream:
      raise RuntimeError('no audio stream detected')
    proc = subprocess.call([
        'ffmpeg',
        '-loglevel', self.loglevel,
        '-y',
        '-i', self.video_info.video_path,
        '-vn',
        '-sn',
        dst_path
    ])
    if proc == 1:
      raise RuntimeError('unable to extract audio from video')

  def extract_subtitles(self, dst_path):
    '''dump subtitles to a file if it exists'''
    if not self.video_info.has_subtitle_stream:
      raise RuntimeError('no subtitle streams detected')
    proc = subprocess.call([
        'ffmpeg',
        '-loglevel', self.loglevel,
        '-y',
        '-i', self.video_info.video_path,
        '-vn',
        '-an',
        dst_path
    ])
    if proc == 1:
      raise RuntimeError('unable to extract subtitles from video')

  @staticmethod
  def mux_video(vid_path, aud_path, sub_path, dst_path, loglevel='fatal'):
    '''muxes video, audio, and subtitle to a new video'''
    if not os.path.exists(vid_path):
      raise IOError('video not found: {}'.format(vid_path))
    if aud_path is not None and not os.path.exists(aud_path):
      raise IOError('audio not found: {}'.format(aud_path))
    if sub_path is not None and not os.path.exists(sub_path):
      raise IOError('subtitle not found: {}'.format(sub_path))

    if aud_path is None and sub_path is None:
      shutil.copy(vid_path, dst_path)
      return

    call = [
        'ffmpeg',
        '-loglevel', loglevel,
        '-y',
    ]
    if aud_path:
      call.extend([
          '-i', aud_path
      ])
    call.extend([
        '-i', vid_path
    ])
    if sub_path:
      call.extend([
          '-i', sub_path
      ])
    if aud_path:
      call.extend([
          '-c:a', 'copy'
      ])
    call.extend([
        '-c:v', 'copy'
    ])
    if sub_path:
      call.extend([
          '-c:s', 'mov_text'
      ])
    call.extend([dst_path])
    proc = subprocess.call(call)
    if proc == 1:
      raise RuntimeError('unable to mux video')
