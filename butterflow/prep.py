import os
import subprocess
import shutil
import config


class VideoPrep(object):
  '''applies some ops to video to aid in the creation of the final
  rendered video. takes in a BaseVideoInfo object
  '''
  def __init__(self, video_info, loglevel='fatal'):
    self.video_info = video_info
    self.loglevel = loglevel

  def normalize_for_interpolation(self, dst_path, vf_scale=1.0,
                                  vf_decimate=False):
    '''transcode the video to a standard format so that interpolation
    yields the the best results. the main goal is to retranscode to the
    lowest possible constant rate in which all unique frames in the vid
    are retained. this is to avoid having to dupe/drop frames during the
    interpolation process which if done incorrectly may cause video and
    audio sync drift. in the future, the process shouldn't be framerate
    sensitive
    '''
    using_avconv = config.settings['avutil'] == 'avconv'
    if not self.video_info.has_video_stream:
      raise RuntimeError('no video stream detected')
    has_sub = self.video_info.has_subtitle_stream
    has_aud = self.video_info.has_audio_stream

    w = -1 if using_avconv else -2
    h = int(self.video_info.height * vf_scale * 0.5) * 2
    scaler = 'bilinear' if vf_scale >= 1.0 else 'lanczos'

    tmp_path = os.path.join(
        os.path.dirname(dst_path), '~' + os.path.basename(dst_path))

    vf = 'scale={}:{}'.format(w, h)
    if vf_decimate:
      vf = 'fieldmatch,decimate,' + vf
    pix_fmt = 'yuv420p'
    if config.settings['args'].grayscale:
      pix_fmt = 'gray'

    call = [
        config.settings['avutil'],
        '-loglevel', self.loglevel,
        '-y',
        '-threads', '0',
        '-i', self.video_info.video_path,
        '-pix_fmt', pix_fmt,
        '-filter:v', vf,
    ]
    if has_aud:
      call.extend([
          '-c:a', 'libvorbis',
          '-ab', '96k'
      ])
    if has_sub and not using_avconv:
      call.extend([
          '-c:s', 'mov_text'
      ])
    call.extend([
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '18',
        '-sws_flags', scaler
    ])
    if not using_avconv:
      call.extend(['-level', '4.2'])
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
        config.settings['avutil'],
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
    if config.settings['avutil'] == 'avconv':
      open(dst_path, 'a').close()
      return
    proc = subprocess.call([
        config.settings['avutil'],
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
        config.settings['avutil'],
        '-loglevel', loglevel,
        '-y',
    ]
    if aud_path:
      call.extend(['-i', aud_path])
    call.extend(['-i', vid_path])
    if sub_path:
      call.extend(['-i', sub_path])
    if aud_path:
      call.extend(['-c:a', 'copy'])
    call.extend(['-c:v', 'copy'])
    if sub_path:
      call.extend(['-c:s', 'mov_text'])
    call.extend([dst_path])
    proc = subprocess.call(call)
    if proc == 1:
      raise RuntimeError('unable to mux video')
