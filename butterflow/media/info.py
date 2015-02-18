from fractions import Fraction
import os
import py_libav_info


class BaseVideoInfo(object):
  '''provides information about the video that is required
  to complete a full render. the min_rate is the smallest possible
  rate of the video stream that can be represented without losing
  any frames. it is usally calclulated by dividing the total number of
  frames (unique frames) by the duration.
  '''
  def __init__(self, video_path):
    if not os.path.exists(video_path):
      raise ValueError('video does not exist: {}'.format(video_path))

    self.video_path = video_path
    self.has_video_stream = False
    self.has_audio_stream = False
    self.has_subtitle_stream = False
    self.width = 0
    self.height = 0
    self.duration = 0.0
    self.rate = None
    self.min_rate = None
    self.num_frames = 0  # actual number of frames coded in the video


class LibAvVideoInfo(BaseVideoInfo):
  '''uses libav/ffmpeg to get media info'''
  def __init__(self, video_path):
    super(LibAvVideoInfo, self).__init__(video_path)

    info = py_libav_info.py_get_video_info(video_path)
    if info is None:
      raise RuntimeError('could not get video info: {}'.format(video_path))

    self.has_video_stream = info[0]
    self.has_audio_stream = info[1]
    self.has_subtitle_stream = info[2]
    self.width = info[3]
    self.height = info[4]
    self.duration = info[5]
    self.rate = Fraction(info[6], info[7])
    self.min_rate = Fraction(info[8])
    self.num_frames = info[9]
