from media.source import OpenCvFrameSource
import cv2
import subprocess
from motion.interpolate import Interpolate
import numpy as np
import os
import math
from region import VideoRegionUtils, RenderingSubRegion
import sys
from __init__ import __version__ as version
from .butterflow import config


class Renderer(object):
  '''renders an interpolated video based on information supplied in
  project settings most important info: video info, playback
  rate, timing regions, and flow method, interpolation method. this
  only creates a video. audio/subs will not be muxed in here
  '''
  def __init__(self, vid_info, playback_rate, timing_regions, flow_method,
               interpolate_method, vf_trim=False, vf_grayscale=False,
               vf_lossless=False, loglevel='fatal', show_preview=False):
    '''should copy of the settings so that any changes to them during
    rendering dont cause any issues
    '''
    self.vid_info = vid_info
    self.playback_rate = playback_rate
    self.timing_regions = timing_regions
    self.flow_method = flow_method
    self.interpolate_method = interpolate_method
    self.pipe = None
    self.loglevel = loglevel
    self.show_preview = show_preview
    self.total_frames_written = 0
    self.num_sub_regions = 0
    self.curr_sub_region_idx = 0
    self.vf_trim = vf_trim
    self.vf_grayscale = vf_grayscale
    self.vf_lossless = vf_lossless

  def init_pipe(self, dst_path):
    '''create pipe to ffmpeg/libav, which will encode the video for us'''
    pix_fmt = 'yuv420p'
    if self.vf_grayscale:
      pix_fmt = 'gray'
    call = [
        config['avutil'],
        '-loglevel', self.loglevel,
        '-y',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', '{}x{}'.format(self.vid_info.width, self.vid_info.height),
        '-r', str(self.playback_rate),
        '-i', '-',
        '-pix_fmt', pix_fmt,
        '-r', str(self.playback_rate),
        '-c:a', 'none',
        '-c:v', 'libx264',
        '-preset', 'fast']
    quality = ['-crf', '18']
    if self.vf_lossless:
      quality = ['-qp', '0']
    call.extend(quality)
    call.extend([dst_path])
    self.pipe = subprocess.Popen(
        call,
        stdin=subprocess.PIPE
    )
    if self.pipe == 1:
      raise RuntimeError('could not create pipe')

  def close_pipe(self):
    '''closes pipe to the encoder if it is open'''
    if self.pipe is not None:
      self.pipe.stdin.flush()
      self.pipe.stdin.close()
      self.pipe.wait()
      self.pipe = None

  def write_frame_to_pipe(self, frame):
    '''writes a frame to the pipe'''
    try:
      self.pipe.stdin.write(bytes(frame.data))
      self.total_frames_written += 1
    except Exception as err:
      print('error writing to pipe: ', err)

  def render_subregion(self, source, sub_region):
    '''calculates flows, interpolates frames, and sends it to the pipe
    to be encoded into a video
    '''
    src = source
    vid_name = os.path.basename(self.vid_info.video_path)
    vid_name, _ = os.path.splitext(vid_name)

    fr_a = sub_region.frame_a
    fr_b = sub_region.frame_b
    frs_in_region = (fr_b - fr_a) + 1
    dur_in_region = sub_region.time_b - sub_region.time_a

    tgt_frs = 0
    fr_factor = 0.0
    time_step = 0.0

    if sub_region.target_duration:
      tgt_dur_secs = sub_region.target_duration / 1000
      tgt_frs = int(self.playback_rate * tgt_dur_secs)
    if sub_region.target_rate:
      reg_dur_secs = dur_in_region / 1000
      tgt_frs = int(sub_region.target_rate * reg_dur_secs)
    if sub_region.target_factor:
      reg_dur_secs = dur_in_region / 1000
      tgt_factor = 1 / sub_region.target_factor
      tgt_frs = int(self.playback_rate * reg_dur_secs * tgt_factor)

    fr_factor = tgt_frs * 1.0 / frs_in_region
    # prevent division by zero when only one frame needs to be written
    if fr_factor == 0:
      tgt_frs = 1
      fr_factor = 1
    time_step = 1 / fr_factor

    time_step = min(time_step, 1.0)

    drop_every_n_frs = 0.0
    dupe_every_n_frs = 0.0

    # if 1.0 % time_step is zero, one less frame will be interpolated
    frs_inter_each_go = int(1 / time_step)
    if abs(0 - math.fmod(1, time_step)) <= 1e-16:
      frs_inter_each_go -= 1

    pairs = frs_in_region - 1
    frs_write_per_pair = frs_inter_each_go + 1
    frs_will_make = frs_write_per_pair * pairs
    frs_extra = frs_will_make - tgt_frs
    if frs_extra > 0:
      drop_every_n_frs = frs_will_make / math.fabs(frs_extra)
    if frs_extra < 0:
      dupe_every_n_frs = frs_will_make / math.fabs(frs_extra)
    pot_drift_secs = frs_extra / self.playback_rate

    if config['verbose']:
      print('region_fr_a', fr_a)
      print('region_fr_b', fr_b)
      print('region_time_a', sub_region.time_a)
      print('region_time_b', sub_region.time_b)
      print('region_dur', dur_in_region)
      print('region_len', frs_in_region)
      print('region_fps', self.playback_rate)
      print('tgt_frs', tgt_frs)
      print('fr_factor', fr_factor)
      print('time_step', time_step)
      print('frs_inter_each_go', frs_inter_each_go)
      print('frs_write_per_pair', frs_write_per_pair)
      print('pairs', pairs)
      print('frs_will_make', frs_will_make)
      print('extra_frs', frs_extra)
      print('drop_every', drop_every_n_frs)
      print('dupe_every', dupe_every_n_frs)
      print('potential_drift_secs', float(pot_drift_secs))

    frs_made = 0
    frs_dropped = 0
    frs_duped = 0
    frs_written = 0
    frs_gen = 1
    wrk_idx = 0
    only_write_one = False

    fr_1 = None
    fr_2 = src.frame_at_idx(fr_a)
    if fr_a == fr_b:
      times_to_run = 1
      only_write_one = True
    else:
      src.seek_to_frame(fr_a + 1)
      times_to_run = frs_in_region - 1

    for x in xrange(0, times_to_run):
      ch = 0xff & cv2.waitKey(30)
      if ch == 23:
        break

      new_frs = []
      fr_1 = fr_2
      if only_write_one:
        new_frs.append(fr_1)
      else:
        try:
          fr_2 = src.read_frame()
          frs_gen += 1
        except Exception as ex:
          print('couldn\'t read a frame {} breaking: {}'.format(x, ex))
          break

        fr_1_gr = cv2.cvtColor(fr_1, cv2.COLOR_BGR2GRAY)
        fr_2_gr = cv2.cvtColor(fr_2, cv2.COLOR_BGR2GRAY)
        fu, fv = self.flow_method([fr_1_gr, fr_2_gr])
        bu, bv = self.flow_method([fr_2_gr, fr_1_gr])
        fr_1_32 = np.float32(fr_1) * 1 / 255.0
        fr_2_32 = np.float32(fr_2) * 1 / 255.0

        i_frs = self.interpolate_method(
            fr_1_32, fr_2_32, fu, fv, bu, bv, time_step)
        new_frs.append(fr_1)
        new_frs.extend(i_frs)

      frs_made += len(new_frs)

      for idx, fr in enumerate(new_frs):
        wrk_idx += 1
        should_dupe = False

        if drop_every_n_frs > 0:
          drop_rem = math.fmod(wrk_idx, drop_every_n_frs)
          should_drop = drop_rem < 1.0
          if should_drop:
            frs_dropped += 1
            continue
        if dupe_every_n_frs > 0:
          dupe_rem = math.fmod(wrk_idx, dupe_every_n_frs)
          should_dupe = dupe_rem < 1.0
          if should_dupe:
            frs_duped += 1

        for k in range(2 if should_dupe else 1):
          frs_written += 1
          fr_to_write = fr

          if config['embed_info']:
            T_PADDING = 20.0
            L_PADDING = 20.0
            R_PADDING = 20.0
            LINE_D_PADDING = 10.0

            # the copy here has a minimal effect on performance
            img_mat = cv2.cv.fromarray(fr.copy())
            # 768x216 is the minimum size in which the unscaled
            # CV_FONT_HERSHEY_PLAIN font fits. The font is scaled up and down
            # based on that reference point
            h_scale = min(self.vid_info.width / 768.0, 1.0)
            v_scale = min(self.vid_info.height / 216.0, 1.0)
            scale = min(h_scale, v_scale)
            font = cv2.cv.InitFont(cv2.cv.CV_FONT_HERSHEY_PLAIN, scale, scale,
                                   0.0, 1, cv2.cv.CV_AA)
            font_color = cv2.cv.RGB(255, 255, 255)

            # embed text starting from the top left going down
            t = ('butterflow {} ({})\n'
                 'Res: {},{}\n'
                 'Playback Rate: {} fps\n'
                 'Pyr: {}, L: {}, W: {}, I: {}, PolyN: {}, PolyS: {}\n\n'
                 'Frame: {}\n'
                 'Work Index: {}, {}, {}\n'
                 'Type Src: {}, Dup: {}\n'
                 'Mem: {}')
            t = t.format(version,
                         sys.platform,
                         self.vid_info.width,
                         self.vid_info.height,
                         config['playback_rate'],
                         config['pyr_scale'],
                         config['levels'],
                         config['winsize'],
                         config['iters'],
                         config['poly_n'],
                         config['poly_s'],
                         self.total_frames_written,
                         x,
                         x + 1,
                         idx,
                         'Y' if idx == 0 else 'N',
                         'Y' if k > 0 else 'N',
                         hex(id(fr)))

            for y, line in enumerate(t.split('\n')):
              line_sz, _ = cv2.cv.GetTextSize(line, font)
              _, line_h = line_sz
              origin = (int(L_PADDING),
                        int(T_PADDING +
                        (y * (line_h + LINE_D_PADDING))))
              cv2.cv.PutText(img_mat, line, origin, font, font_color)

            # embed text from the top right going down
            sub_time_a_sec = sub_region.time_a / 1000
            sub_time_b_sec = sub_region.time_b / 1000
            sub_target_dur = '_'
            sub_target_fps = '_'
            sub_target_fac = '_'
            if sub_region.target_duration:
              dur_in_secs = sub_region.target_duration / 1000
              sub_target_dur = '{:.2f}s'.format(dur_in_secs)
            if sub_region.target_rate:
              sub_target_fps = '{}'.format(sub_region.target_rate)
            if sub_region.target_factor:
              sub_target_fac = '{:.2f}'.format(sub_region.target_factor)
            sub_dur = dur_in_region / 1000.0
            tgt_dur = tgt_frs / float(self.playback_rate)
            write_ratio = frs_written * 100.0 / tgt_frs
            t = ('Region {}/{} F: [{}, {}] T: [{:.2f}s, {:.2f}s]\n'
                 'Len F: {}, T: {:.2f}s\n'
                 'Target Dur: {}, Fac: {}, fps: {}\n'
                 'Out Len F: {}, Dur: {:.2f}s\n'
                 'Drp every {:.1f}, Dup every {:.1f}\n'
                 'Gen: {}, Made: {}, Drp: {}, Dup: {}\n'
                 'Write Ratio: {}/{} ({:.2f}%)')
            t = t.format(self.curr_sub_region_idx,
                         self.num_sub_regions - 1,
                         fr_a,
                         fr_b,
                         sub_time_a_sec,
                         sub_time_b_sec,
                         frs_in_region,
                         sub_dur,
                         sub_target_dur,
                         sub_target_fac,
                         sub_target_fps,
                         tgt_frs, tgt_dur,
                         drop_every_n_frs,
                         dupe_every_n_frs,
                         frs_gen,
                         frs_made,
                         frs_dropped,
                         frs_duped,
                         frs_written,
                         tgt_frs,
                         write_ratio)

            for y, line in enumerate(t.split('\n')):
              line_sz, _ = cv2.cv.GetTextSize(line, font)
              line_w, line_h = line_sz
              origin = (int(self.vid_info.width - R_PADDING - line_w),
                        int(T_PADDING +
                        (y * (line_h + LINE_D_PADDING))))
              cv2.cv.PutText(img_mat, line, origin, font, font_color)

            fr_to_write = np.asarray(img_mat)
          if self.show_preview:
            vid_name = os.path.basename(config['video'])
            win_title = '{} - Butterflow'.format(vid_name)
            cv2.imshow(win_title, fr_to_write)
          self.write_frame_to_pipe(fr_to_write)

    if config['verbose']:
      print('frs_generated:', frs_gen)
      print('frs_made:', frs_made)
      print('frs_dropped:', frs_dropped)
      print('frs_duped:', frs_duped)

    fr_write_ratio = 0 if tgt_frs == 0 else frs_written * 1.0 / tgt_frs
    est_drift_secs = float(tgt_frs - frs_written) / self.playback_rate

    if config['verbose']:
      print('frs_written: {}/{} ({:.2f}%)'.format(
          frs_written, tgt_frs, fr_write_ratio * 100))
      print('est_drift:', est_drift_secs)

  def render(self, dst_path):
    '''separates video regions to render them individually'''
    self.total_frames_written = 0
    self.init_pipe(dst_path)
    src = OpenCvFrameSource(self.vid_info.video_path)

    if config['verbose']:
      print('src_dur', src.duration)
      print('src_frs', src.num_frames)

    new_sub_regions = []
    regions_to_make = 1

    if self.timing_regions is None:
      # create a region spanning from 0 to vids duration
      fa, ta = (0, 0)
      fb, tb = (src.num_frames - 1, src.duration)
      r = RenderingSubRegion(ta, tb)
      r.frame_a = fa
      r.frame_b = fb
      r.target_rate = self.playback_rate
      r.target_duration = tb - ta
      r.target_factor = 1.0
      setattr(r, 'trim', False)

      new_sub_regions.append(r)

    # update top region and subregions to sync with normalized video
    # update frames using relative positions because the video duration
    # and number of frames may have changed during normalization
    if self.timing_regions is not None:
      vid_dur_ms = src.duration
      vid_frs = src.num_frames - 1

      cut_points = set([])
      # add start and end of video cutting points:
      # (frame_idx, duration_ms)
      cut_points.add((0, 0))
      cut_points.add((vid_frs, src.duration))

      for sr in self.timing_regions:
        rel_a = sr.relative_pos_a
        rel_b = sr.relative_pos_b
        sr.resync_points(rel_a, rel_b, vid_dur_ms, vid_frs)
        cut_points.add((sr.frame_a, sr.time_a))
        cut_points.add((sr.frame_b, sr.time_b))

      cut_points = list(cut_points)
      cut_points = sorted(cut_points,
                          key=lambda(x): (x[0], x[1]),
                          reverse=False)
      regions_to_make = len(cut_points) - 1
      in_bounds = lambda(x): x.time_a >= 0 and x.time_b <= src.duration

      for x in xrange(0, regions_to_make):
        fa, ta = cut_points[x]
        fb, tb = cut_points[x + 1]

        region_for_range = None
        for r in self.timing_regions:
          if r.frame_a == fa and r.frame_b == fb:
            region_for_range = r
            setattr(r, 'trim', False)
            break

        if region_for_range is None:
          # create a new region that represents the original video with
          # with the only diff being a new playback rate. this will not
          # stretch or compress the time duration
          r = RenderingSubRegion(ta, tb)
          r.frame_a = fa
          r.frame_b = fb
          r.target_rate = self.playback_rate
          r.target_duration = tb - ta
          r.target_factor = 1.0
          region_for_range = r
          setattr(r, 'trim', self.vf_trim)

        new_sub_regions.append(r)

    VideoRegionUtils.validate_region_set(src.duration, new_sub_regions)

    for r in new_sub_regions:
      if config['verbose']:
        print(r.__dict__)
    if len(new_sub_regions) != regions_to_make:
      raise RuntimeError('unexpected len of subregions to render')

    self.num_sub_regions = len(new_sub_regions)
    for x, r in enumerate(new_sub_regions):
      self.curr_sub_region_idx = x
      if r.trim:
        continue
      self.render_subregion(src, r)

    cv2.destroyAllWindows()
    self.close_pipe()

  def __del__(self):
    '''closes the pipe if it was left open'''
    if self.pipe is not None:
      self.close_pipe()
