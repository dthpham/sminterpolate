# Install From Source Guide
**Important:** Read [What to do when you're done](#what-to-do-when-youre-done) after installing.

## Supported platforms
**Important:** Butterflow only works on 64-bit systems.

Butterflow has been successfully built and tested on several platforms, including OS X 10.11 (El Capitan), Windows 10, Ubuntu 15.04 (Vivid Vervet), Debian 8.2 (Jessie), and Arch Linux. Getting Butterflow to work on other Linux distributions *may* be possible, but expect any kind of support to be limited.

## Instructions
### Windows 10:
See the [Install on Windows Guide](Install-On-Windows-Guide.md).

### OS X (El Capitan):
These instructions will show you how to compile Butterflow using OS X's pre-installed Python. At minimum, you will need to have OS X Mavericks installed.

1. Install dependencies with [Homebrew](http://brew.sh/) with `brew install ffmpeg` and `brew install homebrew/science/opencv --with-ffmpeg`.
 * **Optional:** You can build opencv `--with-opengl` to use OpenGL windows.
2. Install packages that will be used to set up a virtual environment with `sudo easy_install pip`, then `pip install virtualenv`.
3. Clone the butterflow repo with `git clone https://github.com/dthpham/butterflow.git`.
4. Create a virtual environment using the system's python with `virtualenv -p /usr/bin/python butterflow`.
5. Change into the project directory and activate the virtualenv with `source bin/activate`.
6. Pick up the cv2.so module with `echo "$(brew --prefix)/lib/python2.7/site-packages" > lib/python2.7/site-packages/butterflow.pth`.
 * **Alternative:** You can add Homebrew's Python site-packages to your PYTHONPATH with `export PYTHONPATH=$PYTHONPATH:$(brew --prefix)/lib/python2.7/site-packages`. Adding an export to your ~/.profile will save you the trouble of having to set this every time you activate the virtual environment.
7. [Install it](#installing-it).

#### Search paths
You may have to manually add `/usr/local/lib` and `/usr/local/include` to your search paths to pick up some headers and libraries. If you're using Xcode's clang, it will only search OS X SDK paths. You should install the Xcode Command Line tools with `xcode-select --install` to get a version that searches `/usr/local` by default.

### Ubuntu (Vivid Vervet):
1. Install dependencies with `sudo apt-get install git virtualenv python-dev ocl-icd-opencl-dev libopencv-dev python-opencv ffmpeg`.
2. [Set up the project folder](#setting-up-the-project-folder).
3. [Install it](#installing-it).

**Side note:** The Vivid Vervet version of Ubuntu brings back support for FFmpeg, installing Butterflow will be more difficult on older versions of Ubuntu because that package is not readily available.

### Debian (Jessie):
1. Install FFmpeg using the [Install FFmpeg on Debian Guide](Install-FFmpeg-On-Debian-Guide.md).
2. Install other dependencies with `sudo apt-get install build-essential git python-virtualenv python-dev python-setuptools libopencv-dev python-opencv ocl-icd-opencl-dev libgl1-mesa-dev x264`
3. [Set up the project folder](#setting-up-the-project-folder).
4. [Install it](#installing-it).

### Arch Linux:
1. Install dependencies with `sudo pacman -S git python2-setuptools python2-virtualenv python2-numpy ocl-icd opencl-headers ffmpeg`
2. Install the [opencv2](https://aur.archlinux.org/packages/opencv2/) package from the AUR.
 * **Tip:** Remove all packages that depend on opencv, like opencv-samples, before installing opencv2. This will save you the trouble of re-compiling the package, which takes a long time, if the install fails.
3. [Set up the project folder](#setting-up-the-project-folder).
4. [Install it](#installing-it).

## Setting up the project folder
1. Clone the project repo with `git clone https://github.com/dthpham/butterflow.git`.
2. Create a virtual environment with `virtualenv -p /usr/bin/python2 butterflow`.
3. Change into the project directory and activate the virtualenv with `source bin/activate`.
4. Add a path configuration file
 * Ubuntu or Debian: `echo "/usr/lib/python2.7/dist-packages" > lib/python2.7/site-packages/butterflow.pth`. **Side note:** dist-packages is a Debian-specific convention that is present in all derivative distros (Ubuntu, Mint, etc.).
 * Arch Linux: `echo "/usr/lib/python2.7/site-packages/" > lib/python2.7/site-packages/butterflow.pth`.

## Installing it
4. If you intend to edit the source code:
  * Create a development version with `python setup.py develop`.
  * The development version will let you edit the source code and see the changes directly *without* having to reinstall everytime.
  * You will have to be inside a virtualenv to use butterflow if you used one. On Windows 10, you should be able to use butterflow system-wide without having to activate one everytime.
  * **Tip:** Uninstall with `python setup.py develop -u`.
5. If you're going to use the package without making changes:
  * Exit any virtualenv virtual environment you are in first with `deactivate`.
  * Install with `python setup.py install`.
  * **Tip:** Uninstall with `pip2 uninstall butterflow`.

## What to do when you're done installing
1. **Recommended:** Check if your OpenCL device is detected with `buutterflow -d`.
 * If it isn't, refer to [Setting up OpenCL](Setting-up-OpenCL.md) for instructions on how to get it working. This step isn't required but when working on large segments of a video or with high resolution frames, rendering will be extremely slow without it.
2. **Optional:** While in the project directory, you can run a suite of tests against butterflow with `python setup.py test`.
 * Tests will fail if OpenCL isn't set up.
