#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import ast
import re
import subprocess
from setuptools import find_packages, Extension


# get version number
# avoid importing from package
version_re = re.compile(r'__version__\s+=\s+(.*)')
with open('butterflow/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(version_re.search(
        f.read().decode('utf-8')).group(1)))

# directories
rootdir = os.path.abspath(os.sep)
topdir = os.path.join(os.path.dirname(os.path.realpath(__file__)))
pkgdir = os.path.join(topdir, 'butterflow')
vendordir = os.path.join(topdir, 'vendor')

# are we building a development version?
building = True
for x in sys.argv:
    if x.startswith('build'):
        building = False
is_devbuild = 'dev' in version and not building


# make a list with no duplicates
# does not maintain ordering
def mklist(*items):
    s = set([])
    for x in items:
        if isinstance(x, list):
            for y in x:
                s.add(y)
        elif x is not None:
            s.add(x)
    return list(s)


py_ver_X = sys.version_info.major
py_ver_Y = sys.version_info.minor
py_ver = '{}.{}'.format(py_ver_X, py_ver_Y)

homebrew_prefix = None
homebrew_site_pkgs = None
try:
    homebrew_prefix = subprocess.Popen(['brew', '--prefix'],
                                       stdout=subprocess.PIPE)
    homebrew_prefix = homebrew_prefix.stdout.read().strip()
except Exception:
    # fall back to environment variable if brew command is not found
    if 'HOMEBREW_PREFIX' in os.environ:
        homebrew_prefix = os.environ['HOMEBREW_PREFIX']
if homebrew_prefix is not None:
    homebrew_site_pkgs = os.path.join(homebrew_prefix, 'lib/python{}/'
                                      'site-packages/'.format(py_ver))
    # Because some formulae provide python bindings, homebrew builds bindings
    # against the first python (and python-config) in PATH (check
    # `which python`).
    #
    # Homebrew site-packages should preceed all others on sys.path
    # if it exists:
    sys.path.insert(1, homebrew_site_pkgs)

cflags       = ['-std=c11']  # c compilation flags
linkflags    = []            # linker flags
cxxflags     = []

is_win = sys.platform.startswith('win')
is_osx = sys.platform.startswith('darwin')
is_nix = sys.platform.startswith('linux')

# global cflags
if is_devbuild:
    cflags.append('-Wall')
    cflags.append('-g')  # turn off debugging symbols for release
    cflags.extend(['-O0', '-fbuiltin', '-fdiagnostics-show-option'])

# disable warnings that are safe to ignore
cflags.extend(['-Wno-unused-variable', '-Wno-unused-function'])
if is_osx:
    cflags.extend(['-Wno-shorten-64-to-32', '-Wno-overloaded-virtual',
                   '-Wno-#warnings'])
else:
    cflags.extend(['-Wno-cpp'])

# set cxxflags, remove c only options
for x in cflags:
    if x != '-std=c11' and \
       x != '-Wstrict-prototypes':
        cxxflags.append(x)

# global link flags
if is_nix:
    linkflags.extend(['-shared', '-Wl,--export-dynamic'])
elif is_osx:
    # Don't explicity link against the system python on OSX to prevent
    # segfaults arising from modules being built with one python (i.e. system
    # python) and imported from a foreign python (i.e. brewed python).
    #
    # See: https://github.com/Homebrew/homebrew/blob/master/share/doc/
    # homebrew/Common-Issues.md#python-segmentation-fault-11-on-import-
    # some_python_module
    #
    # Building modules with `-undefined dynamic_lookup` instead of an explict
    # link allows symbols to be resolved at import time. `otool -L <module>.so`
    # shouldn't mention Python.
    # See: https://github.com/Homebrew/homebrew-science/pull/1886
    linkflags.append('-Wl,-undefined,dynamic_lookup')
    linkflags.extend(['-arch', 'x86_64'])

avinfo_ext = Extension('butterflow.avinfo', extra_compile_args=cflags,
                       extra_link_args=linkflags,
                       libraries=['avcodec', 'avformat', 'avutil'],
                       sources=[os.path.join(pkgdir, 'avinfo.c')],
                       language='c')

