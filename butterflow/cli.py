# -*- coding: utf-8 -*-

import os
import sys
import re
import argparse
import datetime
import logging
import cv2
from butterflow.settings import default as settings
from butterflow import ocl, avinfo, motion, ocl
from butterflow.render import Renderer
from butterflow.sequence import VideoSequence, Subregion
from butterflow.__init__ import __version__


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


def main():
    par = argparse.ArgumentParser(usage='butterflow [options] [video]',
                                  add_help=False)
    req = par.add_argument_group('Required arguments')
    gen = par.add_argument_group('General options')
    dev = par.add_argument_group('Device options')
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
    gen.add_argument('--cache-dir', type=str,
                     help='Specify path to the cache directory')
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

    dev.add_argument('-d', '--show-devices', action='store_true',
                     help='Show detected OpenCL devices and exit')
    dev.add_argument('-device', type=int,
                     default=-1,
                     help='Specify the preferred OpenCL device to use as an '
                     'integer. Device numbers can be listed with the `-d` '
                     'option. The device will be chosen automatically if '
                     'nothing is specified.')
    dev.add_argument('-sw', action='store_true',
                     help='Set to force software rendering')

    dsp.add_argument('-p', '--show-preview', action='store_true',
                     help='Set to show video preview')
    dsp.add_argument('-e', '--embed-info', action='store_true',
                     help='Set to embed debugging info into the output video')
    dsp.add_argument('-tt', '--text-type',
                     choices=['light', 'dark', 'stroke'],
                     default=settings['text_type'],
                     help='Specify text type for embedded debugging info, '
                     '(default: %(default)s)')
    dsp.add_argument('-m', '--mark-frames', action='store_true',
                     help='Set to mark interpolated frames')

    vid.add_argument('-o', '--output-path', type=str,
                     default=settings['out_path'],
                     help='Specify path to the output video')
    vid.add_argument('-r', '--playback-rate', type=str,
                     help='Specify the playback rate as an integer or a float.'
                     ' Fractional forms are acceptable, e.g., 24/1.001 is the '
                     'same as 23.976. To use a multiple of the source '
                     'video\'s rate, follow a number with `x`, e.g., "2x" '
                     'will double the frame rate. The original rate will be '
                     'used by default if nothing is specified.')
    vid.add_argument('-s', '--subregions', type=str,
                     help='Specify rendering subregions in the form: '
                     '"a=TIME,b=TIME,TARGET=VALUE" where TARGET is either '
                     '`spd`, `dur`, `fps`. Valid TIME syntaxes are [hr:m:s], '
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

    mux.add_argument('-audio', action='store_true',
                     help='Set to add the source audio to the output video')

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

    format = '[butterflow:%(levelname)s]: %(message)s'

    logging.basicConfig(level=settings['loglevel_0'], format=format)
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

    if args.cache_dir is not None:
        cachedir = os.path.normpath(args.cache_dir)
        if os.path.exists(cachedir):
            if not os.path.isdir(cachedir):
                print('Cache path is not a directory')
                return 1
        else:
            os.makedirs(cachedir)
        settings['tempdir'] = cachedir
        settings['clbdir'] = os.path.join(cachedir, 'clb')
        if not os.path.exists(settings['clbdir']):
            os.makedirs(settings['clbdir'])
        ocl.set_cache_path(settings['clbdir'] + os.sep)

    cachedir = settings['tempdir']

    cachedirs = []
    tempfolder = os.path.dirname(cachedir)
    for dirpath, dirnames, filenames in os.walk(tempfolder):
        for d in dirnames:
            if 'butterflow' in d:
                if 'butterflow-'+__version__ not in d:
                    cachedirs.append(os.path.join(dirpath, d))
        break

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
        print('Cache: '+cachedir)
        return 0
    if args.rm_cache:
        cachedirs.append(cachedir)
        for i, x in enumerate(cachedirs):
            print('[{}] {}'.format(i, x))
        choice = raw_input('Remove these directories? [y/N] ')
        if choice != 'y':
            print('Leaving the cache alone, done.')
            return 0
        for x in cachedirs:
            if os.path.exists(x):
                import shutil
                shutil.rmtree(x)
        print('Cache deleted, done.')
        return 0

    if args.show_devices:
        ocl.print_ocl_devices()
        return 0

    if not args.video:
        print('No file specified')
        return 1
    elif not os.path.exists(args.video):
        print('File doesn\'t exist')
        return 1

    if args.probe:
        avinfo.print_av_info(args.video)
        return 0

    av_info = avinfo.get_av_info(args.video)
    if av_info['frames'] == 0:
        print('Bad file with 0 frames')
        return 1

    extension = os.path.splitext(os.path.basename(args.output_path))[1].lower()
    if extension[1:] != settings['v_container']:
        print('Bad output file extension. Must be {}.'.format(
              settings['v_container'].upper()))
        return 0

    if not ocl.compat_ocl_device_available() and not args.sw:
        print('No compatible OpenCL devices were detected.\n'
              'Must force software rendering with the `-sw` flag to continue.')
        return 1

    log.info('Version '+__version__)
    log.info('Cache directory:\t%s' % cachedir)

    for x in cachedirs:
        log.warn('Stale cache directory (delete with `--rm-cache`): %s' % x)

    if ocl.compat_ocl_device_available():
        log.info('At least one compatible OpenCL device was detected')
    else:
        log.warning('No compatible OpenCL devices were detected.')

    if args.device != -1:
        try:
            ocl.select_ocl_device(args.device)
        except IndexError as error:
            print('Error: '+str(error))
            return 1
        except ValueError:
            if not args.sw:
                print('An incompatible device was selected.\n'
                      'Must force software rendering with the `-sw` flag to continue.')
                return 1

    s = "Using device: %s"
    if args.device == -1:
        s += " (autoselected)"
    log.info(s % ocl.get_current_ocl_device_name())

    use_sw_interpolate = args.sw

    if args.flow_filter == 'gaussian':
        args.flow_filter = cv2.OPTFLOW_FARNEBACK_GAUSSIAN
    else:
        args.flow_filter = 0
    if args.smooth_motion:
        args.poly_s = 0.01

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
        log.warn("Hardware acceleration is disabled. Rendering will be slow. "
                 "Do Ctrl+c to quit or suspend the process with Ctrl+z and "
                 "then stop it with `kill %1`, etc. You can list suspended "
                 "processes with `jobs`.)")
    else:
        interpolate_fn = motion.ocl_interpolate_flow
        log.info("Hardware acceleration is enabled")

    try:
        w, h = w_h_from_input_str(args.video_scale, av_info['w'], av_info['h'])
        sequence = sequence_from_input_str(args.subregions,
                                           av_info['duration'],
                                           av_info['frames'])
        rate = rate_from_input_str(args.playback_rate, av_info['rate'])
    except (ValueError, AttributeError) as error:
        print('Error: '+str(error))
        return 1

    def nearest_even_int(x, tag=""):
        new_x = x & ~1
        if x != new_x:
            log.warn("%s: %d is not divisible by 2, setting to %d",
                     tag, x, new_x)
        return new_x

    w1, h1 = av_info['w'], av_info['h']
    w2 = nearest_even_int(w, "W")
    if w2 > 256:
        if w2 % 4 > 0:
            old_w2 = w2
            w2 -= 2
            w2 = max(w2, 0)
            log.warn('W: %d > 256 but is not divisible by 4, setting to %d',
                     old_w2, w2)
    h2 = nearest_even_int(h, "H")

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
                   args.embed_info,
                   args.text_type,
                   args.mark_frames,
                   args.audio)

    ocl.set_num_threads(settings['ocv_threads'])

    log.info('Rendering:')
    added_rate = False
    for x in str(rnd.sequence).split('\n'):
        x = x.strip()
        if not added_rate:
            x += ', Rate={}'.format(av_info['rate'])
            log.info(x)
            added_rate = True
            continue
        if not args.keep_subregions and 'autogenerated' in x:
            log.info(x[:-1]+ ', will skip when rendering)')
            continue
        log.info(x)


    temp_subs = rnd.sequence.subregions
    for x in rnd.sequence.subregions:
        overlaps = False
        for y in temp_subs:
            if x is y:
                continue
            elif x.intersects(y):
                overlaps = True
                break
        if overlaps:
            log.warn('At least 1 subregion overlaps with another')
            break

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
        log_function = log.info
        if rnd.frs_written > rnd.frs_to_render:
            log_function = log.warn
            log.warn('Unexpected write ratio')
        log_function('Write ratio: {}/{}, ({:.2f}%)'.format(
                 rnd.frs_written,
                 rnd.frs_to_render,
                 rnd.frs_written*100.0/rnd.frs_to_render))
        txt = 'Final output frames: {} source, +{} interpolated, +{} duped, -{} dropped'
        if not settings['quiet']:
            log.info(txt.format(rnd.source_frs,
                                rnd.frs_interpolated,
                                rnd.frs_duped,
                                rnd.frs_dropped))
        old_sz = os.path.getsize(args.video) / 1024.0
        new_sz = os.path.getsize(args.output_path) / 1024.0
        log.info('Output file size:\t{:.2f} kB ({:.2f} kB)'.format(new_sz,
                 new_sz - old_sz))
        log.info('Rendering took {:.3g} mins, done.'.format(total_time / 60))
        return 0
    else:
        log.warn('Quit unexpectedly')
        log.warn('Files were left in the cache @ '+settings['tempdir']+'.')
        return 1


def time_str_to_milliseconds(s):
    # syntax: [hrs:mins:secs.xxx], [mins:secs.xxx], [secs.xxx]
    hrs = 0
    mins = 0
    secs = 0
    split = s.strip().split(':')
    n = len(split)
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
        raise ValueError('Unknown playback rate syntax: {}'.format(s))


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
        raise ValueError('Unknown W:H syntax: {}'.format(s))


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
            substr = str(sub)
            try:
                sub = Subregion(
                           time_str_to_milliseconds(match.groupdict()['tm_a']),
                           time_str_to_milliseconds(match.groupdict()['tm_b']))
            except AttributeError as e:
                raise AttributeError("Bad subregion: {} ({})".format(substr, e))
            target = match.groupdict()['target']
            val = match.groupdict()['val']
            if target == 'fps':
                val = rate_from_input_str(val, -1)
            elif target == 'dur':
                val = float(val)*1000.0
            elif target == 'spd':
                val = float(val)
            setattr(sub, 'target_'+target, val)
            try:
                seq.add_subregion(sub)
            except ValueError as e:
                raise ValueError("Bad subregion: {} ({})".format(substr, e))
        else:
            raise ValueError('Unknown subregion syntax: {}'.format(sub))
    return seq
