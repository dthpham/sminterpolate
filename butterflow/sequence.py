# -*- coding: utf-8 -*-

import datetime


class VideoSequence(object):
    def __init__(self, duration, frames):
        self.duration = duration
        self.frames = frames
        self.subregions = []
        self.add_subregion(Subregion(0, duration, skip=True))

    def relative_pos(self, time):
        return max(0.0, min(float(time) / self.duration, 1.0))

    def nearest_fr(self, time):
        return max(0, min(int(self.relative_pos(time) * self.frames),
                          self.frames-1))

    def add_subregion(self, sub):
        duration_string = str(datetime.timedelta(seconds=self.duration/1000.0))
        if sub.ta > self.duration:
            raise ValueError("{} > duration={}".format(sub.ta, duration_string))
        if sub.tb > self.duration:
            raise ValueError("{} > duration={}".format(sub.tb, duration_string))
        sub.fa = self.nearest_fr(sub.ta)
        sub.fb = self.nearest_fr(sub.tb)
        if len(self.subregions) == 0 and sub.skip:
            self.subregions.append(sub)
            return
        temp_subs = []
        for s in self.subregions:
            if not s.skip:
                temp_subs.append(s)
        temp_subs.append(sub)
        temp_subs.sort(key=lambda x: (x.fb, x.fa), reverse=False)
        self.subregions = temp_subs
        temp_subs = []
        seq_len = len(self.subregions)
        i = 0
        while i < seq_len:
            curr = self.subregions[i]
            if i == 0 and curr.ta != 0:  # beginning to first sub
                try:
                    new_sub = Subregion(0, curr.ta, skip=True)
                except AttributeError as e:
                    raise AttributeError("Bad internal subregion ({})".format(e))
                new_sub.fa = 0
                new_sub.fb = curr.fa
                temp_subs.append(new_sub)
            temp_subs.append(curr)
            if i+1 == seq_len:  # last sub to end
                if curr.tb != self.duration:
                    try:
                        new_sub = Subregion(curr.tb, self.duration, skip=True)
                    except AttributeError as e:
                        raise AttributeError("Bad internal subregion ({})".format(e))
                    new_sub.fa = curr.fb
                    new_sub.fb = self.frames-1
                    temp_subs.append(new_sub)
                break
            next = self.subregions[i+1]
            if curr.tb != next.ta:  # between subs
                try:
                    new_sub = Subregion(curr.tb, next.ta, skip=True)
                except AttributeError as e:
                    raise AttributeError("Bad internal subregion ({})".format(e))
                new_sub.fa = curr.fb
                new_sub.fb = next.fa
                temp_subs.append(new_sub)
            i += 1
        self.subregions = temp_subs

    def __str__(self):
        s = 'Sequence: Duration={} ({:.2f}s), Frames={}\n'.format(
            str(datetime.timedelta(seconds=self.duration/1000.0)),
            self.duration/1000,
            self.frames)
        for i, sub in enumerate(self.subregions):
            s += 'Subregion ({}): {}'.format('{}'.format(i), sub)
            if i < len(self.subregions)-1:
                s += '\n'
        return s


class Subregion(object):
    def __init__(self, ta, tb, skip=False):
        if ta > tb:
            raise AttributeError("a>b")
        if ta < 0:
            raise AttributeError("a<0")
        if tb < 0:
            raise AttributeError("a<0")
        self.ta = ta
        self.tb = tb
        self.fa = 0
        self.fb = 0
        self.target_spd = None
        self.target_dur = None
        self.target_fps = None
        self.skip = skip
        if skip:
            self.target_spd = 1.0

    def intersects(self, o):
        # a subregion intersects with another if either end, in terms of time
        # and frame, falls within each others ranges or when one subregion
        # covers, or is enveloped by another
        return self.time_intersects(o) or self.fr_intersects(o)

    def time_intersects(self, o):
        if self is o or \
           self.ta == o.ta and self.tb == o.tb or \
           self.ta >  o.ta and self.ta <  o.tb or \
           self.tb >  o.ta and self.tb <  o.tb or \
           self.ta <  o.ta and self.tb >  o.tb:
            return True
        else:
            return False

    def fr_intersects(self, o):
        if self is o or \
           self.fa == o.fa and self.fb == o.fb or \
           self.fa >  o.fa and self.fa <  o.fb or \
           self.fb >  o.fa and self.fb <  o.fb or \
           self.fa <  o.fa and self.fb >  o.fb:
            return True
        else:
            return False

    def __str__(self):
        s = 'Time={}-{} Frames={}-{} Speed={},Duration={},Fps={}'.format(
            str(datetime.timedelta(seconds=self.ta/1000.0)),
            str(datetime.timedelta(seconds=self.tb/1000.0)),
            self.fa,
            self.fb,
            self.target_spd if self.target_spd is not None else '?',
            self.target_dur if self.target_dur is not None else '?',
            self.target_fps if self.target_fps is not None else '?')
        if self.skip:
            s += ' (autogenerated subregion)'
        return s
