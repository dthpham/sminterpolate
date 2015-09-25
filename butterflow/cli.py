# Author: Duong Pham
# Copyright 2015

import os
import sys
import argparse
import collections
import math
from cv2 import calcOpticalFlowFarneback as sw_farneback_optical_flow
from butterflow.__init__ import __version__
from butterflow import avinfo, motion, ocl, settings
from butterflow.render import Renderer
from butterflow.sequence import VideoSequence, RenderSubregion

NO_OCL_WARNING = 'No compatible OCL devices detected. Check your OpenCL '\
                 'installation.'
NO_VIDEO_SPECIFIED_WARNING = 'No input video specified'


def main():
    import logging
    logging.basicConfig(level=settings.default['loglevel_a'],
                        format='%(levelname)-7s: %(message)s')

    par = argparse.ArgumentParser(usage='butterflow [options] [video]',
                                  add_help=False)
    req = par.add_argument_group('Required arguments')
    gen = par.add_argument_group('General options')
    dsp = par.add_argument_group('Display options')
    vid = par.add_argument_group('Video options')
    mux = par.add_argument_group('Muxing options')
    fgr = par.add_argument_group('Advanced options')

    req.add_argument('video', type=str, nargs='?', default=None,
                     help='Specify the input video')

    gen.add_argument('-h', '--help', action='help',
                     help='Show this help message and exit')
    gen.add_argument('-V', '--version', action='store_true',
                     help='Show program\'s version number and exit')
    gen.add_argument('-i', '--inspect', action='store_true',
                     help='Show video information and exit')
    gen.add_argument('-d', '--devices', action='store_true',
                     help='Show detected OpenCL devices and exit')
    gen.add_argument('-c', '--cache', action='store_true',
                     help='Show cache information and exit')
    gen.add_argument('--rm-cache', action='store_true',
                     help='Set to clear the cache and exit')
    gen.add_argument('-v', '--verbose', action='store_true',
                     help='Set to increase output verbosity')

    dsp.add_argument('-np', '--no-preview', action='store_false',
                     help='Set to disable video preview')
    dsp.add_argument('-a', '--add-info', action='store_true',
                     help='Set to embed debugging info into the output '
                          'video')
    dsp.add_argument('-tt', '--text-type',
                     choices=['light', 'dark', 'stroke'],
                     default=settings.default['text_type'],
                     help='Specify text type for debugging info, '
                     '(default: %(default)s)')

    vid.add_argument('-o', '--output-path', type=str,
                     default=settings.default['out_path'],
                     help='Specify path to the output video')
    vid.add_argument('-r', '--playback-rate', type=str,
                     help='Specify the playback rate as an integer or a '
                     'float. Fractional forms are acceptable. To use a '
                     'multiple of the source video\'s rate, follow a number '
                     'with `x`, e.g., "2x" will double the frame rate. The '
                     'original rate will be used by default if nothing is '
                     'specified.')
    vid.add_argument('-s', '--sub-regions', type=str,
                     help='Specify rendering subregions in the form: '
                     '"a=TIME,b=TIME,TARGET=VALUE" where TARGET is either '
                     '`fps`, `dur`, `spd`, `btw`. Valid TIME syntaxes are '
                     '[hr:m:s], [m:s], [s], [s.xxx], or `end`, which '
                     'signifies to the end the video. You can specify '
                     'multiple subregions by separating them with a colon '
                     '`:`. A special region format that conveniently '
                     'describes the entire clip is available in the form: '
                     '"full,TARGET=VALUE".')
    vid.add_argument('-t', '--trim-regions', action='store_true',
                     help='Set to trim subregions that are not explicitly '
                          'specified')
    vid.add_argument('-vs', '--video-scale', type=str,
                     default=str(settings.default['video_scale']),
                     help='Specify output video size in the form: '
                     '"WIDTH:HEIGHT" or by using a factor. To keep the '
                     'aspect ratio only specify one component, either width '
                     'or height, and set the other component to -1, '
                     '(default: %(default)s)')
    vid.add_argument('-l', '--lossless', action='store_true',
                     help='Set to use lossless encoding settings')

    mux.add_argument('-mux', action='store_true',
                     help='Set to mux the source audio with the output '
                     'video. Audio may not be in sync with the final video if '
                     'speed has been altered during the rendering process.')

    fgr.add_argument('--fast-pyr', action='store_true',
                     help='Set to use fast pyramids')
    fgr.add_argument('--pyr-scale', type=float,
                     default=settings.default['pyr_scale'],
                     help='Specify pyramid scale factor, '
                     '(default: %(default)s)')
    fgr.add_argument('--levels', type=int,
                     default=settings.default['levels'],
                     help='Specify number of pyramid layers, '
                     '(default: %(default)s)')
    fgr.add_argument('--winsize', type=int,
                     default=settings.default['winsize'],
                     help='Specify average window size, '
                     '(default: %(default)s)')
    fgr.add_argument('--iters', type=int,
                     default=settings.default['iters'],
                     help='Specify number of iterations at each pyramid '
                     'level, (default: %(default)s)')
    fgr.add_argument('--poly-n', type=int,
                     choices=settings.default['poly_n_choices'],
                     default=settings.default['poly_n'],
                     help='Specify size of pixel neighborhood, '
                     '(default: %(default)s)')
    fgr.add_argument('--poly-s', type=float,
                     default=settings.default['poly_s'],
                     help='Specify standard deviation to smooth derivatives, '
                     '(default: %(default)s)')
    fgr.add_argument('-ff', '--flow-filter', choices=['box', 'gaussian'],
                     default=settings.default['flow_filter'],
                     help='Specify which filter to use for optical flow '
                     'estimation, (default: %(default)s)')

    # make args that start with a negative number valid
    # needed for the -vs option
    for i, arg in enumerate(sys.argv):
        if (arg[0] == '-') and arg[1].isdigit():
            sys.argv[i] = ' ' + arg

    args = par.parse_args()

    log = logging.getLogger('butterflow')
    if args.verbose:
        log.setLevel(settings.default['loglevel_b'])

    if args.version:
        print(__version__)
        return 0

    if args.cache:
        print_cache_info()
        return 0

    if args.rm_cache:
        rm_cache()
        print('cache cleared')
        return 0

    have_ocl = ocl.ocl_device_available()
    if args.devices:
        if have_ocl:
            ocl.print_ocl_devices()
        else:
            print(NO_OCL_WARNING)
        return 0

    if have_ocl:
        set_clb_dir(settings.default['clb_dir'])
    else:
        print(NO_OCL_WARNING)
        return 1

    src_path = args.video
    if src_path is None:
        print(NO_VIDEO_SPECIFIED_WARNING)
        return 1

    if not os.path.exists(args.video):
        print('Video does not exist at path')
        return 1

    try:
        vid_info = avinfo.get_info(args.video)
    except Exception:
        log.error('Could not get video information:', exc_info=True)
        return 1

    if args.inspect:
        if args.video:
            print_vid_info(args.video)
        else:
            print(NO_VIDEO_SPECIFIED_WARNING)
        return 0

    if not vid_info['v_stream_exists']:
        log.error('No video stream detected')
        return 1

    # make subregions
    try:
        vid_sequence = sequence_from_str(
            vid_info['duration'], vid_info['frames'], args.sub_regions)
    except Exception as e:
        log.error('Bad subregion string: %s' % e)
        return 1

    # set playback rate
    src_rate = (vid_info['rate_n'] * 1.0 /
                vid_info['rate_d'])
    try:
        rate = rate_from_str(args.playback_rate, src_rate)
    except Exception as e:
        log.error('Bad playback rate: %s' % e)
        return 1
    if rate != src_rate:
        log.warning('rate : src_rate=%s rate=%s', src_rate, rate)

    # set video size
    try:
        w, h = w_h_from_str(args.video_scale, vid_info['w'], vid_info['h'])
    except Exception as e:
        log.error('Bad video scale: %s' % e)
        return 1

    # make functions that will generate flows and interpolate frames
    farneback_method = motion.ocl_farneback_optical_flow if have_ocl \
        else sw_farneback_optical_flow
    flags = 0
    if args.flow_filter == 'gaussian':
        import cv2
        flags = cv2.OPTFLOW_FARNEBACK_GAUSSIAN
    opt_flow_function = lambda x, y: \
        farneback_method(x, y, args.pyr_scale, args.levels, args.winsize,
                         args.iters, args.poly_n, args.poly_s, args.fast_pyr,
                         flags)

    # to pass to butterflow.draw.draw_debug_text
    flow_kwargs = collections.OrderedDict([
        ('Pyr', args.pyr_scale),
        ('L', args.levels),
        ('W', args.winsize),
        ('I', args.iters),
        ('PolyN', args.poly_n),
        ('PolyS', args.poly_s),
        ('Filt', flags)])

    renderer = Renderer(
        args.output_path,
        vid_info,
        vid_sequence,
        rate,
        opt_flow_function,
        motion.ocl_interpolate_flow,
        w,
        h,
        args.lossless,
        args.trim_regions,
        args.no_preview,
        args.add_info,
        args.text_type,
        flow_kwargs,
        args.mux)

    # set the number of threads and run
    motion.set_num_threads(settings.default['ocv_threads'])

    try:
        # time how long it takes to render
        # timeit will turn off gc, must turn it back on to maximize performance
        # re-nable it in the setup function
        import timeit
        tot_time = timeit.timeit(renderer.render,
                                 setup='import gc;gc.enable()',
                                 number=1)  # only run once
        print('Frames: src: {} int: {} dup: {} drp: {}'.format(
            renderer.tot_src_frs,
            renderer.tot_frs_int,
            renderer.tot_frs_dup,
            renderer.tot_frs_drp
        ))
        print('Write ratio: {}/{}, ({:.2f}%)'.format(
            renderer.tot_frs_wrt,
            renderer.tot_tgt_frs,
            renderer.tot_frs_wrt * 100.0 / renderer.tot_tgt_frs,
        ))
        print('Butterflow took {:.3g} minutes, done.'.format(tot_time / 60))
        # sizeit and show the diff
        new = sz_in_mb(args.output_path)
        old = sz_in_mb(args.video)
        log.debug('out file size: {:.3g} MB ({:+.3g} MB)'.format(new,
                                                                 new - old))
    except (KeyboardInterrupt, SystemExit):
        log.warning('files were left in the cache')
        return 1


