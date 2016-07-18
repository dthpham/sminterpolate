# Install on Windows 10 Guide
**Important** Only works on 64-bit machines.

## Set up a build environment with MSYS2
Install the 64-bit version of [msys2](https://msys2.github.io/) and set it up
using their guide. Now launch the "Edit system environment variables for your
account dialog" and add to the top of PATH. The ordering is important.
```
PATH=C:\msys64\mingw64\local\bin;C:\msys64\mingw64\bin;C:\msys64\usr\bin
```
Launch the msys2 shell and download some dependencies.
```
pacman -S git mingw-w64-x86_64-toolchain mingw-w64-x86_64-python2  mingw-w64-x86_64-python2-pip mingw-w64-x86_64-python2-numpy mingw-w64-x86_64-ffmpeg
```
Now edit `C:\msys64\mingw64\lib\python2.7\distutils\distutils.cfg` to make
distutils use the mingw32 compiler:
```
[build]
compiler=mingw32
```

### The local folder
We're going to put library files and headers inside `C:\msys64\mingw64\local`
for convenience. Make a `bin`, `lib`, and `include` folder inside it if they
don't exist.

**Tip** It's safe to nuke the folder later on if you want to revert to a fresh
environment.

## Building OpenCV2
Grab the [opencv2 source](https://github.com/opencv/opencv/releases) and
extract it. Go into the source directory and make a `build` folder inside it.

Download [CMake](https://cmake.org/) and launch it. Point to the source and
build directories and click Configure. Select "MSYS2 Makefiles" and use
"Default native compilers". Set these build options:
```
CMAKE_BUILD_TYPE=Release
WITH_OPEN_GL=YES
ENABLE_PRECOMPILED_HEADERS=NO
BUILD_opencv_apps=NO
BUILD_PERF_TESTS=NO
BUILD_TESTS=NO
BUILD_DOCS=NO
PYTHON_LIBRARY="C:/msys64/mingw64/lib/libpython2.7.dll.a"
PYTHON_PACKAGES_PATH="C:/msys64/mingw64/lib/python2.7/site-packages"
```
Generate the build files, then build it.
```
cd build
mingw32-make -j4
mingw32-make install
```  

Copy `build\install\x64\mingw\bin`, `build\install\x64\mingw\lib`, and headers
in `build\install\include` to their corresponding locations in
`C:\msys64\mingw64\local`.

## Building Khronos OpenCL-ICD-Loader
Clone the repo and make a build directory:
```
git clone https://github.com/KhronosGroup/OpenCL-ICD-Loader.git
mkdir -p OpenCL-ICD-Loader\build
mkdir -p OpenCL-ICD-Loader\inc\CL
```
Clone the OpenCL-1.2 headers and copy them over:
```
git clone https://github.com/KhronosGroup/OpenCL-Headers.git
cd OpenCL-Headers
cp *.h ..\OpenCL-ICD-Loader\inc\CL\
cd ..
```

Open CMake and set the source and build folders for OpenCL-ICD-Loader, then
configure with these build options:
```
CMAKE_BUILD_TYPE=Release
```

Generate the build files, then build it:
```
cd OpenCL-ICD-Loader\build
mingw32-make -j4
```

Copy `libOpenCL.dll.a` and `bin\libOpenCL.dll` to their corresponding locations
in `C:\msys64\mingw64\local`. Copy the OpenCL headers to
`C:\msys64\mingw64\local\include\CL`.

## Build a development version of Butterflow

```
git clone https://github.com/dthpham/butterflow.git
cd butterflow
python setup.py build_ext -IC:\msys64\mingw64\local\include -LC:\msys64\mingw64\local\lib
python setup.py develop
```

## System-wide installation
```
python setup.py install
```
To uninstall: `$ pip2 uninstall butterflow`.
