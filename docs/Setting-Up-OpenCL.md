# Setting Up OpenCL
**Note:** This guide is adapted from other sources and is not definitive or up to date.

**Tip for Linux users:** Read [How to set up OpenCL in Linux](http://wiki.tiker.net/OpenCLHowTo) for extra information on how to satisfy the OpenCL requirement.

## Setup instructions
### macOS (Mavericks and newer):
Apple provides support for OpenCL by default on all Macs so you will be able to take advantage of hardware acceleration without having to set anything up.

If you encounter an error that you suspect is related to OpenCL, it may be because you don't have a compatible graphics device. Check if your Mac is listed on Apple's [Mac computers that use OpenCL and OpenGL graphics](https://support.apple.com/en-us/HT202823) support page and verify that it meets the requirements outlined in the [Device compatibility](#device-compatibility) section.

### Windows 10:
OpenCL should be provided by default as long as you have the latest version of your graphics driver installed.

### Ubuntu (Vivid Vervet):
#### Nvidia:
1. Install required packages with `sudo apt-get install nvidia-346 nvidia-346-uvm nvidia-modprobe nvidia-opencl-dev nvidia-opencl-icd-346`.
2. Manually  set Ubuntu to use the proprietary Nvidia 346 drivers via the "Additional Drivers" dialog.
3. Reboot.

#### Intel or AMD:
1. Download the driver/library package from the [AMD website](http://support.amd.com/en-us/download/desktop?os=Linux+x86).
   * The archive file will be named `amd-catalyst-<version>-linux-installer-<build_version>-x86.x86_64.zip`.
2. Extract the package to a folder.
3. Launch a terminal and change into the directory.
4. Extract the driver files with `bash AMD-Catalyst-<version>-Linux-installer-*.run --extract .`.
5. Set the target directory environment variable with `TGT_DIR="/opt/amd-opencl-icd-<version>/lib"`.
6. Make the folder with `mkdir -p "$TGT_DIR"`.
7. Copy the library files over with `cp ./arch/x86_64/usr/lib64/* "$TGT_DIR"`.
    * The "cp: omitting directory ... fglrx" warning is safe to ignore.
8. Make a folder to store the driver with `mkdir -p /etc/OpenCL/vendors`.
9. Create the driver file with `touch /etc/OpenCL/vendors/amd.icd`.
10. Add the location of the library file to it with `echo "$TGT_DIR/libamdocl64.so" > /etc/OpenCL/vendors/amd.icd`.
    * Try adding the full path of libamocl64.so to amd.icd with a text editor if this command doesn't work.

**Optional:** Add the location of the OpenCL library to LD_LIBRARY_PATH If you want to use AMD's OpenCL library at runtime with `export LD_LIBRARY_PATH=/opt/amd-opencl-icd-<version>/lib:$LD_LIBRARY_PATH`.

### Debian (Jessie):
1. Add `deb <repos> jessie main non-free` and `deb-src <repos> jessie main non-free` components to `/etc/apt/sources.list`.
2. Refresh your package list with `sudo apt-get update`.
3. Install a client driver for your hardware device:
   * If you're using an NVIDIA device: nvidia-opencl-icd.
   * If you're using Intel or AMD: amd-opencl-icd (it supports both).

### Arch Linux:
Typically, you just need to install at least one vendor-specific OpenCL implementation that supports your hardware. For NVIDIA install [opencl-nvidia](https://www.archlinux.org/packages/extra/x86_64/opencl-nvidia/), or [intel-opencl-runtime](https://aur.archlinux.org/packages/intel-opencl-runtime/) if you're using an Intel device.

**Tip:** Refer to the Arch [GPGPU wiki page](https://wiki.archlinux.org/index.php/GPGPU) for more information.

## Device compatibility
For hardware accelerated rendering with BF, you will need a FULL_PROFILE hardware device that supports OpenCL 1.2 or above with a:

1. Max Work Group Size greater than 256.
2. Max Work Item Size larger than 256x8x1.

You can print your device info with `butterflow -d` or by using a more comprehensive tool like [clinfo](https://github.com/Oblomov/clinfo).

BF will force you to use CPU rendering with the `-sw` option if there are no compatible devices available (**Important:** `-sw` is deprecated and will be removed in a future version).