def sz_in_mb(file):
    # file, path to file
    # get size of file in megabytes
    sz = float(os.path.getsize(file))
    sz_mb = sz / (1 << 20)
    return sz_mb


def set_clb_dir(dir):
    # set the location of the clb dir
    # make the folder if it doesn't exist
    if not os.path.exists(dir):
        os.makedirs(dir)
    motion.set_cache_path(dir + os.sep)


def print_cache_info():
    # print cache info
    # clb_dir exists inside the tmp_dir
    cache_dir = settings.default['tmp_dir']
    num_files = 0
    sz = 0
    for dirpath, dirnames, filenames in os.walk(cache_dir):
        # ignore the clb_dir
        if dirpath == settings.default['clb_dir']:
            continue
        for f in filenames:
            num_files += 1
            fp = os.path.join(dirpath, f)
            sz += os.path.getsize(fp)
    sz_mb = float(sz) / (1 << 20)  # size in megabytes
    print('{} files, {:.2g} MB'.format(num_files, sz_mb))


def rm_cache():
    # delete contents of cache, including the clb_dir
    cache_dir = settings.default['tmp_dir']
    if os.path.exists(cache_dir):
        import shutil
        shutil.rmtree(cache_dir)


def print_vid_info(video):
    info = avinfo.get_info(video)
    # use Fraction to reduce the display aspect ratio fraction
    from fractions import Fraction
    dar = Fraction(info['dar_n'],
                   info['dar_d'])
    # which streams are avail?
    # make a list then join for text
    streams = []
    if info['v_stream_exists']:
        streams.append('video')
    if info['a_stream_exists']:
        streams.append('audio')
    if info['s_stream_exists']:
        streams.append('subtitle')
    # calculate the src rate
    src_rate = (info['rate_n'] * 1.0 /
                info['rate_d'])
    print('Video information:'
          '\n  Streams available  \t: {}'
          '\n  Resolution         \t: {}x{}, SAR {}:{} DAR {}:{}'
          '\n  Rate               \t: {:.3f} fps'
          '\n  Duration           \t: {} ({:.2f}s)'
          '\n  Num of frames      \t: {}'.format(
              ','.join(streams),
              info['w'], info['h'],
              info['sar_n'], info['sar_d'],
              dar.numerator, dar.denominator,
              src_rate,
              ms_to_time_str(info['duration']), info['duration'] / 1000.0,
              info['frames']
          ))


