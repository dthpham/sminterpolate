# Setting Up OpenCL
**Tip:** Most of this guide is adapted from other sources and should not be considered definitive or up to date. For additional information on how to satisfy the OpenCL requirement, please read [How to set up OpenCL in Linux](http://wiki.tiker.net/OpenCLHowTo).

## Instructions
### OS X (Mavericks and newer):
Apple provides support for OpenCL by default on all Macs so you will be able to take advantage of hardware acceleration without having to set anything up.

If you encounter an error that you suspect is related to OpenCL, it may be because you don't have a compatible graphics device. Double check to see if your Mac is listed on Apple's [Mac computers that use OpenCL and OpenGL graphics](https://support.apple.com/en-us/HT202823) support page and verify that it meets the minimum requirements outlined in the [Device compatibility](#device-compatibility) section.

### Ubuntu (Vivid Vervet):
#### Nvidia:
1. Install required packages with `sudo apt-get install nvidia-346 nvidia-346-uvm nvidia-modprobe nvidia-opencl-dev nvidia-opencl-icd-346`.
2. Manually  set Ubuntu to use the proprietary Nvidia 346 drivers via the "Additional Drivers" dialog.
3. Reboot.

#### Intel or AMD:
1. Download the driver/library package from the [AMD website](http://support.amd.com/en-us/download/desktop?os=Linux+x86).
 * The archive file will be named `amd-catalyst-<VERSION>-linux-installer-<BUILD_VERSION>-x86.x86_64.zip`.
2. Extract the package to a folder.
3. Launch a terminal and change into the directory.
4. Extract the driver files with `bash AMD-Catalyst-<VERSION>-Linux-installer-*.run --extract .`.
5. Set the target directory environment variable with `TGT_DIR="/opt/amd-opencl-icd-<VERSION>/lib"`.
6. Make the folder with `mkdir -p "$TGT_DIR"`.
7. Copy the library files over with `cp ./arch/x86_64/usr/lib64/* "$TGT_DIR"`.
 * The "cp: omitting directory ... fglrx" warning is safe to ignore.
8. Make a folder to store the driver with `mkdir -p /etc/OpenCL/vendors`.
9. Create the driver file with `touch /etc/OpenCL/vendors/amd.icd`.
10. Add the location of the library file to it with `echo "$TGT_DIR/libamdocl64.so" > /etc/OpenCL/vendors/amd.icd`.
 * Try adding the full path of libamocl64.so to amd.icd with a text editor if this command doesn't work.

**Optional:** Add the location of the OpenCL library to LD_LIBRARY_PATH If you want to use AMD's OpenCL library at runtime with `export LD_LIBRARY_PATH=/opt/amd-opencl-icd-<VERSION>/lib:$LD_LIBRARY_PATH`.

### Debian (Jessie):
1. Add `deb <repos> jessie main non-free` and `deb-src <repos> jessie main non-free` components to `/etc/apt/sources.list`.
2. Refresh your package list with `sudo apt-get update`.
3. Install a client driver for your hardware device:
 * If NVIDIA: `nvidia-opencl-icd`.
 * Intel or AMD: `amd-opencl-icd` (supports both).

### Arch Linux:
**Recommended:** Refer to the Arch [GPGPU wiki page](https://wiki.archlinux.org/index.php/GPGPU).

Typically, you just need to install at least one vendor-specific OpenCL implementation that supports your hardware under Arch. For NVIDIA install [opencl-nvidia](https://www.archlinux.org/packages/extra/x86_64/opencl-nvidia/) or [intel-opencl-runtime](https://aur.archlinux.org/packages/intel-opencl-runtime/) if you're using an Intel device.

# Device compatibility
**Important:** You need to have a `FULL_PROFILE` device that supports OpenCL 1.2 or higher to do hardware accelerated rendering with Butterflow. You can print your device info with `butterflow -d` or by using a more comprehensive tool like [clinfo](https://github.com/Oblomov/clinfo).

If there are no compatible devices available, Butterflow will automatically use software-rendering (slow). To force this, use the `-sw` flag.
