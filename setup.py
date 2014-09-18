from setuptools import setup, find_packages, Extension
import subprocess
import os
from butterflow.__init__ import __version__ as version
import pdb


b_repos = 'butterflow/repos/'
b_media = 'butterflow/media/'
b_motion = 'butterflow/motion/'


# Convert README.md to .rst for PyPi, requires pandoc
# Because pandoc has a ridiculous amount of dependencies and it would
# probably be better re-write the README in RST format as Github can
# render it
#
# To install pandoc on Arch Linux:
# $ aur -S haskell-pandoc
# Or
# $ sudo pacman -S ghc alex happy cabal-install
# $ sudo cabal update
# $ sudo cabal install --global pandoc
# For python bindings:
# $ pip install pyandoc
long_description = ''
try:
  import pandoc
  proc = subprocess.Popen(
      ['which pandoc'],
      shell=True,
      stdout=subprocess.PIPE,
      universal_newlines=True
  )
  pandoc_path = proc.communicate()[0]
  pandoc_path = pandoc_path.strip()
  pandoc.core.PANDOC_PATH = pandoc_path

  doc = pandoc.Document()
  doc.markdown = open('README.md', 'r').read()

  long_description = doc.rst
except ImportError:
  pass


def have_command(name):
  '''checks if a command is callable on the system'''
  proc = subprocess.call(['which', name])
  return (proc == 0)


def have_library(name):
  '''check if a library is installed on the system'''
  proc = subprocess.call(['pkg-config', '--exists', name])
  return (proc == 0)


def have_library_object_file(libname, name):
  '''check if library has specific object file'''
  if have_library(libname):
    c = ['pkg-config', '--libs', libname]
    res = subprocess.Popen(c, stdout=subprocess.PIPE).stdout.read()
    res = res.strip()
    res = res.split(' ')
    for x in res:
      if not x.startswith('-l'):
        if os.path.basename(x) == name:
          return True
    return False


def git_init_submodules():
  if not os.path.exists(b_repos):
    os.makedirs(b_repos)
  repo_name = 'opencv-ndarray-conversion'
  submod_path = b_repos + repo_name
  if not os.path.exists(submod_path):
    proc = subprocess.call([
        'git',
        'clone',
        '-b', '2.4-latest',
        '--single-branch',
        'https://github.com/dthpham/opencv-ndarray-conversion.git',
        submod_path
    ])
    if proc == 1:
      raise RuntimeError('submodule initialization failed')
  save_wd = os.getcwd()
  os.chdir(b_motion)
  if not os.path.exists('conversion.cpp'):
    os.symlink('../repos/'+repo_name+'/conversion.cpp', 'conversion.cpp')
  if not os.path.exists('conversion.h'):
    os.symlink('../repos/'+repo_name+'/conversion.h', 'conversion.h')
  os.chdir(save_wd)


def pkg_config_res(*opts):
  '''takes opts for a pkg-config command and returns a list of strings
  without lib prefixes and .so suffixes
  '''
  c = ['pkg-config']
  c.extend(opts)
  res = subprocess.Popen(c, stdout=subprocess.PIPE).stdout.read()
  res = res.strip()
  res = res.split('-')
  lst = []
  for x in res:
    if x is not '':
      x = x.strip()
      if len(x.split(' ')) > 1:
        sep = x.split(' ')
        for y in sep:
          lib_name_ext = os.path.basename(y)
          lib_name, _ = os.path.splitext(lib_name_ext)
          lib_name = lib_name[3:] if lib_name.startswith('lib') else lib_name
          lst.append(lib_name)
        continue
      elif x[0] in 'lLI':
        lst.append(x[1:])
      else:
        lst.append(x)
  return lst


def build_lst(*lsts):
  '''collects multiple irems and lists into a single list'''
  lst = []
  for l in lsts:
    if not isinstance(l, list):
      for x in l:
        lst.append(x)
    else:
      lst.extend(l)
  return lst


for x in ['pkg-config',
          'git',
          'ffmpeg']:
  if not have_command(x):
    raise RuntimeError(
        '{} command is needed to complete the build process'.format(x))

for x in ['opencv',
          'libavformat',
          'libavcodec',
          'python2']:
  if not have_library(x):
    raise RuntimeError(
        '{} library is needed to complete the build process'.format(x))

for x, y in [('opencv', 'libopencv_ocl.so'),
             ('opencv', 'libopencv_core.so'),
             ('opencv', 'libopencv_imgproc.so')]:
  if not have_library_object_file(x, y):
    raise RuntimeError(
        '{} library is missing object file'.format((x, y)))

try:
  import cv2
except ImportError:
  raise RuntimeError('opencv built with BUILD_opencv_python=ON required')


cflags = ['-g', '-Wall']
linkflags = ['-shared', '-Wl,--export-dynamic']
includes = ['/usr/include', '/usr/local/include']
ldflags = ['/usr/lib', '/usr/local/lib']
py_includes = pkg_config_res('--cflags', 'python2')
py_libs = pkg_config_res('--libs', 'python2')
libav_libs = ['avcodec', 'avformat']

py_libav_info = Extension(
    'butterflow.media.py_libav_info',
    extra_compile_args=cflags,
    extra_link_args=linkflags,
    include_dirs=build_lst(b_media, includes, py_includes),
    libraries=build_lst(libav_libs, py_libs),
    library_dirs=ldflags,
    sources=[
        b_media+'py_libav_info.c'
    ],
    depends=[
        b_media+'py_libav_info.h'
    ],
    language='c'
)

cflags = ['-g', '-Wall', '-std=c++11']
cv_includes = pkg_config_res('--cflags', 'opencv')
cv_libs = pkg_config_res('--libs', 'opencv')

py_motion = Extension(
    'butterflow.motion.py_motion',
    extra_compile_args=cflags,
    extra_link_args=linkflags,
    include_dirs=build_lst(b_motion, includes, cv_includes, py_includes),
    libraries=build_lst(cv_libs, py_libs),
    library_dirs=ldflags,
    sources=[
        b_motion+'conversion.cpp',
        b_motion+'ocl_interpolate.cpp',
        b_motion+'ocl_optical_flow.cpp',
        b_motion+'py_motion.cpp'
    ],
    depends=[
        b_motion+'conversion.h',
        b_motion+'ocl_interpolate.h',
        b_motion+'ocl_optical_flow.h',
        b_motion+'py_motion.h',
    ],
    language='c++'
)


git_init_submodules()

setup(
    name='butterflow',
    packages=find_packages(exclude=['repos']),
    install_requires=[
        'numpy'
    ],
    ext_modules=[py_libav_info, py_motion],
    version=version,
    author='Duong Pham',
    author_email='dthpham@gmail.com',
    url='https://github.com/dthpham/butterflow',
    download_url='https://github.com/dthpham/butterflow/tarball/{}'.format(version),
    description='Lets you create slow motion and smooth motion videos',
    long_description=long_description,
    keywords=['slowmo', 'slow motion', 'interpolation'],
    entry_points={
        'console_scripts': ['butterflow = butterflow.butterflow:main']
    },
    test_suite='tests'
)
