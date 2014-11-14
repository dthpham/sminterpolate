#!/usr/bin/env python2

from setuptools import setup, find_packages, Extension, Command
import subprocess
import sys
import os
import re
import shutil
from butterflow.__init__ import __version__ as version
from ctypes.util import find_library

F_NULL = open(os.devnull, 'w')

B_MEDIA = 'butterflow/media/'
B_MOTION = 'butterflow/motion/'


class ProjectInit(Command):
  description = 'inits the project'
  user_options = []

  def initialize_options(self):
    self.root_path = None
    self.repo_path = None

  def finalize_options(self):
    self.root_path = os.path.dirname(os.path.realpath(__file__))
    self.repo_path = os.path.join(self.root_path, 'repos')

  def run(self):
    if not have_command('git'):
      print('Must have git installed to run init')
      return

    os.chdir(self.root_path)
    if not os.path.exists(self.repo_path):
      os.makedirs(self.repo_path)
    subprocess.call([
        'git',
        'submodule',
        'init'
    ])
    subprocess.call([
        'git',
        'submodule',
        'update'
    ])
    submod_path = os.path.join(self.repo_path, 'opencv-ndarray-conversion')
    motion_path = os.path.join(self.root_path, 'butterflow', 'motion')
    shutil.copy(os.path.join(submod_path, 'conversion.cpp'), motion_path)
    shutil.copy(os.path.join(submod_path, 'conversion.h'), motion_path)


class Reset(Command):
  description = 'resets project to original state'
  user_options = []

  def initialize_options(self):
    self.cwd = None
    self.root_path = None

  def finalize_options(self):
    self.cwd = os.getcwd()
    self.root_path = os.path.dirname(os.path.realpath(__file__))

  def run(self):
    if self.cwd != self.root_path:
      raise RuntimeWarning(
          'Must be in pkg root ({}) to run clean'.format(self.root_path))
    else:
      os.system('rm -f out.mp4')
      os.system('rm -rf *.clb')
      os.system('rm -rf *.pyc')
      os.system('rm -rf ~/.butterflow')
      os.system('rm -rf build')
      os.system('rm -rf dist')
      os.system('rm -rf butterflow.egg-info')
      os.system('rm -rf repos')
      os.system('rm -rf butterflow/motion/conversion.*')
      will_rem = set()
      will_walk = [
          os.path.join(self.root_path, 'butterflow'),
          os.path.join(self.root_path, 'tests'),
      ]
      for w in will_walk:
        for root, dirs, files in os.walk(w):
          for f in files:
            name, ext = os.path.splitext(f)
            if ext in ['.so', '.pyc']:
              will_rem.add(os.path.join(root, f))
      for x in will_rem:
        os.remove(x)


def get_long_description():
  '''Convert README.md to .rst for PyPi, requires pandoc. Because
  pandoc has a ridiculous amount of dependencies, it might be better to
  just re-write the README in rST format as Github also supports it.
  '''
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

    # fix interpreted text links when converting to rst
    new_description = []
    re_interpreted_txt_link = r'(```.*``\s<.*>`__)'
    matcher = re.compile(r'^```(.*)``\s<(.*)>`__$')
    for x in re.split(re_interpreted_txt_link, long_description):
      matches = matcher.match(x)
      if matches:
        txt, link = matches.groups()
        new_txt = '``{}``'.format(txt)
        x = new_txt
      new_description.append(x)

    long_description = ''.join(new_description)
  except ImportError:
    pass
  return long_description


def get_extra_envs():
  '''returns a modified environment. needed when running as root
  as it automatically clears some for safety which may cause certain
  calls, to pkg-config for example, to fail. installs may fail
  without passing this env to a subprocess'''
  env = os.environ.copy()
  local_pkg_config_paths = \
      '/usr/local/lib/pkgconfig:'\
      '/usr/local/pkgconfig:'\
      '/usr/share/pkgconfig'
  if 'PKG_CONFIG_PATH' in env:
    pkg_config_path = env['PKG_CONFIG_PATH']
    pkg_config_path = pkg_config_path + ':' + local_pkg_config_paths
    env['PKG_CONFIG_PATH'] = pkg_config_path
  else:
    env['PKG_CONFIG_PATH'] = local_pkg_config_paths
  return env


def have_command(name):
  '''checks if a command is callable on the system'''
  proc = subprocess.call(['which', name], stdout=F_NULL,
                         stderr=subprocess.STDOUT)
  return (proc == 0)


