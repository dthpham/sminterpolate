from media.source import OpenCvFrameSource
import cv2
import subprocess
from motion.interpolate import Interpolate
import numpy as np
import os
import math
import pdb
from region import VideoRegionUtils, RenderingSubRegion


class Renderer(object):
  '''renders an interpolated video based on information supplied in
  project settings most important info: video info, playback
  rate, timing regions, and flow method, interpolation method. this
  only creates a video. audio/subs will not be muxed in here
  '''
  def __init__(self, vid_info, playback_rate, timing_regions, flow_method,
               interpolate_method, loglevel='fatal'):
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

  def init_pipe(self, dst_path):
    '''create pipe to ffmpeg/libav, which will encode the video for us'''
    self.pipe = subprocess.Popen([
        'ffmpeg',
        '-loglevel', self.loglevel,
        '-y',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', '{}x{}'.format(self.vid_info.width, self.vid_info.height),
        '-r', str(self.playback_rate),
        '-i', '-',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'none',
        '-c:v', 'libx264',
        '-preset', 'slow',
        '-crf', '18',
        '-r', str(self.playback_rate),
        dst_path],
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
      fr_factor = tgt_frs * 1.0 / frs_in_region
      time_step = 1 / fr_factor

    if sub_region.target_rate:
      reg_dur_secs = dur_in_region / 1000
      tgt_frs = int(sub_region.target_rate * reg_dur_secs)
      fr_factor = tgt_frs * 1.0 / frs_in_region
      time_step = 1 / fr_factor

    time_step = min(time_step, 1.0)

    drop_every_n_frs = 0.0
    dupe_every_n_frs = 0.0

    # if 1.0 % time_step is zero, one less frame will be interpolated
    # See: loop in the interpolate frames method
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

    # pdb.set_trace()

    frs_made = 0
    frs_dropped = 0
    frs_duped = 0
    frs_written = 0
    frs_gen = 1
    wrk_idx = 0

    fr_1 = None
    fr_2 = src.frame_at_idx(fr_a) # TODO: missing that first frame?
    src.seek_to_frame(fr_a+1)

    for x in xrange(0, frs_in_region - 1):
      ch = 0xff & cv2.waitKey(30)
      if ch == 23:
        break

      new_frs = []
      fr_1 = fr_2
      try:
        fr_2 = src.read_frame()
      except Exception as ex:
        print('couldn\'t read a frame {} breaking: {}'.format(x, ex))
        break
      frs_gen += 1

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
        cv2.imshow(os.path.basename(vid_name), fr)
        wrk_idx += 1

        if drop_every_n_frs > 0:
          drop_rem = math.fmod(wrk_idx, drop_every_n_frs)
          should_drop = drop_rem < 1.0
          if should_drop:
            # print('DRP <idx={0:0>6d}, rem={1:.2f}>'.format(wrk_idx, drop_rem))
            frs_dropped += 1
            continue
        if dupe_every_n_frs > 0:
          dupe_rem = math.fmod(wrk_idx, dupe_every_n_frs)
          should_dupe = dupe_rem < 1.0
          if should_dupe:
            # print('DUP <idx={0:0>6d}, rem={1:.2f}>'.format(wrk_idx, dupe_rem))
            self.write_frame_to_pipe(fr)
            frs_duped += 1

        self.write_frame_to_pipe(fr)
        frs_written += 1

    print('frs_generated:', frs_gen)
    print('frs_made:', frs_made)
    print('frs_dropped:', frs_dropped)
    print('frs_duped:', frs_duped)

    fr_write_ratio = frs_written * 1.0 / tgt_frs
    est_drift_secs = float(tgt_frs - frs_written) / self.playback_rate

    print('frs_written: {}/{} ({:.2f}%)'.format(
        frs_written, tgt_frs, fr_write_ratio * 100))
    print('est_drift:', est_drift_secs)

    # pdb.set_trace()

  def render(self, dst_path):
    '''separates video regions to render them individually'''
    self.init_pipe(dst_path)
    src = OpenCvFrameSource(self.vid_info.video_path)

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

      new_sub_regions.append(r)

    # update top region and subregions to sync with normalized video
    # update frames using relative positions because the video duration
    # and number of frames may have changed during normalization
    if self.timing_regions is not None:
      vid_dur_ms = src.duration
      vid_frs = src.num_frames

      cut_points = set([])
      # add start and end of video cutting points:
      # (frame_idx, duration_ms)
      cut_points.add((0, 0))
      cut_points.add((src.num_frames - 1, src.duration))

      for sr in self.timing_regions:
        rel_a = sr.relative_pos_a
        rel_b = sr.relative_pos_b
        sr.resync_points(rel_a, rel_b, vid_dur_ms, vid_frs)
        cut_points.add((sr.frame_a, sr.time_a))
        cut_points.add((sr.frame_b, sr.time_b))

      cut_points = list(cut_points)
      cut_points = sorted(cut_points, key=lambda(x, y): x, reverse=False)
      regions_to_make = len(cut_points) - 1
      in_bounds = lambda(x): x.time_a >= 0 and x.time_b <= src.duration

      for x in xrange(0, regions_to_make):
        fa, ta = cut_points[x]
        fb, tb = cut_points[x + 1]

        region_for_range = None
        for r in self.timing_regions:
          if r.frame_a == fa and r.frame_b == fb:
            region_for_range = r
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
          region_for_range = r

        new_sub_regions.append(r)

    VideoRegionUtils.validate_region_set(src.duration, new_sub_regions)

    for x in new_sub_regions:
      print(x.__dict__)
    if len(new_sub_regions) != regions_to_make:
      raise RuntimeError('unexpected len of subregions to render')

    for r in new_sub_regions:
      self.render_subregion(src, r)

    cv2.destroyAllWindows()
    self.close_pipe()

  def __del__(self):
    '''closes the pipe if it was left open'''
    if self.pipe is not None:
      self.close_pipe()
