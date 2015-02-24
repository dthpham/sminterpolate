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

NO_AVUTIL_WARNING = 'You need FFMPEG or Libav to use this app.'
NO_OCL_WARNING = 'No compatible OCL devices detected. Check your OpenCL '\
                 'installation.'
NO_VID_WARNING = 'No input video specified'
EPILOG = 'Send bugs and questions to dthpham@gmail.com.'


def main():
  par = argparse.ArgumentParser(usage='%(prog)s [options] [video]',
                                add_help=False,
                                epilog=EPILOG)
  req = par.add_argument_group('Required arguments')
  gen = par.add_argument_group('General arguments')
  vid = par.add_argument_group('Video arguments')
  fgr = par.add_argument_group('Advanced arguments')

  req.add_argument('video', type=str, nargs='?', default=None,
                   help='Specify the input video')

  gen.add_argument('-h', '--help', action='help',
                   help='Show this help message and exit')
  gen.add_argument('-V', '--version', action='store_true',
                   help='Show program\'s version number and exit')
  gen.add_argument('-d', '--devices', action='store_true',
                   help='Show detected OpenCL devices and exit')
  gen.add_argument('-v', '--verbose', action='store_true',
                   help='Set to increase output verbosity')
  gen.add_argument('--no-preview', action='store_false',
                   help='Set to disable video preview')
  gen.add_argument('--preview-flows', action='store_true',
                   help='Set to preview optical flows')
  gen.add_argument('--render-flows', action='store_true',
                   help='Set to render optical flows and write them to a file')
  gen.add_argument('--render-info', action='store_true',
                   help='Set to add debugging info into the output video')

  vid.add_argument('-o', '--output-path', type=str,
                   default=os.path.join(os.getcwd(), 'out.mp4'),
                   help='Specify path to the output video')
  vid.add_argument('-r', '--playback-rate', type=str, default='23.976',
                   help='Specify the playback rate, '
                        '(default: %(default)s)')
  vid.add_argument('-s', '--sub-regions', type=str,
                   help='Specify rendering sub regions in the form: '
                   '"a=TIME,b=TIME,TARGET=FLOAT" where '
                   'TARGET is either `fps`, `duration`, `factor`. '
                   'Valid TIME syntaxes are [hr:m:s], [m:s], [s.xxx], '
                   'or `end`. You can specify multiple sub regions by '
                   'separting them with a semi-colon `;`. A special region '
                   'format that conveniently describes the entire clip is '
                   'available in the form: "full,TARGET=FLOAT".')

  vid.add_argument('-t', '--trim-regions', action='store_true',
                   help='Set to trim subregions that are not explicity '
                        'specified')
  vid.add_argument('-vs', '--video-scale', type=float, default=1.0,
                   help='Specify the output video scale, '
                        '(default: %(default)s)')
  vid.add_argument('-l', '--lossless', action='store_true',
                   help='Set to use lossless encoding settings')
  vid.add_argument('--decimate', action='store_true',
                   help='Set to decimate duplicate frames')
  vid.add_argument('--grayscale', action='store_true',
                   help='Set to enhance grayscale coloring')

  fgr.add_argument('--fast-pyr', action='store_true',
                   help='Set to use fast pyramids')
  fgr.add_argument('--pyr-scale', type=float, default=0.5,
                   help='Specify pyramid scale factor, (default: %(default)s)')
  fgr.add_argument('--levels', type=int, default=3,
                   help='Specify number of pyramid layers, '
                   '(default: %(default)s)')
  fgr.add_argument('--winsize', type=int, default=25,
                   help='Specify average window size, (default: %(default)s)')
  fgr.add_argument('--iters', type=int, default=3,
                   help='Specify number of iterations at each pyramid level, '
                   '(default: %(default)s)')
  fgr.add_argument('--poly-n', type=int, choices=[5, 7], default=7,
                   help='Specify size of pixel neighborhood, '
                   '(default: %(default)s)')
  fgr.add_argument('--poly-s', type=float, default=1.5,
                   help='Specify standard deviation to smooth derivatives, '
                   '(default: %(default)s)')
  fgr.add_argument('-ff', '--flow-filter', choices=['box', 'gaussian'],
                   default='box',
                   help='Specify which filter to use for optical flow '
                   'estimation, (default: %(default)s)')

  args = par.parse_args()
  config.update(dict(vars(args)))

  if args.version:
    print(__version__)
    exit(0)

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
    print(NO_VID_WARNING)
    exit(0)

  if config['avutil'] == 'none':
    print(NO_AVUTIL_WARNING)
    exit(1)

  dst_path = args.output_path
  playback_rate = args.playback_rate
  timing_regions = args.sub_regions
  farneback_method = Flow.farneback_optical_flow_ocl if have_ocl \
      else Flow.farneback_optical_flow
  flags = 0
  if args.flow_filter == 'gaussian':
    import cv2
    flags = cv2.OPTFLOW_FARNEBACK_GAUSSIAN
  flow_method = lambda(x, y): \
      farneback_method(x, y, args.pyr_scale, args.levels, args.winsize,
                       args.iters, args.poly_n, args.poly_s, args.fast_pyr,
                       flags)
  interpolate_method = Interpolate.interpolate_frames_ocl if have_ocl \
      else Interpolate.interpolate_frames

  project = Project.new(src_path)

  project.video_path = src_path
  # Allow fractional rates to have floating point numerators and denominators
  if '/' in playback_rate and '.' in playback_rate:
    n, d = playback_rate.split('/')
    playback_rate = float(n) / float(d)
  project.playback_rate = Fraction(playback_rate)
  project.flow_method = flow_method
  project.interpolate_method = interpolate_method
  if timing_regions is not None:
    project.set_timing_regions_with_string(timing_regions)

  project.render_video(dst_path, args.video_scale, args.decimate,
                       args.grayscale, args.lossless, args.trim_regions,
                       args.no_preview, args.render_flows)
