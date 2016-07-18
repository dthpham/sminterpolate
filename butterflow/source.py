import cv2


class OpenCvFrameSource(object):
    def __init__(self, src):
        self.src = src
        self.capture = None
        self.frames = 0

    @property
    def idx(self):  # next fr to be read, zero-indexed
        return self.capture.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)

    def open(self):
        self.capture = cv2.VideoCapture(self.src)
        if not self.capture.isOpened():
            raise RuntimeError
        self.frames = int(self.capture.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))

    def close(self):
        if self.capture is not None:
            self.capture.release()
        self.capture = None

    def seek_to_fr(self, idx):
        if idx < 0 or idx > self.frames-1:
            raise IndexError
        # do seek, idx will +1 automatically
        if self.capture.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, idx) is not True:
            raise RuntimeError

    def read(self):
        # read fr at self.idx and return it, return None if there are no frames
        # available. seek pos will +1 automatically if successful
        if self.idx < 0 or self.idx > self.frames-1:
            return None
        success, fr = self.capture.read()
        if success is not True:  # can be False or None
            raise RuntimeError
        return fr

    def __del__(self):
        self.close()
