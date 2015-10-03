# Author: Duong Pham
# Copyright 2015

import cv2

class FrameSource(object):
    def __init__(self, path):
        # uses opencv video api as a frame source
        self.path = path
        self.src = None  # the `videocapture` object
        self.frames = 0

    def open(self):
        self.src = cv2.VideoCapture(self.path)
        if not self.src.isOpened():
            raise RuntimeError('unable to open file')
        # the num of frames should be equal to `avinfo.get_av_info.frames`
        # because several calculations in `render.py` are based upon it
        self.frames = int(self.src.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))

    def close(self):
        if self.src is not None:
            self.src.release()  # will close the video file
        self.src = None

    @property
    def idx(self):
        # zero-based index of the frame to be read next
        return self.src.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)

    def seek_to_frame(self, idx):
        if idx < 0 or idx > self.frames - 1:
            msg = 'seeked out of frame range [0,%s]'.format(self.frames - 1)
            raise IndexError(msg)
        # do seek, position will +1 automatically
        rc = self.src.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, idx)
        if rc is not True:
            msg = 'unable to seek to frame at idx={}'.format(idx)
            raise RuntimeError(msg)

    def read(self):
        # reads frame at `self.idx` and returns it. returns `None` if there are
        # no frames available. seek position will +1 automatically after a
        # successful read
        if self.idx < 0 or self.idx > self.frames - 1:
            return None
        rc, fr = self.src.read()
        if rc is not True:
            msg = 'unable to read frame at idx=%s'.format(self.idx)
            raise RuntimeError(msg)
        return fr

    def __del__(self):
        # clean up in case the frame source was left open. this could happen if
        # the user does `ctr+c` when rendering
        self.close()
