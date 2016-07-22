# Install From Source Guide

## Supported platforms
**Important:** BF only works on 64-bit systems.

Butterflow has been successfully built and tested on OS X 10.11 (El Capitan), Windows 10, Ubuntu 15.04 (Vivid Vervet), Debian 8.2 (Jessie), and Arch Linux. Getting BF to work on other Linux distributions *may* be possible, but expect any kind of support to be limited.

## Instructions

**Important:** Windows users, refer to the [Install on Windows Guide](Install-On-Windows-Guide.md#install-from-source).

### Compile and install Butterflow:
1. Install dependencies:
  * **OS X:**
    1. Install with [Homebrew](http://brew.sh/), `brew install ffmpeg` and `brew install homebrew/science/opencv --with-ffmpeg --with-opengl`.
    2. Install packages that will be used to set up a virtual environment with `sudo easy_install pip`, then `pip install virtualenv`.
  * **Arch Linux:**
    1. Install with `sudo pacman -S git python2-setuptools python2-virtualenv python2-numpy ocl-icd opencl-headers ffmpeg`.
    2. Install the [opencv2](https://aur.archlinux.org/packages/opencv2/) package from the AUR.
      * **Tip:** Remove all packages that depend on opencv, like opencv-samples, before installing opencv2. This will save you the trouble of re-compiling the package, which takes a long time, if the install fails.
  * **Ubuntu:** Install with `sudo apt-get install git virtualenv python-dev ocl-icd-opencl-dev libopencv-dev python-opencv ffmpeg`.
  * **Debian:**
      1. Install FFmpeg (See: [Install FFmpeg on Debian Guide](Install-FFmpeg-On-Debian-Guide.md)).
      2. Install other dependencies with `sudo apt-get install build-essential git python-virtualenv python-dev python-setuptools libopencv-dev python-opencv ocl-icd-opencl-dev libgl1-mesa-dev x264`.
2. Clone the project repo with `git clone https://github.com/dthpham/butterflow.git`.
3. Create a virtual environment:
  * **OS X (using the system's python):** `virtualenv -p /usr/bin/python butterflow`.
  * **Linux:** `virtualenv -p /usr/bin/python2 butterflow`.
4. Change into the project directory and activate the virtualenv with `source bin/activate`.
5. Add a path configuration file:
  * **OS X:** Pick up the cv2.so module with `echo "$(brew --prefix)/lib/python2.7/site-packages" > lib/python2.7/site-packages/butterflow.pth`.
    * **Alternative:** You can add Homebrew's Python site-packages to your PYTHONPATH with `export PYTHONPATH=$PYTHONPATH:$(brew --prefix)/lib/python2.7/site-packages`. Adding an export to your ~/.profile will save you the trouble of having to set this every time you activate the virtual environment.
    * **Important:** You may have to manually add /usr/local/lib and /usr/local/include to your search paths to pick up some headers and libraries. If you're using Xcode's clang, it will only search OS X SDK paths. You should install the Xcode Command Line tools with `xcode-select --install` to get a version that searches /usr/local by default.
  * **Arch Linux:** `echo "/usr/lib/python2.7/site-packages/" > lib/python2.7/site-packages/butterflow.pth`.
  * **Ubuntu or Debian:** `echo "/usr/lib/python2.7/dist-packages" > lib/python2.7/site-packages/butterflow.pth`.
    * **Side note:** dist-packages is a Debian-specific convention that is present in all derivative distros (Ubuntu, Mint, etc.).
6. Install it:
  * If you intend to edit the source code:
    * Create a development version with `python setup.py develop`.
    * **Tip:** Uninstall with `python setup.py develop -u`.
    * The development version will let you edit the source code and see the changes directly *without* having to reinstall everytime.
    * You must be inside a virtualenv to use butterflow if you used one (activate with `source bin/activate`).
  * If you're using the package without making changes:
    * Exit any virtualenv virtual environment you are in with `deactivate`.
    * Install with `python setup.py install`.
    * **Tip:** Uninstall with `pip2 uninstall butterflow`.

## What to do when you're done
* **Recommended:** Check if your OpenCL device is detected with `buutterflow -d`.
 * If it isn't, refer to [Setting up OpenCL](Setting-Up-OpenCL.md) for instructions on how to get it working. This step isn't required but when working on large segments of a video or with high resolution frames, rendering will be extremely slow without it.
* **Optional:** While in the project directory, you can run a suite of tests against butterflow with `python setup.py test`.
 * Tests will fail if OpenCL isn't set up.
