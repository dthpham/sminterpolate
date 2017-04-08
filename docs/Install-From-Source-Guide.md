# Install From Source Guide
**Requirements:** A 64-bit system.

## Known working platforms
* macOS 10.12 (Mavericks and newer)
* Windows 10
* Arch Linux
* Ubuntu 15.04 (Vivid Vervet)
* Debian 8.2 (Jessie)

**Note:** Getting BF to work on other Linux distributions may be possible, but expect any support to be limited.

## Instructions
**Windows users:** Refer to the [Install on Windows Guide](Install-On-Windows-Guide.md#install-from-source).

### Compile and install BF:
#### Install dependencies:
##### macOS:
 1. Install with [Homebrew](http://brew.sh/), `brew install ffmpeg` and `brew install homebrew/science/opencv --with-ffmpeg`.
 2. Install packages that will be used to set up a virtual environment with `sudo easy_install pip`, then `pip install virtualenv`.

##### Arch Linux:
 1. Install with `sudo pacman -S git python2-setuptools python2-virtualenv python2-numpy ocl-icd opencl-headers ffmpeg`.
 2. Install the [opencv2](https://aur.archlinux.org/packages/opencv2/) package from the AUR.
      * **Tip:** Remove all packages that depend on opencv, like opencv-samples, before installing opencv2. This will save you the trouble of re-compiling the package, which takes a long time, if the install fails.

##### Ubuntu:
Install with `sudo apt-get install git virtualenv python-dev ocl-icd-opencl-dev libopencv-dev python-opencv ffmpeg`.

##### Debian:
 1. Add `deb http://www.deb-multimedia.org jessie main non-free` and `deb-src http://www.deb-multimedia.org jessie main non-free` to the bottom of `/etc/apt/sources.list`.
 2. Update your package list with `sudo apt-get update`.
 3. Update your keyring with `sudo apt-get install deb-multimedia-keyring`.
 4. Re-update your package list.
 5. Download dependencies with `sudo apt-get install build-essential libmp3lame-dev libvorbis-dev libtheora-dev libspeex-dev yasm pkg-config libfaac-dev libopenjpeg-dev libx264-dev`.
 6. Download [FFmpeg](http://ffmpeg.org/releases/) and extract it.
 7. Go into the folder.
 8. Configure it with `./configure --enable-gpl --enable-postproc --enable-swscale --enable-avfilter --enable-libmp3lame --enable-libvorbis --enable-libtheora --enable-libx264 --enable-libspeex --enable-shared --enable-pthreads --enable-libopenjpeg --enable-libfaac --enable-nonfree`.
 9. Build it with `make`.
 10. Install it with `sudo make install`.
      * This will install FFmpeg into /usr/local.
 11. Install other dependencies with `sudo apt-get install build-essential git python-virtualenv python-dev python-setuptools libopencv-dev python-opencv ocl-icd-opencl-dev libgl1-mesa-dev x264`.

### Compile:
1. Clone the project repo with `git clone https://github.com/dthpham/butterflow.git`.
2. Create a virtual environment:
    * **macOS (using the system's python):** `virtualenv -p /usr/bin/python butterflow`.
    * **Linux:** `virtualenv -p /usr/bin/python2 butterflow`.
3. Change into the project directory and activate the virtualenv with `source bin/activate`.
4. Add a path configuration file:
    * **macOS:** Pick up the cv2.so module with `echo "$(brew --prefix)/lib/python2.7/site-packages" > lib/python2.7/site-packages/butterflow.pth`.
        * **Important:** You may have to manually add /usr/local/lib and /usr/local/include to your search paths to pick up some headers and libraries. If you're using Xcode's clang, it will only search macOS SDK paths. You should install the Xcode Command Line tools with `xcode-select --install` to get a version that searches /usr/local by default.
        * **Alternative:** You can add Homebrew's Python site-packages to your PYTHONPATH with `export PYTHONPATH=$PYTHONPATH:$(brew --prefix)/lib/python2.7/site-packages`. Adding an export to your ~/.profile will save you the trouble of having to set this every time you activate the virtual environment.
    * **Arch Linux:** `echo "/usr/lib/python2.7/site-packages/" > lib/python2.7/site-packages/butterflow.pth`.
    * **Ubuntu or Debian:** `echo "/usr/lib/python2.7/dist-packages" > lib/python2.7/site-packages/butterflow.pth`.
        * **Side note:** dist-packages is a Debian-specific convention that is present in all derivative distros (Ubuntu, Mint, etc.).

### Install:
If you intend to edit the source code:
 1. Create a development version with `python setup.py develop`.
     * **Tip:** Uninstall with `python setup.py develop -u`.
     * The development version will let you edit the source code and see the changes directly without having to reinstall every time.
     * You must be inside a virtualenv to use BF if you used one (activate with `source bin/activate`).

Or if you're using the package without making changes:
 1. Exit any virtualenv virtual environment you are in with `deactivate`.
 2. Install with `python setup.py install`.
      * **Tip:** Uninstall with `pip2 uninstall butterflow`.

## Tricks
### Is FFmpeg missing flags?
To check if your version of FFmpeg was configured with all required flags you can run this snippet:
1 means not available, 0 available
```bash
#!/bin/bash
flags_available="$(ffmpeg 2>&1)";
flags_required="--enable-gpl --enable-postproc --enable-swscale --enable-avfilter --enable-libmp3lame --enable-libvorbis --enable-libtheora --enable-libx264 --enable-libspeex --enable-shared --enable-pthreads --enable-libopenjpeg --enable-libfaac --enable-nonfree";
for flag in ${flags_required}; do
     echo "${flags_available}" | grep -sq -- "${flag}"; printf -- "$?\t${flag}\n";
  done
```

## When finished
* Check if your OpenCL device is detected with `butterflow -d`.
   * If it isn't, refer to [Setting up OpenCL](Setting-Up-OpenCL.md) for instructions on how to get it working. This step isn't required, but rendering will be extremely slow without it.
* **Optional:** While in the project directory, you can run a suite of tests against butterflow with `python setup.py test`.
   * Tests will fail if OpenCL isn't set up.
* See: [Example Usage](https://github.com/dthpham/butterflow/blob/master/docs/Example-Usage.md).
