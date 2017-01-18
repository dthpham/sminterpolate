# -*- coding: utf-8 -*-

import sys
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
    log.info('[Subprocess] Combinining audio & video')
    log.debug('Call: {}'.format(' '.join(call)))
    if subprocess.call(call) == 1:
        raise RuntimeError
    log.info("Moving:\t%s -> %s", os.path.basename(tempfile), dest)
    shutil.move(tempfile, dest)


def concat_av_files(dest, files):
    tempfile = os.path.join(settings['tempdir'], 'list.{}.txt'.format(
                            os.getpid()))
    log.info("Writing list file:\t{}".format(os.path.basename(tempfile)))
    with open(tempfile, 'w') as f:
        for file in files:
            if sys.platform.startswith('win'):
                file = file.replace('/', '//')
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
    log.info('[Subprocess] Concatenating audio files')
    log.debug('Call: {}'.format(' '.join(call)))
    if subprocess.call(call) == 1:
        raise RuntimeError
    log.info("Delete:\t%s", os.path.basename(tempfile))
    os.remove(tempfile)


def extract_audio(vid, dest, ss, to, speed=1.0):
    filename = os.path.splitext(os.path.basename(dest))[0]
    tempfile1 = os.path.join(settings['tempdir'],
                             '{}.{}'.format(filename, settings['v_container']).
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
    log.info('[Subprocess] Video chunk extraction')
    log.debug('Call: {}'.format(' '.join(call)))
    log.info("Extracting to:\t%s", os.path.basename(tempfile1))
    if subprocess.call(call) == 1:
        raise RuntimeError
    tempfile2 = os.path.join(settings['tempdir'],
                             '{}.{}x.{}'.format(filename, speed,
                                                settings['a_container']))
    def solve_atempo_chain(speed):
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
    atempo_chain = solve_atempo_chain(speed)
    chain_string = ""
    chain = []
    for i, tempo in enumerate(atempo_chain):
        chain.append('atempo={}'.format(tempo))
        chain_string += str(tempo)
        if i < len(atempo_chain)-1:
            chain_string += "*"
    log.info("Solved tempo chain for speed ({}x): {}".format(speed,
                                                              chain_string))
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
    log.info('[Subprocess] Altering audio tempo')
    log.debug('Call: {}'.format(' '.join(call)))
    log.info("Writing to:\t%s", os.path.basename(tempfile2))
    if subprocess.call(call) == 1:
        raise RuntimeError
    log.info("Delete:\t%s", os.path.basename(tempfile1))
    os.remove(tempfile1)
    log.info("Moving:\t%s -> %s", os.path.basename(tempfile2),
             os.path.basename(dest))
    shutil.move(tempfile2, dest)
