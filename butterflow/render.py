# -*- coding: utf-8 -*-

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
from butterflow.interpolate import time_steps_for_nfrs


import logging
log = logging.getLogger('butterflow')


class Renderer(object):
    def __init__(self, src, dest, sequence, rate, optflow_fn, interpolate_fn,
                 w, h, scaling_method, lossless, keep_subregions, show_preview,
                 add_info, text_type, mark_frames, mux):
        self.src = src
        self.dest = dest
        self.sequence = sequence
        self.rate = rate
        self.optflow_fn = optflow_fn
        self.interpolate_fn = interpolate_fn
        self.w = w
        self.h = h
        self.scaling_method = scaling_method
        self.lossless = lossless
        self.keep_subregions = keep_subregions
        self.show_preview = show_preview
        self.add_info = add_info
        self.text_type = text_type
        self.mark_frames = mark_frames
        self.mux = mux
        self.pipe = None
        self.fr_source = None
        self.av_info = avinfo.get_av_info(src)
        self.source_frs = 0
        self.frs_interpolated = 0
        self.frs_duped = 0
        self.frs_dropped = 0
        self.frs_written = 0
        self.subs_to_render = 0
        self.frs_to_render = 0
        self.curr_sub_idx = 0
        self.window_title = os.path.basename(self.src) + ' - Butterflow'
        self.progress = 0

    def mk_render_pipe(self, dest):
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
                quality = ['-qp', '0']
            call.extend(quality)
            call.extend(['-level', '4.2'])
        params = []
        call.extend(['-{}-params'.format(settings['cv'].replace('lib', ''))])
        params.append('log-level={}'.format(settings['enc_loglevel']))
        if settings['cv'] == 'libx265':
            quality = 'crf={}'.format(settings['crf'])
            if self.lossless:
                # Bug: https://trac.ffmpeg.org/ticket/4284
                quality = 'lossless=1'
            params.append(quality)
        if len(params) > 0:
            call.extend([':'.join(params)])
        call.extend([dest])
        log.info('[Subprocess] Opening a pipe to the video writer')
        log.debug('Call: {}'.format(' '.join(call)))
        self.pipe = subprocess.Popen(call, stdin=subprocess.PIPE)
        if self.pipe == 1:
            raise RuntimeError

    def close(self):
        if self.pipe and not self.pipe.stdin.closed:
            self.pipe.stdin.flush()
            self.pipe.stdin.close()
            self.pipe.wait()
            log.info('[Subprocess] Closing pipe to the video writer')

    def scale_fr(self, fr):
        return cv2.resize(fr,
                          (self.w, self.h),
                          interpolation=self.scaling_method)

    def calc_frs_to_render(self, sub):
        reg_len = (sub.fb - sub.fa) + 1
        reg_duration = (sub.tb - sub.ta) / 1000.0
        to_render = 0

        if sub.target_dur:
            to_render = int(self.rate *
                            (sub.target_dur / 1000.0))
        elif sub.target_fps:
            to_render = int(sub.target_fps * reg_duration)
        elif sub.target_spd:
            to_render = int(self.rate * reg_duration *
                            (1 / sub.target_spd))

        to_render = max(0, to_render)
        interpolate_each_go = float(to_render) / max(1, (reg_len - 1))

        if interpolate_each_go == 0:
            to_render = 1
        return to_render

    def render_subregion(self, sub):
        reg_len = (sub.fb - sub.fa) + 1
        frs_to_render = self.calc_frs_to_render(sub)
        interpolate_each_go = int(float(frs_to_render) / max(1, (reg_len - 1)))
        pairs = reg_len - 1

        log.info("Frames in region:\t%d-%d", sub.fa, sub.fb)
        log.info("Region length:\t%d", reg_len)
        log.info("Region duration:\t%fs", (sub.tb - sub.ta) / 1000.0)
        log.info("Number of frame pairs:\t%d", pairs)

        if interpolate_each_go == 0:
            log.warn("Interpolation rate:\t0 (only render S-frames)")
        else:
            log.info("Interpolation rate:\t%d", interpolate_each_go)

        steps_string = ""
        steps = time_steps_for_nfrs(interpolate_each_go)
        for i, x in enumerate(steps):
            steps_string += "{:.3f}".format(x)
            if i < len(steps)-1:
                steps_string += ","
        if steps_string == "":
            steps_string = "N/A"
        log.info("Time stepping:\t%s", steps_string)

        log.info("Frames to write:\t%d", frs_to_render)

        if pairs >= 1:
            will_make = (interpolate_each_go * pairs) + pairs
        else:
            will_make = 1

        extra_frs = will_make - frs_to_render

        log.info("Will interpolate:\t%d", will_make)
        log.info("Extra frames (to discard):\t%d", extra_frs)

        drp_every = 0
        dup_every = 0

        if extra_frs > 0:
            drp_every = will_make / math.fabs(extra_frs)
        if extra_frs < 0:
            dup_every = will_make / math.fabs(extra_frs)

        log.info("Drop every:\t%d", drp_every)
        log.info("Dupe every:\t%d", dup_every)

        src_seen = 0
        frs_interpolated = 0
        work_idx = 0
        frs_written = 0
        frs_duped = 0
        frs_dropped = 0
        runs = 0
        final_run = False

        fr_1 = None

        log.debug("Seeking to %d", sub.fa)
        self.fr_source.seek_to_fr(sub.fa)

        log.debug("Reading %d into B", sub.fa)
        fr_2 = self.fr_source.read()

        if fr_2 is None:
            log.warn("First frame in the region is None (B is None)")
        src_seen += 1

        if sub.fa == sub.fb or frs_to_render == 1:
            runs = 1
            final_run = True
            log.info("Ready to run:\t1 time (only writing S-frame)")
        else:
            log.debug("Seeking to %d", sub.fa+1)
            self.fr_source.seek_to_fr(sub.fa + 1)

            runs = reg_len
            log.info("Ready to run:\t%d times", runs)

        if self.scaling_method == settings['scaler_dn']:
            fr_2 = self.scale_fr(fr_2)

        def fr_draw_scale(w_fits, h_fits):
            return min(float(fr_2.shape[1]) / float(w_fits),
                       float(fr_2.shape[0]) / float(h_fits))

        debug_draw_scale = fr_draw_scale(settings['txt_w_fits'],
                                         settings['txt_h_fits'])
        progress_bar_draw_scale = fr_draw_scale(settings['bar_w_fits'],
                                                settings['bar_h_fits'])
        marker_draw_scale = fr_draw_scale(settings['mrk_w_fits'],
                                          settings['mrk_h_fits'])

        txt = 'Frame, Shape={}x{}, is too small to draw on: Type={{}}\tScale={{}} < Min={{}}'.format(
              fr_2.shape[1], fr_2.shape[0])
        if self.add_info and debug_draw_scale < settings['txt_min_scale']:
            log.warning(txt.format('info', debug_draw_scale,
                                   settings['txt_min_scale']))
        if self.show_preview and progress_bar_draw_scale < 1.0:
            log.warning(txt.format('progress', progress_bar_draw_scale, 1.0))
        if self.mark_frames and marker_draw_scale < 1.0:
            log.warning(txt.format('marker', marker_draw_scale, 1.0))

        show_n = settings['debug_show_n_runs']
        show_period = settings['debug_show_progress_period']
        showed_snipped_message = False

        def in_show_debug_range(x):
            if show_n == -1:
                return True
            return x <= show_n or x >= runs - show_n + 1

        if show_n == -1 or show_n*2 >= runs:
            log.info("Showing all runs:")
        else:
            log.info("Showing a sample of the first and last %d runs:", show_n)

        for run in range(0, runs):
            fr_period = max(1, int(show_period * (runs - show_n*2)))

            if not in_show_debug_range(run) and not showed_snipped_message:
                log.info("<Snipping %d runs from the console, but will update progress periodically every %d frames rendered>",
                         runs - show_n*2, fr_period)
                showed_snipped_message = True

            if not in_show_debug_range(run) and showed_snipped_message:
                if run % fr_period == 0:
                    log.info("<Rendering progress: {:.2f}%>".format(
                             self.progress*100))

            if run >= runs - 1:
                final_run = True

            pair_a = sub.fa + run
            pair_b = pair_a + 1 if run + 1 < runs else pair_a

            if final_run:
                log.info("Run %d (this is the final run):", run)
            else:
                log.debug("Run %d:", run)
            log.debug("Pair A: %d, B: %d", pair_a, pair_b)

            frs_to_write = []

            log.debug("Copy last B frame, %d, into A", self.fr_source.idx-1)
            fr_1 = fr_2
            if fr_1 is None:
                log.error("A is None")

            if final_run:
                frs_to_write.append((fr_1, 'SOURCE', 1))
                log.info("To write: S{}".format(pair_a))
            else:
                try:
                    log.debug("Read %d into B", self.fr_source.idx)
                    fr_2 = self.fr_source.read()
                except RuntimeError:
                    log.error("Couldn't read %d (will abort runs)", self.fr_source.idx)
                    log.warn("Setting B to None")
                    fr_2 = None
                if fr_2 is None:
                    log.warn("B is None")
                    frs_to_write.append((fr_1, 'SOURCE', 1))
                    final_run = True
                    log.info("To write: S{}".format(pair_a))
                if not final_run:
                    src_seen += 1

                    if self.scaling_method == settings['scaler_dn']:
                        fr_2 = self.scale_fr(fr_2)

                    fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
                    fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)

                    f_uv = self.optflow_fn(fr_1_gr, fr_2_gr)
                    b_uv = self.optflow_fn(fr_2_gr, fr_1_gr)

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

                    will_write = True

                    would_drp = []
                    cmp_interpolate_each_go = interpolate_each_go
                    cmp_work_idx = work_idx - 1

                    for x in range(1 + interpolate_each_go):
                        cmp_work_idx += 1
                        if drp_every > 0 and \
                                math.fmod(cmp_work_idx, drp_every) < 1.0:
                            would_drp.append(x + 1)

                    if len(would_drp) > 0:
                        txt = ""
                        for i, x in enumerate(would_drp):
                            txt += "{}".format(str(x))
                            if i < len(would_drp)-1:
                                txt += ","
                        log.debug("Would drop indices:\t" + txt)

                        if len(would_drp) <= interpolate_each_go:
                            cmp_interpolate_each_go -= len(would_drp)
                            log.debug("Compensating interpolation rate:\t%d (-%d)",
                                      cmp_interpolate_each_go, len(would_drp))
                        else:
                            will_write = False
                        if not will_write:
                            work_idx += 1
                            self.frs_dropped += 1
                            if in_show_debug_range(run):
                                log.info("Compensating, dropping S-frame")

                    if will_write:
                        interpolated_frs = self.interpolate_fn(
                            fr_1_32, fr_2_32, fu, fv, bu, bv,
                            cmp_interpolate_each_go)

                        frs_interpolated += len(interpolated_frs)

                        frs_to_write.append((fr_1, 'SOURCE', 0))
                        for i, fr in enumerate(interpolated_frs):
                            frs_to_write.append((fr, 'INTERPOLATED', i+1))
                        if in_show_debug_range(run):
                            temp_progress = (float(self.frs_written) +
                                        len(frs_to_write)) / self.frs_to_render
                            temp_progress *= 100.0
                            log.info("To write: S{}\tI{},{}\t{:.2f}%".format(
                                     pair_a, len(interpolated_frs), len(would_drp),
                                     temp_progress))

            for i, (fr, fr_type, idx_between_pair) in enumerate(frs_to_write):
                work_idx += 1
                writes_needed = 1

                if dup_every > 0 and math.fmod(work_idx, dup_every) < 1.0:
                    frs_duped += 1
                    writes_needed = 2
                if final_run:
                    writes_needed = (frs_to_render - frs_written)
                    if drp_every > 0 and math.fmod(work_idx, drp_every) < 1.0:
                        self.frs_dropped += 1
                        if i == 0:
                            log.warn("Dropping S{}".format(pair_a))
                        else:
                            log.warn("Dropping I{}".format(idx_between_pair))
                        continue

                for write_idx in range(writes_needed):
                    fr_to_write = fr
                    frs_written += 1
                    self.frs_written += 1
                    self.progress = float(self.frs_written)/self.frs_to_render
                    is_dupe = False
                    if write_idx == 0:
                        if fr_type == 'SOURCE':
                            self.source_frs += 1
                        else:
                            self.frs_interpolated += 1
                    else:
                        is_dupe = True
                        self.frs_duped += 1
                        if fr_type == 'SOURCE':
                            log.warn("Duping S%d", pair_a)
                        else:
                            log.warn("Duping I%d", idx_between_pair)

                    if self.scaling_method == settings['scaler_up']:
                        fr = self.scale_fr(fr)

                    if self.mark_frames:
                        draw.draw_marker(fr, fill=fr_type == 'INTERPOLATED')
                    if self.add_info:
                        if writes_needed > 1:
                            fr_to_write = fr.copy()
                        draw.draw_debug_text(fr_to_write, self.text_type,
                                             self.rate, self.optflow_fn,
                                             self.frs_written, pair_a, pair_b,
                                             idx_between_pair, fr_type,
                                             is_dupe, frs_to_render,
                                             frs_written, sub,
                                             self.curr_sub_idx,
                                             self.subs_to_render,
                                             drp_every, dup_every, src_seen,
                                             frs_interpolated, frs_dropped,
                                             frs_duped)
                    if self.show_preview:
                        fr_to_show = fr.copy()
                        draw.draw_progress_bar(fr_to_show, progress=self.progress)
                        cv2.imshow(self.window_title, np.asarray(fr_to_show))
                        cv2.waitKey(settings['imshow_ms'])

                    self.pipe.stdin.write(bytes(fr_to_write.data))

    def render(self):
        filename = os.path.splitext(os.path.basename(self.src))[0]
        tempfile1 = os.path.join(
            settings['tempdir'],
            '{}.{}.{}'.format(filename, os.getpid(), settings['v_container']).lower())
        log.info("Rendering to:\t%s", os.path.basename(tempfile1))
        log.info("Final destination:\t%s", self.dest)
        self.fr_source = OpenCvFrameSource(self.src)
        self.fr_source.open()
        self.mk_render_pipe(tempfile1)
        self.frs_to_render = 0
        for sub in self.sequence.subregions:
            if not self.keep_subregions and sub.skip:
                continue
            else:
                self.subs_to_render += 1
                self.frs_to_render += self.calc_frs_to_render(sub)
        if self.show_preview:
            cv2.namedWindow(self.window_title,
                            cv2.WINDOW_OPENGL)
            cv2.resizeWindow(self.window_title, self.w, self.h)
        self.progress = 0
        log.info("Rendering progress:\t{:.2f}%".format(0))
        for i, sub in enumerate(self.sequence.subregions):
            if not self.keep_subregions and sub.skip:
                log.info("Skipping Subregion (%d): %s", i, str(sub))
                continue
            else:
                log.info("Start working on Subregion (%d): %s", i, str(sub))
                self.curr_sub_idx += 1
                self.render_subregion(sub)
                log.info("Done rendering Subregion (%d)", i)
        if self.show_preview:
            cv2.destroyAllWindows()
        self.fr_source.close()
        self.close()
        log.info("Rendering is finished")
        if self.mux:
            if self.av_info['a_stream_exists']:
                self.mux_orig_audio_with_rendered_video(tempfile1)
                return
            else:
                log.warn('Not muxing because no audio stream exists in the input file')
        log.info("Moving: %s -> %s", os.path.basename(tempfile1), self.dest)
        shutil.move(tempfile1, self.dest)

    def mux_orig_audio_with_rendered_video(self, vid):
        log.info("Muxing progress:\t{:.2f}%".format(0))
        progress = 0
        def update_progress():
            log.info("Muxing progress:\t{:.2f}%".format(progress*100))
        filename = os.path.splitext(os.path.basename(self.src))[0]
        audio_files = []
        to_extract = 0
        for sub in self.sequence.subregions:
            if not self.keep_subregions and sub.skip:
                continue
            else:
                to_extract += 1
        if to_extract == 0:
            progress += 1.0/3
            update_progress()
        progress_chunk = 1.0/to_extract/3
        for i, sub in enumerate(self.sequence.subregions):
            if not self.keep_subregions and sub.skip:
                continue
            tempfile1 = os.path.join(
                settings['tempdir'],
                '{}.{}.{}.{}'.format(filename,
                                     i,
                                     os.getpid(),
                                     settings['a_container']).lower())
            log.info("Start working on audio from subregion (%d):", i)
            log.info("Extracting to:\t%s", os.path.basename(tempfile1))
            speed = sub.target_spd
            if speed is None:
                reg_duration = (sub.tb - sub.ta) / 1000.0
                frs = self.calc_frs_to_render(sub)
                speed = (self.rate * reg_duration) / frs
                log.info("Speed not set for mux, calculated as: %fx", speed)
            mux.extract_audio(self.src,
                              tempfile1,
                              sub.ta,
                              sub.tb,
                              speed)
            audio_files.append(tempfile1)
            progress += progress_chunk
            update_progress()
        tempfile2 = os.path.join(
            settings['tempdir'],
            '{}.merged.{}.{}'.format(filename,
                                     os.getpid(),
                                     settings['a_container']).lower())
        log.info("Merging to:\t%s", os.path.basename(tempfile2))
        mux.concat_av_files(tempfile2, audio_files)
        progress += 1.0/3
        update_progress()
        mux.mux_av(vid, tempfile2, self.dest)
        progress += 1.0/3
        update_progress()
        for file in audio_files:
            log.info("Delete:\t%s", os.path.basename(file))
            os.remove(file)
        log.info("Delete:\t%s", os.path.basename(tempfile2))
        os.remove(tempfile2)
        log.info("Delete:\t%s", os.path.basename(vid))
        os.remove(vid)

    def __del__(self):
        self.close()