def have_library(name):
  '''check if a library is installed on the system using
  ctypes.util.find_library, fallback to pkg-config if not found.
  find_library will run external programs (ldconfig, gcc, and objdump)
  to find library files'''
  short_name = get_lib_short_name(name)
  res = find_library(short_name)
  if not res:
    proc = subprocess.call(['pkg-config', '--exists', name],
                           env=get_extra_envs())
    return (proc == 0)
  return True


def have_library_object_file(libname, name):
  '''check if library has specific object file'''
  if have_library(libname):
    call = ['pkg-config', '--libs', libname]
    res = subprocess.Popen(
        call,
        stdout=subprocess.PIPE,
        env=get_extra_envs()).stdout.read()
    res = res.strip()
    res = res.split(' ')
    res = map(get_lib_short_name, res)
    return get_lib_short_name(name) in res


def pkg_config_res(*opts):
  '''takes opts for a pkg-config command and returns a list of strings
  that are compatible with setuptools
  '''
  call = ['pkg-config']
  call.extend(opts)
  res = subprocess.Popen(call,
                         stdout=subprocess.PIPE,
                         env=get_extra_envs()).stdout.read()
  res = res.strip()
  res = res.split(' ')
  lst = []
  for x in res:
    if x == '':
      continue
    x = x.strip()
    if x[0] == '-':
      x = x[1:]
    if x[0] in 'lLI':
      lst.append(x[1:])
    else:
      lst.append(get_lib_short_name(x))
  return lst


def get_lib_installed_path(libname):
  '''use ldconfig to find the full installation path of a library'''
  call = ['ldconfig', '-p']
  res = subprocess.Popen(call,
                         stdout=subprocess.PIPE,
                         universal_newlines=True).stdout.read()
  if libname not in res:
    return None
  res = res.split('\n\t')
  for x in res:
    if x.startswith(libname):
      y = x.split('=>')
      return y[1].strip()
  return None


def get_lib_filename_namespec(libname):
  '''returns library's namespec in the form :filename. ld will search
  the library path for a file called filename, otherwise it will
  search the library path for a file called libnamespec.a.'''
  return ':' + os.path.basename(get_lib_installed_path(libname))


def get_lib_short_name(name):
  '''returns a setuptools compatible lib name, without lib prefixes
  and suffixes such as .so, .dylib or version number'''
  name = name.strip()
  name = os.path.basename(name)
  if name.startswith('-l'):
    name = name[2:]
  if name.startswith('lib'):
    name = name[3:]

  def chop_at(x, y):
    idx = x.find(y)
    if idx != -1:
      x = x[:idx]
    return x
  name = chop_at(name, '.so')
  name = chop_at(name, '.dylib')
  name = chop_at(name, '.a')
  return name


def build_lst(*items):
  '''collects multiple string and lists items into a single list with
  all duplicates removed'''
  item_set = set([])
  for x in items:
    if isinstance(x, str):
      item_set.add(x)
    if isinstance(x, list):
      for y in x:
        item_set.add(y)
  return list(item_set)


def check_dependencies():
  '''verifies if all dependencies have been met'''
  for x in ['pkg-config',
            'ldconfig']:
    if x == 'ldconfig' and sys.platform.startswith('darwin'):
        continue
    if not have_command(x):
      return False, '{} command is needed to complete the build process'.\
          format(x)
  for x in ['opencv',
            'avformat',
            'avcodec',
            'avutil',
            'OpenCL']:
    if not have_library(x):
      return False, '{} library is needed to complete the build process'.\
          format(x)
  for x, y in [('opencv', 'libopencv_ocl.so'),
               ('opencv', 'libopencv_core.so'),
               ('opencv', 'libopencv_imgproc.so')]:
    if not have_library_object_file(x, y):
      return False, '{} library is missing object file {}'.format(x, y)

  # debian based distros use dist-packages
  local_site_pkgs = \
      '/usr/local/lib/python2.7/site-packages'
  local_dist_pkgs = \
      '/usr/local/lib/python2.7/dist-packages'
  systm_site_pkgs = \
      '/usr/lib/python2.7/site-packages'
  systm_dist_pkgs = \
      '/usr/lib/python2.7/dist-packages'
  sys.path.insert(1, local_site_pkgs)
  sys.path.insert(2, local_dist_pkgs)
  sys.path.insert(3, systm_site_pkgs)
  sys.path.insert(4, systm_dist_pkgs)
  try:
    import cv2
  except ImportError:
    return False, 'opencv built with BUILD_opencv_python=ON required'
  return True, None


