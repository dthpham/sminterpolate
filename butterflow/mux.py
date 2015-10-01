# Author: Duong Pham
# Copyright 2015

import os
import shutil
import subprocess
import math
from butterflow import avinfo
from butterflow.settings import default as settings

# `atempo` filter values are bounded
ATEMPO_MIN = 0.5  # slow down to no less than half the original speed
ATEMPO_MAX = 2.0  # speed up to no more than double


def extract_audio(video, destination, start, end, spd=1.0):
    av_info = avinfo.get_av_info(video)
    if not av_info['a_stream_exists']:
        raise RuntimeError('no audio stream found')
    filename = os.path.splitext(os.path.basename(destination))[0]
    tempfile1 = '~{filename}.{ext}'.format(
            filename=filename,
            ext=settings['v_container']).lower()
    tempfile1 = os.path.join(settings['tmp_dir'], tempfile1)
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-i', video,
        '-ss', str(start / 1000.0),
        '-to', str(end / 1000.0),
        '-map_metadata', '-1',
        '-map_chapters', '-1',
        '-vn',
        '-sn',
    ]
    # `aac` is considered an experimental encoder and so `-strict experimental`
    # or `-strict 2` is required
    if settings['ca'] == 'aac':
        call.extend(['-strict', '-2'])
    call.extend([
        '-c:a', settings['ca'],
        '-b:a', settings['ba'],
        tempfile1
    ])
    proc = subprocess.call(call)
    if proc == 1:
        raise RuntimeError('extraction failed')
    # change speed of file using the `atempo` filter
    tempfile2 = '~{filename}.{spd}x.{ext}'.format(
        filename=filename,
        spd=spd,
        ext=settings['a_container']
    )
    tempfile2 = os.path.join(settings['tmp_dir'], tempfile2)
    # the `atempo` filter is limited to using values between `ATEMPO_MIN=0.5`
    # and `ATEMPO_MAX=2.0` work around this limitation by stringing multiple
    # `atempo` filters together
    atempo_chain = []
    for f in atempo_factors_for_spd(spd):
        atempo_chain.append('atempo={}'.format(f))
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-i', tempfile1,
        '-filter:a', ','.join(atempo_chain),
    ]
    if settings['ca'] == 'aac':
        call.extend(['-strict', '-2'])
    call.extend([
        '-c:a', settings['ca'],
        '-b:a', settings['ba'],
        tempfile2,
    ])
    proc = subprocess.call(call)
    if proc == 1:
        raise RuntimeError('change tempo failed')
    os.remove(tempfile1)
    shutil.move(tempfile2, destination)


def concat_files(destination, files):
    # concatenates files of the same type (same codec and codec parameters) in
    # sequence using ffmpeg's concat demuxer method
    # See: https://trac.ffmpeg.org/wiki/Concatenate#demuxer
    listfile = os.path.join(settings['tmp_dir'], 'list.txt')
    with open(listfile, 'w') as f:  # write list of files to be concatenated
        for file in files:
            f.write('file \'{}\'\n'.format(file))
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-f', 'concat',
        '-i', listfile,
        '-c', 'copy',
        destination
    ]
    proc = subprocess.call(call)
    if proc == 1:
        raise RuntimeError('merge files failed')
    os.remove(listfile)


def mux(video, audio, destination):
    tempfile = '~{vidname}+{audname}.{ext}'.format(
            vidname=os.path.splitext(os.path.basename(video))[0],
            audname=os.path.splitext(os.path.basename(audio))[0],
            ext=settings['v_container'])
    tempfile = os.path.join(settings['tmp_dir'], tempfile)
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-i', video,
        '-i', audio,
        '-c', 'copy',  # use copy to avoid re-encoding
        tempfile
    ]
    proc = subprocess.call(call)
    if proc == 1:
        raise RuntimeError('mux failed')
    shutil.move(tempfile, destination)


def atempo_factors_for_spd(s):
    # returns a list of `atempo` values between `ATEMPO_MIN` and `ATEMPO_MAX`
    # that when multiplied together will produce a desired speed
    def solve(s, limit):
        facs = []
        x = int(math.log(s) / math.log(limit))  # apply log rule for exponents
        for i in range(x):
            facs.append(limit)
        # get the final value
        y = s * 1.0 / math.pow(limit, x)
        facs.append(y)
        return facs
    if s < ATEMPO_MIN:
        return solve(s, ATEMPO_MIN)
    elif s > ATEMPO_MAX:
        return solve(s, ATEMPO_MAX)
    return [s]  # `s` is between bounds, no chaining needed
