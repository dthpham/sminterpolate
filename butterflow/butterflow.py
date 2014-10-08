import argparse
from motion.flow import Flow
from motion.interpolate import Interpolate
import motion.py_motion as py_motion
from project import Project
from fractions import Fraction
import os
from os.path import expanduser

_NO_OCL_WARNING =\
    'No compatible OCL device available. Check your OpenCL installation'


def main():
  user_home = expanduser('~')
  config_path = os.path.join(user_home, '.butterflow')
  cache_path = os.path.join(config_path, 'cache')
  if not os.path.exists(config_path):
    os.makedirs(config_path)
  if not os.path.exists(cache_path):
    os.makedirs(cache_path)

  have_ocl = py_motion.py_ocl_device_available()

  par = argparse.ArgumentParser(version='0.1')

  par.add_argument('-d', '--ocl-devices', action='store_true',
                   help='List detected OpenCL devices')
  args = par.parse_known_args()
  if args[0].ocl_devices:
    py_motion.py_print_ocl_devices()
    if not have_ocl:
      print(_NO_OCL_WARNING)
    exit(0)

  par.add_argument('video', type=str, help='Specify the input video')

  par.add_argument('-r', '--playback-rate', type=str, nargs='?',
                   default='24000/1001', help='Specify the playback rate')
  par.add_argument('-t', '--timing-regions', type=str, nargs='?',
                   help='Specify rendering sub regions')

  par.add_argument('-o', '--out-path', type=str, nargs='?',
                   default=os.path.join(os.getcwd(), 'out.mp4'),
                   help='Set path to the output video')

  par.add_argument('--video-scale', type=float, default=1.0,
                   help='Set the video scale')
  par.add_argument('--decimate', action='store_true',
                   help='Specify if should decimate duplicate frames')

  par.add_argument('--pyr-scale', type=float, default=0.5,
                   help='Set pyramid scale factor')
  par.add_argument('--levels', type=int, default=3,
                   help='Set number of pyramid layers')
  par.add_argument('--winsize', type=int, default=15,
                   help='Set average window size')
  par.add_argument('--iters', type=int, default=3,
                   help='Set number of iterations at each pyramid level')
  par.add_argument('--poly-n', type=int, default=7,
                   help='Set size of pixel neighborhood')
  par.add_argument('--poly-s', type=float, default=1.5,
                   help='Set standard deviation to smooth derivatives')

  args = par.parse_args()

  src_path = args.video
  dst_path = args.out_path
  playback_rate = args.playback_rate
  timing_regions = args.timing_regions

  if have_ocl:
    py_motion.py_ocl_set_cache_path(cache_path)
  else:
    print(_NO_OCL_WARNING)
    exit(1)

  farneback_method = Flow.farneback_optical_flow_ocl if have_ocl \
      else Flow.farneback_optical_flow
  flow_method = lambda(x, y): \
      farneback_method(x, y, args.pyr_scale, args.levels, args.winsize,
                       args.iters, args.poly_n, args.poly_s, 0)
  interpolate_method = Interpolate.interpolate_frames_ocl if have_ocl \
      else Interpolate.interpolate_frames

  project = Project.new(src_path)
  project.video_path = src_path
  project.playback_rate = Fraction(playback_rate)
  project.flow_method = flow_method
  project.interpolate_method = interpolate_method
  if timing_regions is not None:
    project.set_timing_regions_with_string(timing_regions)

  project.render_video(dst_path, args.video_scale, args.decimate)
