__version__ = '0.1.4a2'
__all__ = ['butterflow']

import os
import subprocess

user_home = os.path.expanduser('~')
data_path = os.path.join(user_home, '.butterflow')
cache_path = os.path.join(data_path, 'cache')
conf_path = os.path.join(data_path, 'config')
if not os.path.exists(data_path):
  os.makedirs(data_path)
if not os.path.exists(cache_path):
  os.makedirs(cache_path)

have_command = lambda(x): (subprocess.call(['which', x],
                                           stdout=open(os.devnull, 'w'),
                                           stderr=subprocess.STDOUT)) == 0
av_util = None
have_ffmpeg = have_command('ffmpeg')
have_avconv = have_command('avconv')
if not have_ffmpeg and not have_avconv:
  print('You need FFMPEG or Libav to use this app.')
  exit(1)
if have_avconv:
  av_util = 'avconv'
if have_ffmpeg:
  av_util = 'ffmpeg'

with open(conf_path, 'w') as f:
  f.write('avutil={}'.format(av_util))
  f.write('\n')
