import os
import sys
import re
import argparse
import datetime
import logging
import cv2
from butterflow.settings import default as settings
from butterflow import ocl, avinfo, motion
from butterflow.render import Renderer
from butterflow.sequence import VideoSequence, Subregion
from butterflow.__init__ import __version__


def main():
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
    gen.add_argument('--version', action='store_true',
                     help='Show program\'s version number and exit')
    gen.add_argument('-d', '--devices', action='store_true',
                     help='Show detected OpenCL devices and exit')
    gen.add_argument('-sw', action='store_true',
                     help='Set to force software rendering')
    gen.add_argument('-c', '--cache', action='store_true',
                     help='Show cache information and exit')
    gen.add_argument('--rm-cache', action='store_true',
                     help='Set to clear the cache and exit')
    gen.add_argument('-prb', '--probe', action='store_true',
                     help='Show media file information and exit')
    gen.add_argument('-v', '--verbosity', action='count',
                     help='Set to increase output verbosity')
    gen.add_argument('-q', '--quiet', action='store_true',
                     help='Set to suppress console output')

    dsp.add_argument('-p', '--show-preview', action='store_true',
                     help='Set to show video preview')
    dsp.add_argument('-a', '--add-info', action='store_true',
                     help='Set to embed debugging info into the output video')
    dsp.add_argument('-tt', '--text-type',
                     choices=['light', 'dark', 'stroke'],
                     default=settings['text_type'],
                     help='Specify text type for debugging info, '
                     '(default: %(default)s)')
    dsp.add_argument('-mrk', '--mark-frames', action='store_true',
                     help='Set to mark interpolated frames')

    vid.add_argument('-o', '--output-path', type=str,
                     default=settings['out_path'],
                     help='Specify path to the output video')
    vid.add_argument('-r', '--playback-rate', type=str,
                     help='Specify the playback rate as an integer or a float '
                     'Fractional forms are acceptable, e.g., 24/1.001 is the '
                     'same as 23.976. To use a multiple of the source '
                     'video\'s rate, follow a number with `x`, e.g., "2x" '
                     'will double the frame rate. The original rate will be '
                     'used by default if nothing is specified.')
    vid.add_argument('-s', '--subregions', type=str,
                     help='Specify rendering subregions in the form: '
                     '"a=TIME,b=TIME,TARGET=VALUE" where TARGET is either '
                     '`fps`, `dur`, `spd`. Valid TIME syntaxes are [hr:m:s], '
                     '[m:s], [s], [s.xxx], or `end`, which signifies to the '
                     'end the video. You can specify multiple subregions by '
                     'separating them with a colon `:`. A special subregion '
                     'format that conveniently describes the entire clip is '
                     'available in the form: "full,TARGET=VALUE".')
    vid.add_argument('-k', '--keep-subregions', action='store_true',
                     help='Set to render subregions that are not explicitly '
                          'specified')
    vid.add_argument('-vs', '--video-scale', type=str,
                     default=str(settings['video_scale']),
                     help='Specify output video size in the form: '
                     '"WIDTH:HEIGHT" or by using a factor. To keep the '
                     'aspect ratio only specify one component, either width '
                     'or height, and set the other component to -1, '
                     '(default: %(default)s)')
    vid.add_argument('-l', '--lossless', action='store_true',
                     help='Set to use lossless encoding settings')
    vid.add_argument('-sm', '--smooth-motion', action='store_true',
                     help='Set to tune for smooth motion. This mode yields '
                     'artifact-less frames by emphasizing blended frames over '
                     'warping pixels.')

    mux.add_argument('-mux', action='store_true',
                     help='Set to mux the source audio with the output video')

    fgr.add_argument('--fast-pyr', action='store_true',
                     help='Set to use fast pyramids')
    fgr.add_argument('--pyr-scale', type=float,
                     default=settings['pyr_scale'],
                     help='Specify pyramid scale factor, '
                     '(default: %(default)s)')
    fgr.add_argument('--levels', type=int,
                     default=settings['levels'],
                     help='Specify number of pyramid layers, '
                     '(default: %(default)s)')
    fgr.add_argument('--winsize', type=int,
                     default=settings['winsize'],
                     help='Specify averaging window size, '
                     '(default: %(default)s)')
    fgr.add_argument('--iters', type=int,
                     default=settings['iters'],
                     help='Specify number of iterations at each pyramid '
                     'level, (default: %(default)s)')
    fgr.add_argument('--poly-n', type=int,
                     choices=settings['poly_n_choices'],
                     default=settings['poly_n'],
                     help='Specify size of pixel neighborhood, '
                     '(default: %(default)s)')
    fgr.add_argument('--poly-s', type=float,
                     default=settings['poly_s'],
                     help='Specify standard deviation to smooth derivatives, '
                     '(default: %(default)s)')
    fgr.add_argument('-ff', '--flow-filter', choices=['box', 'gaussian'],
                     default=settings['flow_filter'],
                     help='Specify which filter to use for optical flow '
                     'estimation, (default: %(default)s)')

    for i, arg in enumerate(sys.argv):
        if arg[0] == '-' and arg[1].isdigit():
            sys.argv[i] = ' '+arg

    args = par.parse_args()

    fmt = '[butterflow:%(filename)s:%(funcName)s.%(levelname)s]: %(message)s'
    logging.basicConfig(level=settings['loglevel_0'], format=fmt)
    log = logging.getLogger('butterflow')

    if args.verbosity == 1:
        log.setLevel(settings['loglevel_1'])
    if args.verbosity >= 2:
        log.setLevel(settings['loglevel_2'])
    if args.quiet:
        log.setLevel(settings['loglevel_quiet'])
        settings['quiet'] = True

    if args.version:
        print(__version__)
        return 0

    cachedir = settings['tempdir']
    if args.cache:
        nfiles = 0
        sz = 0
        for dirpath, dirnames, filenames in os.walk(cachedir):
            if dirpath == settings['clbdir']:
                continue
            for filename in filenames:
                nfiles += 1
                fp = os.path.join(dirpath, filename)
                sz += os.path.getsize(fp)
        sz = sz / 1024.0**2
        print('{} files, {:.2f} MB'.format(nfiles, sz))
        print('cache @ '+cachedir)
        return 0
    if args.rm_cache:
        if os.path.exists(cachedir):
            import shutil
            shutil.rmtree(cachedir)
        print('cache deleted, done.')
        return 0

    if args.devices:
        ocl.print_ocl_devices()
        return 0

    if not args.video:
        print('no file specified, use: -h for help')
        return 1
    elif not os.path.exists(args.video):
        print('file does not exist')
        return 1

    if args.probe:
        avinfo.print_av_info(args.video)
        return 0

    extension = os.path.splitext(os.path.basename(args.output_path))[1].lower()
    if extension[1:] != 'mp4':
        print('bad out file extension')
        return 0

    av_info = avinfo.get_av_info(args.video)

    use_sw_interpolate = args.sw or not ocl.compat_ocl_device_available()
    if use_sw_interpolate:
        log.warn('not using opencl, ctrl+c to quit')

    if args.flow_filter == 'gaussian':
        args.flow_filter = cv2.OPTFLOW_FARNEBACK_GAUSSIAN
    else:
        args.flow_filter = 0

    if args.smooth_motion:
        args.polys = 0.01

    def optflow_fn(x, y,
                   pyr=args.pyr_scale, levels=args.levels,
                   winsize=args.winsize, iters=args.iters, polyn=args.poly_n,
                   polys=args.poly_s, fast=args.fast_pyr,
                   filt=args.flow_filter):
        if use_sw_interpolate:
            return cv2.calcOpticalFlowFarneback(
                x, y, pyr, levels, winsize, iters, polyn, polys, filt)
        else:
            return motion.ocl_farneback_optical_flow(
                x, y, pyr, levels, winsize, iters, polyn, polys, fast, filt)

    interpolate_fn = None
    if use_sw_interpolate:
        from butterflow.interpolate import sw_interpolate_flow
        interpolate_fn = sw_interpolate_flow
    else:
        interpolate_fn = motion.ocl_interpolate_flow

    try:
        w, h = w_h_from_input_str(args.video_scale, av_info['w'], av_info['h'])
        sequence = sequence_from_input_str(args.subregions,
                                           av_info['duration'],
                                           av_info['frames'])
        rate = rate_from_input_str(args.playback_rate, av_info['rate'])
    except (ValueError, AttributeError) as error:
        print('error: '+str(error))
        return 1

    def nearest_even_int(x):
        return x & ~1

    w1, h1 = av_info['w'], av_info['h']
    w2, h2 = nearest_even_int(w), nearest_even_int(h)

    if w1*h1 > w2*h2:
        scaling_method = settings['scaler_dn']
    elif w1*h1 < w2*h2:
        scaling_method = settings['scaler_up']
    else:
        scaling_method = None

    rnd = Renderer(args.video,
                   args.output_path,
                   sequence,
                   rate,
                   optflow_fn,
                   interpolate_fn,
                   w2,
                   h2,
                   scaling_method,
                   args.lossless,
                   args.keep_subregions,
                   args.show_preview,
                   args.add_info,
                   args.text_type,
                   args.mark_frames,
                   args.mux)

    motion.set_num_threads(settings['ocv_threads'])

    log.info('will render:\n' + str(rnd.sequence))

    success = True
    total_time = 0
    try:
        import timeit
        total_time = timeit.timeit(rnd.render,
                                   setup='import gc;gc.enable()',
                                   number=1)
    except (KeyboardInterrupt, SystemExit):
        success = False
    if success:
        log.info('made: '+args.output_path)
        out_sz = os.path.getsize(args.output_path) / 1024.0**2
        log.info('write ratio: {}/{}, ({:.2f}%) {:.2f} MB'.format(
                 rnd.frs_written,
                 rnd.frs_to_render,
                 rnd.frs_written*100.0/rnd.frs_to_render,
                 out_sz))
        txt = 'frames: {} real, +{} interpolated, +{} dupe, -{} drop'
        if not settings['quiet']:
            print(txt.format(rnd.source_frs,
                             rnd.frs_interpolated,
                             rnd.frs_duped,
                             rnd.frs_dropped))
        log.info('butterflow took {:.3g} mins, done.'.format(total_time / 60))
        return 0
    else:
        log.warn('quit unexpectedly')
        log.warn('files left in cache @ '+settings['tempdir'])
        return 1


