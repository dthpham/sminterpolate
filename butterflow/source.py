# Author: Duong Pham
# Copyright 2015

import cv2


class FrameSource(object):
    def __init__(self, path):
        # use opencv api as a frame source
        # i'd prefer if libav was the frame source and this was written in c
        # but this is simple and convienent enough, plus it's proven to work
        self.path = path
        self.src = None  # the videocapture object
        # the num of frames should be equal to the whatever
        # `avinfo.get_av_info` returns since several calculations in
        # `render.py` are based upon it
        self.frames = 0  # total num of frames
        self._idx = 0    # zero-based index of the frame to be read next

    def open(self):
        self.src = cv2.VideoCapture(self.path)  # open the file
        if not self.src.isOpened():
            raise RuntimeError('unable to open file')
        self.frames = int(self.src.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
        self.idx = 0  # will seek to the first frame

    def close(self):
        if self.src is not None:
            self.src.release()  # closes video file or capturing device
        self.src = None

    @property
    def idx(self):
        # videocapture will keep track of `idx` for us
        # return whatever it reports
        return self.src.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)

    @idx.setter
    def idx(self, idx):
        # setting `idx` will do a seek
        # TODO: do nothing if seeking to the current pos
        self._idx = self.src.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, idx)

    def seek_to_frame(self, idx):
        # seek to frame that will be read next
        if idx < 0 or idx > self.frames - 1:
            msg = 'seeked out of frame range [0,%s]'.format(self.frames - 1)
            raise IndexError(msg)
        # do seek, position will update automatically
        self.idx = idx

    def read(self):
        # reads frame at `self.idx` and returns it
        # returns `None` if there are no longer any frames to be read
        # seek position will +1 automatically after a successful read
        if self.idx < 0 or self.idx > self.frames - 1:
            return None
        rc, fr = self.src.read()
        if rc is not True:
            msg = 'unable to read frame at idx=%s'.format(self.idx)
            raise RuntimeError(msg)
        return fr

    def __del__(self):
        # clean up in case the frame source was left open
        # this could happen if the user does `ctr+c` when rendering
        self.close()
