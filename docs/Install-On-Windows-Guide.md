# Install on Windows 10 Guide
**Important:** This guide is only meant for 64-bit systems.

## Set up a build environment with MSYS2
1. Install the 64-bit version of [msys2](https://msys2.github.io/) and set it up using their guide.
2. Launch the "Edit the system environment variables" dialog from the Control Panel and add these to the front of PATH: `PATH=C:\msys64\mingw64\local\bin;C:\msys64\mingw64\bin;C:\msys64\usr\bin`.
 * The ordering is important, make sure these paths are above all other paths.
3. Launch the msys2 shell and download dependencies with `pacman -S git mingw-w64-x86_64-toolchain mingw-w64-x86_64-python2  mingw-w64-x86_64-python2-pip mingw-w64-x86_64-python2-numpy mingw-w64-x86_64-ffmpeg`.
4. Make distutils use the mingw32 compiler with `echo -e "[build]\ncompiler=mingw32" >> C:\msys64\mingw64\lib\python2.7\distutils\distutils.cfg`.
5. Make a `C:\msys64\mingw64\local` folder, and a `bin`, `lib`, and `include` folder inside it.
 * Library files and headers from dependencies built from hand will be put here so we can point to a central location (as a search path) more easily when compiling butterflow later on.
 * `bin` will contain dynamic library files (.dll) and executables (.exe).
 * Headers (.h, .hpp) will be in `include`.
 * Import libraries (.dll.a) belong in `lib`.
 * **Tip**: It's safe to delete everything in this folder later on if you want to revert back to a fresh environment.

 **Tip:** After set up you can use any console emulator of your choice, like [Cmder](http://cmder.net/) or Windows PowerShell, as long as the PATH is set correctly.

## Build more dependencies

### OpenCV 2.x:
1. Grab the latest [opencv2 source archive](https://github.com/opencv/opencv/releases) and extract it.
2. Go into the source directory and make a `build` folder inside it.
3. Download [CMake](https://cmake.org/) and launch it.
4. Set the source and build directories and click Configure.
5. Select "MSYS2 Makefiles" and use "Default native compilers".
6. Most options will be prepopulated, but you'll have to set these manually:
 * `CMAKE_BUILD_TYPE=Release`
 * `WITH_OPEN_GL=YES`
 * `ENABLE_PRECOMPILED_HEADERS=NO`
 * `PYTHON_LIBRARY="C:/msys64/mingw64/lib/libpython2.7.dll.a"`
 * `PYTHON_PACKAGES_PATH="C:/msys64/mingw64/lib/python2.7/site-packages"`
 * **Optional:** `BUILD_opencv_apps`, `BUILD_PERF_TESTS` , `BUILD_TESTS`, and `BUILD_DOCS` can be safely set to `NO`.
7. Reconfigure, generate the build files, then change to the `build` directory.
8. Compile with `mingw32-make -j<NUMBER>`.
  * `<NUMBER>` specifies how many threads to use.
9. Install with `mingw32-make install`.
10. Copy the files from `build\install\x64\mingw\bin`, `build\install\x64\mingw\lib` and the headers from `build\install\include` to their corresponding locations in `C:\msys64\mingw64\local`.

### Khronos OpenCL-ICD-Loader:
1. Do `git clone https://github.com/KhronosGroup/OpenCL-ICD-Loader.git`.
2. Get headers with `git clone https://github.com/KhronosGroup/OpenCL-Headers.git`.
3. Copy the header files (.h) from the OpenCL-Headers folder and put them inside `OpenCL-ICD-Loader\inc\CL`.
4. Change into the OpenCL-ICD-Loader project directory.
5. Add a `build` folder.
6. Open CMake and set the source and build directories and click Configure.
7. Select "MSYS2 Makefiles" and use "Default native compilers".
8. Set `CMAKE_BUILD_TYPE=Release`.
9. Reconfigure, generate the build files, and change to the `build` directory.
10. Compile with `mingw32-make`.
11. Copy `libOpenCL.dll.a` and `bin\libOpenCL.dll` to their corresponding locations in `C:\msys64\mingw64\local`.
12. Copy the OpenCL headers to `C:\msys64\mingw64\local\include\CL`.
 * Make the `CL` folder because it won't exist.

## Compile and install Butterflow
1. Clone the repo with `git clone https://github.com/dthpham/butterflow.git`.
2. Change into the project directory.
3. Build extension modules with `python setup.py build_ext -IC:\msys64\mingw64\local\include -LC:\msys64\mingw64\local\lib`.
4. Install Butterflow (See: [Installing it](Install-From-Source-Guide.md#installing-it)).
5. See: [What to do when you're done](Install-From-Source-Guide.md#what-to-do-when-youre-done-installing).
