#!/usr/bin/env python2

import os
import re
import ast
from ctypes.util import find_library
from setuptools import setup, find_packages, Extension
import subprocess
import sys


# don't want to import __init__
version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('butterflow/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(version_re.search(
        f.read().decode('utf-8')).group(1)))

PKG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        'butterflow')
VND_PATH = os.path.join(PKG_PATH, '3rdparty')


def get_long_description():
    '''Convert README.md to .rst for PyPi, requires pandoc'''
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
    '''returns a modified environment. needed when running as root as it
    automatically clears some for safety which may cause certain calls, to
    pkg-config for example, to fail. installs may fail without passing this env
    to a subprocess'''
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
    proc = subprocess.call(['which', name], stdout=open(os.devnull, 'w'),
                           stderr=subprocess.STDOUT)
    return (proc == 0)


def have_library(name):
    '''check if a library is installed on the system using
    ctypes.util.find_library, fallback to pkg-config if not found. find_library
    will run external programs (ldconfig, gcc, and objdump) to find library
    files'''
    short_name = get_lib_short_name(name)
    res = find_library(short_name)
    if res:
        return True
    else:
        proc = subprocess.call(['pkg-config', '--exists', name],
                               env=get_extra_envs())
        return (proc == 0)


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
    else:
        return False


