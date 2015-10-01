# Author: Duong Pham
# Copyright 2015

import os
import shutil
import subprocess
import math
from butterflow import avinfo
from butterflow.settings import default as settings

ATEMPO_MIN = 0.5
ATEMPO_MAX = 2.0


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
    # change tempo
    tempfile2 = '~{filename}.{spd}x.{ext}'.format(
        filename=filename,
        spd=spd,
        ext=settings['a_container']
    )
    tempfile2 = os.path.join(settings['tmp_dir'], tempfile2)
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
    listfile = os.path.join(settings['tmp_dir'], 'list.txt')
    with open(listfile, 'w') as f:
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
        '-c', 'copy',
        tempfile
    ]
    proc = subprocess.call(call)
    if proc == 1:
        raise RuntimeError('mux failed')
    shutil.move(tempfile, destination)


def atempo_factors_for_spd(s):
    def solve(s, limit):
        facs = []
        # apply log rule to solve for exponent
        x = int(math.log(s) / math.log(limit))
        for i in range(x):
            facs.append(limit)
        y = s * 1.0 / math.pow(limit, x)
        facs.append(y)
        return facs
    if s < ATEMPO_MIN:
        return solve(s, ATEMPO_MIN)
    elif s > ATEMPO_MAX:
        return solve(s, ATEMPO_MAX)
    return [s]
