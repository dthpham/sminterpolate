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
from .butterflow import config


def main():
  par = argparse.ArgumentParser()
  par.add_argument('-V', '--version', action='store_true',
                   help='Show program\'s version number and exit')
  par.add_argument('-v', '--verbose', action='store_true',
                   help='Set to increase output verbosity')
  par.add_argument('-d', '--devices', action='store_true',
                   help='Show detected OpenCL devices and exit')
  par.add_argument('--no-preview', action='store_false',
                   help='Set to disable video preview while encoding')
  par.add_argument('--embed-info', action='store_true',
                   help='Set to embed debugging info into the output video')

  par.add_argument('video', type=str, nargs='?', default=None,
                   help='Specify the input video')

  par.add_argument('-o', '--output-path', type=str,
                   default=os.path.join(os.getcwd(), 'out.mp4'),
                   help='Set path to the output video')
  par.add_argument('-r', '--playback-rate', type=str, default='23.976',
                   help='Specify the playback rate, '
                        '(default: %(default)s)')
  par.add_argument('-s', '--sub-regions', type=str,
                   help='Specify rendering sub regions in the form: '
                   '"a=TIME,b=TIME,TARGET=FLOAT" where '
                   'TARGET is either `fps`, `duration`, `factor`. '
                   'Valid TIME syntaxes are [hr:m:s], [m:s], or [s.xxx]. '
                   'You can specify multiple sub regions by separting them '
                   'with a semi-colon `;`. A special region format that '
                   'conveniently describes the entire clip is available in '
                   'the form: "full,TARGET=FLOAT".')

  par.add_argument('--trim', action='store_true',
                   help='Set to trim subregions that are not explicity '
                        'specified')
  par.add_argument('--video-scale', type=float, default=1.0,
                   help='Set the output video scale, '
                        '(default: %(default)s)')
  par.add_argument('--decimate', action='store_true',
                   help='Specify if should decimate duplicate frames')
  par.add_argument('--grayscale', action='store_true',
                   help='Specify to enhance grayscale coloring')

  fgr = par.add_argument_group('advanced arguments')
  fgr.add_argument('--pyr-scale', type=float, default=0.5,
                   help='Set pyramid scale factor, (default: %(default)s)')
  fgr.add_argument('--levels', type=int, default=3,
                   help='Set number of pyramid layers, (default: %(default)s)')
  fgr.add_argument('--winsize', type=int, default=25,
                   help='Set average window size, (default: %(default)s)')
  fgr.add_argument('--iters', type=int, default=3,
                   help='Set number of iterations at each pyramid level, '
                   '(default: %(default)s)')
  fgr.add_argument('--poly-n', type=int, default=7,
                   help='Set size of pixel neighborhood, '
                   '(default: %(default)s)')
  fgr.add_argument('--poly-s', type=float, default=1.5,
                   help='Set standard deviation to smooth derivatives, '
                   '(default: %(default)s)')

  args = par.parse_args()
  config['args'] = args

  if args.version:
    print(__version__)
    exit(0)

  NO_OCL_WARNING = 'No compatible OCL devices detected. Check your OpenCL '\
                   'installation.'

  have_ocl = py_motion.py_ocl_device_available()
  if args.devices:
    py_motion.py_print_ocl_devices()
    if not have_ocl:
      print(NO_OCL_WARNING)
    exit(0)

  if have_ocl:
    py_motion.py_ocl_set_cache_path(cache_path + os.sep)
  else:
    print(NO_OCL_WARNING)
    exit(1)

  src_path = args.video
  if src_path is None:
    print('No input video specified.')
    exit(0)

  if config['avutil'] == 'none':
    print('You need FFMPEG or Libav to use this app.')
    exit(1)

  dst_path = args.output_path
  playback_rate = args.playback_rate
  timing_regions = args.sub_regions

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

  project.render_video(dst_path, args.video_scale, args.decimate,
                       show_preview=args.no_preview)
