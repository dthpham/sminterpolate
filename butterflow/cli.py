from __future__ import absolute_import

import os
import argparse
import collections
from cv2 import calcOpticalFlowFarneback as sw_farneback_optical_flow
from butterflow.__init__ import __version__
from butterflow import avinfo, motion, ocl, settings
from butterflow.render import Renderer
from butterflow.sequence import VideoSequence, RenderSubregion

NO_OCL_WARNING = 'No compatible OCL devices detected. Check your OpenCL '\
                 'installation.'
NO_VIDEO_SPECIFIED = 'No input video specified'

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
                     help='Set to embed debugging info into the output video')
    dsp.add_argument('-tt', '--text-type', choices=['light', 'dark', 'stroke'],
                     default=settings.default['text_type'],
                     help='Specify text type for debugging info, '
                     '(default: %(default)s)')

    vid.add_argument('-o', '--output-path', type=str,
                     default=settings.default['out_path'],
                     help='Specify path to the output video')
    vid.add_argument('-r', '--playback-rate', type=str,
                     help='Specify the playback rate')
    vid.add_argument('-s', '--sub-regions', type=str,
                     help='Specify rendering sub regions in the form: '
                     '"a=TIME,b=TIME,TARGET=VALUE" where TARGET is either '
                     '`fps`, `dur`, `spd`, `btw`. Valid TIME syntaxes are '
                     '[hr:m:s], [m:s], [s], [s.xxx], or `end`, which '
                     'signifies to the end the video. You can specify '
                     'multiple sub regions by separating them with a colon '
                     '`:`. A special region format that conveniently '
                     'describes the entire clip is available in the form: '
                     '"full,TARGET=VALUE".')

    vid.add_argument('-t', '--trim-regions', action='store_true',
                     help='Set to trim subregions that are not explicitly '
                          'specified')
    vid.add_argument('-vs', '--video-scale', type=float,
                     default=settings.default['video_scale'],
                     help='Specify the output video scale, '
                     '(default: %(default)s)')
    vid.add_argument('-l', '--lossless', action='store_true',
                     help='Set to use true lossless encoding settings')

    mux.add_argument('-m', '--mux', action='store_true',
                     help='Set to mux source audio and subtitles with the '
                     'output video. Audio and subtitles may be truncated or '
                     'may not be in sync with the final video if the duration '
                     'has been altered during the rendering process.')

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
                     help='Specify number of iterations at each pyramid level, '
                     '(default: %(default)s)')
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

    if settings.default['debug_opts']:
        dbg = par.add_argument_group('Debugging arguments')
        dbg.add_argument('-npad', '--no-pad', action='store_false',
                         help='Set to discard duplicate frames that are '
                         'padded to the end of subregions. This will alter '
                         'the expected duration of the output video.')
        dbg.add_argument('--grayscale', action='store_true',
                         help='Set output a grayscale video')

    args = par.parse_args()

    log = logging.getLogger('butterflow')
    if args.verbose:
        log.setLevel(settings.default['loglevel_b'])

    if args.version:
        print(__version__)
        return 0

    # clb_dir exists inside the tmp_dir
    cache_dir = settings.default['tmp_dir']

    if args.cache:
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
        return 0

    if args.rm_cache:
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir)
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
        cache_dir = settings.default['clb_dir']
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        motion.set_cache_path(cache_dir + os.sep)
    else:
        print(NO_OCL_WARNING)
        return 1

    src_path = args.video
    if src_path is None:
        print(NO_VIDEO_SPECIFIED)
        return 1

    if not os.path.exists(args.video):
        print('Video does not exist at path')
        return 1

    if settings.default['avutil'] == 'none':
        print('You need `ffmpeg` to use this app')
        return 1

    # setup functions that will be used to generate flows and interpolate frames
    farneback_method = motion.ocl_farneback_optical_flow if have_ocl \
        else sw_farneback_optical_flow
    flags = 0
    if args.flow_filter == 'gaussian':
        import cv2
        flags = cv2.OPTFLOW_FARNEBACK_GAUSSIAN
    flow_func = lambda x, y: \
        farneback_method(x, y, args.pyr_scale, args.levels, args.winsize,
                         args.iters, args.poly_n, args.poly_s, args.fast_pyr,
                         flags)

    # for the information filter
    flow_kwargs = collections.OrderedDict([
        ('Pyr', args.pyr_scale),
        ('L', args.levels),
        ('W', args.winsize),
        ('I', args.iters),
        ('PolyN', args.poly_n),
        ('PolyS', args.poly_s)])

    try:
        vid_info = avinfo.get_info(args.video)
    except Exception:
        log.error('Could not get video information:', exc_info=True)
        return 1

    src_rate = vid_info['rate_num'] * 1.0 / vid_info['rate_den']

    if args.inspect:
        if args.video:
            from fractions import Fraction
            # simplify the display aspect ratio
            dar = Fraction(vid_info['dar_n'], vid_info['dar_d'])
            dur = vid_info['duration']
            streams = []
            if vid_info['v_stream_exists']:
                streams.append('video')
            if vid_info['a_stream_exists']:
                streams.append('audio')
            if vid_info['s_stream_exists']:
                streams.append('subtitle')
            print('Video information:'
                  '\n  Streams available  \t: {}'
                  '\n  Resolution         \t: {}x{}, SAR {}:{} DAR {}:{}'
                  '\n  Rate               \t: {:.3f} fps'
                  '\n  Duration           \t: {} ({:.2f}s)'
                  '\n  Num of frames      \t: {}'.format(
                      ','.join(streams),
                      vid_info['width'], vid_info['height'],
                      vid_info['sar_n'], vid_info['sar_d'],
                      dar.numerator, dar.denominator,
                      src_rate,
                      ms_to_time_str(dur), dur / 1000.0,
                      vid_info['frames']
                  ))
            return 0
        else:
            print(NO_VIDEO_SPECIFIED)
            return 1

    if not vid_info['v_stream_exists']:
        log.error('No video stream detected')
        return 1

    try:
        vid_sequence = sequence_from_str(
            vid_info['duration'], vid_info['frames'], args.sub_regions)
    except Exception as e:
        log.error('Bad subregion string: %s' % e)
        return 1

    rate = 0
    if args.playback_rate is None:
        # use original rate
        rate = src_rate
    else:
        # allow fractional rates and fractions with non-rational numerators
        # and denominators
        rate = args.playback_rate
        if '/' in rate and '.' in rate:
            num, den = rate.split('/')
            rate = float(num) / float(den)
        else:
            rate = float(rate)

    if rate != src_rate:
        log.warning('rate mismatch: src_rate=%s rate=%s', src_rate, rate)

    renderer = Renderer(
        args.output_path,
        vid_info,
        vid_sequence,
        rate,
        flow_func,
        motion.ocl_interpolate_flow,
        args.video_scale,
        False,  # grayscale
        args.lossless,
        args.trim_regions,
        args.no_preview,
        args.add_info,
        args.text_type,
        args.mux,
        True,  # pad with dupes?
        settings.default['av_loglevel'],
        settings.default['enc_loglevel'],
        flow_kwargs)

    # apply debugging options
    if settings.default['debug_opts']:
        renderer.grayscale = args.grayscale
        renderer.pad_with_dupes = args.no_pad

    motion.set_num_threads(settings.default['ocv_threads'])

    try:
        import timeit
        tot_time = timeit.timeit(renderer.render, number=1)
        log.info('butterflow took {:.3g} minutes, done.'.format(tot_time / 60))
        sz = os.path.getsize(args.output_path)
        sz_mb = float(sz) / (1 << 20)  # size in megabytes
        log.info('out file size: {:.2g} MB'.format(sz_mb))
    except (KeyboardInterrupt, SystemExit):
        log.warning('files left in cache')
        return 1


def ms_to_time_str(time_ms):
    # converts a time in ms to a time string
    # time string in form:
    # [hrs:mins:secs.xxx]
    import time
    t_str = time.strftime('%H:%M:%S', time.gmtime(time_ms / 1000.0))
    return t_str


def time_str_to_ms(time_str):
    # converts a time str to milliseconds
    # time str syntax:
    # [hrs:mins:secs.xxx], [mins:secs.xxx], [secs.xxx]
    hr = 0
    minute = 0
    sec = 0
    valid_char_set = '0123456789:.'
    if time_str == '' or time_str.count(':') > 2:
        raise ValueError('invalid time syntax')
    for char in time_str:
        if char not in valid_char_set:
            raise ValueError('unknown char in time string')
    val = time_str.split(':')
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
        # duration will eventually be reconverted to milliseconds automatically
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
