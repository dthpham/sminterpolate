# track and manage subregions in a sequence

import datetime

class VideoSequence(object):
    def __init__(self, dur, nfrs):
        self.dur = dur
        self.nfrs = nfrs
        self.subregions = []
        self.add_subregion(Subregion(0, dur, True))  # initial sub w/ skip

    def relative_pos(self, time):
        return max(0.0, min(float(time) / self.dur, 1.0))  # [0,1]

    def nearest_fr(self, time):
        fr_idx = self.relative_pos(time) * self.nfrs
        fr_idx = int(fr_idx)
        return max(0, min(fr_idx, self.nfrs-1))  # [0,self.nfrs-1]

    def add_subregion(self, sub):
        sub.fa = self.nearest_fr(sub.ta)
        sub.fb = self.nearest_fr(sub.tb)
        # check bounds
        if sub.fa < 0 or \
           sub.fb < 0 or \
           sub.ta < 0 or \
           sub.tb < 0 or \
           sub.fa > self.nfrs-1 \
           or sub.fb > self.nfrs-1 or \
           sub.ta > self.dur or \
           sub.tb > self.dur or \
           sub.fa > sub.fb:
            raise RuntimeError
        if len(self.subregions) == 0 and sub.skip:  # initial sub
            self.subregions.append(sub)
            return
        temp_subs = []
        for s in self.subregions:
            if not s.skip:
                temp_subs.append(s)
        temp_subs.append(sub)
        temp_subs.sort(key=lambda x: (x.fb, x.fa), reverse=False)
        self.subregions = temp_subs
        # add skips
        temp_subs = []
        seq_len = len(self.subregions)
        i = 0
        while i < seq_len:
            curr = self.subregions[i]
            if i == 0 and curr.ta != 0:  # beginning to first sub
                new_sub = Subregion(0, curr.ta, True)
                new_sub.fa = 0
                new_sub.fb = curr.fa
                temp_subs.append(new_sub)
            temp_subs.append(curr)
            if i+1 == seq_len:  # last sub to end
                if curr.tb != self.dur:
                    new_sub = Subregion(curr.tb, self.dur, True)
                    new_sub.fa = curr.fb
                    new_sub.fb = self.nfrs-1
                    temp_subs.append(new_sub)
                break
            next = self.subregions[i+1]
            if curr.tb != next.ta:  # between subs
                new_sub = Subregion(curr.tb, next.ta, True)
                new_sub.fa = curr.fb
                new_sub.fb = next.fa
                temp_subs.append(new_sub)
            i += 1
        self.subregions = temp_subs
        # TODO: walk through and de-overlap / update fr positions?
        # TODO: warn if intersecting?

    def __str__(self):
        s = 'Sequence: dur={}, nfrs={} [\n'.format(
            str(datetime.timedelta(seconds=self.dur/1000.0)),
            self.nfrs)
        for i, sub in enumerate(self.subregions):
            s += '  {} {}\n'.format('{0:02d}'.format(i), sub)
        s += ']'
        return s

class Subregion(object):
    def __init__(self, ta, tb, skip=False):  # skip = can make subs inside
        if ta > tb or \
           ta < 0 or \
           tb < 0:
            raise AttributeError
        self.ta = ta
        self.tb = tb
        self.fa = 0
        self.fb = 0
        self.target_spd = None
        self.target_dur = None
        self.target_fps = None
        self.skip = skip
        if skip:
            self.target_spd = 1

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
        s = 'Sub: {}-{} [{}-{}]'.format(
            str(datetime.timedelta(seconds=self.ta/1000.0)),
            str(datetime.timedelta(seconds=self.tb/1000.0)),
            self.fa,
            self.fb)
        if self.skip:
            s += ' (skip)'
        return s
