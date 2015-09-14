#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
This setup script will build the application for Linux, OS X, and Windows.

A frozen distribution of the application (with the python interpreter and third
party libraries embedded) can be built for Windows if cx_Freeze is installed.

"""
import os
import sys
import ast
import re
import subprocess
from ctypes.util import find_library
from setuptools import find_packages, Extension


# get version number (avoid importing from package)
version_re = re.compile(r'__version__\s+=\s+(.*)')
with open('butterflow/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(version_re.search(
        f.read().decode('utf-8')).group(1)))

# directories
rootdir   = os.path.abspath(os.sep)
topdir    = os.path.join(os.path.dirname(os.path.realpath(__file__)))
pkgdir    = os.path.join(topdir, 'butterflow')
vendordir = os.path.join(topdir, 'vendor')

# are we building a development version?
building = True
for x in sys.argv:
    if x.startswith('build'):
        building = False
is_devbuild = 'dev' in version and not building


def have_cmd(c):
    """Checks if a command is callable on the system.
    """
    proc = subprocess.call(['which', c], stdout=open(os.devnull, 'w'),
                           stderr=subprocess.STDOUT)
    return (proc == 0)


def have_library(l):
    """Checks if a library is installed on the system using `ctypes.util.
    find_library`. `find_library` will run external programs such as
    `ldconfig`, `gcc`, and `objdump` to find library files. This will fall back
    to using `pkg-config` if it is not found.
    """
    short_name = get_lib_short_name(l)
    res = find_library(short_name)
    if res:
        return True
    else:
        proc = subprocess.call(['pkg-config', '--exists', l])
        return (proc == 0)


def have_library_object_file(lib, objfilename):
    """Check if a library object file exists.
    """
    if have_library(lib):
        call = ['pkg-config', '--libs', lib]
        res = subprocess.Popen(call, stdout=subprocess.PIPE).stdout.read()
        res = res.strip()
        res = res.split(' ')
        res = map(get_lib_short_name, res)
        return (get_lib_short_name(objfilename) in res)
    else:
        return False


def get_lib_installed_path(l):
    """Use `ldconfig` to find the full installation path of a library
    """
    call = ['ldconfig', '-p']
    res = subprocess.Popen(call, stdout=subprocess.PIPE,
                           universal_newlines=True).stdout.read()
    if l not in res:
        return None
    res = res.split('\n\t')
    for x in res:
        if x.startswith(l):
            y = x.split('=>')
            return y[1].strip()
    return None


def get_lib_short_name(l):
    """"Returns a `setuptools` compatible library name - without prefixes and
    suffixes such as `.so`, `.dylib` or version number.
    """
    l = l.strip()
    l = os.path.basename(l)
    if l.startswith('-l'):
        l = l[2:]
    elif l.startswith('lib'):
        l = l[3:]
    cut_at_str = lambda x, y: x[:x.find(y)] if x.find(y) != -1 else x
    l = cut_at_str(l, '.so')
    l = cut_at_str(l, '.dylib')
    l = cut_at_str(l, '.a')
    return l


def get_lib_filename_namespec(l):
    """Returns a library's namespec in the form `:<filename>`.

    `ld` will search the library path for a file called `<filename>`, otherwise
    it will search the library path for a file called `libnamespec.a`.
    """
    return ':' + os.path.basename(get_lib_installed_path(l))


def mklist(*items):
    """Collects string and lists and returns a single list with all duplicate
    items removed.
    """
    s = set([])
    for x in items:
        if isinstance(x, str):
            s.add(x)
        elif isinstance(x, list):
            for y in x:
                s.add(y)
    return list(s)


def pkg_config_res_to_setuptools(*opts):
    """Takes options from `pkg-config` and returns a list of strings that are
    compatible with `setuptools`.
    """
    call = ['pkg-config']
    call.extend(opts)
    res = subprocess.Popen(call, stdout=subprocess.PIPE).stdout.read()
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
    # Because some formulae provide python bindings, homebrew builds
    # bindings against the first `python` (and `python-config`) in `PATH`
    # (check `which python`).
    #
    # Hombrew site-packages should preceed all others on sys.path if it
    # exists:
    sys.path.insert(1, homebrew_site_pkgs)

cflags       = []      # compilation flags
includes     = []      # search paths for header files
ldflags      = []      # library search paths
linkflags    = []      # linker flags
py_includes  = None    # python header files
py_libs      = None    # python library search paths
libav_libs   = ['avcodec', 'avformat', 'avutil']
cl_ldflag    = None    # opencl library search path
cl_lib       = None    # name of the opencl library
cl_includes  = None    # opencl header search paths
cl_linkflags = None
cxxflags     = cflags
np_includes  = None    # numpy header search paths
cv_includes  = None    # search path for opencv header files
cv_ldflags   = None    # opencv library search paths
cv_libs      = ['opencv_core', 'opencv_ocl', 'opencv_imgproc']
cv_ver       = 2411    # cv library version

is_win = sys.platform.startswith('win')
is_osx = sys.platform.startswith('darwin')
is_nix = sys.platform.startswith('linux')

# windows vendor dirs
if is_win:
    various_dir = os.path.join(vendordir, 'various', 'bin')
    cl_dir = os.path.join(vendordir, 'opencl')
    cv_dir = os.path.join(vendordir, 'opencv')

# global cflags
if is_devbuild:
    cflags.append('-Wall')
    cflags.append('-g')  # turn off debugging symbols for release
    cflags.extend(['-O0', '-fbuiltin'])

# building with msvc?
if is_win:
    # http://bugs.python.org/issue11722
    # cflags.append('-DMS_WIN64')  # code specific to the MS Win64 API
    # cflags.append('-DWIN32')     # and to the MS Win32 API
    pass

# disable warnings that are safe to ignore
cflags.extend(['-Wno-unused-variable', '-Wno-unused-function'])
if is_nix or is_win:
    cflags.append('-Wno-cpp')
elif is_osx:
    cflags.extend(['-Wno-shorten-64-to-32', '-Wno-overloaded-virtual',
                   '-Wno-#warnings'])

# global link flags
if is_nix:
    linkflags.extend(['-shared', '-Wl,--export-dynamic'])
elif is_osx:
    # Don't explicity link against the system python on OSX to prevent
    # segfaults arising from modules being built with one python (i.e.
    # system python) and imported from a foreign python (i.e. brewed
    # python).
    #
    # See: https://github.com/Homebrew/homebrew/blob/master/share/doc/
    # homebrew/Common-Issues.md#python-segmentation-fault-11-on-import-
    # some_python_module
    #
    # Building modules with `-undefined dynamic_lookup` instead of an
    # explict link allows symbols to be resolved at import time. `otool -L
    # <module>.so` shouldn't mention `Python`.
    # See: https://github.com/Homebrew/homebrew-science/pull/1886
    linkflags.append('-Wl,-undefined,dynamic_lookup')
    linkflags.extend(['-arch', 'x86_64'])

avinfo_ext = Extension('butterflow.avinfo',
                       extra_compile_args=cflags,
                       extra_link_args=linkflags,
                       libraries=libav_libs,
                       sources=[os.path.join(pkgdir, 'avinfo.c')],
                       language='c')
# opencl flags
if is_nix:
    # Use install path and a filename namespec to specify the OpenCL library
    cl_ldflag = os.path.dirname(get_lib_installed_path('libOpenCL'))
    cl_lib = get_lib_filename_namespec('libOpenCL')
elif is_osx:
    cl_linkflags = ['-framework', 'OpenCL']
elif is_win:
    cl_includes = os.path.join(cl_dir, 'include')
    cl_ldflag = os.path.join(cl_dir, 'lib')
    cl_lib = 'OpenCL'

ocl_ext = Extension('butterflow.ocl',
                    extra_compile_args=cflags,
                    extra_link_args=linkflags + cl_linkflags,
                    include_dirs=mklist(cl_includes),
                    libraries=mklist(cl_lib),
                    library_dirs=mklist(cl_ldflag),
                    sources=[os.path.join(pkgdir, 'ocl.c')],
                    language='c')

# numpy flags
if is_osx:
    if homebrew_prefix is not None:
        # Homebrew opencv uses a brewed numpy by default but it's possible for
        # a user to their own or the system one if the `--without-brewed-numpy`
        # option is used.
        #
        # Note: usually all pythonX.Y packages with headers are placed in
        # `/usr/include/pythonX.Y/<package>` or `/usr/local/include/` but
        # homebrew policy is to put them in `site-packages`
        np_includes = os.path.join(homebrew_site_pkgs, 'numpy/core/include')
    else:
        np_includes = '/System/Library/Frameworks/Python.framework/Versions/'\
                      '{}/Extras/lib/python/numpy/core/include'.format(py_ver)
elif is_win:
    import site
    np_includes = [os.path.join(dir, 'numpy', 'core', 'include') for dir in
                   site.getsitepackages()]

# opencv flags
if is_nix or is_osx:
    cv_includes = pkg_config_res_to_setuptools('--cflags', 'opencv')
elif is_win:
    # path to cv headers and libraries
    cv_includes = os.path.join(cv_dir, 'include')
    cv_ldflags = os.path.join(cv_dir, 'lib')
    # append version number to library names
    cv_libs = ['{}{}'.format(lib, cv_ver) for lib in cv_libs]

# opencv ndarray conversion flags
ndconv_dir = os.path.join(vendordir, 'opencv-ndarray-conversion')
ndconv_includes = os.path.join(ndconv_dir, 'include')

motion_ext = Extension('butterflow.motion',
                       extra_compile_args=cxxflags,
                       extra_link_args=linkflags,
                       include_dirs=mklist(cv_includes, ndconv_includes),
                       libraries=mklist(cv_libs, cl_lib),
                       library_dirs=mklist(cv_ldflags, cl_ldflag),
                       sources=[os.path.join(pkgdir, 'motion.cpp'),
                                os.path.join(ndconv_dir, 'src',
                                             'conversion.cpp')],
                       language='c++')

use_cx_freeze = False
if 'build_exe' in sys.argv:
    try:
        # cx_Freeze extends setuptools and should be imported after it
        from cx_Freeze import setup, Executable
        use_cx_freeze = True
    except ImportError:
        # just use setuptools if cxfreeze doesn't exist
        from setuptools import setup
else:
    from setuptools import setup

# shared arguments
setup_kwargs = {
    'name': 'butterflow',
    'packages': find_packages(),
    'ext_modules': [avinfo_ext, ocl_ext, motion_ext],
    'version': version,
    'author': 'Duong Pham',
    'author_email': 'dthpham@gmail.com',
    'url': 'https://github.com/dthpham/butterflow',
    'download_url': 'http://srv.dthpham.me/butterflow-{}.tar.gz'.
                    format(version),
    'description': 'Makes slow motion and motion interpolated videos',
    'keywords': ['slowmo', 'slow motion', 'smooth motion',
                 'motion interpolation'],
    'entry_points': {
        'console_scripts': ['butterflow = butterflow.cli:main']
    },
    'test_suite': 'tests'
}

import functools
setup_function = functools.partial(setup, **setup_kwargs)

if use_cx_freeze:
    # collect ffmpeg executable and all other dependent DLLs
    # these files should have been copied to the vendor dir before conducting
    # the build process but were not
    include_files = []
    for fname in os.listdir(various_dir):
        include_files.append((os.path.join(various_dir, fname), fname))
    # manually add DLL for opencv that wasn't picked up by cxfreeze
    cv_ffmpeg_dll = 'opencv_ffmpeg{}_64.dll'.format(cv_ver)
    include_files.append(
        (os.path.join(vendordir, 'opencv', 'bin', cv_ffmpeg_dll),
         cv_ffmpeg_dll)
    )
    build_exe_options = {
        'packages': ['butterflow'],
        'include_msvcr': True,
        'excludes': ['Tkinter'],
        'include_files': include_files
    }
    executables = [
        Executable(script='butterflow/__main__.py',
                   targetName='butterflow.exe',
                   icon='share/butterflow.ico',
                   base=None)
    ]
    setup_function(
        options={'build_exe': build_exe_options},
        executables=executables
    )
else:
    setup_function()
