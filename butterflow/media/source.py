import numpy as np
import abc
import cv2


class BaseFrameSource(object):
  '''Base class for video sources that produces frames'''
  __metaclass__ = abc.ABCMeta

  def __init__(self):
    '''time is in milliseconds'''
    self._curr_time_pos = 0
    self._curr_frame_idx = 0

  @abc.abstractmethod
  def seek_to_frame(self, idx):
    '''concrete classes have to update frame and time position, should
    raise IndexError if out of bounds
    '''
    pass

  @abc.abstractmethod
  def seek_to_time(self, time):
    '''concrete classes have to update frame and time position, should
    raise IndexError if out of bounds
    '''
    pass

  @abc.abstractmethod
  def retrieve_frame():
    '''have the source retrieve frame at curr position in the video and
    increments the position by 1. returns None if no frames are left to
    be read
    '''
    pass

  def read_frame(self):
    return self.retrieve_frame()

  def frame_at_idx(self, idx):
    self.seek_to_frame(idx)
    return self.read_frame()

  def frame_at_time(self, time):
    self.seek_to_time(time)
    return self.read_frame()

  def frame_generator(self):
    '''return a generator that yields frames starting at 0 index'''
    self.seek_to_frame(0)
    while True:
      frame = self.read_frame()
      if frame is None:
        break
      yield frame

  def normalize_frame(self, frame):
    '''validate and convert frame to numpy.ndarray of shape
    (w,h,channels) with bgr channels of type np.uint8 if necessary.
    '''
    if frame is None:
      return None
    if frame.dtype is not np.dtype('uint8'):
      frame = frame.astype(np.uint8, copy=False)
    return frame

  @abc.abstractproperty
  def num_frames():
    pass

  @abc.abstractproperty
  def duration():
    '''duration is in milliseconds'''
    pass

  @abc.abstractmethod
  def update_position_info():
    '''update frame index and time position'''
    pass

  @property
  def curr_frame_idx(self):
    self.update_position_info()
    return self._curr_frame_idx

  @curr_frame_idx.setter
  def curr_frame_idx(self, val):
    self._curr_frame_idx = val

  @property
  def curr_time_pos(self):
    '''time is in milliseconds'''
    self.update_position_info()
    return self._curr_time_pos

  @curr_time_pos.setter
  def curr_time_pos(self, val):
    self._curr_time_pos = val


class OpenCvFrameSource(BaseFrameSource):
  '''a video source using the opencv api'''

  def __init__(self, video_path):
    super(OpenCvFrameSource, self).__init__()
    self.cap = cv2.VideoCapture(video_path)
    if self.cap is None or not self.cap.isOpened():
      raise RuntimeError(
          'unable to open video source: {}'.format(video_path))
    self._num_frames = self.cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)

  def update_position_info(self):
    self.curr_time_pos = self.cap.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
    self.curr_frame_idx = self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)

  @property
  def num_frames(self):
    return int(self._num_frames)

  @property
  def duration(self):
    frame_rate = self.cap.get(cv2.cv.CV_CAP_PROP_FPS)
    dur_s = float(self._num_frames) / frame_rate
    dur_ms = dur_s * 1000.0
    return dur_ms

  def seek_to_frame(self, idx):
    if idx < 0 or idx >= self._num_frames:
      raise IndexError(
          'idx is out of frame range [0,{})'.format(self._num_frames))
    self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, idx)
    self.curr_frame_idx = idx

  def seek_to_time(self, time):
    if time < 0 or time > self.duration:
      raise IndexError(
          'time is out of video range [0,{}]'.format(self.duration))
    self.cap.set(cv2.cv.CV_CAP_PROP_POS_MSEC, time)

  def retrieve_frame(self):
    if self.curr_frame_idx >= self._num_frames:
      return None
    ret, frame = self.cap.read()
    if ret is False:
      raise RuntimeError(
          'unable to read a frame at idx: {}'.format(self.curr_frame_idx))
    return frame

  def __del__(self):
    self.cap.release()
