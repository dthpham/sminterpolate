from __future__ import absolute_import

import os
import sys
import tempfile
from butterflow.__init__ import __version__
from butterflow import motion
import cv2
import logging


default = {
    'debug_opts':     False,
    # default logging level
    # levels in order of urgency: critical, error, warning, info, debug
    'loglevel_a':     logging.ERROR,
    # loglevel will be set to `DEBUG` if verbose is True
    'loglevel_b':     logging.DEBUG,
    'verbose':        False,
    # only support `ffmpeg` for now
    'avutil':         'ffmpeg',
    # avutil and encoder loglevel
    # `info` is default, set to `fatal` for quiet
    'av_loglevel':    'fatal',
    'enc_loglevel':   'error',
    # See: https://trac.ffmpeg.org/wiki/Encode/H.264#a2.Chooseapreset
    # presets: ultrafast, superfast, veryfast, faster, fast, medium, slow,
    # slower, veryslow
    'preset':         'veryslow',
    'crf':            18,  # visually lossless
    # scaling opts
    'video_scale':    1.0,
    'scaler_up':      cv2.cv.CV_INTER_AREA,
    # `CV_INTER_CUBIC` looks best but is slower, `CV_INTER_LINEAR` is faster
    # but still looks okay
    'scaler_dn':      cv2.cv.CV_INTER_CUBIC,
    # farneback optical flow options
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
    # milliseconds to display image in preview window
    'imshow_ms':      1,
    # debug text settings
    'text_type':      'light',  # other options: `dark`, `stroke`
    'light_color':    cv2.cv.RGB(255, 255, 255),
    'dark_color':     cv2.cv.RGB(0, 0, 0),
    # h_fits and v_fits is the minimium size in which the unscaled
    # CV_FONT_HERSHEY_PLAIN font text fits in the rendered video. The font is
    # scaled up and down based on this reference point
    'font_face':      cv2.cv.CV_FONT_HERSHEY_PLAIN,
    'font_type':      cv2.cv.CV_AA,
    'txt_thick':      1,
    'strk_thick':     2,
    'h_fits':         768,
    'v_fits':         216,
    'txt_t_pad':      20,
    'txt_l_pad':      20,
    'txt_r_pad':      20,
    'txt_ln_b_pad':   10,    # spacing between lines
    'txt_min_scale':  0.6,   # don't draw if the font is scaled below this
    'txt_placeh':     '_',   # placeholder if value in fmt text is None
    # progress bar settings
    'bar_t_pad':      0.7,   # relative padding from the top
    'bar_s_pad':      0.12,  # relative padding on each side
    'ln_thick':       3,     # pixels of lines that make outer rectangle
    'strk_sz':        1,     # size of the stroke in pixels
    'ln_type':        cv2.cv.CV_FILLED,  # -1, a filled line
    'bar_in_pad':     3,     # padding from the inner bar
    'bar_thick':      15,    # thickness of the inner bar
    'bar_color':      cv2.cv.RGB(255, 255, 255),
    'bar_strk_color': cv2.cv.RGB(192, 192, 192),
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