flt_pattern = r"(?P<flt>\d*\.\d+|\d+)"
wh_pattern = re.compile(r"""
(?=(?P<semicolon>.+:.+)|.+)
(?(semicolon)
  (?P<width>-1|\d+):(?P<height>-1|\d+)|
  {}
)
(?<!^-1:-1$)  # ignore -1:-1
""".format(flt_pattern), re.X)
sl_pattern = r"(?=(?P<slash>.+/.+)|.+)"
nd_pattern = r"(?P<numerator>\d*\.\d+|\d+)/(?P<denominator>\d*\.\d+|\d+)"
pr_pattern = re.compile(r"""
{}
(?(slash)
  {}|
  (?P<flt_or_x>\d*\.\d+x?|\d+x?)
)
""".format(sl_pattern, nd_pattern), re.X)
tm_pattern = r"""^
(?:
  (?:([01]?\d|2[0-3]):)?
  ([0-5]?\d):
)?
(\.\d{1,3}|[0-5]?\d(?:\.\d{1,3})?)$
"""
sr_tm_pattern = tm_pattern[1:-2]  # remove ^$
sr_end_pattern = r"end"
sr_ful_pattern = r"full"
sr_pattern = re.compile(r"""^
a=(?P<tm_a>{tm}),
b=(?P<tm_b>{tm}),
(?P<target>fps|dur|spd)=
{}
(?P<val>
  (?(slash)
    {}|
    {}
  )
)$
""".format(sl_pattern, nd_pattern, flt_pattern, tm=sr_tm_pattern), re.X)


