# -*- coding: utf-8 -*-

import os
import logging
import tempfile
import cv2
import ocl
from butterflow.__init__ import __version__


default = {
    'debug_opts':     False,
    # show first and last n runs, -1 to show all
    'debug_show_n_runs':            15,
    'debug_show_progress_period':   0.1,  # show progress every % if snipped
    # default logging level
    # levels in order of urgency: critical, error, warning, info, debug
    'loglevel_0':     logging.WARNING,
    # loglevel will be set to INFO if verbose count is x
    'loglevel_1':     logging.INFO,
    'loglevel_2':     logging.DEBUG,
    'verbose':        False,
    'quiet':          False,
    # quiet loglevel
    'loglevel_quiet': logging.ERROR,
    # only support ffmpeg for now, can change to avutil if needed
    # Documentation: https://ffmpeg.org/ffmpeg.html
    'avutil':         'ffmpeg',
    # avutil and encoder loglevel
    # options: panic, fatal, error, warning, info, verbose, debug, trace
    'av_loglevel':    'error',  # `info` is default
    # default loglevel is `info` for x264 and x265
    # x265 opts: `none`, `error`, `warning`, `info`, `debug`, plus `full`
    'enc_loglevel':   'info',
    # x265 is considered a work in progress and is under heavy development
    # + 50-75% more compression efficiency than x264
    # + retains same visual quality
    # - veryslow preset encoding speed is noticeably slower than x264
    # for x265 options, See: http://x265.readthedocs.org/en/default/cli.html
    #
    # x264 is stable and used in many popular video conversion tools
    # + uses gpu for some lookahead ops but doesn't mean algos are optimized
    # + well tuned for high quality encodings
    'cv':             'libx264',
    # See: https://trac.ffmpeg.org/wiki/Encode/H.264
    # See: https://trac.ffmpeg.org/wiki/Encode/H.264#a2.Chooseapreset
    # presets: ultrafast, superfast, veryfast, faster, fast, medium, slow,
    # slower, veryslow
    'preset':         'veryslow',
    'crf':            18,       # visually lossless
    # scaling opts
    'video_scale':    1.0,
    'scaler_up':      cv2.cv.CV_INTER_AREA,
    # CV_INTER_CUBIC looks best but is slower, CV_INTER_LINEAR is faster but
    # still looks okay
    'scaler_dn':      cv2.cv.CV_INTER_CUBIC,
    # muxing opts
    'v_container':    'mp4',
    # See: https://trac.ffmpeg.org/wiki/Encode/HighQualityAudio
    'a_container':    'm4a',   # will keep some useful metadata
    # audio codec and quality
    # See: https://trac.ffmpeg.org/wiki/Encode/AAC
    'ca':             'aac',   # built in encoder, doesnt require an ext lib
    'ba':             '192k',  # bitrate, usable >= 192k
    'qa':             4,       # quality scale of audio from 0.1 to 10
    # location of files and directories
    'out_path':       os.path.join(os.getcwd(), 'out.mp4'),
    # since value of tempfile.tempdir is None python will search std list of
    # dirs and will select the first one that the user can create a file in
    # See: https://docs.python.org/2/library/tempfile.html#tempfile.tempdir
    #
    # butterflow will write renders to a temp file in tempdir and will move it
    # to it's destination path when completed using shutil.move(). if the dest
    # is on the current filesystem then os.rename() is used, otherwise the file
    # is copied with shutil.copy2 then removed
    'tempdir':        os.path.join(tempfile.gettempdir(),
                                   'butterflow-{}'.format(__version__)),
    # farneback optical flow options
    'pyr_scale':      0.5,
    'levels':         3,
    'winsize':        25,
    'iters':          3,
    'poly_n_choices': [5, 7],
    'poly_n':         5,
    'poly_s':         1.1,
    'fast_pyr':       False,
    'flow_filter':    'box',
    # -1 is max threads and it's the opencv default
    'ocv_threads':    -1,    # 0 will disable threading optimizations
    # milliseconds to display image in preview window
    'imshow_ms':      1,
    # debug text settings
    'text_type':      'light',      # other options: `dark`, `stroke`
    'light_color':    cv2.cv.RGB(255, 255, 255),
    'dark_color':     cv2.cv.RGB(0, 0, 0),
    # h_fits and v_fits is the minimium size in which the unscaled
    # CV_FONT_HERSHEY_PLAIN font text fits in the rendered video. The font is
    # scaled up and down based on this reference point
    'font_face':      cv2.cv.CV_FONT_HERSHEY_PLAIN,
    'font_type':      cv2.cv.CV_AA,
    'txt_max_scale':  1.0,
    'txt_thick':      1,
    'txt_stroke_thick':  2,
    'txt_w_fits':     768,
    'txt_h_fits':     216,
    'txt_t_pad':      30,
    'txt_l_pad':      20,
    'txt_r_pad':      20,
    'txt_ln_b_pad':   10,    # spacing between lines
    'txt_min_scale':  0.55,  # don't draw if the font is scaled below this
    'txt_placeh':     '?',   # placeholder if value in fmt text is None
    # progress bar settings
    'bar_w_fits':     420,
    'bar_h_fits':     142,
    'bar_t_pad':      0.7,   # relative padding from the top
    'bar_s_pad':      0.12,  # relative padding on each side
    'bar_ln_thick':   3,     # pixels of lines that make outer rectangle
    'bar_stroke_thick':  1,  # size of the stroke in pixels
    'bar_ln_type':    cv2.cv.CV_FILLED,  # -1, a filled line
    'bar_in_pad':     3,     # padding from the inner bar
    'bar_thick':      15,    # thickness of the inner bar
    'bar_color':      cv2.cv.RGB(255, 255, 255),
    'bar_stroke_color':  cv2.cv.RGB(192, 192, 192),
    # frame marker settings
    'mrk_w_fits':     572,
    'mrk_h_fits':     142,
    'mrk_d_pad':      20,
    'mrk_r_pad':      20,
    'mrk_out_thick':  -1,    # -1, a filled circle
    'mrk_out_radius': 6,
    'mrk_in_thick':   -1,
    'mrk_in_radius':  4,
    'mrk_ln_type':    cv2.cv.CV_AA,
    'mrk_out_color':  cv2.cv.RGB(255, 255, 255),
    'mrk_color':      cv2.cv.RGB(255, 255, 255),
    'mrk_fill_color': cv2.cv.RGB(255, 0, 0)
}

default['clbdir'] = os.path.join(default['tempdir'], 'clb')  # ocl cache files

# override default settings with development settings
# ignore errors when dev_settings.py does not exist
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
for x in [default['clbdir'], default['tempdir']]:
    if not os.path.exists(x):
        os.makedirs(x)

# set the location of the clb cache
ocl.set_cache_path(default['clbdir'] + os.sep)
