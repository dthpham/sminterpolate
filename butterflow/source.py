# Author: Duong Pham
# Copyright 2015

import cv2


class FrameSource(object):
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        if self.cap is None:
            raise RuntimeError('unable to open video')
        if self.cap.isOpened():
            import logging
            log = logging.getLogger('butterflow')
            log.warning('capturing already initialized')
        # frames is used in app but duration is for debugging only
        self.frames = int(self.cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
        self.duration = self.frames * 1.0 / \
            self.cap.get(cv2.cv.CV_CAP_PROP_FPS) * 1000.0
        self.idx = 0  # index of the frame to be read, zero-indexed

    def update_pos(func):
        # decorator, update frame and time position in the video
        # should be added to every seek and read
        def wrapper(self, *args, **kwargs):
            fr = func(self, *args, **kwargs)
            if fr is not None:
                self.idx = self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)
            return fr
        return wrapper

    @update_pos
    def seek_to_frame(self, idx):
        if idx < 0 or idx > self.frames - 1:
            msg = 'seeked out of frame range f[0,%s]'.format(self.frames - 1)
            raise IndexError(msg)
        self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, idx)  # do seek
        # should always be successful if checked we were in bounds correctly
        return True

    @update_pos
    def read(self):
        # reads frame at `self.idx` and return it
        # returns None if there are not longer any frames to be read
        if self.idx > self.frames - 1:
            return None
        rc, fr = self.cap.read()
        if rc is True:
            return fr
        else:
            msg = 'unable to read frame at idx %s'.format(self.idx)
            raise RuntimeError(msg)

    def __del__(self):
        self.cap.release()