def w_h_from_str(string, source_width, source_height):
    w = source_width
    h = source_height
    aspect = w * 1.0 / h
    if ':' in string:  # using w:h syntax
        w, h = string.split(':')
        w = int(w)
        h = int(h)
        # keep aspect ratio if either component is -1
        if w == -1:
            w = int(h / aspect)
        if h == -1:
            h = int(w / aspect)
    elif float(string) != 1.0:  # using a factor
        w = int(math.floor(w * float(string) / 2) * 2)
        h = int(math.floor(h * float(string) / 2) * 2)
    # w and h must be divisible by 2 for yuv420p outputs
    if math.fmod(w, 2) != 0 or math.fmod(h, 2) != 0:
        msg = "size {width}x{height}, component not divisible by two".\
            format(width=w, height=h)
        raise ValueError(msg)
    return w, h


def rate_from_str(string, source_rate):
    # allow fractional rates and fractions with non-rational numbers
    # use original rate if nothing is specified
    rate = 0
    if string is None:
        rate = source_rate
    else:
        if '/' in string and '.' in string:  # fraction with non-rational num
            num, den = rate.split('/')
            rate = float(num) / float(den)
        elif 'x' in string:  # used the "multiple of" syntax
            rate = float(string.replace('x', ''))
            rate = rate * source_rate
        else:  # used a singular integer or float
            rate = float(rate)
    return rate


