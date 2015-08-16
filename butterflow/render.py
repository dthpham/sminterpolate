# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import datetime
from fractions import Fraction
import math
import shutil
import subprocess
import cv2
import numpy as np
from butterflow import avinfo
from butterflow.__init__ import __version__
from butterflow.settings import default as settings
from butterflow.flow import bgr_from_flow
from butterflow.source import FrameSource
from butterflow.sequence import VideoSequence, RenderSubregion


class Renderer(object):
    def __init__(self, dst_path, video_info, video_sequence, playback_rate,
        flow_func=settings['flow_func'],
        interpolate_func=settings['interpolate_func'],
        scale=settings['video_scale'], decimate=False, grayscale=False,
        lossless=False, trim=False, show_preview=True, add_info=False,
        text_type=settings['text_type'], preview_flows=False,
        make_flows=False, loglevel=settings['loglevel'],
        enc_loglevel=settings['enc_loglevel'], flow_kwargs=None):

        self.dst_path = dst_path
        self.video_info = video_info
        self.video_sequence = video_sequence
        self.flow_func = flow_func
        self.interpolate_func = interpolate_func
        # general options
        self.show_preview = show_preview
        self.text_type = text_type
        self.add_info = add_info
        self.loglevel = loglevel
        self.enc_loglevel = enc_loglevel
        # video options
        self.playback_rate = float(playback_rate)
        self.scale = scale
        self.decimate = decimate
        self.grayscale = grayscale
        self.lossless = lossless
        self.trim = trim
        # debugging options
        self.preview_flows = preview_flows
        self.make_flows = make_flows
        # normalized video information
        self.nrm_info = None
        # pipes
        self.rendered_pipe = None
        self.fwd_pipe = None
        self.bwd_pipe = None
        # information for the add info option
        self.flow_kwargs = flow_kwargs
        self.total_frs_wrt = 0
        self.subregions_to_render = 0
        self.curr_subregion_idx = 0
        # window names
        vid_name = os.path.basename(self.video_info['path'])
        self.window_title = '{} - Butterflow'.format(vid_name)
        self.fwd_window_title = '{} - Forward'.format(vid_name)
        self.bwd_window_title = '{} - Backward'.format(vid_name)

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
        if self.decimate:
            vf.extend(['fieldmatch', 'decimate'])
        if self.grayscale:
            vf.append('format=gray')
        vf.append('format=yuv420p')

        call = [
            settings['avutil'],
            '-loglevel', self.loglevel,
            '-y',
            '-threads', '0',
            '-i', self.video_info['path'],
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
            '-loglevel', self.loglevel,
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
            '-loglevel', self.loglevel,
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
            '-loglevel', self.loglevel,
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
            '-loglevel', self.loglevel,
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

    def close_pipes(self):
        for p in [self.rendered_pipe, self.fwd_pipe, self.bwd_pipe]:
            if p is not None and not p.stdin.closed:
                # flush does not necessarily write the file's data to disk. Use
                # flush followed by os.fsync to ensure this behavior.
                p.stdin.flush()
                p.stdin.close()
                p.wait()

    def write_frame_to_pipe(self, pipe, frame):
        try:
            pipe.stdin.write(bytes(frame.data))
        except Exception as err:
            print('write to pipe failed: ', err)

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
        pot_drift = extra_frs / self.playback_rate

        if settings['verbose']:
            print('Working on Subregion: ', self.curr_subregion_idx)
            print('fa:', fa)
            print('fb:', fb)
            print('ta:', ta)
            print('tb:', tb)
            print('reg_dur', reg_dur * 1000.0)
            print('reg_len', reg_len)
            print('tgt_fps', subregion.fps)
            print('tgt_dur', subregion.dur)
            print('tgt_spd', subregion.spd)
            print('tgt_frs', tgt_frs)
            print('mak_fac', mak_fac)
            print('ts:', time_step)
            print('iter_each_go', iter_each_go)
            print('wr_per_pair', iter_each_go + 1)  # +1 because of fr_1
            print('pairs', reg_len - 1)
            print('will_make', will_make)
            print('extra_frs', extra_frs)
            print('dup_every', dup_every)
            print('drp_every', drp_every)
            print('pot_drift', pot_drift)

        # keep track of progress in this subregion
        src_gen = 1  # num of source frames seen
        frs_mak = 0  # num of frames interpolated
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

        if settings['verbose']:
            print('wrt_one', fin_run)
            print('runs', runs)

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
                frs_mak += 1
            else:
                # begin interpolating frames between pairs
                try:
                    fr_2 = framesrc.read()
                except Exception as e:
                    print(e)
                    continue
                src_gen += 1

                # grayscaled images
                fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
                fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)
                # optical flow components
                fu, fv = self.flow_func(fr_1_gr, fr_2_gr)
                bu, bv = self.flow_func(fr_2_gr, fr_1_gr)

                fr_1_32 = np.float32(fr_1) * 1/255.0
                fr_2_32 = np.float32(fr_2) * 1/255.0

                if self.preview_flows or self.make_flows:
                    fwd, bwd = bgr_from_flow(fu, fv, bu, bv)
                    if self.preview_flows:
                        cv2.imshow(self.fwd_window_title, fwd)
                        cv2.imshow(self.bwd_window_title, bwd)
                    if self.make_flows:
                        self.write_frame_to_pipe(self.fwd_pipe, fwd)
                        self.write_frame_to_pipe(self.bwd_pipe, bwd)

                inter_frs = self.interpolate_func(
                    fr_1_32, fr_2_32, fu, fv, bu, bv, time_step)
                frs_mak += len(inter_frs)
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
                        self.total_frs_wrt, x, x + 1, y,
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
                        frs_mak,
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
                    self.write_frame_to_pipe(self.rendered_pipe, fr_to_wrt)

        # finished, we're outside of the main loop
        if settings['verbose']:
            wrt_ratio = 0 if tgt_frs == 0 else float(frs_wrt) / tgt_frs
            est_drift = float(tgt_frs - frs_wrt) / self.playback_rate
            print('src_gen:', src_gen)
            print('frs_mak:', frs_mak)
            print('frs_drp:', frs_drp)
            print('frs_dup:', frs_dup)
            print('fin_dup:', fin_dup)
            print('wrt_ratio: {}/{} ({:.2f}%)'.format(
                frs_wrt, tgt_frs, wrt_ratio * 100))
            print('est_drft:', pot_drift)
            print('act_drft:', est_drift)

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
        dst_dir = os.path.dirname(self.dst_path)
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
            'd' if self.decimate  else 'x',
            'g' if self.grayscale else 'x',
            'l' if self.lossless  else 'x',
            settings['encoder']).lower()

        makepth = lambda pth: \
            os.path.join(settings['tmp_dir'], pth.format(tmp_name))

        nrm_path = makepth('{}.nrm.mp4')
        rnd_path = makepth('{}.rnd.mp4')
        rff_path = makepth('{}.rff.mp4')
        rbf_path = makepth('{}.rbf.mp4')
        aud_path = makepth('{}_aud.ogg')
        sub_path = makepth('{}_sub.srt')

        # destination paths for forward and backward flows
        fwd_dst_path = os.path.join(dst_dir, '{}.fwd.mp4'.format(dst_name))
        bwd_dst_path = os.path.join(dst_dir, '{}.bwd.mp4'.format(dst_name))

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

        self.rendered_pipe = self.make_pipe(rnd_path, self.playback_rate)
        if self.make_flows:
            # use the original fps because flows are generated from src frames
            # and aren't interpolated
            fps = Fraction(self.video_info['rate_num'],
                           self.video_info['rate_den'])
            fps = float(fps)
            self.fwd_pipe = self.make_pipe(rff_path, fps)
            self.bwd_pipe = self.make_pipe(rbf_path, fps)

        # make a resizable window
        if self.show_preview:
            if sys.platform.startswith('linux'):
                flag = cv2.WINDOW_OPENGL
            else:
                flag = cv2.WINDOW_NORMAL  # avoid opengl dependency on osx
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

        if self.show_preview or self.preview_flows:
            cv2.destroyAllWindows()
        self.close_pipes()

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

        if self.make_flows:
            shutil.move(rff_path, fwd_dst_path)
            shutil.move(rbf_path, bwd_dst_path)

    def __del__(self):
        """close any pipes that were inadvertently left open"""
        self.close_pipes()
