# -*- coding: utf-8 -*-

# Author: Duong Pham
# Copyright 2015

import os
import math
import shutil
import subprocess
import cv2
import numpy as np
from butterflow.draw import draw_progress_bar, draw_debug_text
from butterflow.settings import default as settings
from butterflow.source import FrameSource
from butterflow.sequence import VideoSequence, RenderSubregion
from butterflow.mux import extract_audio, mux, concat_files

import logging
log = logging.getLogger('butterflow')


class Renderer(object):
    def __init__(
        self, dst_path, vid_info, vid_seq, playback_rate,
        flow_func=settings['flow_func'],
        interpolate_func=settings['interpolate_func'],
        w=None, h=None, lossless=False, trim=False, show_preview=True,
        add_info=False, text_type=settings['text_type'],
        av_loglevel=settings['av_loglevel'],
        enc_loglevel=settings['enc_loglevel'], flow_kwargs=None, mux=False):
        # user args
        self.dst_path         = dst_path      # path to write the render
        self.vid_info         = vid_info      # information from avinfo
        self.vid_seq          = vid_seq       # passed using `-s`
        self.playback_rate    = float(playback_rate)
        self.flow_func        = flow_func
        self.interpolate_func = interpolate_func
        self.w                = w
        self.h                = h
        self.lossless         = lossless      # encode losslessly?
        self.trim             = trim          # trim extra subregion?
        self.show_preview     = show_preview  # show preview window?
        self.add_info         = add_info      # embed debug info?
        self.text_type        = text_type     # overlay text type
        self.av_loglevel      = av_loglevel   # ffmpeg loglevel
        self.enc_loglevel     = enc_loglevel  # x264, x265 loglevel
        self.flow_kwargs      = flow_kwargs   # will pass to draw_debug_text
        self.mux              = mux           # mux?
        self.render_pipe      = None
        # keep track of progress
        self.tot_frs_wrt      = 0             # total frames written
        self.tot_tgt_frs      = 0
        self.tot_src_frs      = 0             # total source frames read
        self.tot_frs_int      = 0             # total interpolated
        self.tot_frs_dup      = 0
        self.tot_frs_drp      = 0
        self.subs_to_render   = 0
        self.curr_sub_idx     = 0             # region being worked on
        # choose the best scaler
        new_res = w * h
        src_res = vid_info['w'] * vid_info['h']
        if new_res == src_res:
            self.scaler = None
        elif new_res < src_res:
            self.scaler = settings['scaler_dn']
        else:
            self.scaler = settings['scaler_up']
        # set the window title
        filename = os.path.basename(vid_info['path'])
        self.window_title = '{} - Butterflow'.format(filename)

    def make_pipe(self, dst_path, rate):
        vf = []
        vf.append('format=yuv420p')
        # keep the original display aspect ratio
        # see: https://ffmpeg.org/ffmpeg-filters.html#setdar_002c-setsar
        if self.scaler is None:
            vf.append('setdar={}:{}'.format(self.vid_info['dar_n'],
                                            self.vid_info['dar_d']))
        call = [
            settings['avutil'],
            '-loglevel', self.av_loglevel,
            '-y',
            '-threads', '0',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', '{}x{}'.format(self.w, self.h),
            '-r', str(rate),
            '-i', '-',
            '-map_metadata', '-1',
            '-map_chapters', '-1',
            '-vf', ','.join(vf),
            '-r', str(rate),
            '-an',
            '-sn',
            '-c:v', settings['cv'],
            '-preset', settings['preset']]
        if settings['cv'] == 'libx264':
            quality = ['-crf', str(settings['crf'])]
            # -qp 0 is recommended over -crf for lossless
            # See: https://trac.ffmpeg.org/wiki/Encode/H.264#LosslessH.264
            if self.lossless:
                quality = ['-qp', '0']
            call.extend(quality)
            call.extend(['-level', '4.2'])
        params = []
        call.extend(['-{}-params'.format(settings['cv'].replace('lib', ''))])
        params.append('log-level={}'.format(self.enc_loglevel))
        if settings['cv'] == 'libx265':
            quality = 'crf={}'.format(settings['crf'])
            if self.lossless:
                # ffmpeg doesn't pass -x265-params to x265 correctly, must
                # provide keys for every single value until fixed
                # See: https://trac.ffmpeg.org/ticket/4284
                quality = 'lossless=1'
            params.append(quality)
        if len(params) > 0:
            call.extend([':'.join(params)])
        call.extend([dst_path])
        pipe = subprocess.Popen(
            call,
            stdin=subprocess.PIPE
        )
        if pipe == 1:
            raise RuntimeError('could not create pipe')
        return pipe

    def close_pipe(self, pipe):
        # flush does not necessarily write the file's data to disk. Use
        # flush followed by os.fsync to ensure this behavior
        if pipe is not None and not pipe.stdin.closed:
            pipe.stdin.flush()
            pipe.stdin.close()
            pipe.wait()

    def write_frame_to_pipe(self, pipe, frame):
        try:
            pipe.stdin.write(bytes(frame.data))
        except Exception:
            log.error('Writing frame to pipe failed:', exc_info=True)

    def render_subregion(self, frame_src, subregion):
        log.debug('Working on subregion: %s', self.curr_sub_idx + 1)

        fa = subregion.fa
        fb = subregion.fb
        ta = subregion.ta
        tb = subregion.tb

        reg_len = (fb - fa) + 1  # num of frames in the region
        reg_dur = (tb - ta) / 1000.0  # duration of subregion in seconds

        tgt_frs = 0  # num of frames we're targeting to render

        # only one of these needs to be set to calculate tgt_frames
        if subregion.dur:
            tgt_frs = int(self.playback_rate *
                          (subregion.dur / 1000.0))
        elif subregion.fps:
            tgt_frs = int(subregion.fps * reg_dur)
        elif subregion.spd:
            tgt_frs = int(self.playback_rate * reg_dur *
                          (1 / subregion.spd))
        elif subregion.btw:
            tgt_frs = int(reg_len + ((reg_len - 1) * subregion.btw))

        tgt_frs = max(0, tgt_frs)
        # the make factor or inverse time step
        int_each_go = float(tgt_frs) / max(1, (reg_len - 1))

        # stop a division by zero error when only a single frame needs to be
        # written
        if int_each_go == 0:
            tgt_frs = 1

        self.tot_tgt_frs += tgt_frs

        # TODO: overcompensate for frames?
        # int_each_go = math.ceil(int_each_go)

        int_each_go = int(int_each_go)

        pairs = reg_len - 1
        if pairs >= 1:
            will_make = (int_each_go * pairs) + pairs
        else:
            # no pairs available. will only add src frame to to_wrt
            will_make = 1
        extra_frs = will_make - tgt_frs

        # frames will need to be dropped or duped based on how many
        # frames are expected to be generated. this includes source and
        # interpolated frames
        drp_every = 0
        if extra_frs > 0:
            drp_every = will_make / math.fabs(extra_frs)

        dup_every = 0
        if extra_frs < 0:
            dup_every = will_make / math.fabs(extra_frs)

        log.debug('fa: %s', fa)
        log.debug('fb: %s', fb)
        log.debug('ta: %s', ta)
        log.debug('tb: %s', tb)
        log.debug('reg_dur: %s', reg_dur * 1000.0)
        log.debug('reg_len: %s', reg_len)
        log.debug('tgt_fps: %s', subregion.fps)
        log.debug('tgt_dur: %s', subregion.dur)
        with np.errstate(divide='ignore', invalid='ignore'):
            s = subregion.spd
            if subregion.spd is None:
                s = 0
            log.debug('tgt_spd: %s %.2gx', subregion.spd,
                      np.divide(1, s))
        log.debug('tgt_btw: %s', subregion.btw)
        log.debug('tgt_frs: %s', tgt_frs)
        sub_div = int_each_go + 1
        ts = []
        for x in range(int_each_go):
            y = max(0.0, min(1.0, (1.0 / sub_div) * (x + 1)))
            y = '{:.2f}'.format(y)
            ts.append(y)
        if len(ts) > 0:
            log.debug('ts: %s..%s', ts[0], ts[-1])

        log.debug('int_each_go: %s', int_each_go)
        log.debug('wr_per_pair: %s', int_each_go + 1)  # +1 because of fr_1
        log.debug('pairs: %s', pairs)
        log.debug('will_make: %s', will_make)
        log.debug('extra_frs: %s', extra_frs)
        log.debug('dup_every: %s', dup_every)
        log.debug('drp_every: %s', drp_every)

        est_dur = tgt_frs / self.playback_rate
        log.debug('est_dur: %s', est_dur)

        # audio may drift because of the change in which frames are rendered in
        # relation to the source video this is used for debugging:
        pot_aud_drift = extra_frs / self.playback_rate
        log.debug('pot_aud_drift: %s', pot_aud_drift)

        # keep track of progress in this subregion
        src_gen = 0  # num of source frames seen
        frs_int = 0  # num of frames interpolated
        frs_src_drp = 0  # num of source frames dropped
        frs_int_drp = 0  # num of interpolated frames dropped
        wrk_idx = 0  # idx in the subregion being worked on
        frs_wrt = 0  # num of frames written in this subregion
        frs_dup = 0  # num of frames duped
        frs_drp = 0  # num of frames dropped
        fin_run = False  # is this the final run?
        frs_fin_dup = 0  # num of frames duped on the final run
        runs = 0  # num of runs through the loop

        # frames are zero based indexed
        fa_idx = fa - 1   # seek pos of the frame in the video

        fr_1 = None
        frame_src.seek_to_frame(fa_idx)
        # log.debug('seek: %s', frame_src.idx + 1)  # seek pos of first frame
        # log.debug('read: %s', frame_src.idx + 1)  # next frame to be read
        fr_2 = frame_src.read()       # first frame in the region

        # scale down now but wait after drawing on the frame before scaling up
        if self.scaler == settings['scaler_dn']:
            fr_2 = cv2.resize(fr_2, (self.w, self.h),
                              interpolation=self.scaler)
        src_gen += 1
        if fa == fb or tgt_frs == 1:
            # only 1 frame expected. run through the main loop once
            fin_run = True
            runs = 1
        else:
            # at least one frame pair is available. num of runs is equal to the
            # the total number of frames in the region - 1. range will run
            # from [0,runs)
            frame_src.seek_to_frame(fa_idx + 1)  # seek to the next frame
            # log.debug('seek: %s', frame_src.idx + 1)
            runs = reg_len

        log.debug('wrt_one: %s', fin_run)  # only write 1 frame
        log.debug('runs: %s', runs)

        for run_idx in range(0, runs):
            # which frame in the video is being worked on
            pair_a = fa_idx + run_idx + 1
            pair_b = pair_a + 1 if run_idx + 1 < runs else pair_a

            # if working on the last frame, write it out because we cant
            # interpolate without a pair.
            if run_idx >= runs - 1:
                fin_run = True

            frs_to_wrt = []  # hold frames to be written
            fr_1 = fr_2  # reference to prev fr saves a seek & read

            if fin_run:
                frs_to_wrt.append((fr_1, 'source', 1))
            else:
                # begin interpolating frames between pairs
                # the frame being read should always be valid otherwise break
                try:
                    # log.debug('read: %s', frame_src.idx + 1)
                    fr_2 = frame_src.read()
                    src_gen += 1
                except Exception:
                    log.error('Could not read frame:', exc_info=True)
                    break
                if fr_2 is None:
                    break
                elif self.scaler == settings['scaler_dn']:
                    fr_2 = cv2.resize(fr_2, (self.w, self.h),
                                      interpolation=self.scaler)

                fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
                fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)

                fu, fv = self.flow_func(fr_1_gr, fr_2_gr)
                bu, bv = self.flow_func(fr_2_gr, fr_1_gr)

                fr_1_32 = np.float32(fr_1) * 1/255.0
                fr_2_32 = np.float32(fr_2) * 1/255.0

                will_wrt = True  # frames will be written?

                # look ahead to see if frames will be dropped
                # compensate by lowering the num of frames to be interpolated
                cmp_int_each_go = int_each_go    # compensated int_each_go
                w_drp = []                       # frames that would be dropped
                tmp_wrk_idx = wrk_idx - 1        # zero indexed
                for x in range(1 + int_each_go):  # 1 real + interpolated frame
                    tmp_wrk_idx += 1
                    if drp_every > 0:
                        if math.fmod(tmp_wrk_idx, drp_every) < 1.0:
                            w_drp.append(x + 1)
                n_drp = len(w_drp)
                # warn if a src frame was going to be dropped
                log_msg = log.debug
                if 1 in w_drp:
                    log_msg = log.warning
                # start compensating
                if n_drp > 0:
                    # can compensate by reducing num of frames to be
                    # interpolated since they are available
                    if n_drp <= int_each_go:
                        cmp_int_each_go -= n_drp
                    else:
                        # can't compensate using interpolated frames alone
                        # will have to drop the source frame. nothing will be
                        # written
                        will_wrt = False
                    log_msg('w_drp: %3s,%3s,%2s %s,-%s',
                            pair_a,
                            pair_b,
                            ','.join([str(x) for x in w_drp]),
                            cmp_int_each_go,
                            n_drp)
                    if not will_wrt:
                        # nothing will be written this go
                        wrk_idx += 1  # still have to increment the work index
                        log.warning('will_wrt: %s', will_wrt)
                        self.tot_frs_drp += 1

                if will_wrt:
                    int_frs = self.interpolate_func(
                        fr_1_32, fr_2_32, fu, fv, bu, bv, cmp_int_each_go)

                    if len(int_frs) != cmp_int_each_go:
                        log.warning('unexpected frs interpolated: act=%s '
                                    'est=%s',
                                    len(int_frs), cmp_int_each_go)

                    frs_int += len(int_frs)
                    frs_to_wrt.append((fr_1, 'source', 1))
                    for x, fr in enumerate(int_frs):
                        frs_to_wrt.append((fr, 'interpolated', x + 2))

            for (fr, fr_type, btw_idx) in frs_to_wrt:
                wrk_idx += 1
                wrts_needed = 1
                # duping should never happen unless the subregion being worked
                # on only has one frame
                if dup_every > 0:
                    if math.fmod(wrk_idx, dup_every) < 1.0:
                        frs_dup += 1
                        wrts_needed = 2
                        log.warning('dup: %s,%s,%s 2x',
                                    pair_a,
                                    pair_b,
                                    btw_idx)
                if fin_run:
                    wrts_needed = (tgt_frs - frs_wrt)
                    frs_fin_dup = wrts_needed - 1
                    log.debug('fin_dup: %s,%s,%s wrts=%sx',
                              pair_a,
                              pair_b,
                              btw_idx,
                              wrts_needed)
                    # final frame should be dropped if needed
                    if drp_every > 0:
                        if math.fmod(wrk_idx, drp_every) < 1.0:
                            log.warning('drp last frame')
                            self.tot_frs_drp += 1
                            continue

                for wrt_idx in range(wrts_needed):
                    frs_wrt += 1
                    if wrt_idx == 0:
                        if fr_type == 'source':
                            self.tot_src_frs += 1
                        else:
                            self.tot_frs_int += 1
                    else:
                        self.tot_frs_dup += 1
                    self.tot_frs_wrt += 1
                    if self.scaler == settings['scaler_up']:
                        fr = cv2.resize(fr, (self.w, self.h),
                                        interpolation=self.scaler)
                    if self.add_info:
                        draw_debug_text(fr,
                                        self.text_type,
                                        self.playback_rate,
                                        self.flow_kwargs,
                                        self.tot_frs_wrt,
                                        pair_a,
                                        pair_b,
                                        btw_idx,
                                        fr_type,
                                        wrt_idx > 0,
                                        tgt_frs,
                                        frs_wrt,
                                        subregion,
                                        self.curr_sub_idx,
                                        self.subs_to_render,
                                        drp_every,
                                        dup_every,
                                        src_gen,
                                        frs_int,
                                        frs_drp,
                                        frs_dup)
                    # show the frame on the screen
                    if self.show_preview:
                        fr_to_show = fr.copy()
                        draw_progress_bar(fr_to_show, float(frs_wrt) / tgt_frs)
                        cv2.imshow(self.window_title, np.asarray(fr_to_show))
                        # every imshow call should be followed by waitKey to
                        # display the image for x milliseconds, otherwise it
                        # won't display the image
                        cv2.waitKey(settings['imshow_ms'])
                    # send the frame to the pipe
                    self.write_frame_to_pipe(self.render_pipe, fr)
                    # log.debug('wrt: %s,%s,%s (%s)', pair_a, pair_b, btw_idx,
                    #           self.tot_frs_wrt)

        # finished encoding
        act_aud_drift = float(tgt_frs - frs_wrt) / self.playback_rate
        log.debug('act_aud_drift: %s', act_aud_drift)

        log.debug('src_gen: %s', src_gen)
        log.debug('frs_int: %s', frs_int)
        log.debug('frs_drp: %s', frs_drp)

        with np.errstate(divide='ignore', invalid='ignore'):
            log.debug('frs_src_drp: %s %.2f', frs_src_drp,
                      np.divide(float(frs_src_drp), frs_drp))
            log.debug('frs_int_drp: %s %.2f', frs_int_drp,
                      np.divide(float(frs_int_drp), frs_drp))

            # 1 - (frames dropped : real and interpolated frames)
            efficiency = 1 - (frs_drp * 1.0 / (src_gen + frs_int))
            log.debug('efficiency: %.2f%%', efficiency * 100.0)

        log.debug('frs_dup: %s', frs_dup,)
        log.debug('frs_fin_dup: %s', frs_fin_dup)

        act_dur = frs_wrt / self.playback_rate
        log.debug('act_dur: %s', act_dur)

        if not np.isclose(act_dur, est_dur, rtol=1e-03):
            log.warning('unexpected dur: est_dur=%s act_dur=%s',
                        est_dur, act_dur)

        if tgt_frs == 0:
            wrt_ratio = 0
        else:
            wrt_ratio = float(frs_wrt) / tgt_frs
        log_msg = log.debug
        if frs_wrt != tgt_frs:
            log_msg = log.warning
        log_msg('wrt_ratio: {}/{}, {:.2f}%'.format(
            frs_wrt, tgt_frs, wrt_ratio * 100))

    def get_renderable_sequence(self):
        # this method will fill holes in the sequence with dummy subregions
        dur = self.vid_info['duration']
        frs = self.vid_info['frames']
        new_subregions = []

        if self.vid_seq.subregions is None or \
                len(self.vid_seq.subregions) == 0:
            # make a subregion from 0 to vid duration if there are no regions
            # in the video sequence. only the framerate could be changing
            fa, ta = (0, 0)
            fb, tb = (frs, dur)
            s = RenderSubregion(ta, tb)
            s.fa = fa
            s.fb = fb
            s.fps = self.playback_rate
            s.dur = tb - ta
            s.spd = 1.0
            tgt_frs = int(self.playback_rate * (dur / 1000.0))
            # use max to avoid division by zero error
            s.btw = (tgt_frs - frs) * 1.0 / max(1, frs - 1)
            setattr(s, 'trim', False)
            new_subregions.append(s)
        else:
            # create placeholder/dummy subregions that fill holes in the video
            # sequence where subregions were not explicity specified
            cut_points = set([])
            # add start and end of video cutting points
            # (fr index, dur in milliseconds)
            cut_points.add((1, 0))      # frame 0 and time 0
            cut_points.add((frs, dur))  # last frame and end time

            # add current subregions
            for s in self.vid_seq.subregions:
                cut_points.add((s.fa, s.ta))
                cut_points.add((s.fb, s.tb))

            # sort them out
            cut_points = list(cut_points)
            cut_points = sorted(cut_points,
                                key=lambda x: (x[0], x[1]),
                                reverse=False)

            # make dummy regions
            to_make = len(cut_points) - 1
            for x in range(0, to_make):
                fa, ta = cut_points[x]      # get start of region
                fb, tb = cut_points[x + 1]  # get end
                sub_for_range = None        # matching subregion in range
                # look for matching subregion
                for s in self.vid_seq.subregions:
                    if s.fa == fa and s.fb == fb:
                        sub_for_range = s
                        setattr(s, 'trim', False)  # found it, won't trim it
                        break
                # if subregion isnt found, make a dummy region
                if sub_for_range is None:
                    s = RenderSubregion(ta, tb)
                    s.fa = fa
                    s.fb = fb
                    s.fps = self.playback_rate
                    s.dur = tb - ta
                    s.spd = 1.0
                    reg_frs = (s.fb - s.fa) + 1
                    tgt_frs = int(s.fps * ((s.dur + 1) / 1000.0))
                    s.btw = (tgt_frs - reg_frs) * 1.0 / (reg_frs - 1)
                    sub_for_range = s
                    setattr(s, 'trim', self.trim)
                new_subregions.append(sub_for_range)

        # create a new video sequence w/ original plus dummy regions
        # they will automatically be validated and sorted as they are added in
        seq = VideoSequence(dur, frs)
        for s in new_subregions:
            seq.add_subregion(s)
        return seq

    def render(self):
        src_path = self.vid_info['path']
        src_name = os.path.splitext(os.path.basename(src_path))[0]

        # where we're going to put the tmp file
        tmp_name = '~{filename}.{ext}'.format(filename=src_name,
                                              ext=settings['v_container']).lower()
        tmp_path = os.path.join(settings['tmp_dir'], tmp_name)

        # make a resizable window
        if self.show_preview:
            # to get opengl on osx you have to build opencv --with-opengl
            # TODO: butterflow.rb and wiki needs to be updated for this
            flag = cv2.WINDOW_OPENGL
            cv2.namedWindow(self.window_title, flag)
            cv2.resizeWindow(self.window_title, self.w, self.h)

        # prep for rendering
        self.render_pipe = self.make_pipe(tmp_path, self.playback_rate)
        frame_src = FrameSource(src_path)
        renderable_seq = self.get_renderable_sequence()

        log.debug('Rendering sequence:')
        for s in renderable_seq.subregions:
            log.debug(
                'subregion: {},{},{} {:.3g},{:.3g},{:.3g} {:.3g},{:.3g},{:.3g}'.
                format(s.fa,
                       s.fb,
                       (s.fb - s.fa + 1),
                       s.ta / 1000,0,
                       s.tb / 1000.0,
                       (s.tb - s.ta) / 1000.0,
                       s.ra,
                       s.rb,
                       s.rb - s.ra))

        # start rendering subregions
        self.subs_to_render = len(renderable_seq.subregions)
        for x, s in enumerate(renderable_seq.subregions):
            self.curr_sub_idx = x
            if s.trim:
                # the region is being trimmed and shouldn't be rendered
                continue
            else:
                self.render_subregion(frame_src, s)

        # cleanup
        if self.show_preview:
            cv2.destroyAllWindows()
        self.close_pipe(self.render_pipe)

        if self.mux:
            log.debug('muxing ...')
            aud_files = []
            for x, s in enumerate(renderable_seq.subregions):
                if s.trim:
                    continue
                tmp_name = '~{filename}.{sub}.{ext}'.format(
                        filename=src_name,
                        sub=x,
                        ext=settings['a_container']).lower()
                aud_path = os.path.join(settings['tmp_dir'], tmp_name)
                extract_audio(src_path, aud_path, s.ta, s.tb, s.spd)
                aud_files.append(aud_path)
            merged_audio = '~{filename}.merged.{ext}'.format(
                filename=src_name,
                ext=settings['a_container']
            ).lower()
            merged_audio = os.path.join(settings['tmp_dir'], merged_audio)
            concat_files(merged_audio, aud_files)
            mux(tmp_path, merged_audio, self.dst_path)
            for f in aud_files:
                os.remove(f)
            os.remove(merged_audio)
            os.remove(tmp_path)
        else:
            shutil.move(tmp_path, self.dst_path)

    def __del__(self):
        # close the pipe if it was inadvertently left open. this could happen
        # if the user does ctr+c while rendering. this would leave temporary
        # files in the cache
        self.close_pipe(self.render_pipe)
