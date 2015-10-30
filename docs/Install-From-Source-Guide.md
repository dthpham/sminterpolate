# Install From Source Guide

## Supported platforms
Butterflow has been successfully built and tested on several platforms including
OS X 10.11 (El Capitan), Windows 10, Ubuntu 15.04 (Vivid Vervet), Debian 8.2
(Jessie), and Arch Linux. Getting Butterflow to work on other Linux
distributions may be possible but expect support to be limited.

## Instructions
### OS X (El Capitan)
These instructions will show you how to compile and build a development version
of Butterflow using OS X's pre-installed Python. At minimum, you will need to
have OS X Mavericks installed.

To begin, install dependencies with [Homebrew](http://brew.sh/).

```
brew install ffmpeg
brew install homebrew/science/opencv --with-ffmpeg --with-opengl
```

Then install packages that will be used to set up a virtual environment.

```
sudo easy_install pip
pip install virtualenv
```

Finally build and install a development version of Butterflow.

```
git clone https://github.com/dthpham/butterflow.git
virtualenv -p /usr/bin/python butterflow
cd butterflow
source bin/activate
# Pick up the cv2.so module
echo "$(brew --prefix)/lib/python2.7/site-packages" > lib/python2.7/site-packages/butterflow.pth
# Alternatively, you can add Homebrew's Python site-packages to your
# PYTHONPATH. Adding an expoert to your ~/.profile will save you the trouble of
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
(Vivid Vervet). This version of Ubuntu brings back support for FFmpeg.
Installing Butterflow is more difficult on older versions of Ubuntu because
FFmpeg is not readily available.

Begin by installing tools, development files, and a generic OpenCL library and
headers.

```
sudo apt-get install git virtualenv python-dev ocl-icd-opencl-dev libopencv-dev python-opencv ffmpeg
```

Now compile and install Butterflow.

```
git clone https://github.com/dthpham/butterflow.git
virtualenv -p /usr/bin/python2 butterflow
cd butterflow
source bin/activate
# dist-packages is a Debian-specific convention that is present in
# derivative distros
echo "/usr/lib/python2.7/dist-packages" > lib/python2.7/site-packages/butterflow.pth
python setup.py develop
```

### Debian (Jessie)
Begin by installing FFmpeg. These instructions are adapted from this [guide](https://www.assetbank.co.uk/support/documentation/install/ffmpeg-debian-squeeze/ffmpeg-debian-jessie/).
This [gist](https://gist.github.com/holms/7009218) is a tad more comprehensive
and will show you how to make a package that you can manage with `apt-get`.

First add the multimedia source to the bottom of `/etc/apt/sources.list`.

```
deb http://www.deb-multimedia.org jessie main non-free
deb-src http://www.deb-multimedia.org jessie main non-free
```

Update your package list and keyring.

```
sudo apt-get update
sudo apt-get install deb-multimedia-keyring
sudo apt-get update
```

Download dependencies.

```
sudo apt-get install build-essential libmp3lame-dev libvorbis-dev libtheora-dev libspeex-dev yasm pkg-config libfaac-dev libopenjpeg-dev libx264-dev
```

Download the latest package of FFmpeg from their [releases](http://ffmpeg.org/releases/)
page. Extract it to a folder, `cd` into it and run:

```
# This is going to install it into /usr/local
./configure --enable-gpl --enable-postproc --enable-swscale --enable-avfilter --enable-libmp3lame --enable-libvorbis --enable-libtheora --enable-libx264 --enable-libspeex --enable-shared --enable-pthreads --enable-libopenjpeg --enable-libfaac --enable-nonfree
make
sudo make install
```

Install all other dependencies.

```
sudo apt-get install build-essential git python-virtualenv python-dev python-setuptools libopencv-dev python-opencv ocl-icd-opencl-dev libgl1-mesa-dev x264
```

Finally, build and install Butterflow.

```
git clone https://github.com/dthpham/butterflow.git
virtualenv -p /usr/bin/python2 butterflow
cd butterflow
source bin/activate
echo "/usr/lib/python2.7/dist-packages" > lib/python2.7/site-packages/butterflow.pth
python setup.py develop
```

### Arch Linux
Install dependencies:

```
sudo pacman -S git python2-setuptools python2-virtualenv python2-numpy ocl-icd opencl-headers opencv ffmpeg
```

Now build and install Butterflow.

```
git clone https://github.com/dthpham/butterflow.git
virtualenv2 -p /usr/bin/python2 butterflow
cd butterflow
source bin/activate
echo "/usr/lib/python2.7/site-packages/" > lib/python2.7/site-packages/butterflow.pth
python setup.py develop
```

## What to do afterwards
### Enabling OpenCL acceleration
Refer to [Setting up OpenCL](Setting-up-OpenCL.md) for details on how to take
advantage of hardware acceleration through OpenCL. This step isn't mandatory but
it's one you are expected to take.

### Testing
You can run a suite of tests against Butterflow to ensure everything is set up
properly with `python setup.py test` or just `nosetests` or `nosetests2` if you
have [nose](https://nose.readthedocs.org/en/latest/) installed. Tests will fail
if you don't have OpenCL set up.

### Installing outside of a virtualenv
To install Butterflow outside of a virtual environment, first exit your
virtualenv if you are in one with `deactivate` and then run
`python setup.py install`. To uninstall run `pip uninstall butterflow`.
