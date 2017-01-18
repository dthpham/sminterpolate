import os
import shutil
import subprocess
import math
from butterflow.settings import default as settings


import logging
log = logging.getLogger('butterflow')


def mux_av(vid, audio, dest):
    tempfile = '{}+{}.{}.{}'.format(os.path.splitext(os.path.basename(vid))[0],
                                 os.path.splitext(os.path.basename(audio))[0],
                                 os.getpid(),
                                 settings['v_container'])
    tempfile = os.path.join(settings['tempdir'], tempfile)
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-i', vid,
        '-i', audio,
        '-c', 'copy',
        tempfile]
    log.debug('subprocess: {}'.format(' '.join(call)))
    if subprocess.call(call) == 1:
        raise RuntimeError
    shutil.move(tempfile, dest)


def concat_av_files(dest, files):
    tempfile = os.path.join(settings['tempdir'], 'list.{}.txt'.format(os.getpid()))
    with open(tempfile, 'w') as f:
        for file in files:
            f.write('file \'{}\'\n'.format(file))
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', tempfile,
        '-c', 'copy',
        dest]
    log.debug('subprocess: {}'.format(' '.join(call)))
    if subprocess.call(call) == 1:
        raise RuntimeError
    os.remove(tempfile)


def extract_audio(vid, dest, ss, to, speed=1.0):
    filename = os.path.splitext(os.path.basename(dest))[0]
    tempfile1 = os.path.join(settings['tempdir'],
                             '{}.{}.{}'.format(filename, os.getpid(), settings['v_container']).
                             lower())
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-i', vid,
        '-ss', str(ss/1000.0),
        '-to', str(to/1000.0),
        '-map_metadata', '-1',
        '-map_chapters', '-1',
        '-vn',
        '-sn']
    if settings['ca'] == 'aac':
        call.extend(['-strict', '-2'])
    call.extend([
        '-c:a', settings['ca'],
        '-b:a', settings['ba'],
        tempfile1])
    log.debug('subprocess: {}'.format(' '.join(call)))
    if subprocess.call(call) == 1:
        raise RuntimeError
    tempfile2 = os.path.join(settings['tempdir'],
                             '{}.{}x.{}.{}'.format(filename, speed, os.getpid(),
                                                settings['a_container']))
    def mk_atempo_chain(speed):
        if speed >= 0.5 and speed <= 2.0:
            return [speed]
        def solve(speed, limit):
            vals = []
            x = int(math.log(speed) / math.log(limit))
            for i in range(x):
                vals.append(limit)
            y = float(speed) / math.pow(limit, x)
            vals.append(y)
            return vals
        if speed < 0.5:
            return solve(speed, 0.5)
        else:
            return solve(speed, 2.0)
    chain = []
    for x in mk_atempo_chain(speed):
        chain.append('atempo={}'.format(x))
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-i', tempfile1,
        '-filter:a', ','.join(chain)]
    if settings['ca'] == 'aac':
        call.extend(['-strict', '-2'])
    call.extend([
        '-c:a', settings['ca'],
        '-b:a', settings['ba'],
        tempfile2])
    log.debug('subprocess: {}'.format(' '.join(call)))
    if subprocess.call(call) == 1:
        raise RuntimeError
    os.remove(tempfile1)
    shutil.move(tempfile2, dest)
