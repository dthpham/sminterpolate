# Install on Windows Guide
**Important:** BF only works on 64-bit systems.

## The prebuilt version
Download link: [butterflow-0.2.2.dev0-alpha.1.7z](http://srv.dthpham.me/butterflow/releases/win/butterflow-0.2.2.dev0-alpha.1.7z).

### How to use it:
1. Extract the archive to a folder.
2. Launch cmd.exe.
3. Change into the package directory.
4. Run butterflow.exe with `butterflow <options> <video>`.
 * **Tip:** Add the location of the project folder to PATH to run BF from anywhere.

## Install from source
**Important:** This guide is meant for Windows 10 users.

### Set up a build environment with MSYS2:
1. Install the 64-bit version of [msys2](https://msys2.github.io/) and set it up using their guide.
2. Open the "Edit the system environment variables" dialog from the Control Panel and add these to the front of PATH: `PATH=C:\msys64\mingw64\local\bin;C:\msys64\mingw64\bin;C:\msys64\usr\bin`.
 * The ordering is important, make sure these paths are above all other paths.
3. Launch the msys2 shell and download dependencies with `pacman -S git mingw-w64-x86_64-toolchain mingw-w64-x86_64-python2  mingw-w64-x86_64-python2-pip mingw-w64-x86_64-python2-numpy mingw-w64-x86_64-ffmpeg`.
4. Make distutils use the mingw32 compiler with `echo -e "[build]\ncompiler=mingw32" >> C:\msys64\mingw64\lib\python2.7\distutils\distutils.cfg`.
5. Make a `C:\msys64\mingw64\local` folder, and a `bin`, `lib`, and `include` folder inside it.
 * Libraries and headers from dependencies built manually will be put here so we don't pollute the main environment.
 * `bin` will contain dynamic library files (.dll) and executables (.exe).
 * Headers (.h, .hpp) will be in `include`.
 * Import libraries (.dll.a) belong in `lib`.
 * **Tip**: It's safe to delete everything in this folder later on to revert back to a fresh environment.
6. Add the directory to sys.path with `echo -e "import site\n
site.addsitedir('C:/msys64/mingw64/local/lib/python2.7/site-packages')" > C:/msys64/mingw64/lib/python2.7/site-packages/sitecustomize.py`.

 **Tip:** After set up you can use any console emulator of your choice, like [Cmder](http://cmder.net/) or Windows PowerShell, as long as PATH is set correctly.

### Build dependencies:

#### OpenCV 2.x:
1. Grab the latest [opencv2 source archive](https://github.com/opencv/opencv/releases) and extract it.
2. Go into the source directory and make a `build` folder inside it.
3. Go into the `3rdparty\ffmpeg` folder.
4. Delete al the \*.dll files inside.
5. Compile our version of FFmpeg with `gcc -Wall -shared -o opencv_ffmpeg_64.dll -x c++ -I..\include -I..\..\modules\highgui\src ffopencv.c -lavformat -lavcodec -lavdevice -lavresample -lswscale -lavutil -lws2_32 -lstdc++`.
6. Download [CMake](https://cmake.org/) and launch it.
7. Set the source and build directories and click Configure.
8. Select "MSYS2 Makefiles" and use "Default native compilers".
9. Most options will be prepopulated, but you'll have to set these manually:
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
5. Add a `build` folder.
6. Open CMake and set the source and build directories and click Configure.
7. Select "MSYS2 Makefiles" and use "Default native compilers".
8. Set `CMAKE_BUILD_TYPE=Release`.
9. Reconfigure, generate the build files, and change to the `build` directory.
10. Compile with `make`.
11. Copy `bin\libOpenCL.dll` to `C:\msys64\mingw64\local\bin`.
12. Copy `libOpenCL.dll.a` to `C:\msys64\mingw64\local\lib`.
13. Copy the OpenCL headers to `C:\msys64\mingw64\local\include\CL`.

### Compile and install Butterflow:
1. Clone the repo with `git clone https://github.com/dthpham/butterflow.git`.
2. Change into the project directory.
3. Build extension modules with `python setup.py build_ext -IC:\msys64\mingw64\local\include -LC:\msys64\mingw64\local\lib`.
4. Install it with `python setup.py develop`.
 * At this point you should be able to use BF system-wide.
 * **Tip:** To uninstall: `pip uninstall butterflow`.
5. See: [What to do when you're done](Install-From-Source-Guide.md#what-to-do-when-youre-done).