cflags = ['-g', '-Wall']
linkflags = []
includes = ['/usr/include', '/usr/local/include']
ldflags = ['/usr/lib', '/usr/local/lib']
py_includes = None
py_libs = None
libav_libs = ['avcodec', 'avformat', 'avutil']
homebrew_prefix = None
if sys.platform.startswith('linux'):
  py_includes = pkg_config_res('--cflags', 'python-2.7')
  py_libs = pkg_config_res('--libs', 'python-2.7')
  linkflags.extend(['-shared', '-Wl,--export-dynamic'])
elif sys.platform.startswith('darwin'):
  linkflags.extend(['-arch', 'x86_64'])
  homebrew_prefix = None
  try:
      homebrew_prefix = subprocess.Popen(['brew', '--prefix'],
                                         stdout=subprocess.PIPE,
                                         env=get_extra_envs()).stdout.read().strip()
  except Exception:
    # fall back to environment variable if brew command is not found
    if 'HOMEBREW_PREFIX' in os.environ:
        homebrew_prefix = os.environ['HOMEBREW_PREFIX']
  if homebrew_prefix is not None:
    includes.append(os.path.join(homebrew_prefix, 'include'))
    includes.append(os.path.join(homebrew_prefix, 'lib'))
  # py_libs and py_includes is not being found under osx
  # py_libs.append('python2.7')

py_libav_info = Extension(
    'butterflow.media.py_libav_info',
    extra_compile_args=cflags,
    extra_link_args=linkflags,
    include_dirs=build_lst(B_MEDIA, includes, py_includes),
    libraries=build_lst(libav_libs, py_libs),
    library_dirs=ldflags,
    sources=[
        B_MEDIA + 'py_libav_info.c'
    ],
    depends=[
        B_MEDIA + 'py_libav_info.h'
    ],
    language='c'
)

cflags = ['-g', '-Wall', '-std=c++11']
cv_includes = pkg_config_res('--cflags', 'opencv')
cv_libs = pkg_config_res('--libs', 'opencv')
cl_ldflag = None
cl_lib = None
if sys.platform.startswith('linux'):
  # Use install path and a filename namespec to specify the OpenCL library
  cl_ldflag = os.path.dirname(get_lib_installed_path('libOpenCL'))
  cl_lib = get_lib_filename_namespec('libOpenCL')
elif sys.platform.startswith('darwin'):
  # Expecting python and numpy installed with homebrew
  # Ideally, all python2.x packages with headers should be placed in
  # /usr/include/python2.x/<package> or /usr/local/include/... but that doesn't
  # happen when using the numpy package from homebrew
  includes.append(os.path.join(homebrew_prefix,
                               'lib/python2.7/site-packages/numpy/core/include'))
  linkflags.extend(['-framework', 'OpenCL'])

py_motion = Extension(
    'butterflow.motion.py_motion',
    extra_compile_args=cflags,
    extra_link_args=linkflags,
    include_dirs=build_lst(B_MOTION, includes, cv_includes, py_includes),
    libraries=build_lst(cv_libs, py_libs, cl_lib),
    library_dirs=build_lst(ldflags, cl_ldflag),
    sources=[
        B_MOTION + 'conversion.cpp',
        B_MOTION + 'ocl_interpolate.cpp',
        B_MOTION + 'ocl_optical_flow.cpp',
        B_MOTION + 'py_motion.cpp'
    ],
    depends=[
        B_MOTION + 'conversion.h',
        B_MOTION + 'ocl_interpolate.h',
        B_MOTION + 'ocl_optical_flow.h',
        B_MOTION + 'py_motion.h',
    ],
    language='c++'
)

ret, err = check_dependencies()
if not ret:
  print(err)
  exit(1)

setup(
    name='butterflow',
    packages=find_packages(),
    ext_modules=[py_libav_info, py_motion],
    version=version,
    author='Duong Pham',
    author_email='dthpham@gmail.com',
    url='https://github.com/dthpham/butterflow',
    download_url='https://github.com/dthpham/butterflow/tarball/{}'.format(
        version),
    description='Lets you create slow motion and smooth motion videos',
    long_description=get_long_description(),
    keywords=['slowmo', 'slow motion', 'interpolation'],
    entry_points={
        'console_scripts': ['butterflow = butterflow.butterflow:main']
    },
    cmdclass={
        'init': ProjectInit,
        'reset': Reset
    },
    test_suite='tests'
)
