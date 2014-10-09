import argparse
from motion.flow import Flow
from motion.interpolate import Interpolate
import motion.py_motion as py_motion
from project import Project
from fractions import Fraction
import os
from os.path import expanduser
import subprocess
import motion.py_motion as py_motion
from __init__ import __version__, cache_path


_NO_OCL_WARNING =\
    'No compatible OCL device available. Check your OpenCL installation.'


def main():
  have_ocl = py_motion.py_ocl_device_available()

  par = argparse.ArgumentParser(version=__version__)
  par.add_argument('-d', '--devices', action='store_true',
                   help='Show detected OpenCL devices and exit')

  par.add_argument('video', type=str, nargs='?', default=None,
                   help='Specify the input video')
  par.add_argument('-o', '--output-path', type=str, nargs='?',
                   default=os.path.join(os.getcwd(), 'out.mp4'),
                   help='Set path to the output video')

  par.add_argument('-p', '--preview', action='store_true',
                   help='Set to show video preview while encoding')

  par.add_argument('-r', '--playback-rate', type=str, nargs='?',
                   default='23.976',
                   help='Specify the playback rate, '
                        '(default: %(default)s)')
  par.add_argument('-t', '--timing-regions', type=str, nargs='?',
                   help='Specify rendering sub regions')

  par.add_argument('--video-scale', type=float, default=1.0,
                   help='Set the output video scale, '
                        '(default: %(default)s)')
  par.add_argument('--decimate', action='store_true',
                   help='Specify if should decimate duplicate frames')

  par.add_argument('--pyr-scale', type=float, default=0.6,
                   help='Set pyramid scale factor, '
                        '(default: %(default)s)')
  par.add_argument('--levels', type=int, default=3,
                   help='Set number of pyramid layers, '
                        '(default: %(default)s)')
  par.add_argument('--winsize', type=int, default=25,
                   help='Set average window size, '
                        '(default: %(default)s)')
  par.add_argument('--iters', type=int, default=3,
                   help='Set number of iterations at each pyramid level, '
                        '(default: %(default)s)')
  par.add_argument('--poly-n', type=int, default=7,
                   help='Set size of pixel neighborhood, '
                        '(default: %(default)s)')
  par.add_argument('--poly-s', type=float, default=1.5,
                   help='Set standard deviation to smooth derivatives, '
                        '(default: %(default)s)')

  args = par.parse_args()

  if args.devices:
    py_motion.py_print_ocl_devices()
    if not have_ocl:
      print(_NO_OCL_WARNING)
    exit(0)

  if have_ocl:
    py_motion.py_ocl_set_cache_path(cache_path + os.sep)
  else:
    print(_NO_OCL_WARNING)
    exit(1)

  src_path = args.video
  if src_path is None:
    print('No input video specified.')
    exit(0)

  dst_path = args.output_path
  playback_rate = args.playback_rate
  timing_regions = args.timing_regions

  farneback_method = Flow.farneback_optical_flow_ocl if have_ocl \
      else Flow.farneback_optical_flow
  flow_method = lambda(x, y): \
      farneback_method(x, y, args.pyr_scale, args.levels, args.winsize,
                       args.iters, args.poly_n, args.poly_s, 0)
  interpolate_method = Interpolate.interpolate_frames_ocl if have_ocl \
      else Interpolate.interpolate_frames

  try:
    project = Project.new(src_path)
  except Exception as error:
    print(error)
    exit(1)

  project.video_path = src_path
  project.playback_rate = Fraction(playback_rate)
  project.flow_method = flow_method
  project.interpolate_method = interpolate_method
  if timing_regions is not None:
    project.set_timing_regions_with_string(timing_regions)

  try:
    project.render_video(dst_path, args.video_scale, args.decimate,
                         show_preview=args.preview)
  except Exception as error:
    print(error)
    exit(1)