def time_str_to_milliseconds(s):
    # syntax: [hrs:mins:secs.xxx], [mins:secs.xxx], [secs.xxx]
    hrs = 0
    mins = 0
    secs = 0
    split = s.strip().split(':')
    n = len(split)
    # going backwards
    if n >= 1 and split[-1] != '':
        secs = float(split[-1])
    if n >= 2 and split[-2] != '':
        mins = float(split[-2])
    if n == 3 and split[-3] != '':
        hrs = float(split[-3])
    ms_time = (hrs*3600 + mins*60 + secs) * 1000.0
    return ms_time


def rate_from_input_str(s, src_rate):
    if not s:
        return src_rate
    match = re.match(pr_pattern, s)
    if match:
        if match.groupdict()['slash']:
            return (float(match.groupdict()['numerator']) /
                    float(match.groupdict()['denominator']))
        flt_or_x = match.groupdict()['flt_or_x']
        if 'x' in flt_or_x:
            return float(flt_or_x[:-1])*src_rate
        else:
            return float(flt_or_x)
    else:
        raise ValueError('bad rate')


def w_h_from_input_str(s, src_w, src_h):
    if not s:
        return src_w, src_h
    match = re.match(wh_pattern, s)
    if match:
        if match.groupdict()['semicolon']:
            w = int(match.groupdict()['width'])
            h = int(match.groupdict()['height'])
            if w == -1:
                w = int(h*src_w/src_h)
            if h == -1:
                h = int(w*src_h/src_w)
            return w, h
        else:
            flt = float(match.groupdict()['flt'])
            w = int(src_w * flt)
            h = int(src_h * flt)
            return w, h
    else:
        raise ValueError('bad width:height')


def sequence_from_input_str(s, src_duration, src_frs):
    seq = VideoSequence(src_duration, src_frs)
    if not s:
        seq.subregions[0].skip = False
        return seq
    src_duration = str(datetime.timedelta(seconds=src_duration / 1000.0))
    partition = list(src_duration.partition('.'))
    partition[-1] = partition[-1][:3]  # keep secs.xxx...
    src_duration = ''.join(partition)
    s = re.sub(sr_ful_pattern,
               'a=0,b={}'.format(src_duration), re.sub(sr_end_pattern,
                                                       src_duration, s))
    subs = re.split(':a', s)
    new_subs = []
    if len(subs) > 1:
        for sub in subs:
            if not sub.startswith('a'):
                new_subs.append('a'+sub)
            else:
                new_subs.append(sub)
        subs = new_subs
    for sub in subs:
        match = re.match(sr_pattern, sub)
        if match:
            sub = Subregion(time_str_to_milliseconds(match.groupdict()['tm_a']),
                            time_str_to_milliseconds(match.groupdict()['tm_b']))
            target = match.groupdict()['target']
            val    = match.groupdict()['val']
            if target == 'fps':
                val = rate_from_input_str(val, -1)
            elif target == 'dur':
                val = float(val)*1000.0
            elif target == 'spd':
                val = float(val)
            setattr(sub, 'target_'+target, val)
            seq.add_subregion(sub)
        else:
            raise ValueError('bad subregion')
    return seq
