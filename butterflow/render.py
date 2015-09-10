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
from butterflow import avinfo
from butterflow.__init__ import __version__
from butterflow.settings import default as settings
from butterflow.source import FrameSource
from butterflow.sequence import VideoSequence, RenderSubregion

import logging
log = logging.getLogger('butterflow')


class Renderer(object):
    def __init__(self, dst_path, video_info, video_sequence, playback_rate,
                 flow_func=settings['flow_func'],
                 interpolate_func=settings['interpolate_func'],
                 scale=settings['video_scale'],
                 detelecine=False,
                 grayscale=False,
                 lossless=False,
                 trim=False,
                 show_preview=True,
                 add_info=False,
                 text_type=settings['text_type'],
                 mux=False,
                 av_loglevel=settings['av_loglevel'],
                 enc_loglevel=settings['enc_loglevel'],
                 flow_kwargs=None):
        self.dst_path = dst_path
        self.video_info = video_info
        self.video_sequence = video_sequence
        self.flow_func = flow_func
        self.interpolate_func = interpolate_func
        self.show_preview = show_preview
        self.text_type = text_type
        self.add_info = add_info
        self.mux = mux
        self.av_loglevel = av_loglevel
        self.enc_loglevel = enc_loglevel
        self.playback_rate = float(playback_rate)
        self.scale = scale
        self.detelecine = detelecine
        self.grayscale = grayscale
        self.lossless = lossless
        self.trim = trim
        self.nrm_info = None
        self.render_pipe = None
        self.flow_kwargs = flow_kwargs
        self.total_frs_wrt = 0
        self.subregions_to_render = 0
        self.curr_subregion_idx = 0
        self.window_title = '{} - Butterflow'.format(os.path.basename(
            self.video_info['path']))

    def normalize_for_interpolation(self, dst_path):
        using_avconv = settings['avutil'] == 'avconv'
        if not self.video_info['v_stream_exists']:
            raise RuntimeError('no video stream detected')
        has_sub = self.video_info['s_stream_exists']
        has_aud = self.video_info['a_stream_exists']

        w = -1 if using_avconv else -2
        h = int(self.video_info['height'] * self.scale * 0.5) * 2
        scaler = 'bilinear' if self.scale >= 1.0 else 'lanczos'

        tmp_dir = os.path.join(
            os.path.dirname(dst_path), '~' + os.path.basename(dst_path))

        vf = []
        vf.append('scale={}:{}'.format(w, h))
        if self.detelecine:
            vf.extend(['fieldmatch', 'decimate'])
        if self.grayscale:
            vf.append('format=gray')
        vf.append('format=yuv420p')

        call = [
            settings['avutil'],
            '-loglevel', self.av_loglevel,
            '-y',
            '-threads', '0',
            '-i', self.video_info['path'],
            '-map_metadata', '-1',
            '-map_chapters', '-1',
            '-vf', ','.join(vf),
            '-sws_flags', scaler
        ]
        if has_aud:
            call.extend([
                '-c:a', 'libvorbis',
                '-ab', '96k'
            ])
        if has_sub and not using_avconv:
            call.extend([
                '-c:s', 'mov_text'
            ])
        call.extend([
            '-c:v', settings['encoder'],
            '-preset', settings['preset'],
        ])
        if settings['encoder'] == 'libx264':
            quality = ['-crf', str(settings['crf'])]
            if self.lossless:
                quality = ['-qp', '0']
            call.extend(quality)
            if not using_avconv:
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
        call.extend([tmp_dir])
        nrm_proc = subprocess.call(call)
        if nrm_proc == 1:
            raise RuntimeError('could not normalize video')
        shutil.move(tmp_dir, dst_path)

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
            raise RuntimeError('no subtitle streams detected')
        if settings['avutil'] == 'avconv':
            open(dst_path, 'a').close()
            return
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
            raise RuntimeError('unable to extract subtitles from video')

    def mux_video(self, vid_path, aud_path, sub_path, dst_path, cleanup=False):
        if not os.path.exists(vid_path):
            raise IOError('video not found: {}'.format(vid_path))
        if aud_path is not None and not os.path.exists(aud_path):
            raise IOError('audio not found: {}'.format(aud_path))
        if sub_path is not None and not os.path.exists(sub_path):
            raise IOError('subtitle not found: {}'.format(sub_path))

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
        w = self.nrm_info['width']
        h = self.nrm_info['height']
        call = [
            settings['avutil'],
            '-loglevel', self.av_loglevel,
            '-y',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', '{}x{}'.format(w, h),
            '-r', str(rate),
            '-i', '-',
            '-vf', ','.join(vf),
            '-r', str(rate),
            '-c:a', 'none',
            '-c:v', settings['encoder'],
            '-preset', settings['preset']]
        if settings['encoder'] == 'libx264':
            quality = ['-crf', str(settings['crf'])]
            if self.lossless:
                quality = ['-qp', '0']
            call.extend(quality)
        elif settings['encoder'] == 'libx265':
            call.extend(['-x265-params'])
            quality = 'crf={}'.format(settings['crf'])
            if self.lossless:
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

    def render_subregion(self, framesrc, subregion, filters=None):
        fa = subregion.fa
        fb = subregion.fb
        ta = subregion.ta
        tb = subregion.tb

        reg_len = (fb - fa) + 1  # num of frames in the region
        reg_dur = (tb - ta) / 1000.0  # duration of subregion in seconds

        tgt_frs = 0  # num of frames we're targeting to render

        if subregion.dur:
            tgt_frs = int(self.playback_rate *
                          (subregion.dur / 1000.0))
        if subregion.fps:
            tgt_frs = int(subregion.fps * reg_dur)
        if subregion.spd:
            tgt_frs = int(self.playback_rate * reg_dur *
                          (1 / subregion.spd))
        if subregion.btw:
            tgt_frs = int(reg_len + ((reg_len - 1) * subregion.btw))

        tgt_frs = max(0, tgt_frs)

        # prevent division a division by zero error when only a single frame
        # needs to be written
        mak_fac = float(tgt_frs) / reg_len
        if mak_fac == 0:
            tgt_frs = 1
            mak_fac = 1
        time_step = min(1.0, 1 / mak_fac)

        # if 1.0 % time_step is zero, one less frame will be
        # interpolated
        iter_each_go = int(1 / time_step)
        if abs(0 - math.fmod(1, time_step)) <= 1e-8:
            iter_each_go -= 1

        will_make = (iter_each_go + 1) * reg_len
        extra_frs = will_make - tgt_frs

        # frames will be need to be dropped or duped based on how many
        # interpolated frames are expected to be made
        dup_every = 0
        drp_every = 0
        if extra_frs > 0:
            drp_every = will_make / math.fabs(extra_frs)
        if extra_frs < 0:
            dup_every = will_make / math.fabs(extra_frs)

        # audio may drift because of the change in which frames are rendered in
        # relation to the source video this is used for debugging:
        pot_aud_drift = extra_frs / self.playback_rate

        log.debug('sub_idx: %s', self.curr_subregion_idx)
        log.debug('fa: %s', fa)
        log.debug('fb: %s', fb)
        log.debug('ta: %s', ta)
        log.debug('tb: %s', tb)
        log.debug('reg_dur: %s', reg_dur * 1000.0)
        log.debug('reg_len: %s', reg_len)
        log.debug('tgt_fps: %s', subregion.fps)
        log.debug('tgt_dur: %s', subregion.dur)
        log.debug('tgt_spd: %s', subregion.spd)
        log.debug('tgt_btw: %s', subregion.btw)
        log.debug('tgt_frs: %s', tgt_frs)
        log.debug('mak_fac: %s', mak_fac)
        log.debug('ts: %s', time_step)
        log.debug('iter_each_go: %s', iter_each_go)
        log.debug('wr_per_pair: %s', iter_each_go + 1)  # +1 because of fr_1
        log.debug('pairs: %s', reg_len - 1)
        log.debug('will_make: %s', will_make)
        log.debug('extra_frs: %s', extra_frs)
        log.debug('dup_every: %s', dup_every)
        log.debug('drp_every: %s', drp_every)
        log.debug('pot_aud_drift: %s', pot_aud_drift)

        # keep track of progress in this subregion
        src_gen = 1  # num of source frames seen
        frs_itr = 0  # num of frames interpolated
        wrk_idx = 0  # idx in the subregion being worked on
        frs_wrt = 0  # num of frames written in this subregion
        frs_dup = 0  # num of frames duped
        frs_drp = 0  # num of frames dropped
        fin_run = False  # is this the final run?
        fin_dup = 0  # num of frames duped on the final run
        runs = 0  # num of runs through the loop

        # frames are zero based indexed
        fa_idx = fa - 1

        fr_1 = None
        fr_2 = framesrc.frame_at_idx(fa_idx)  # first frame in the region
        if fa == fb or tgt_frs == 1:
            # only 1 frame expected. run through the main loop once
            fin_run = True
            runs = 1
        else:
            # at least one frame pair is available. num of runs is equal to the
            # the total number of frames in the region - 1. range will run
            # from [0,runs)
            framesrc.seek_to_frame(fa_idx + 1)
            runs = reg_len

        log.debug('wrt_one: %s', fin_run)
        log.debug('runs: %s', runs)

        for x in range(0, runs):
            # hit the `Esc` key to stop running
            ch = 0xff & cv2.waitKey(30)
            if ch == 23:
                break

            # if working on the last frame, write it out because we cant
            # interpolate without a pair
            if x >= runs - 1:
                fin_run = True

            to_wrt = []  # hold frames to be written
            fr_1 = fr_2  # reference to prev fr saves a seek & read

            if fin_run:
                to_wrt.append(fr_1)
                frs_itr += 1
            else:
                # begin interpolating frames between pairs
                # the frame being read should always be valid otherwise break
                try:
                    fr_2 = framesrc.read()
                except Exception as e:
                    break
                if fr_2 is None:
                    break
                src_gen += 1

                # grayscaled images
                fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
                fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)
                # optical flow components
                fu, fv = self.flow_func(fr_1_gr, fr_2_gr)
                bu, bv = self.flow_func(fr_2_gr, fr_1_gr)

                fr_1_32 = np.float32(fr_1) * 1/255.0
                fr_2_32 = np.float32(fr_2) * 1/255.0

                inter_frs = self.interpolate_func(
                    fr_1_32, fr_2_32, fu, fv, bu, bv, time_step)
                frs_itr += len(inter_frs)
                to_wrt.append(fr_1)
                to_wrt.extend(inter_frs)

            for y, fr in enumerate(to_wrt):
                wrk_idx += 1
                wrts_needed = 1
                if drp_every > 0:
                    if math.fmod(wrk_idx, drp_every) < 1.0:
                        frs_drp += 1
                        continue
                if dup_every > 0:
                    if math.fmod(wrk_idx, dup_every) < 1.0:
                        frs_dup += 1
                        wrts_needed = 2
                if fin_run:
                    wrts_needed = (tgt_frs - frs_wrt)
                    fin_dup = wrts_needed - 1
                for z in range(wrts_needed):
                    frs_wrt += 1
                    self.total_frs_wrt += 1

                    fr_to_wrt = fr

                    # frame copy here has minimal affect on performance
                    fr_with_info = cv2.cv.fromarray(fr.copy())

                    w = self.nrm_info['width']
                    h = self.nrm_info['height']
                    hscale = min(w / float(settings['h_fits']), 1.0)
                    vscale = min(h / float(settings['v_fits']), 1.0)
                    scale = min(hscale, vscale)

                    if self.text_type == 'light':
                        text_color = settings['light_color']
                    if self.text_type == 'dark':
                        text_color = settings['dark_color']
                    if self.text_type == 'stroke':
                        text_color = settings['light_color']
                        strk_color = settings['dark_color']

                    font = cv2.cv.InitFont(
                        settings['font'], scale, scale, 0.0,
                        settings['text_thick'], cv2.cv.CV_AA)
                    stroke = cv2.cv.InitFont(
                        settings['font'], scale, scale, 0.0,
                        settings['strk_thick'], cv2.cv.CV_AA)

                    t = "butterflow {} ({})\n"\
                        "Res: {},{}\n"\
                        "Playback Rate: {} fps\n"
                    t = t.format(__version__, sys.platform, w, h,
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
                        t += flow_format

                    t += "Frame: {}\n"\
                         "Work Index: {}, {}, {}\n"\
                         "Type Src: {}, Dup: {}\n"\
                         "Mem: {}\n"
                    t = t.format(
                        self.total_frs_wrt, fa_idx + x, fa_idx + x + 1, y,
                        'Y' if y == 0 else 'N', 'Y' if z > 0 else 'N',
                        hex(id(fr)))

                    for y, line in enumerate(t.split('\n')):
                        line_sz, _ = cv2.cv.GetTextSize(line, font)
                        _, line_h = line_sz
                        origin = (int(settings['l_padding']),
                                  int(settings['t_padding'] +
                                  (y * (line_h +
                                   settings['line_d_padding']))))
                        if self.text_type == 'stroke':
                            cv2.cv.PutText(
                                fr_with_info, line, origin, stroke, strk_color)
                        cv2.cv.PutText(
                            fr_with_info, line, origin, font, text_color)

                    sub_tgt_dur = '*'
                    sub_tgt_fps = '*'
                    sub_tgt_spd = '*'
                    sub_tgt_btw = '*'
                    if subregion.dur is not None:
                        sub_tgt_dur = '{:.2f}s'.format(
                            subregion.dur / 1000.0)
                    if subregion.fps is not None:
                        sub_tgt_fps = '{}'.format(subregion.fps)
                    if subregion.spd is not None:
                        sub_tgt_spd = '{:.2f}'.format(subregion.spd)
                    if subregion.btw is not None:
                        sub_tgt_btw = '{:.2f}'.format(subregion.btw)
                    tgt_dur = tgt_frs / float(self.playback_rate)
                    write_ratio = frs_wrt * 100.0 / tgt_frs

                    t = "Region {}/{} F: [{}, {}] T: [{:.2f}s, {:.2f}s]\n"\
                        "Len F: {}, T: {:.2f}s\n"\
                        "Target Dur: {} Spd: {} Fps: {} Btw: {}\n"\
                        "Out Len F: {}, Dur: {:.2f}s\n"\
                        "Drp every {:.1f}, Dup every {:.1f}\n"\
                        "Gen: {}, Made: {}, Drp: {}, Dup: {}\n"\
                        "Write Ratio: {}/{} ({:.2f}%)\n"

                    t = t.format(
                        self.curr_subregion_idx + 1,
                        self.subregions_to_render,
                        fa,
                        fb,
                        ta / 1000,
                        tb / 1000,
                        reg_len,
                        reg_dur,
                        sub_tgt_dur,
                        sub_tgt_spd,
                        sub_tgt_fps,
                        sub_tgt_btw,
                        tgt_frs,
                        tgt_dur,
                        drp_every,
                        dup_every,
                        src_gen,
                        frs_itr,
                        frs_drp,
                        frs_dup,
                        frs_wrt,
                        tgt_frs,
                        write_ratio)

                    for y, line in enumerate(t.split('\n')):
                        line_sz, _ = cv2.cv.GetTextSize(line, font)
                        line_w, line_h = line_sz
                        origin = (int(w - settings['r_padding'] - line_w),
                                  int(settings['t_padding'] +
                                  (y * (line_h +
                                   settings['line_d_padding']))))
                        if self.text_type == 'stroke':
                            cv2.cv.PutText(
                                fr_with_info, line, origin, stroke, strk_color)
                        cv2.cv.PutText(
                            fr_with_info, line, origin, font, text_color)

                    # finshed adding info. show the frame on the screen
                    if self.show_preview:
                        cv2.imshow(self.window_title, np.asarray(fr_with_info))
                    if self.add_info:
                        fr_to_wrt = np.asarray(fr_with_info)

                    # send the frame to the pipe
                    self.write_frame_to_pipe(self.render_pipe, fr_to_wrt)

        # finished, we're outside of the main loop
        act_aud_drift = float(tgt_frs - frs_wrt) / self.playback_rate
        log.debug('act_aud_drift: %s', act_aud_drift)

        log.debug('src_gen: %s', src_gen)
        log.debug('frs_itr: %s', frs_itr)
        log.debug('frs_drp: %s', frs_drp)
        log.debug('frs_dup: %s', frs_dup)
        log.debug('fin_dup: %s', fin_dup)

        if tgt_frs == 0:
            wrt_ratio = 0
        else:
            wrt_ratio = float(frs_wrt) / tgt_frs
        log.debug('wrt_ratio: {}/{}, {:.2f}%'.format(
            frs_wrt, tgt_frs, wrt_ratio * 100))

    def renderable_sequence(self):
        dur = self.nrm_info['duration']
        frs = self.nrm_info['frames']

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
            s.btw = (tgt_frs - frs) * 1.0 / (frs - 1)
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

        # create a new video sequence. the new subregions will automatically
        # be validated as they are added to the sequence
        seq = VideoSequence(dur, frs)
        for s in new_subregions:
            seq.add_subregion(s)
        return seq

    def render(self):
        """normalizes, renders, muxes an interpolated video, if necessary. when
        doing slow/fast motion, audio and subtitles will not be muxed into the
        final video because it wouldnt be in sync. we also need to recalculate
        relative positions after normalization because the video may have
        changed in frame count, frame rate, and duration.
        """
        dst_name, _ = os.path.splitext(os.path.basename(self.dst_path))

        src_path = self.video_info['path']

        # use the modification time of the file to determine if renormalization
        # is needed. if it hasn't been modified and the settings haven't changed
        # then we can just use the old video if it exists
        vid_mod_dt = os.path.getmtime(src_path)
        vid_mod_utc = datetime.datetime.utcfromtimestamp(vid_mod_dt)
        unix_time = lambda dt:\
            (dt - datetime.datetime.utcfromtimestamp(0)).total_seconds()

        tmp_name = '{}.{}.{}.{}.{}.{}.{}'.format(
            os.path.basename(src_path),
            str(unix_time(vid_mod_utc)),
            self.scale,
            'd' if self.detelecine else 'x',
            'g' if self.grayscale  else 'x',
            'l' if self.lossless   else 'x',
            settings['encoder']).lower()

        makepth = lambda pth: \
            os.path.join(settings['tmp_dir'], pth.format(tmp_name))

        nrm_path = makepth('{}.nrm.mp4')
        rnd_path = makepth('{}.rnd.mp4')
        aud_path = makepth('{}_aud.ogg')
        sub_path = makepth('{}_sub.srt')

        if not os.path.exists(nrm_path):
            self.normalize_for_interpolation(nrm_path)
        self.nrm_info = avinfo.get_info(nrm_path)

        # normalization may have changed the framecnt, fps, and duration need
        # to recalculate the videosequence subregions' time and frame positions
        # using saved relative positions
        self.video_sequence.recalculate_subregion_positions(
            self.nrm_info['duration'], self.nrm_info['frames'])

        frame_src = FrameSource(self.nrm_info['path'])

        renderable_seq = self.renderable_sequence()

        self.render_pipe = self.make_pipe(rnd_path, self.playback_rate)

        # make a resizable window
        if self.show_preview:
            if sys.platform.startswith('darwin'):
                flag = cv2.WINDOW_NORMAL  # avoid opengl dependency on osx
            else:
                flag = cv2.WINDOW_OPENGL
            cv2.namedWindow(self.window_title, flag)
            cv2.resizeWindow(
                self.window_title, self.nrm_info['width'],
                self.nrm_info['height'])

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
