# use opencv's video api to get frs from a video

import cv2

class OpenCvFrameSource(object):
    def __init__(self, src):
        self.src = src
        self.capture = None
        self.nfrs = 0

    @property
    def idx(self):  # next fr to be read, zero-indexed
        return self.capture.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)

    def open(self):
        self.capture = cv2.VideoCapture(self.src)
        if not self.capture.isOpened():
            raise RuntimeError
        self.nfrs = int(self.capture.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))

    def close(self):
        if self.capture is not None:
            self.capture.release()
        self.capture = None

    def seek_to_fr(self, idx):
        if idx < 0 or idx > self.nfrs-1:
            raise IndexError
        # do seek, idx will +1 automatically
        if self.capture.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, idx) is not True:
            raise RuntimeError

    def read(self):
        # read fr at self.idx and return it, return None if there are no frs
        # available. seek pos will +1 automatically if successful
        if self.idx < 0 or self.idx > self.nfrs-1:
            return None
        success, fr = self.capture.read()
        if success is not True:  # can be False or None
            raise RuntimeError
        return fr

    def __del__(self):
        # clean up in case the fr source was left open. this could happen if
        # the user does ctr+c while rendering
        self.close()
