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


def main():
    par = argparse.ArgumentParser(usage='%(prog)s [options] [video]',
                                  add_help=False)
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
    gen.add_argument('--add-info', action='store_true',
                     help='Set to add debugging info into the output video')

    vid.add_argument('-o', '--output-path', type=str,
                     default=settings.default['out_path'],
                     help='Specify path to the output video')
    vid.add_argument('-r', '--playback-rate', type=str,
                     default=str(settings.default['playback_rate']),
                     help='Specify the playback rate, '
                     '(default: %(default)s)')
    vid.add_argument('-s', '--sub-regions', type=str,
                     help='Specify rendering sub regions in the form: '
                     '"a=TIME,b=TIME,TARGET=VALUE" where '
                     'TARGET is either `fps`, `duration`, `factor`. '
                     'Valid TIME syntaxes are [hr:m:s], [m:s], [s.xxx], '
                     'or `end`, which signifies to the end of the video. '
                     'You can specify multiple sub regions by separating them '
                     'with a semi-colon `;`. A special region format that '
                     'conveniently describes the entire clip is available in '
                     'the form: "full,TARGET=VALUE".')

    vid.add_argument('-t', '--trim-regions', action='store_true',
                     help='Set to trim subregions that are not explicitly '
                          'specified')
    vid.add_argument('-vs', '--video-scale', type=float,
                     default=settings.default['video_scale'],
                     help='Specify the output video scale, '
                     '(default: %(default)s)')
    vid.add_argument('-l', '--lossless', action='store_true',
                     help='Set to use lossless encoding settings')
    vid.add_argument('--decimate', action='store_true',
                     help='Set to decimate duplicate frames from the'
                     ' video source')
    vid.add_argument('--grayscale', action='store_true',
                     help='Set to enhance grayscale coloring')

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
        dbg.add_argument('--preview-flows', action='store_true',
                         help='Set to preview optical flows')
        dbg.add_argument('--make-flows', action='store_true',
                         help='Set to render optical flows and write them to '
                         'disk')

    args = par.parse_args()

    if args.version:
        print(__version__)
        exit(0)

    have_ocl = ocl.ocl_device_available()
    if args.devices:
        if have_ocl:
            ocl.print_ocl_devices()
        else:
            print(NO_OCL_WARNING)
        exit(0)

    if have_ocl:
        cache_dir = settings.default['clb_dir']
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        motion.set_cache_path(cache_dir + os.sep)
    else:
        print(NO_OCL_WARNING)
        exit(1)

    src_path = args.video
    if src_path is None:
        print('No input video specified')
        exit(0)

    if not os.path.exists(args.video):
        print('Video does not exist at path')
        exit(1)

    if settings.default['avutil'] == 'none':
        print('You need `ffmpeg` or `avconv` to use this app')
        exit(1)

    settings.default['verbose'] = args.verbose

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

    # allow fractional rates and fractions with non-rational numerators and
    # denominators
    rate = args.playback_rate
    if '/' in rate and '.' in rate:
        num, den = rate.split('/')
        rate = float(num) / float(den)
    else:
        rate = float(rate)

    try:
        vid_info = avinfo.get_info(args.video)
    except Exception as e:
        print('Could not get video information')
        exit(1)

    if not vid_info['v_stream_exists']:
        print('No video stream detected')
        exit(1)

    try:
        vid_sequence = sequence_from_string(
            vid_info['duration'], vid_info['frames'], args.sub_regions)
    except Exception as e:
        print('Invalid subregion string')
        exit(1)

    renderer = Renderer(
        args.output_path,
        vid_info,
        vid_sequence,
        rate,
        flow_func,
        motion.ocl_interpolate_flow,
        args.video_scale,
        args.decimate,
        args.grayscale,
        args.lossless,
        args.trim_regions,
        args.no_preview,
        args.add_info,
        False,
        False,
        settings.default['loglevel'],
        flow_kwargs)

    # apply debugging options
    if settings.default['debug_opts']:
        renderer.preview_flows = args.preview_flows
        renderer.make_flows = args.make_flows

    motion.set_num_threads(settings.default['ocv_threads'])
    renderer.render()


def time_string_to_ms(time):
    """Converts a time string to milliseconds. valid time string syntax:
    [hrs:mins:secs.xxx] OR [mins:secs.xxx] OR [secs.xxx]"""
    value_error = ValueError('invalid time syntax: {}'.format(time))
    hr, min, sec = 0, 0, 0
    valid_char_set = '0123456789:.'
    if time == '' or time.count(':') > 2:
        raise value_error
    for char in time:
        if char not in valid_char_set:
            raise value_error
    val = time.split(':')
    if len(val) >= 1 and val[-1] != '':
        sec = float(val[-1])
    if len(val) >= 2 and val[-2] != '':
        min = float(val[-2])
    if len(val) == 3 and val[-3] != '':
        hr = float(val[-3])
    return (hr * 3600 + min * 60 + sec) * 1000.0


def parse_tval_string(string):
    """Extracts a target and value from a subregion string where TARGET is
    either `fps`, `dur`, or `spd`"""
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
        # duration in milliseconds
        val = float(val) * 1000.0
    elif tgt == 'spd':
        val = float(val)
    else:
        raise ValueError('invalid target: {}'.format(tgt))
    return tgt, val


def subregion_from_string(string):
    """Returns a subregion from a string with no special keywords. valid string
    syntax: a=<time>,b=<time>,TARGET=VALUE"""
    val = string.split(',')
    a = val[0].split('=')[1]  # the `a=` portion
    b = val[1].split('=')[1]  # the `b=` portion
    c = val[2]
    sub = RenderSubregion(time_string_to_ms(a),
                          time_string_to_ms(b))
    tgt, val = parse_tval_string(c)
    setattr(sub, tgt, val)
    return sub


def subregion_from_string_full_key(string, duration):
    """Returns a subregion from a string that contains the `full` keyword. the
    `full` keyword denotes the entire length of the video. valid string syntax:
    full,TARGET=VALUE"""
    val = string.split(',')
    if val[0] == 'full':
        # create a subregion from [0, duration]
        sub = RenderSubregion(0, float(duration))
        tgt, val = parse_tval_string(val[1])
        setattr(sub, tgt, val)
        return sub
    else:
        raise ValueError('`full` keyword not found: {}'.format(string))


def subregion_from_string_end_key(string, duration):
    """Returns a subregion from a string that contains the `end` keyword. the
    `end` keyword denotes to the end of the video. valid string syntax:
    a=<time>,b=end,TARGET=FULL"""
    val = string.split(',')
    b = val[1].split('=')[1]  # the `b=` portion
    if b == 'end':
        # replace the `end` with the duration of the video in seconds. the
        # duration will eventually be reconverted to milliseconds automatically
        string = string.replace('end', str(duration / 1000.0))
        return subregion_from_string(string)
    else:
        raise ValueError('`end` keyword not found: {}'.format(string))


def sequence_from_string(duration, frames, strings):
    """Returns a video sequence from multiple subregion strings separated by a
    semi-colon. For example: a=<time>,b=<time>,TARGET=FULL;a=<time>,b=<time>,
    TARGET=FULL,a=<time>,b=end,TARGET=FULL. Another example using the `full`
    keyword: full,TARGET=VALUE"""
    seq = VideoSequence(duration, frames)
    if strings is None:
        return seq
    for string in strings.split(';'):
        sub = None
        if 'full' in string:
            sub = subregion_from_string_full_key(string, duration)
        elif 'end' in string:
            sub = subregion_from_string_end_key(string, duration)
        else:
            sub = subregion_from_string(string)
        seq.add_subregion(sub)
    return seq
