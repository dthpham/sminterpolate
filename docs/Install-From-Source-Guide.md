# Install From Source Guide
**Important** [Set up OpenCL](Setting-up-OpenCL.md) when you're done.

## Supported platforms
Butterflow has been successfully built and tested on several platforms,
including OS X 10.11 (El Capitan), Windows 10, Ubuntu 15.04 (Vivid Vervet),
Debian 8.2 (Jessie), and Arch Linux.

Getting Butterflow to work on other Linux distributions may be possible, but
expect support to be limited.

## Instructions
### Windows 10
See the [Install on Windows Guide](Install-On-Windows-Guide.md).

### OS X (El Capitan)
These instructions will show you how to compile and build a development version
of Butterflow using OS X's pre-installed Python. At minimum, you will need to
have OS X Mavericks installed.

First, install dependencies with [Homebrew](http://brew.sh/).
```
brew install ffmpeg
brew install homebrew/science/opencv --with-ffmpeg --with-opengl
```

Then install packages that will be used to set up a virtual environment.
```
sudo easy_install pip
pip install virtualenv
```

Then build and install a development version of Butterflow.
```
git clone https://github.com/dthpham/butterflow.git
virtualenv -p /usr/bin/python butterflow
cd butterflow
source bin/activate
# Pick up the cv2.so module
echo "$(brew --prefix)/lib/python2.7/site-packages" > lib/python2.7/site-packages/butterflow.pth
# Alternatively, you can add Homebrew's Python site-packages to your
# PYTHONPATH. Adding an exxport to your ~/.profile will save you the trouble of
# having to set this every time you activate the virtual environment:
# export PYTHONPATH=$PYTHONPATH:$(brew --prefix)/lib/python2.7/site-packages
python setup.py develop
```

#### Search paths
You may have to manually add /usr/local/lib and /usr/local/include to your
search paths to pick up some headers and libraries. If you're using Xcode's
clang, it will only search OS X SDK paths. You should install the Xcode Command
Line tools with `xcode-select --install` to get a version that searches
/usr/local by default.

### Ubuntu (Vivid Vervet)
These instructions will show you how to get Butterflow working in Ubuntu 15.04
(Vivid Vervet). This version of Ubuntu brings back support for FFmpeg,
installing Butterflow is more difficult on older versions of Ubuntu because it's
not readily available.

First, install tools, development files, and a generic OpenCL library and its
headers.
```
sudo apt-get install git virtualenv python-dev ocl-icd-opencl-dev libopencv-dev python-opencv ffmpeg
```

Then download and build Butterflow.
```
git clone https://github.com/dthpham/butterflow.git
virtualenv -p /usr/bin/python2 butterflow
cd butterflow
source bin/activate
# dist-packages is a Debian-specific convention that is present in derivative distros
echo "/usr/lib/python2.7/dist-packages" > lib/python2.7/site-packages/butterflow.pth
python setup.py develop
```

### Debian (Jessie)
First, install FFMPEG using this [guide](Install-FFmpeg-On-Debian-Guide.md).

Then install all other dependencies.
```
sudo apt-get install build-essential git python-virtualenv python-dev python-setuptools libopencv-dev python-opencv ocl-icd-opencl-dev libgl1-mesa-dev x264
```

Then download and build Butterflow.
```
git clone https://github.com/dthpham/butterflow.git
virtualenv -p /usr/bin/python2 butterflow
cd butterflow
source bin/activate
echo "/usr/lib/python2.7/dist-packages" > lib/python2.7/site-packages/butterflow.pth
python setup.py develop
```

### Arch Linux
First, install dependencies.
```
sudo pacman -S git python2-setuptools python2-virtualenv python2-numpy ocl-icd opencl-headers ffmpeg
# Get OpenCV 2.x the AUR
yaourt -S opencv2
```

Then download and build Butterflow.
```
git clone https://github.com/dthpham/butterflow.git
virtualenv2 -p /usr/bin/python2 butterflow
cd butterflow
source bin/activate
echo "/usr/lib/python2.7/site-packages/" > lib/python2.7/site-packages/butterflow.pth
python setup.py develop
```

## What to do afterwards
### Enabling OpenCL acceleration (recommended)
Refer to [Setting up OpenCL](Setting-up-OpenCL.md) for details on how to take
advantage of hardware acceleration through OpenCL. This isn't required but
rendering will be slow without it.

### Testing
Run `python setup.py test` to test.

### Installing outside of virtualenv
First, exit the virtual environment with `deactivate`, then run
`python setup.py install`.

To uninstall, run `pip uninstall butterflow`.
