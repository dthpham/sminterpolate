# -*- coding: utf-8 -*-
# make video w/ interpolated frames

import os
import shutil
import subprocess
import math
import cv2
import numpy as np
from butterflow.settings import default as settings
from butterflow.source import OpenCvFrameSource
from butterflow import mux
from butterflow import avinfo
from butterflow import draw

import logging
log = logging.getLogger('butterflow')

class Renderer(object):
    def __init__(self, src, dst, sequence, rate, flow_fn, inter_fn, w, h,
                 lossless, trim, preview, add_info, text_type, mark_frames,
                 mux):
        self.src = src
        self.dst = dst
        self.sequence = sequence
        self.rate = rate
        self.flow_fn = flow_fn
        self.inter_fn = inter_fn
        self.w = w
        self.h = h
        self.lossless = lossless
        self.trim = trim
        self.preview = preview
        self.add_info = add_info
        self.text_type = text_type
        self.mark_frames = mark_frames
        self.mux = mux
        self.render_pipe = None
        self.fr_source = None
        self.av_info = avinfo.get_av_info(src)
        self.tot_src_frs = 0
        self.tot_frs_int = 0
        self.tot_frs_dup = 0
        self.tot_frs_drp = 0
        self.tot_frs_wrt = 0
        self.tot_tgt_frs = 0
        self.subs_to_render = 0
        self.curr_sub_idx = 0

    @property
    def preview_win_title(self):
        return '{} - Butterflow'.format(os.path.basename(self.src))

    @property
    def scaling_method(self):
        new_res = self.w * self.h
        src_res = self.av_info['w'] * self.av_info['h']
        if new_res < src_res:
            return settings['scaler_dn']
        elif new_res > src_res:
            return settings['scaler_up']
        else:
            return None

    def mk_render_pipe(self, dst):
        vf = []
        vf.append('format=yuv420p')
        call = [
            settings['avutil'],
            '-loglevel', settings['av_loglevel'],
            '-y',
            '-threads', '0',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', '{}x{}'.format(self.w, self.h),
            '-r', str(self.rate),
            '-i', '-',
            '-map_metadata', '-1',
            '-map_chapters', '-1',
            '-vf', ','.join(vf),
            '-r', str(self.rate),
            '-an',
            '-sn',
            '-c:v', settings['cv'],
            '-preset', settings['preset']]
        if settings['cv'] == 'libx264':
            quality = ['-crf', str(settings['crf'])]
            if self.lossless:
                # -qp 0 is recommended over -crf for lossless
                # See: https://trac.ffmpeg.org/wiki/Encode/H.264#LosslessH.264
                quality = ['-qp', '0']
            call.extend(quality)
            call.extend(['-level', '4.2'])
        params = []
        call.extend(['-{}-params'.format(settings['cv'].replace('lib', ''))])
        params.append('log-level={}'.format(settings['enc_loglevel']))
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
        call.extend([dst])
        self.render_pipe = subprocess.Popen(call, stdin=subprocess.PIPE)
        if self.render_pipe == 1:
            raise RuntimeError

    def close_render_pipe(self):
        if self.render_pipe and not self.render_pipe.stdin.closed:
            # flush doesn't necessarily write file's data to disk, must use
            # flush followed by os.fsync() to ensure this behavior
            self.render_pipe.stdin.flush()
            self.render_pipe.stdin.close()
            self.render_pipe.wait()

    def render_subregion(self, sub):
        fa = sub.fa
        fb = sub.fb
        ta = sub.ta
        tb = sub.tb

        reg_len = (fb - fa) + 1       # num of frs in the region
        reg_dur = (tb - ta) / 1000.0  # duration of sub in secs

        tgt_frs = 0  # num of frs we're targeting to render

        # only one of these needs to be set to calculate tgt_frames
        if sub.target_dur:
            tgt_frs = int(self.rate *
                          (sub.target_dur / 1000.0))
        elif sub.target_fps:
            tgt_frs = int(sub.target_fps * reg_dur)
        elif sub.target_spd:
            tgt_frs = int(self.rate * reg_dur *
                          (1 / sub.target_spd))

        tgt_frs = max(0, tgt_frs)
        # the make factor or inverse the time step
        int_each_go = float(tgt_frs) / max(1, (reg_len - 1))

        # prevent a division by zero error when only a fr frame needs to be
        # written
        if int_each_go == 0:
            tgt_frs = 1

        self.tot_tgt_frs += tgt_frs

        int_each_go = int(int_each_go)

        pairs = reg_len - 1
        if pairs >= 1:
            will_make = (int_each_go * pairs) + pairs
        else:
            # no pairs available, will only add src fr to to_wrt
            will_make = 1
        extra_frs = will_make - tgt_frs

        # frs will need to be dropped or duped based on how many frs are
        # expected to be generated. this includes source and interpolated frs
        drp_every = 0
        if extra_frs > 0:
            drp_every = will_make / math.fabs(extra_frs)

        dup_every = 0
        if extra_frs < 0:
            dup_every = will_make / math.fabs(extra_frs)

        # keep track of progress in this subregion
        src_seen = 0  # num of source frames seen
        frs_int = 0  # num of frames interpolated
        wrk_idx = 0  # idx in the subregion being worked on
        frs_wrt = 0  # num of frames written in this subregion
        frs_dup = 0  # num of frames duped
        frs_drp = 0  # num of frames dropped
        fin_run = False  # is this the final run?
        runs = 0  # num of runs through the loop

        fr_1 = None
        self.fr_source.seek_to_fr(fa)
        fr_2 = self.fr_source.read()  # first frame in the region

        # scale down now, but wait after drawing on the frame before scaling up
        if self.scaling_method == settings['scaler_dn']:
            fr_2 = cv2.resize(fr_2,
                              (self.w, self.h),
                              interpolation=self.scaling_method)
        src_seen += 1
        if fa == fb or tgt_frs == 1:
            # only 1 fr expected. run through the main loop once
            fin_run = True
            runs = 1
        else:
            # at least one fr pair is available. num of runs is equal to the
            # the total number of frames in the region - 1. range will run from
            # [0,runs)
            self.fr_source.seek_to_fr(fa + 1)  # seek to the next fr
            runs = reg_len

        for run_idx in range(0, runs):
            # which fr in the video is being worked on
            pair_a = fa + run_idx
            pair_b = pair_a + 1 if run_idx + 1 < runs else pair_a

            # if working on the last fr, write it out because we cant
            # interpolate without a pair
            if run_idx >= runs - 1:
                fin_run = True

            frs_to_wrt = []  # hold frs to be written
            fr_1 = fr_2  # reference to prev fr saves a seek & read

            if fin_run:
                frs_to_wrt.append((fr_1, 'source', 1))
            else:
                # begin interpolating frs between pairs
                # the fr being read should always be valid otherwise break
                fr_2 = self.fr_source.read()
                src_seen += 1
                if fr_2 is None:
                    raise RuntimeError
                elif self.scaling_method == settings['scaler_dn']:
                    fr_2 = cv2.resize(fr_2,
                                      (self.w, self.h),
                                      interpolation=self.scaling_method)

                fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
                fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)

                f_uv = self.flow_fn(fr_1_gr, fr_2_gr)
                b_uv = self.flow_fn(fr_2_gr, fr_1_gr)

                if isinstance(f_uv, np.ndarray):
                    fu = f_uv[:,:,0]
                    fv = f_uv[:,:,1]
                    bu = b_uv[:,:,0]
                    bv = b_uv[:,:,1]
                else:
                    fu, fv = f_uv
                    bu, bv = b_uv

                fr_1_32 = np.float32(fr_1) * 1/255.0
                fr_2_32 = np.float32(fr_2) * 1/255.0

                will_wrt = True  # frs will be written?

                # look ahead to see if frs will be dropped. compensate by
                # lowering the num of frames to be interpolated
                cmp_int_each_go = int_each_go    # compensated int_each_go
                w_drp = []                       # frs that would be dropped
                tmp_wrk_idx = wrk_idx - 1        # zero-indexed
                for x in range(1 + int_each_go):  # 1 real + interpolated fr
                    tmp_wrk_idx += 1
                    if drp_every > 0:
                        if math.fmod(tmp_wrk_idx, drp_every) < 1.0:
                            w_drp.append(x + 1)
                n_drp = len(w_drp)

                # start compensating
                if n_drp > 0:
                    # can compensate by reducing num of frs to be interpolated,
                    # since they are available
                    if n_drp <= int_each_go:
                        cmp_int_each_go -= n_drp
                    else:
                        # can't compensate using interpolated frs alone, will
                        # have to drop the source fr. nothing will be written
                        will_wrt = False
                    if not will_wrt:
                        # nothing will be written this go
                        wrk_idx += 1  # still have to increment the wrk_idx
                        self.tot_frs_drp += 1

                if will_wrt:
                    int_frs = self.inter_fn(
                        fr_1_32, fr_2_32, fu, fv, bu, bv, cmp_int_each_go)
                    frs_int += len(int_frs)
                    frs_to_wrt.append((fr_1, 'source', 0))
                    for i, fr in enumerate(int_frs):
                        frs_to_wrt.append((fr, 'interpolated', i + 1))

            for (fr, fr_type, btw_idx) in frs_to_wrt:
                wrk_idx += 1
                wrts_needed = 1
                # duping should never happen unless the sub being worked on
                # only has one fr
                if dup_every > 0:
                    if math.fmod(wrk_idx, dup_every) < 1.0:
                        frs_dup += 1
                        wrts_needed = 2
                if fin_run:
                    wrts_needed = (tgt_frs - frs_wrt)
                    # final fr should be dropped if needed
                    if drp_every > 0:
                        if math.fmod(wrk_idx, drp_every) < 1.0:
                            self.tot_frs_drp += 1
                            continue

                for wrt_idx in range(wrts_needed):
                    fr_to_write = fr
                    frs_wrt += 1
                    is_dup = False
                    if wrt_idx == 0:
                        if fr_type == 'source':
                            self.tot_src_frs += 1
                        else:
                            self.tot_frs_int += 1
                    else:
                        is_dup = True
                        self.tot_frs_dup += 1
                    self.tot_frs_wrt += 1
                    if self.scaling_method == settings['scaler_up']:
                        fr = cv2.resize(fr,
                                        (self.w, self.h),
                                        interpolation=self.scaling_method)

                    if self.mark_frames:
                        draw.draw_fr_marker(fr, fr_type == 'interpolated')

                    if self.add_info:
                        if wrts_needed > 1:
                            fr_to_write = fr.copy()
                        draw.draw_debug_text(fr_to_write,
                                             self.text_type,
                                             self.rate,
                                             self.flow_fn,
                                             self.tot_frs_wrt,
                                             pair_a,
                                             pair_b,
                                             btw_idx,
                                             fr_type,
                                             is_dup,
                                             tgt_frs,
                                             frs_wrt,
                                             sub,
                                             self.curr_sub_idx,
                                             self.subs_to_render,
                                             drp_every,
                                             dup_every,
                                             src_seen,
                                             frs_int,
                                             frs_drp,
                                             frs_dup)

                    if self.preview:
                        fr_to_show = fr.copy()
                        draw.draw_progress_bar(fr_to_show,
                                               float(frs_wrt) / tgt_frs)
                        cv2.imshow(self.preview_win_title,
                                   np.asarray(fr_to_show))
                        cv2.waitKey(settings['imshow_ms'])

                    self.render_pipe.stdin.write(bytes(fr_to_write.data))

    def render_video(self):
        src_fname = os.path.splitext(os.path.basename(self.src))[0]
        tempfile1 = os.path.join(settings['tempdir'],
                                 '~{}.{}'.format(src_fname,
                                                 settings['v_container']).
                                 lower())

        self.fr_source = OpenCvFrameSource(self.src)
        self.fr_source.open()
        self.mk_render_pipe(tempfile1)
        self.subs_to_render = 0
        for sub in self.sequence.subregions:
            if self.trim and sub.skip:
                continue
            else:
                self.subs_to_render += 1
        if self.preview:
            cv2.namedWindow(self.preview_win_title, cv2.WINDOW_OPENGL)
            cv2.resizeWindow(self.preview_win_title, self.w, self.h)
        for i, sub in enumerate(self.sequence.subregions):
            if self.trim and sub.skip:
                continue
            else:
                self.curr_sub_idx += 1
                log.info('Rendering: Sub {0:02d}...'.format(i))
                self.render_subregion(sub)
        if self.preview:
            cv2.destroyAllWindows()
        self.fr_source.close()
        self.close_render_pipe()

        if self.mux:
            log.info('Muxing...')
            if self.av_info['a_stream_exists']:
                audio_files = []
                for i, sub in enumerate(self.sequence.subregions):
                    if self.trim and sub.skip:
                        continue
                    tempfile2 = os.path.join(
                        settings['tempdir'],
                        '~{}.{}.{}'.format(src_fname,
                                           i,
                                           settings['a_container']).lower())
                    mux.extract_audio_with_spd(self.src,
                                               tempfile2,
                                               sub.ta,
                                               sub.tb,
                                               sub.target_spd)
                    audio_files.append(tempfile2)
                tempfile3 = os.path.join(
                    settings['tempdir'],
                    '~{}.merged.{}'.format(src_fname,
                                           settings['a_container']).lower())
                mux.concat_av_files(tempfile3, audio_files)
                mux.mux_av(tempfile1, tempfile3, self.dst)
                for file in audio_files:
                    os.remove(file)
                os.remove(tempfile3)
                os.remove(tempfile1)
                return
            else:
                log.warn('no audio stream exists')

        shutil.move(tempfile1, self.dst)

    def __del__(self):
        # close the pipe if it was inadvertently left open. this can happen if
        # user does ctrl+c while rendering
        self.close_render_pipe()
