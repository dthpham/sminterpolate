# cli to butterflow

import os
import sys
import argparse
import logging
import datetime
import cv2
from butterflow.settings import default as settings
from butterflow import ocl, avinfo, motion
from butterflow.render import Renderer
from butterflow.sequence import VideoSequence, Subregion

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
    gen.add_argument('-v', '--verbose', action='store_true',
                     help='Set to increase output verbosity')

    dsp.add_argument('-np', '--no-preview', action='store_false',
                     help='Set to disable video preview')
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
                     help='Specify the playback rate as an integer or a '
                     'float. Fractional forms are acceptable. To use a '
                     'multiple of the source video\'s rate, follow a number '
                     'with `x`, e.g., "2x" will double the frame rate. The '
                     'original rate will be used by default if nothing is '
                     'specified.')
    vid.add_argument('-s', '--subregions', type=str,
                     help='Specify rendering subregions in the form: '
                     '"a=TIME,b=TIME,TARGET=VALUE" where TARGET is either '
                     '`fps`, `dur`, `spd`. Valid TIME syntaxes are [hr:m:s], '
                     '[m:s], [s], [s.xxx], or `end`, which signifies to the '
                     'end the video. You can specify multiple subregions by '
                     'separating them with a colon `:`. A special subregion '
                     'format that conveniently describes the entire clip is '
                     'available in the form: "full,TARGET=VALUE".')
    vid.add_argument('-t', '--trim-subregions', action='store_true',
                     help='Set to trim subregions that are not explicitly '
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
                     help='Set to tune for smooth motion. This mode favors '
                     'accurate and artifact-less frames above all and will '
                     'emphasize blending frames over warping pixels.')

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
        if arg[0] == '-' and arg[1].isdigit():  # accept args w/ - for -vs
            sys.argv[i] = ' '+arg

    args = par.parse_args()

    logging.basicConfig(level=settings['loglevel_a'],
                        format='[butterflow.%(levelname)s]: %(message)s')
    log = logging.getLogger('butterflow')
    if args.verbose:
        log.setLevel(settings['loglevel_b'])

    if args.version:
        from butterflow.__init__ import __version__
        print('butterflow version {}'.format(__version__))
        return 0

    cachedir = settings['tempdir']
    if args.cache:
        nfiles = 0
        sz = 0
        for dirpath, dirnames, fnames in os.walk(cachedir):
            if dirpath == settings['clbdir']:
                continue
            for fname in fnames:
                nfiles += 1
                fp = os.path.join(dirpath, fname)
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
        print('no file specified')
        return 1
    elif not os.path.exists(args.video):
        print('file does not exist')
        return 1

    if args.probe:
        avinfo.print_av_info(args.video)
        return 0

    av_info = avinfo.get_av_info(args.video)

    if args.flow_filter == 'gaussian':
        args.flow_filter = cv2.OPTFLOW_FARNEBACK_GAUSSIAN
    else:
        args.flow_filter = 0

    if args.smooth_motion:
        args.polys = 0.01

    use_sw_inter = args.sw or not ocl.compat_ocl_device_available()
    if use_sw_inter:
        log.warn('not using opencl, ctrl+c to quit')

    def flow_fn(x, y,
                pyr=args.pyr_scale, levels=args.levels, winsize=args.winsize,
                iters=args.iters, polyn=args.poly_n, polys=args.poly_s,
                fast=args.fast_pyr, filt=args.flow_filter):
        if use_sw_inter:
            return cv2.calcOpticalFlowFarneback(
                x, y, pyr, levels, winsize, iters, polyn, polys, filt)
        else:
            return motion.ocl_farneback_optical_flow(
                x, y, pyr, levels, winsize, iters, polyn, polys, fast, filt)

    inter_fn = None
    if use_sw_inter:
        from butterflow.interpolate import sw_interpolate_flow
        inter_fn = sw_interpolate_flow
    else:
        inter_fn = motion.ocl_interpolate_flow

    w, h = w_h_from_input_str(args.video_scale, av_info['w'], av_info['h'])
    def mk_even(x):
        return x & ~1
    w = mk_even(w)
    h = mk_even(h)

    rnd = Renderer(args.video,
                   args.output_path,
                   sequence_from_input_str(args.subregions,
                                           av_info['duration'],
                                           av_info['frames']),
                   rate_from_input_str(args.playback_rate, av_info['rate']),
                   flow_fn,
                   inter_fn,
                   w,
                   h,
                   args.lossless,
                   args.trim_subregions,
                   args.no_preview,
                   args.add_info,
                   args.text_type,
                   args.mark_frames,
                   args.mux)

    motion.set_num_threads(settings['ocv_threads'])

    log.info('Will render:\n' + str(rnd.sequence))

    success = True
    total_time = 0
    try:
        import timeit
        total_time = timeit.timeit(rnd.render_video,
                                   setup='import gc;gc.enable()',
                                   number=1)
    except (KeyboardInterrupt, SystemExit):
        success = False
    if success:
        log.debug('Made: '+args.output_path)
        out_sz = os.path.getsize(args.output_path) / 1024.0**2
        log.debug('Write ratio: {}/{}, ({:.2f}%) {:.2f} MB'.format(
                  rnd.tot_frs_wrt,
                  rnd.tot_tgt_frs,
                  rnd.tot_frs_wrt*100.0/rnd.tot_tgt_frs,
                  out_sz))
        print('Frames: {} real, {} interpolated, {} duped, {} dropped'.format(
              rnd.tot_src_frs,
              rnd.tot_frs_int,
              rnd.tot_frs_dup,
              rnd.tot_frs_drp))
        print('butterflow took {:.3g} mins, done.'.format(total_time / 60))
        return 0
    else:
        log.warn('files left in cache @ '+settings['tempdir'])
        return 1


import re

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
    # converts a time str to milliseconds
    # time str syntax:
    # [hrs:mins:secs.xxx], [mins:secs.xxx], [secs.xxx]
    hr = 0
    minute = 0
    sec = 0
    tm_split = s.strip().split(':')
    n = len(tm_split)
    # going backwards in the list
    # get secs.xxx portion
    if n >= 1:
        if tm_split[-1] != '':
            sec = float(tm_split[-1])
    # get mins
    if n >= 2:
        if tm_split[-2] != '':
            minute = float(tm_split[-2])
    # get hrs
    if n == 3:
        if tm_split[-3] != '':
            hr = float(tm_split[-3])
    return (hr*3600 + minute*60 + sec) * 1000.0

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
        raise RuntimeError

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
        raise RuntimeError

def sequence_from_input_str(s, src_dur, src_nfrs):
    seq = VideoSequence(src_dur, src_nfrs)
    if not s:
        return seq
    src_dur = str(datetime.timedelta(seconds=src_dur / 1000.0))
    partition = list(src_dur.partition('.'))
    partition[-1] = partition[-1][:3]  # keep secs.xxx...
    src_dur = ''.join(partition)
    s = re.sub(sr_ful_pattern,
               'a=0,b={}'.format(src_dur), re.sub(sr_end_pattern, src_dur, s))
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
            raise RuntimeError
    return seq
