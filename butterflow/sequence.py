# Author: Duong Pham
# Copyright 2015


class VideoSequence(object):
    def __init__(self, duration, frames):
        self.duration = float(duration)  # in milliseconds
        self.frames = frames             # total frames in the video
        self.subregions = []  # only explicitly defined regions

    def add_subregion(self, s):
        # append to collection of subregions, sort based on frame position
        s.fa = self.nearest_frame(s.ta)
        s.fb = self.nearest_frame(s.tb)
        self.validate(s)
        self.subregions.append(s)
        self.subregions.sort(key=lambda x: (x.fb, x.fa),
                             reverse=False)

    def relative_position(self, t):
        # returns the relative position in video from [0,1] given a time; a
        # fraction of `duration`
        rel_pos = float(t) / self.duration
        return max(0.0, min(rel_pos, 1.0))

    def nearest_frame(self, t):
        # returns the nearest zero-indexed frame, rounded upwards, from
        # [0, frames-1] given a time
        fr_idx = int(self.relative_position(t) * self.frames + 0.5) - 1
        return max(0, min(fr_idx, self.frames - 1))

    def validate(self, s):
        # a subregion, x, is valid if and only if x's time is within bounds
        # [0, duration] and x's frame positions are within bounds [0, frames-1]
        # and x doesn't already exist in the collection of subregions or
        # intersect any other subregion
        in_bounds = lambda x: \
            x.ta >= 0 and x.tb <= self.duration and \
            x.fa >= 0 and x.fb <= self.frames - 1
        if not in_bounds(s):
            raise RuntimeError('not in time bounds')
        for x in self.subregions:
            if x is s:
                continue
            elif s.intersects(x):
                raise RuntimeError('regions overlap')
        return True


class Subregion(object):
    def __init__(self, ta, tb):
        # values aren't bounded by anything
        self.ta = ta
        self.tb = tb
        self.fa = 0.0
        self.fb = 0.0

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
    def __init__(self, ta, tb, fps=None, dur=None, spd=None):
        super(RenderSubregion, self).__init__(ta, tb)
        # what's being targeted?
        self.fps = fps
        self.dur = dur
        self.spd = spd