def pkg_config_res(*opts):
    '''takes opts for a pkg-config command and returns a list of strings that
    are compatible with setuptools
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
    '''returns library's namespec in the form :filename. ld will search the
    library path for a file called filename, otherwise it will search the
    library path for a file called libnamespec.a.'''
    return ':' + os.path.basename(get_lib_installed_path(libname))


def get_lib_short_name(name):
    '''returns a setuptools compatible lib name, without lib prefixes and
    suffixes such as .so, .dylib or version number'''
    name = name.strip()
    name = os.path.basename(name)
    if name.startswith('-l'):
        name = name[2:]
    if name.startswith('lib'):
        name = name[3:]

    chomp_at_string = lambda x, y: \
        x[:x.find(y)] if x.find(y) != -1 else x
    name = chomp_at_string(name, '.so')
    name = chomp_at_string(name, '.dylib')
    name = chomp_at_string(name, '.a')
    return name


def build_lst(*items):
    '''collects multiple string and lists items into a single list with all
    duplicates removed'''
    item_set = set([])
    for x in items:
        if isinstance(x, str):
            item_set.add(x)
        if isinstance(x, list):
            for y in x:
                item_set.add(y)
    return list(item_set)


def brew_pkg_installed(pkg):
    """Returns True if a brewed package is installed"""
    if have_command('brew'):
        brew_ls = subprocess.Popen(['brew', 'ls', '--versions', pkg],
                                   stdout=subprocess.PIPE,
                                   env=get_extra_envs()).stdout.read().strip()
        return (brew_ls != '')
    else:
        return False


py_ver_X = sys.version_info.major
py_ver_Y = sys.version_info.minor
py_ver = '{}.{}'.format(py_ver_X, py_ver_Y)
py_local_lib = '/usr/local/lib/python{}'.format(py_ver)
py_systm_lib = '/usr/lib/python{}'.format(py_ver)

homebrew_prefix = None
homebrew_site_pkgs = None
try:
    homebrew_prefix = subprocess.Popen(['brew', '--prefix'],
                                       stdout=subprocess.PIPE,
                                       env=get_extra_envs())
    homebrew_prefix = homebrew_prefix.stdout.read().strip()
except Exception:
    # fall back to environment variable if brew command is not found
    if 'HOMEBREW_PREFIX' in os.environ:
        homebrew_prefix = os.environ['HOMEBREW_PREFIX']
if homebrew_prefix is not None:
    homebrew_site_pkgs = os.path.join(homebrew_prefix, 'lib/python{}/'
                                      'site-packages/'.format(py_ver))


def check_dependencies():
    '''verifies if all dependencies have been met'''
    if py_ver_X != 2:
        return False, 'Python {} is not version 2.x'.format(py_ver)
    tools = ['pkg-config']
    # ldconfig is not guaranteed on OS X
    if sys.platform.startswith('linux'):
        tools.append('ldconfig')
    tools.append('python{}-config'.format(py_ver))
    for x in tools:
        if not have_command(x):
            return False, '{} is needed to complete the build process'.format(x)
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

    # Debian based distros use dist-packages
    sys.path.insert(1, os.path.join(py_local_lib, 'site-packages'))
    sys.path.insert(2, os.path.join(py_local_lib, 'dist-packages'))
    sys.path.insert(3, os.path.join(py_systm_lib, 'site-packages'))
    sys.path.insert(4, os.path.join(py_systm_lib, 'dist-packages'))
    if homebrew_site_pkgs is not None:
        # Because some formulae provide python bindings, homebrew builds
        # bindings against the first `python` (and `python-config`) in `PATH`
        # (check `which python`).
        # Hombrew site-packages should preceed all others on sys.path if it
        # exists:
        sys.path.insert(1, homebrew_site_pkgs)
    try:
        import cv2
    except ImportError:
        return False, 'opencv built with BUILD_opencv_python=ON required'
    return True, None


cflags = ['-g', '-Wall']
cflags.extend(['-Wno-cpp', '-Wno-unused-variable',
               '-Wno-unused-function'])  # Disable annoying warnings
cflags.extend(['-O0', '-fbuiltin'])  # With debug options
linkflags = []
includes = ['/usr/include', '/usr/local/include']
ldflags = ['/usr/lib', '/usr/local/lib']
py_includes = None
py_libs = None
libav_libs = ['avcodec', 'avformat', 'avutil']
py_prefix = subprocess.Popen(['python{}-config'.format(py_ver), '--prefix'],
                             stdout=subprocess.PIPE,
                             env=get_extra_envs()).stdout.read().strip()
if sys.platform.startswith('linux'):
    py_includes = pkg_config_res('--cflags', 'python-{}'.format(py_ver))
    py_libs = pkg_config_res('--libs', 'python-{}'.format(py_ver))
    linkflags.extend(['-shared', '-Wl,--export-dynamic'])
elif sys.platform.startswith('darwin'):
    linkflags.extend(['-arch', 'x86_64'])
    ldflags.append(os.path.join(py_prefix, 'lib'))
    if homebrew_prefix is not None:
        # The system python may not know which compiler flags to set to build
        # bindings for software installed in Homebrew so this may be needed:
        includes.append(os.path.join(homebrew_prefix, 'include'))
        ldflags.append(os.path.join(homebrew_prefix, 'lib'))
        # Don't explicity link against the system python on OSX to prevent
        # segfaults arising from modules being built with one python (i.e.
        # system python) and imported from a foreign python (i.e. brewed
        # python).
        # See: https://github.com/Homebrew/homebrew/blob/master/share/doc/
        # homebrew/Common-Issues.md#python-segmentation-fault-11-on-import-
        # some_python_module
        #
        # Building modules with `-undefined dynamic_lookup` instead of an
        # explict link allows symbols to be resolved at import time. `otool -L
        # <module>.so` shouldn't mention `Python`.
        # See: https://github.com/Homebrew/homebrew-science/pull/1886

    linkflags.extend(['-Wl,-undefined,dynamic_lookup'])
    # py_includes = os.path.join(py_prefix, 'include',
    #                            'python{}'.format(py_ver))
    # linkflags.append(os.path.join(py_prefix,
    #                              'lib/libpython{}.dylib'.format(py_ver)))
    # py_libs = ['python{}'.format(py_ver)]

avinfo = Extension(
    'butterflow.avinfo',
    extra_compile_args=cflags,
    extra_link_args=linkflags,
    include_dirs=build_lst(includes, py_includes),
    libraries=build_lst(libav_libs, py_libs),
    library_dirs=ldflags,
    sources=[
        os.path.join(PKG_PATH, 'avinfo.c'),
    ],
    language='c'
)

cl_ldflag = None
cl_lib = None
if sys.platform.startswith('linux'):
    # Use install path and a filename namespec to specify the OpenCL library
    cl_ldflag = os.path.dirname(get_lib_installed_path('libOpenCL'))
    cl_lib = get_lib_filename_namespec('libOpenCL')
elif sys.platform.startswith('darwin'):
    if homebrew_prefix is not None:
        # Homebrew opencv uses a brewed numpy by default but it's possible for
        # a user to their own or the system one if the `--without-brewed-numpy`
        # option is used.
        #
        # Note: usually all pythonX.Y packages with headers are placed in
        # `/usr/include/pythonX.Y/<package>` or `/usr/local/include/` but
        # homebrew policy is to put them in `site-packages`
        includes.append(os.path.join(homebrew_site_pkgs, 'numpy/core/include'))
    else:
        includes.append(os.path.join('/System/Library/Frameworks/'
                                     'Python.framework/Versions/{}/Extras/lib/'
                                     'python/numpy/core/include'.format(py_ver)))
    linkflags.extend(['-framework', 'OpenCL'])

ocl = Extension(
    'butterflow.ocl',
    extra_compile_args=cflags,
    extra_link_args=linkflags,
    include_dirs=build_lst(includes, py_includes),
    libraries=build_lst(py_libs, cl_lib),
    library_dirs=build_lst(ldflags, cl_ldflag),
    sources=[
        os.path.join(PKG_PATH, 'ocl.c'),
    ],
    language='c'
)

cxxflags = cflags
cv_includes = pkg_config_res('--cflags', 'opencv')
# cv_libs = pkg_config_res('--libs', 'opencv')
cv_libs = ['opencv_core', 'opencv_ocl', 'opencv_imgproc']

motion = Extension(
    'butterflow.motion',
    extra_compile_args=build_lst(cxxflags, '-std=c++11'),
    extra_link_args=linkflags,
    include_dirs=build_lst(VND_PATH, includes, cv_includes, py_includes),
    libraries=build_lst(cv_libs, py_libs, cl_lib),
    library_dirs=build_lst(ldflags, cl_ldflag),
    sources=[
        os.path.join(VND_PATH, 'opencv-ndarray-conversion/conversion.cpp'),
        os.path.join(PKG_PATH, 'motion.cpp'),
    ],
    depends=[
        os.path.join(VND_PATH, 'opencv-ndarray-conversion/conversion.h'),
    ],
    language='c++'
)

ret, error = check_dependencies()
if not ret:
    print(error)
    exit(1)

setup(
    name='butterflow',
    packages=find_packages(),
    ext_modules=[avinfo, ocl, motion],
    version=version,
    author='Duong Pham',
    author_email='dthpham@gmail.com',
    url='https://github.com/dthpham/butterflow',
    download_url='http://srv.dthpham.me/butterflow-{}.tar.gz'.format(
        version),
    description='Makes slow motion and smooth motion videos',
    long_description=get_long_description(),
    keywords=['slowmo', 'slow motion', 'smooth motion',
              'motion interpolation'],
    entry_points={
        'console_scripts': ['butterflow = butterflow.cli:main']
    },
    test_suite='tests'
)
