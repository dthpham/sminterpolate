# extracts audio, alters speed, and muxes it with a video

import os
import shutil
import subprocess
import math
from butterflow.settings import default as settings

def extract_audio_with_spd(src, dst, ss, to, spd=1.0):
    fname = os.path.splitext(os.path.basename(dst))[0]
    tempfile1 = os.path.join(settings['tempdir'],
                             '~{}.{}'.format(fname, settings['v_container']).
                             lower())
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-i', src,
        '-ss', str(ss/1000.0),  # ss in ms
        '-to', str(to/1000.0),  # to in ms
        '-map_metadata', '-1',
        '-map_chapters', '-1',
        '-vn',
        '-sn']
    if settings['ca'] == 'aac':
        call.extend(['-strict', '-2'])  # aac is an experimental encoder so
        # -strict experimental or -strict 2 is req
    call.extend([
        '-c:a', settings['ca'],
        '-b:a', settings['ba'],
        tempfile1])
    if subprocess.call(call) == 1:
        raise RuntimeError
    # change spd using atempo filter
    tempfile2 = os.path.join(settings['tempdir'],
                             '~{}.{}x.{}'.format(fname, spd,
                                                 settings['a_container']))
    atempo_chain = []  # chain atempo filts to workaround val limitation
    for f in mk_product_chain(spd, 0.5, 2.0):
        if f == 1:
            continue
        atempo_chain.append('atempo={}'.format(f))
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-i', tempfile1,
        '-filter:a', ','.join(atempo_chain)]
    if settings['ca'] == 'aac':
        call.extend(['-strict', '-2'])
    call.extend([
        '-c:a', settings['ca'],
        '-b:a', settings['ba'],
        tempfile2])
    if subprocess.call(call) == 1:
        raise RuntimeError
    os.remove(tempfile1)
    shutil.move(tempfile2, dst)

def concat_av_files(dst, files):
    # concatenates files of the same type (same codec and codec parameters) in
    # sequence using ffmpeg's concat demuxer method
    # See: https://trac.ffmpeg.org/wiki/Concatenate#demuxer
    tempfile = os.path.join(settings['tempdir'], 'list.txt')
    with open(tempfile, 'w') as f:
        for file in files:
            f.write('file \'{}\'\n'.format(file))
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-f', 'concat',
        '-i', tempfile,
        '-c', 'copy',
        dst]
    if subprocess.call(call) == 1:
        raise RuntimeError
    os.remove(tempfile)

def mux_av(vid, audio, dst):
    tempfile = '~{}+{}.{}'.format(os.path.splitext(os.path.basename(vid))[0],
                                  os.path.splitext(os.path.basename(audio))[0],
                                  settings['v_container'])
    tempfile = os.path.join(settings['tempdir'], tempfile)
    call = [
        settings['avutil'],
        '-loglevel', settings['av_loglevel'],
        '-y',
        '-i', vid,
        '-i', audio,
        '-c', 'copy',  # use copy to avoid re-encoding
        tempfile]
    if subprocess.call(call) == 1:
        raise RuntimeError
    shutil.move(tempfile, dst)

def mk_product_chain(prd, min, max):
    # returns a list of values between [min,max] when multiplied together will
    # yield a desired product
    if prd >= min and prd <= max:
        return [1, prd]
    def solve(prd, limit):
        vals = []
        x = int(math.log(prd) / math.log(limit))  # apply log rule for exps
        for i in range(x):
            vals.append(limit)
        y = float(prd) / math.pow(limit, x)
        vals.append(y)
        return vals
    if prd < min:
        return solve(prd, min)
    else:
        return solve(prd, max)