def ms_to_time_str(time_ms):
    # converts a time in ms to a string in a friendly form
    # time str will be in form:
    # [hrs:mins:secs]
    import time
    t_str = time.strftime('%H:%M:%S', time.gmtime(time_ms / 1000.0))
    return t_str


def time_str_to_ms(time):
    # converts a time str to milliseconds
    # time str syntax:
    # [hrs:mins:secs.xxx], [mins:secs.xxx], [secs.xxx]
    hr = 0
    minute = 0
    sec = 0
    valid_char_set = '0123456789:.'
    if time == '' or time.count(':') > 2:
        raise ValueError('invalid syntax')
    for char in time:
        if char not in valid_char_set:
            raise ValueError('unknown char in time')
    val = time.split(':')
    val_len = len(val)
    # going backwards in the list
    # get secs.xxx portion
    if val_len >= 1:
        if val[-1] != '':
            sec = float(val[-1])
    # get mins portion
    if val_len >= 2:
        if val[-2] != '':
            minute = float(val[-2])
    # get hrs portion
    if val_len == 3:
        if val[-3] != '':
            hr = float(val[-3])
    return (hr * 3600 + minute * 60 + sec) * 1000.0


def parse_tval_str(string):
    # extract values from TARGET=VALUE string
    # target can be fps, dur, spd, or btw
    tgt = string.split('=')[0]
    val = string.split('=')[1]
    if tgt == 'fps':
        if '/' in val:
            # we can't create a Fraction then cast to a float because Fraction
            # won't take in non-rational numbers
            num, den = val.split('/')
            val = float(num) / float(den)
        else:
            val = float(val)
    elif tgt == 'dur':
        val = float(val) * 1000  # duration in ms
    elif tgt == 'spd' or tgt == 'btw':
        val = float(val)
    else:
        raise ValueError('invalid target')
    return tgt, val


def sub_from_str(string):
    # returns a subregion from string
    # input syntax:
    # a=<time>,b=<time>,TARGET=VALUE
    val = string.split(',')
    a = val[0].split('=')[1]  # the `a=` portion
    b = val[1].split('=')[1]  # the `b=` portion
    c = val[2]  # the `TARGET=VALUE` portion
    sub = RenderSubregion(time_str_to_ms(a),
                          time_str_to_ms(b))
    tgt, val = parse_tval_str(c)
    setattr(sub, tgt, val)
    return sub


def sub_from_str_full_key(string, duration):
    # returns a subregion from string with the `full` keyword
    # input syntax:
    # full,TARGET=VALUE
    val = string.split(',')
    if val[0] == 'full':
        # create a subregion from [0, duration]
        sub = RenderSubregion(0, float(duration))
        tgt, val = parse_tval_str(val[1])
        setattr(sub, tgt, val)
        return sub
    else:
        raise ValueError('full key not found')


def sub_from_str_end_key(string, duration):
    # returns a subregion from string with the `end` keyword
    # input syntax:
    # a=<time>,b=end,TARGET=VALUE
    val = string.split(',')
    b = val[1].split('=')[1]  # the `b=` portion
    if b == 'end':
        # replace the `end` with the duration of the video in seconds. the
        # duration will be converted to ms automatically
        string = string.replace('end', str(duration / 1000.0))
        return sub_from_str(string)
    else:
        raise ValueError('end key not found')


def sequence_from_str(duration, frames, strings):
    # return a vid sequence from -s <subregion>:<subregion>...
    seq = VideoSequence(duration, frames)
    if strings is None:
        return seq
    # look for `:a` which is the start of a new subregion
    newsubstrs = []
    substrs = strings.split(':a')
    if len(substrs) > 1:
        # replace `a` character that was stripped when split
        for substr in substrs:
            if not substr.startswith('a'):
                newsubstrs.append('a' + substr)
            else:
                newsubstrs.append(substr)
        substrs = newsubstrs
    for substr in substrs:
        sub = None
        # has the full key
        if 'full' in substr:
            sub = sub_from_str_full_key(substr, duration)
        # has the end key
        elif 'end' in substr:
            sub = sub_from_str_end_key(substr, duration)
        else:
            sub = sub_from_str(substr)
        seq.add_subregion(sub)
    return seq