# opencl args
cl_lib = None
cl_linkflags = None
if is_osx:
    cl_linkflags = ['-framework', 'OpenCL']
else:
    cl_lib = ['OpenCL']

ocl_ext = Extension('butterflow.ocl', extra_compile_args=cxxflags,
                    extra_link_args=cl_linkflags, libraries=cl_lib,
                    sources=[os.path.join(pkgdir, 'ocl.cpp')], language='c')

# numpy args
np_includes = None
if is_osx:
    if homebrew_prefix is not None:
        # Homebrew opencv uses a brewed numpy by default but it's possible for
        # a user to their own or the system one if the --without-brewed-numpy
        # option is used.
        #
        # Note: usually all pythonX.Y packages with headers are placed in
        # /usr/include/pythonX.Y/<package> or /usr/local/include/, but
        # homebrew policy is to put them in site-packages
        np_includes = os.path.join(homebrew_site_pkgs, 'numpy/core/include')
    else:
        # fallback to the system's numpy
        np_includes = '/System/Library/Frameworks/Python.framework/Versions/'\
                      '{}/Extras/lib/python/numpy/core/include'.format(py_ver)

# opencv-ndarray-conversion args
nddir = os.path.join(vendordir, 'opencv-ndarray-conversion')
nd_includes = os.path.join(nddir, 'include')

motion_ext = Extension('butterflow.motion',
                       extra_compile_args=cxxflags,
                       extra_link_args=linkflags,
                       include_dirs=mklist(nd_includes, np_includes),
                       libraries=['opencv_core', 'opencv_ocl',
                                  'opencv_imgproc'],
                       sources=[os.path.join(pkgdir, 'motion.cpp'),
                                os.path.join(nddir, 'src', 'conversion.cpp')],
                       language='c++')

# should we use cxfreeze?
use_cx_freeze = False
if is_win and 'build_exe' in sys.argv:
    try:
        # cxfreeze extends setuptools and should be imported after it
        from cx_Freeze import setup, Executable
        use_cx_freeze = True
    except ImportError:
        # use setuptools if cxfreeze doesn't exist
        from setuptools import setup
else:
    from setuptools import setup

# shared args
setup_kwargs = {
    'name':         'butterflow',
    'packages':     find_packages(exclude=['tests']),
    'ext_modules':  [avinfo_ext, ocl_ext, motion_ext],
    'version':      version,
    'author':       'Duong Pham',
    'author_email': 'dthpham@gmail.com',
    'url':          'https://github.com/dthpham/butterflow',
    'download_url': 'http://srv.dthpham.me/butterflow/butterflow-{}.tar.gz'.
                    format(version),
    'description':  'Makes motion interpolated and fluid slow motion videos',
    'keywords':     ['motion interpolation', 'slow motion', 'slowmo',
                     'smooth motion'],
    'entry_points': {'console_scripts': ['butterflow = butterflow.cli:main']},
    'test_suite':   'tests'
}

import functools
setup = functools.partial(setup, **setup_kwargs)

if use_cx_freeze:
    # get files not picked up by cxfreeze
    import fnmatch
    include_files = []
    with open('win10-cxfreeze_include_files', 'r') as f:
        for line in f:
            line = line.rstrip()
            if line.startswith('PREFIX'):
                prefix = line.split('=')[1]
                continue
            else:
                pattern = line
                for file in os.listdir(prefix):
                    if fnmatch.fnmatch(file, pattern):
                        filename = file
                relpath = os.path.relpath(os.path.join(prefix, filename))
                include_files.append((relpath, filename))
    build_exe_options = {
        'packages': ['butterflow'],
        'include_msvcr': True,
        'excludes': ['Tkinter'],
        'include_files': include_files
    }
    executables = [
        Executable(script='butterflow/__main__.py',
                   targetName='butterflow.exe',
                   icon='butterflow.ico',
                   base=None)
    ]
    setup(options={'build_exe': build_exe_options}, executables=executables)
else:
    setup()
