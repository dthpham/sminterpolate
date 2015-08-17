from __future__ import absolute_import

import os
import sys
import tempfile
from butterflow.__init__ import __version__
from butterflow import motion
import cv2


default = {
    'verbose':        False,
    'debug_opts':     False,
    # `ffmpeg` and `avconv` options
    'avutil':         'ffmpeg',
    # avutil and encoder loglevel
    # `info` is default, set to `fatal` for quiet
    'loglevel':       'fatal',
    'enc_loglevel':   'error',
    'preset':         'fast',
    'crf':            18,
    # farneback optical flow options
    'playback_rate':  23.976,
    'video_scale':    1.0,
    'pyr_scale':      0.5,
    'levels':         3,
    'winsize':        25,
    'iters':          3,
    'poly_n_choices': [5, 7],
    'poly_n':         7,
    'poly_s':         1.5,
    'fast_pyr':       False,
    'flow_filter':    'box',
    # -1 is max threads and it's the opencv default
    'ocv_threads':    1*-1,
    # debugging info font options
    'text_type':      'light',
    'light_color':    cv2.cv.RGB(255, 255, 255),
    'dark_color':     cv2.cv.RGB(0, 0, 0),
    # h_fits and v_fits is the minimium size in which the unscaled
    # CV_FONT_HERSHEY_PLAIN font text fits in the rendered video. The font is
    # scaled up and down based on this reference point
    'font':           cv2.cv.CV_FONT_HERSHEY_PLAIN,
    'text_thick':     1,
    'strk_thick':     2,
    'h_fits':         768,
    'v_fits':         216,
    't_padding':      20,
    'l_padding':      20,
    'r_padding':      20,
    'line_d_padding': 10,
}

if sys.platform.startswith('linux'):
    # for x265 options: http://x265.readthedocs.org/en/default/cli.html
    default['encoder'] = 'libx265'
else:
    default['encoder'] = 'libx264'

# define location of files and directories
default['out_path'] = os.path.join(os.getcwd(), 'out.mp4')

tempdir = tempfile.gettempdir()
default['tmp_dir'] = os.path.join(tempdir, 'butterflow-{}'.format(__version__))
default['clb_dir'] = os.path.join(default['tmp_dir'], 'clb')


# define interpolation and flow functions
default['flow_func'] = lambda x, y: \
    motion.ocl_farneback_optical_flow(
        x, y, default['pyr_scale'], default['levels'], default['winsize'],
        default['iters'], default['poly_n'], default['poly_s'],
        default['fast_pyr'], 0)
default['interpolate_func'] = motion.ocl_interpolate_flow


# override default settings with development settings
# ignore errors when `dev_settings.py` does not exist
# ignore errors when `default` variable is not defined in the file
try:
    from butterflow import dev_settings
    for k, v in dev_settings.default.items():
        default[k] = v
except ImportError:
    pass
except AttributeError:
    pass


# make temporary directories
for x in [default['clb_dir'], default['tmp_dir']]:
    if not os.path.exists(x):
        os.makedirs(x)

# set the location of the clb cache
motion.set_cache_path(default['clb_dir'] + os.sep)
