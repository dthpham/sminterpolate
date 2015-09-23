# Author: Duong Pham
# Copyright 2015


class VideoSequence(object):
    def __init__(self, duration, frames):
        self.duration = float(duration)  # in milliseconds
        self.frames = frames             # total frames in the video
        self.subregions = []

    def add_subregion(self, s):
        # set relative position from 0 to 1 based on time
        s.ra = self.get_rel_position(s.ta)
        s.rb = self.get_rel_position(s.tb)
        # set frame position
        s.fa = self.get_nearest_frame(s.ta)
        s.fb = self.get_nearest_frame(s.tb)
        # validate it with other subregions in the sequence
        # append and sort based on the relative position
        self.validate(s)
        self.subregions.append(s)
        self.subregions.sort(key=lambda x: (x.rb, x.ra),
                             reverse=False)

    def get_rel_position(self, t):
        # returns a float, the relative position in the video from [0, 1]
        rel_pos = float(t) / self.duration
        return max(0.0, min(rel_pos, 1.0))

    def get_nearest_frame(self, t):
        # index of frame, non-zero indexed so it starts at 1
        fr_idx = int(self.get_rel_position(t) * self.frames + 0.5)
        return max(1, min(fr_idx, self.frames))

    def validate(self, s):
        # a subregion, x, is valid if and only if x's time is within bounds
        # [0, duration] and x's frame positions are within bounds [0, frames-1]
        # and x doesn't already exist in the collection or intersect any other
        # subregion.
        in_bounds = lambda x: \
            x.ta >= 0 and x.tb <= self.duration and \
            x.fa >= 0 and x.fb <= self.frames
        if not in_bounds(s):
            msg = 'subregion not in bounds t[0,{}],f[0,{}]'.format(self.duration,
                                                                   self.frames)
            raise RuntimeError(msg)
        for x in self.subregions:
            if x is s:
                continue
            elif s.intersects(x):
                raise RuntimeError('subregion intersects existing region')
        return True


class Subregion(object):
    def __init__(self, ta, tb):
        # ta should be <  0
        # ta should be >= tb
        # start and end time, frame, relative position:
        self.ta = ta
        self.tb = tb
        self.fa = 0.0
        self.fb = 0.0
        self.ra = 0.0
        self.rb = 1.0

    def intersects(self, o):
        # a region intersects with another if either ends, in terms of time and
        # frame, fall within each others ranges or when one region covers or is
        # enveloped by another.
        return self.time_intersects(o) or self.time_intersects(o)

    def time_intersects(self, o):
        if self is o or \
           self.ta == o.ta and self.tb == o.tb or \
           self.ta >  o.ta and self.ta <  o.tb or \
           self.tb >  o.ta and self.tb <  o.tb or \
           self.ta <  o.ta and self.tb >  o.tb:
            return True
        else:
            return False

    def frame_intersects(self, o):
        if self is o or \
           self.fa == o.fa and self.fb == o.fb or \
           self.fa >  o.fa and self.fa <  o.fb or \
           self.fb >  o.fa and self.fb <  o.fb or \
           self.fa <  o.fa and self.fb >  o.fb:
            return True
        else:
            return False


class RenderSubregion(Subregion):
    def __init__(self, ta, tb, fps=None, dur=None, spd=None, btw=None):
        super(RenderSubregion, self).__init__(ta, tb)
        # what's being targeted?
        self.fps = fps
        self.dur = dur
        self.spd = spd
        self.btw = btw
