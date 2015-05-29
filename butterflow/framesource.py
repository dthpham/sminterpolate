from cv2 import cv, VideoCapture


class FrameSource(object):
    def __init__(self, video_path):
        self.capture = VideoCapture(video_path)
        if self.capture is None or not self.capture.isOpened():
            raise RuntimeError(
                'unable to open video source: {}'.format(video_path))
        self.frames = int(self.capture.get(cv.CV_CAP_PROP_FRAME_COUNT))
        self.duration = float(self.frames) / \
            self.capture.get(cv.CV_CAP_PROP_FPS) * 1000.0
        self.time_position = 0.0
        self.index = 0

    def update_position(self):
        self.time_position = self.capture.get(cv.CV_CAP_PROP_POS_MSEC)
        self.index = self.capture.get(cv.CV_CAP_PROP_POS_FRAMES)

    def seek_to_frame(self, idx):
        if idx < 0 or idx >= self.frames:
            raise IndexError(
                'idx is out of frame range [0,{})'.format(self.frames))
        self.capture.set(cv.CV_CAP_PROP_POS_FRAMES, idx)
        self.update_position()

    def frame_at_idx(self, idx):
        self.seek_to_frame(idx)
        return self.read()

    def frame_at_time(self, t):
        self.seek_to_time(t)
        return self.read()

    def seek_to_time(self, t):
        if t < 0 or t > self.duration:
            raise IndexError(
                'time is out of video range [0,{}]'.format(self.duration))
        self.capture.set(cv.CV_CAP_PROP_POS_MSEC, t)
        self.update_position()

    def read(self):
        """returns None if there are not longer any frames to be read"""
        if self.index >= self.frames:
            return None
        rc, frame = self.capture.read()
        if rc is False:
            raise RuntimeError(
                'unable to read a frame at idx: {}'.format(self.index))
        else:
            self.update_position()
            return frame

    def __del__(self):
        self.capture.release()
