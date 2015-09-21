# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import datetime
import math
import shutil
import subprocess
import cv2
import numpy as np
from butterflow.__init__ import __version__
from butterflow.settings import default as settings
from butterflow.source import FrameSource
from butterflow.sequence import VideoSequence, RenderSubregion

import logging
log = logging.getLogger('butterflow')


class Renderer(object):
    def __init__(
        self, dst_path, video_info, video_sequence, playback_rate,
        flow_func=settings['flow_func'],
        interpolate_func=settings['interpolate_func'],
        scale=settings['video_scale'], grayscale=False,
        lossless=False, trim=False, show_preview=True, add_info=False,
        text_type=settings['text_type'], mux=False, pad_with_dupes=True,
        av_loglevel=settings['av_loglevel'],
        enc_loglevel=settings['enc_loglevel'], flow_kwargs=None):

        self.dst_path = dst_path
        self.video_info = video_info
        self.video_sequence = video_sequence
        self.flow_func = flow_func
        self.interpolate_func = interpolate_func
        self.show_preview = show_preview
        self.text_type = text_type
        self.add_info = add_info
        self.mux = mux
        self.pad_with_dupes = pad_with_dupes
        self.av_loglevel = av_loglevel
        self.enc_loglevel = enc_loglevel
        self.playback_rate = float(playback_rate)
        self.scale = scale
        # keep the aspect ratio
        # w and h must be divisible by 2 for yuv420p outputs
        w = video_info['width']  * scale
        h = video_info['height'] * scale
        w = math.floor(w / 2) * 2
        h = math.floor(h / 2) * 2
        self.w = int(w)
        self.h = int(h)
        if scale < 1.0:
            self.scaler = settings['scaler_dn']
        elif scale > 1.0:
            self.scaler = settings['scaler_up']
        self.grayscale = grayscale
        self.lossless = lossless
        self.trim = trim
        self.render_pipe = None
        self.flow_kwargs = flow_kwargs
        self.total_frs_wrt = 0
        self.total_frs_inter = 0
        self.subregions_to_render = 0
        self.curr_subregion_idx = 0
        self.window_title = '{} - Butterflow'.format(os.path.basename(
            self.video_info['path']))

    def extract_audio(self, dst_path):
        if not self.video_info['a_stream_exists']:
            raise RuntimeError('no audio stream detected')
        proc = subprocess.call([
            settings['avutil'],
            '-loglevel', self.av_loglevel,
            '-y',
            '-i', self.video_info['path'],
            '-vn',
            '-sn',
            dst_path
        ])
        if proc == 1:
            raise RuntimeError('unable to extract audio from video')

    def extract_subtitles(self, dst_path):
        if not self.video_info['s_stream_exists']:
            raise RuntimeError('no subtitle stream detected')
        proc = subprocess.call([
            settings['avutil'],
            '-loglevel', self.av_loglevel,
            '-y',
            '-i', self.video_info['path'],
            '-vn',
            '-an',
            dst_path
        ])
        if proc == 1:
            raise RuntimeError('unable to extract subtitle from video')

    def mux_video(self, vid_path, aud_path, sub_path, dst_path, cleanup=False):
        if not os.path.exists(vid_path):
            raise IOError('video file not found')
        if aud_path is not None and not os.path.exists(aud_path):
            raise IOError('audio file not found')
        if sub_path is not None and not os.path.exists(sub_path):
            raise IOError('subtitle file not found')

        if aud_path is None and sub_path is None:
            if cleanup:
                shutil.move(vid_path, dst_path)
            else:
                shutil.copy(vid_path, dst_path)
            return

        call = [
            settings['avutil'],
            '-loglevel', self.av_loglevel,
            '-y',
        ]
        if aud_path:
            call.extend(['-i', aud_path])
        call.extend(['-i', vid_path])
        if sub_path:
            call.extend(['-i', sub_path])
        if aud_path:
            call.extend(['-c:a', 'copy'])
        call.extend(['-c:v', 'copy'])
        if sub_path:
            call.extend(['-c:s', 'mov_text'])
        call.extend([dst_path])
        proc = subprocess.call(call)
        if proc == 1:
            raise RuntimeError('unable to mux video')

        if cleanup:
            os.remove(vid_path)

    def make_pipe(self, dst_path, rate):
        vf = []
        if self.grayscale:
            vf.append('format=gray')
        vf.append('format=yuv420p')

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
            '-c:v', settings['encoder'],
            '-preset', settings['preset']]
        if settings['encoder'] == 'libx264':
            quality = ['-crf', str(settings['crf'])]
            # -qp 0 is recommended over -crf for lossless
            # See: https://trac.ffmpeg.org/wiki/Encode/H.264#LosslessH.264
            if self.lossless:
                quality = ['-qp', '0']
            call.extend(quality)
            call.extend(['-level', '4.2'])
        elif settings['encoder'] == 'libx265':
            call.extend(['-x265-params'])
            quality = 'crf={}'.format(settings['crf'])
            if self.lossless:
                # ffmpeg doesn't pass -x265-params to x265 correctly, must
                # provide keys for every single value until fixed
                # See: https://trac.ffmpeg.org/ticket/4284
                quality = 'lossless=1'
            loglevel = 'log-level={}'.format(self.enc_loglevel)
            call.extend([':'.join([quality, loglevel])])
        call.extend([dst_path])
        pipe = subprocess.Popen(
            call,
            stdin=subprocess.PIPE
        )
        if pipe == 1:
            raise RuntimeError('could not create pipe')
        return pipe

    def close_pipe(self):
        p = self.render_pipe
        if p is not None and not p.stdin.closed:
            # flush does not necessarily write the file's data to disk. Use
            # flush followed by os.fsync to ensure this behavior.
            p.stdin.flush()
            p.stdin.close()
            p.wait()

    def write_frame_to_pipe(self, pipe, frame):
        try:
            pipe.stdin.write(bytes(frame.data))
        except Exception:
            log.error('Writing frame to pipe failed:', exc_info=True)

    def render_subregion(self, framesrc, subregion):
        log.debug('Working on subregion: %s', self.curr_subregion_idx + 1)

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
            subregion.spd = 1  # if unset, as a precaution against div by zero
            tgt_frs = int(reg_len + ((reg_len - 1) * subregion.btw))

        tgt_frs = max(0, tgt_frs)
        # the make factor or inverse time step
        int_each_go = float(tgt_frs) / max(1, (reg_len - 1))

        # stop a division by zero error when only a single frame needs to be
        # written
        if int_each_go == 0:
            tgt_frs = 1

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
        log.debug('tgt_spd: %s %.2gx', subregion.spd, 1 / subregion.spd)
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
        framesrc.seek_to_frame(fa_idx)
        # log.debug('seek: %s', framesrc.index + 1)  # seek pos of first frame
        # log.debug('read: %s', framesrc.index + 1)  # next frame to be read
        fr_2 = framesrc.read()       # first frame in the region

        if self.scale != 1.0:
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
            framesrc.seek_to_frame(fa_idx + 1)  # seek to the next frame
            # log.debug('seek: %s', framesrc.index + 1)
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
                    # log.debug('read: %s', framesrc.index + 1)
                    fr_2 = framesrc.read()
                    src_gen += 1
                except Exception:
                    log.error('Could not read frame:', exc_info=True)
                    break
                if fr_2 is None:
                    break
                elif self.scale != 1.0:
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
                    if not self.pad_with_dupes:
                        # write out frame at least once
                        if len(frs_to_wrt) == 1:
                            wrts_needed = 1
                    log.debug('fin_dup: %s,%s,%s wrts=%sx',
                              pair_a,
                              pair_b,
                              btw_idx,
                              wrts_needed)
                    # final frame should be dropped if needed
                    if drp_every > 0:
                        if math.fmod(wrk_idx, drp_every) < 1.0:
                            log.warning('drp last frame')
                            continue

                for wrt_idx in range(wrts_needed):
                    frs_wrt += 1
                    self.total_frs_wrt += 1
                    # log.debug('wrt: %s,%s,%s (%s)', pair_a, pair_b, btw_idx,
                    #           self.total_frs_wrt)
                    # frame copy has a minimal effect on performance
                    fr_to_wrt = fr
                    fr_with_info = cv2.cv.fromarray(fr.copy())

                    w = self.w
                    h = self.h
                    hscale = min(w / float(settings['h_fits']), 1.0)
                    vscale = min(h / float(settings['v_fits']), 1.0)
                    scale = min(hscale, vscale)

                    if self.text_type == 'light':
                        text_color = settings['light_color']
                    elif self.text_type == 'dark':
                        text_color = settings['dark_color']
                    elif self.text_type == 'stroke':
                        text_color = settings['light_color']
                        strk_color = settings['dark_color']

                    font = cv2.cv.InitFont(
                        settings['font'], scale, scale, 0.0,
                        settings['text_thick'], cv2.cv.CV_AA)
                    stroke = cv2.cv.InitFont(
                        settings['font'], scale, scale, 0.0,
                        settings['strk_thick'], cv2.cv.CV_AA)

                    txt = "butterflow {} ({})\n"\
                          "Res: {},{}\n"\
                          "Playback Rate: {} fps\n"
                    txt = txt.format(__version__, sys.platform, w, h,
                                     self.playback_rate)

                    if self.flow_kwargs is not None:
                        flow_format = ''
                        i = 0
                        for k, v in self.flow_kwargs.items():
                            flow_format += "{}: {}".format(k, v)
                            if i == len(self.flow_kwargs) - 1:
                                flow_format += '\n\n'
                            else:
                                flow_format += ', '
                            i += 1
                        txt += flow_format

                    txt += "Frame: {}\n"\
                           "Pair Index: {}, {}, {}\n"\
                           "Type Src: {}, Int: {}, Dup: {}\n"\
                           "Mem: {}\n"
                    txt = txt.format(
                        self.total_frs_wrt,
                        pair_a,
                        pair_b,
                        btw_idx,
                        'Y' if fr_type == 'source' else 'N',
                        'Y' if fr_type == 'interpolated' else 'N',
                        'Y' if wrt_idx > 0 else 'N',
                        hex(id(fr_to_wrt)))

                    for line_idx, line in enumerate(txt.split('\n')):
                        line_sz, _ = cv2.cv.GetTextSize(line, font)
                        _, line_h = line_sz
                        origin = (int(settings['l_padding']),
                                  int(settings['t_padding'] +
                                  (line_idx * (line_h +
                                   settings['line_d_padding']))))
                        if self.text_type == 'stroke':
                            cv2.cv.PutText(
                                fr_with_info, line, origin, stroke, strk_color)
                        cv2.cv.PutText(
                            fr_with_info, line, origin, font, text_color)

                    sub_tgt_dur = '{:.2f}s'.format(
                        subregion.dur / 1000.0) if subregion.dur else '_'
                    sub_tgt_fps = '{}'.format(
                        subregion.fps) if subregion.fps else '_'
                    sub_tgt_spd = '{:.2f}'.format(
                        subregion.spd) if subregion.spd else '_'
                    sub_tgt_btw = '{:.2f}'.format(
                        subregion.btw) if subregion.btw else '_'

                    tgt_dur = tgt_frs / float(self.playback_rate)
                    write_ratio = frs_wrt * 100.0 / tgt_frs

                    txt = "Region {}/{} F: [{}, {}] T: [{:.2f}s, {:.2f}s]\n"\
                          "Len F: {}, T: {:.2f}s\n"\
                          "Target Spd: {} Dur: {} Fps: {} Btw: {}\n"\
                          "Out Len F: {}, Dur: {:.2f}s\n"\
                          "Drp every {:.1f}, Dup every {:.1f}\n"\
                          "Src seen: {}, Int: {}, Drp: {}, Dup: {}\n"\
                          "Write Ratio: {}/{} ({:.2f}%)\n"

                    txt = txt.format(
                        self.curr_subregion_idx + 1,
                        self.subregions_to_render,
                        fa,
                        fb,
                        ta / 1000,
                        tb / 1000,
                        reg_len,
                        reg_dur,
                        sub_tgt_spd,
                        sub_tgt_dur,
                        sub_tgt_fps,
                        sub_tgt_btw,
                        tgt_frs,
                        tgt_dur,
                        drp_every,
                        dup_every,
                        src_gen,
                        frs_int,
                        frs_drp,
                        frs_dup,
                        frs_wrt,
                        tgt_frs,
                        write_ratio)

                    for line_idx, line in enumerate(txt.split('\n')):
                        line_sz, _ = cv2.cv.GetTextSize(line, font)
                        line_w, line_h = line_sz
                        origin = (int(w - settings['r_padding'] - line_w),
                                  int(settings['t_padding'] +
                                  (line_idx * (line_h +
                                   settings['line_d_padding']))))
                        if self.text_type == 'stroke':
                            cv2.cv.PutText(
                                fr_with_info, line, origin, stroke, strk_color)
                        cv2.cv.PutText(
                            fr_with_info, line, origin, font, text_color)

                    # show the frame on the screen
                    if self.show_preview:
                        cv2.imshow(self.window_title, np.asarray(fr_with_info))
                        # every imshow call should be followed by waitKey to
                        # display the image for x milliseconds, otherwise it
                        # won't display the image
                        cv2.waitKey(settings['imshow_ms'])

                    # add debugging information
                    if self.add_info:
                        fr_to_wrt = np.asarray(fr_with_info)

                    # send the frame to the pipe
                    self.write_frame_to_pipe(self.render_pipe, fr_to_wrt)

        # finished encoding
        self.total_frs_inter += (frs_int - frs_int_drp)

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

    def renderable_sequence(self):
        dur = self.video_info['duration']
        frs = self.video_info['frames']

        new_subregions = []

        if self.video_sequence.subregions is None or \
                len(self.video_sequence.subregions) == 0:
            # make a subregion from 0 to vid duration if there are no regions
            # in the video sequence. only framerate is changing.
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
            # create dummy subregions that fill holes in the video sequence
            # where subregions were not explicity specified
            cut_points = set([])
            # add start and end of video cutting points
            cut_points.add((1, 0))  # (frame idx, duration in millesconds)
            cut_points.add((frs, dur))

            for s in self.video_sequence.subregions:
                cut_points.add((s.fa, s.ta))
                cut_points.add((s.fb, s.tb))

            cut_points = list(cut_points)
            cut_points = sorted(cut_points,
                                key=lambda x: (x[0], x[1]),
                                reverse=False)

            to_make = len(cut_points) - 1

            for x in range(0, to_make):
                fa, ta = cut_points[x]
                fb, tb = cut_points[x + 1]
                sub_for_range = None
                # look for matching subregion in the sequence
                for s in self.video_sequence.subregions:
                    if s.fa == fa and s.fb == fb:
                        sub_for_range = s
                        setattr(s, 'trim', False)
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

        # create a new video sequence. the new subregions will
        # be auto validated and sorted as they are added to the sequence
        seq = VideoSequence(dur, frs)
        for s in new_subregions:
            seq.add_subregion(s)

        log.debug('Rendering sequence:')
        for s in new_subregions:
            log.debug(
                'subregion: {},{},{} {:.3g},{:.3g},{:.3g} {:.3g},{:.3g},{:.3g}'.
                format(s.fa,
                       s.fb,
                       (s.fb - s.fa + 1),
                       s.ta / 1000,
                       s.tb / 1000,
                       (s.tb - s.ta) / 1000,
                       s.ra,
                       s.rb,
                       s.rb - s.ra))
        return seq

    def render(self):
        dst_name, _ = os.path.splitext(os.path.basename(self.dst_path))
        src_path = self.video_info['path']

        vid_mod_dt = os.path.getmtime(src_path)
        vid_mod_utc = datetime.datetime.utcfromtimestamp(vid_mod_dt)
        unix_time = lambda dt:\
            (dt - datetime.datetime.utcfromtimestamp(0)).total_seconds()

        tmp_name = '{name}.{mod_date}.{w}x{h}.{g}.{l}.{enc}'.format(
            name=os.path.basename(src_path),
            mod_date=str(unix_time(vid_mod_utc)),
            w=self.w,
            h=self.h,
            g='g' if self.grayscale else 'x',
            l='l' if self.lossless else 'x',
            enc=settings['encoder']).lower()

        makepth = lambda pth: \
            os.path.join(settings['tmp_dir'], pth.format(tmp_name))

        rnd_path = makepth('{}.rnd.mp4')
        aud_path = makepth('{}_aud.ogg')
        sub_path = makepth('{}_sub.srt')

        frame_src = FrameSource(src_path)

        renderable_seq = self.renderable_sequence()

        # make a resizable window
        if self.show_preview:
            if sys.platform.startswith('darwin'):
                flag = cv2.WINDOW_NORMAL  # avoid opengl dependency on osx
            else:
                flag = cv2.WINDOW_OPENGL
            cv2.namedWindow(self.window_title, flag)
            cv2.resizeWindow(
                self.window_title, self.w, self.h)

        rnd_tmp_path = os.path.join(
            os.path.dirname(rnd_path), '~' + os.path.basename(rnd_path))

        self.render_pipe = self.make_pipe(rnd_tmp_path, self.playback_rate)

        # start rendering subregions
        self.total_frs_wrt = 0
        self.subregions_to_render = len(renderable_seq.subregions)
        for x, s in enumerate(renderable_seq.subregions):
            self.curr_subregion_idx = x
            if s.trim:
                # the region is being trimmed and shouldnt be rendered
                continue
            else:
                self.render_subregion(frame_src, s)

        if self.show_preview:
            cv2.destroyAllWindows()
        self.close_pipe()

        shutil.move(rnd_tmp_path, rnd_path)

        speed_changed = False
        if self.video_sequence.subregions is not None:
            for s in self.video_sequence.subregions:
                if s.fps != self.playback_rate:
                    speed_changed = True
                elif s.spd != 1.0:
                    speed_changed = True
                elif s.dur != (s.fb - s.fa):
                    speed_changed = True
                if speed_changed:
                    break

        # dont mux if speed changed or video was trimmed
        if self.trim or speed_changed:
            shutil.move(rnd_path, self.dst_path)
        else:
            if self.mux:
                # start extracting audio and subtitle streams if they exist
                if self.video_info['a_stream_exists']:
                    self.extract_audio(aud_path)
                else:
                    aud_path = None
                if self.video_info['s_stream_exists']:
                    self.extract_subtitles(sub_path)
                    # it's possible for a subtitle stream to exist but have no
                    # information
                    with open(sub_path, 'r') as f:
                        if f.read() == '':
                            sub_path = None
                else:
                    sub_path = None
                # move files to their destinations
                try:
                    self.mux_video(rnd_path, aud_path, sub_path, self.dst_path,
                                   cleanup=True)
                except RuntimeError:
                    shutil.move(rnd_path, self.dst_path)
            else:
                shutil.move(rnd_path, self.dst_path)

    def __del__(self):
        """close the pipe if it was inadvertently left open"""
        self.close_pipe()
