# Install on Windows Guide
**Requirements:** A 64-bit Windows 10 system with a [compatible graphics device](Setting-Up-OpenCL.md#device-compatibility).

## Instructions
### Using custom package scripts (recommended method):
1. Install the 64-bit version of [MSYS2](https://msys2.github.io/) and set it up using their guide.
2. Launch a MSYS2 shell.
3. Install dependencies with `pacman -S base-devel msys2-devel mingw-w64-x86_64-toolchain mingw-w64-x86_64-python2 mingw-w64-x86_64-python2-pip mingw-w64-x86_64-python2-numpy mingw-w64-x86_64-ffmpeg mingw-w64-x86_64-SDL2 git`.
    * Select to download all items in the toolchain when prompted.
4. Clone the BF repo with `git clone https://github.com/dthpham/butterflow.git`.
5. Change into the project's `packaging\windows` directory.
6. Install the mingw-w64-ocl-icd-git and mingw-w64-opencv2 packages by:
    1. Changing into each package directory.
    2. Building with `MINGW_INSTALLS=mingw64 makepkg-mingw -sLf`.
        * **Note:** Select defaults when prompted.
    3. Installing with `pacman -U mingw-w64-x86_64-<PACKAGE_NAME>-any.pkg.tar.xz`
7. Close the MSYS2 shell and launch a MINGW64 shell.
8. Switch back into the top-level of the project folder.
9. Install BF with `python2 setup.py develop`. At this point, you can use BF system-wide while in a MINGW64 shell.
    * **Tip:** To uninstall: `pip2 uninstall butterflow`.
10. See: [When finished](Install-From-Source-Guide.md#when-finished).

### Manually:
#### Set up a build environment with MSYS2:
1. Install the 64-bit version of [MSYS2](https://msys2.github.io/) and set it up using their guide.
2. Open the "Edit the system environment variables" dialog from the Control Panel and add these to the front of PATH: `PATH=C:\msys64\mingw64\local\bin;C:\msys64\mingw64\bin;C:\msys64\usr\bin`.
    * The ordering is important. Make sure these paths are above all other paths.
3. Launch a MSYS2 shell and download dependencies with `pacman -S git mingw-w64-x86_64-toolchain mingw-w64-x86_64-python2  mingw-w64-x86_64-python2-pip mingw-w64-x86_64-python2-numpy mingw-w64-x86_64-ffmpeg mingw-w64-x86_64-SDL2 git`.
    * Select to download all items in the toolchain when prompted.
4. Make distutils use the mingw32 compiler with `echo -e "[build]\ncompiler=mingw32" >> C:\msys64\mingw64\lib\python2.7\distutils\distutils.cfg`.
5. Make a `C:\msys64\mingw64\local` folder, and a `bin`, `lib`, and `include` folder inside it.
    * Libraries and headers from dependencies built manually will be put here so that we don't pollute the main environment.
    * `bin` will contain dynamic library files (.dll) and executables (.exe).
    * Headers (.h, .hpp) will be in `include`.
    * Import libraries (.dll.a) belong in `lib`.
    * **Tip**: It's safe to delete everything in this folder later on to revert back to a fresh environment.
6. Add the directory to sys.path with `echo -e "import site\n
site.addsitedir('C:/msys64/mingw64/local/lib/python2.7/site-packages')" > C:/msys64/mingw64/lib/python2.7/site-packages/sitecustomize.py`.
7. **Tip:** After setup you can use any console emulator of your choice, like [Cmder](http://cmder.net/) or Windows PowerShell, as long as PATH is set correctly.

#### Build dependencies:
##### OpenCV 2.x:
1. Grab the [OpenCV 2.4.13](https://github.com/opencv/opencv/releases/tag/2.4.13) source archive and extract it.
2. Go into the source directory and make a `build` folder inside it.
3. Go into the `3rdparty\ffmpeg` folder.
4. Delete al the \*.dll files inside.
5. Compile our version of FFmpeg with `gcc -Wall -shared -o opencv_ffmpeg_64.dll -x c++ -I..\include -I..\..\modules\highgui\src ffopencv.c -lavformat -lavcodec -lavdevice -lavresample -lswscale -lavutil -lws2_32 -lstdc++`.
6. Download [CMake](https://cmake.org/) and launch it.
7. Set the source and build directories then click Configure.
8. Select "MSYS2 Makefiles" and use "Default native compilers".
9. Most options will be pre-populated but you'll have to set these manually:
    * `CMAKE_BUILD_TYPE=Release`
    * `WITH_OPEN_GL=YES`
    * `ENABLE_PRECOMPILED_HEADERS=NO`
    * `CMAKE_SKIP_RPATH=ON`
    * `PYTHON_LIBRARY="C:\msys64\mingw64\lib\libpython2.7.dll.a"`
    * `PYTHON_PACKAGES_PATH="C:\msys64\mingw64\local\lib\python2.7\site-packages"`
    * **Optional:** `BUILD_WITH_DEBUG_INFO`, `BUILD_DOCS`, `BUILD_PERF_TESTS` , `BUILD_TESTS`, `BUILD_opencv_apps` can be safely set to `NO`.
10. Reconfigure, generate the build files, then change to the `build` directory.
11. Compile with `make -j<NUMBER>`.
    * `<NUMBER>` specifies how many threads to use.
12. Install with `make install`.
13. Copy the files in `build\install\x64\mingw\bin`, `build\install\x64\mingw\lib` and the headers from `build\install\include` to their corresponding locations in `C:\msys64\mingw64\local`.

#### Khronos OpenCL-ICD-Loader:
1. Do `git clone https://github.com/KhronosGroup/OpenCL-ICD-Loader.git`.
2. Get headers with `git clone https://github.com/KhronosGroup/OpenCL-Headers.git`.
3. Copy the header files (.h) from the OpenCL-Headers folder and put them inside `OpenCL-ICD-Loader\inc\CL`.
    * Make the `CL` folder because it won't exist.
4. Change into the OpenCL-ICD-Loader project directory.
5. Checkout a working branch with `git checkout -b r5.cb4acb9 cb4acb9`.
6. Add a `build` folder.
7. Open CMake and set the source and build directories then click Configure.
8. Select "MSYS2 Makefiles" and use "Default native compilers".
9. Set `CMAKE_BUILD_TYPE=Release`.
10. Reconfigure, generate the build files, and change to the `build` directory.
11. Compile with `make`.
12. Copy `bin\libOpenCL.dll` to `C:\msys64\mingw64\local\bin`.
13. Copy `libOpenCL.dll.a` to `C:\msys64\mingw64\local\lib`.
14. Copy the OpenCL headers to `C:\msys64\mingw64\local\include\CL`.

#### Compile and install BF:
1. Clone the repo with `git clone https://github.com/dthpham/butterflow.git`.
2. Change into the project directory.
3. Build extension modules with `python2 setup.py build_ext -IC:\msys64\mingw64\local\include -LC:\msys64\mingw64\local\lib`.
4. Install it with `python2 setup.py develop`. At this point, you can use BF system-wide.
    * **Tip:** To uninstall: `pip2 uninstall butterflow`.
5. See: [When finished](Install-From-Source-Guide.md#when-finished).
