# Author: Duong Pham
# Copyright 2015

import cv2


class FrameSource(object):
    def __init__(self, path):
        # use opencv api as a frame source
        # i'd prefer if this was written in c and uses libav but this is
        # convienent and has proven to work
        self.path = path
        self.src = None  # videocapture object
        self.frames = 0
        self._idx = 0  # zero-based index of the frame to be read next

    def open(self):
        self.src = cv2.VideoCapture(self.path)  # open the file
        if not self.src.isOpened():
            raise RuntimeError('unable to open file')
        self.frames = int(self.src.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
        self.idx = 0

    def close(self):
        if self.src is not None:
            self.src.release()
        self.src = None

    @property
    def idx(self):
        return self.src.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)

    @idx.setter
    def idx(self, idx):
        self._idx = self.src.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, idx)

    def seek_to_frame(self, idx):
        # seek to frame that will be read next
        if idx < 0 or idx > self.frames - 1:
            msg = 'seeked out of frame range [0,%s]'.format(self.frames - 1)
            raise IndexError(msg)
        # do seek and updat the position
        self.src.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, idx)

    def read(self):
        # reads frame at `self.idx` and returns it
        # returns None if there are no longer any frames to be read
        # seek position +1 after the a successful read
        if self.idx < 0 or self.idx > self.frames - 1:
            return None
        rc, fr = self.src.read()
        if rc is not True:
            msg = 'unable to read frame at idx %s'.format(self.idx)
            raise RuntimeError(msg)
        return fr

    def __del__(self):
        # clean up in case the frame source was left open
        self.close()
