# Setting Up OpenCL

## General requirements
In general, setting up OpenCL only requires that you to install at least one
vendor-specific OpenCL implementation that supports your hardware.

Furthermore, at minimum, you need to have a `FULL_PROFILE` device that supports
OpenCL 1.2 or higher to do hardware accelerated rendering with Butterflow.

## Additional information
This is not a definitive guide. For additional information on how to satisfy the
OpenCL requirements, please read [How to set up OpenCL in Linux](http://wiki.tiker.net/OpenCLHowTo).
If you're on Arch Linux, have a look at their
[GPGPU wiki page](https://wiki.archlinux.org/index.php/GPGPU).

When finished, you can run `butterflow -d` to print a list of detected devices.

Butterflow will always pick the fastest rendering method possible (it will
automatically switch to OpenCL if it detects you have a compatible device) but
you can still force it to use software rendering with the `-sw` flag.

## OS X (Mavericks and newer)
Luckily, Apple provides support for OpenCL by default on all Macs so you
will be able to take advantage of hardware acceleration without having to set
anything up.

If you encounter an error that you suspect is related to OpenCL, it may be
because you don't have a compatible graphics device. Double check to see if
your Mac is listed on Apple's
[Mac computers that use OpenCL and OpenGL graphics](https://support.apple.com/en-us/HT202823)
support page and verify that it meets the minimum requirements outlined in the
[Requirements](#Requirements) section.

## Ubuntu (Vivid Vervet)
### Nvidia
Install these packages:

```
sudo apt-get install nvidia-346 nvidia-346-uvm nvidia-modprobe nvidia-opencl-dev nvidia-opencl-icd-346
```

Then manually set Ubuntu to use the proprietary Nvidia 346 drivers via the
"Additional Drivers" dialog.

Finally, reboot.

### Intel or AMD
I recommend installing and using AMD's OpenCL library and ICD if you're using
an Intel or AMD device.

To do this, download the driver from the [AMD website](http://support.amd.com/en-us/download/desktop?os=Linux+x86).
We're going to use version 15.9 as an example
(`amd-catalyst-15.9-linux-installer-15.201.1151-x86.x86_64.zip`).

Extract the driver package to a folder. Launch a terminal and `cd` into it and
run:

```
bash AMD-Catalyst-15.9-Linux-installer-*.run --extract .
```

Then using a 64-bit machine as an example (the commands are slightly different
on a 32-bit machine):

```
TGT_DIR="/opt/amd-opencl-icd-15.9/lib"
mkdir -p "$TGT_DIR"
# The "cp: omitting directory ... fglrx" warning is safe to ignore
cp ./arch/x86_64/usr/lib64/* "$TGT_DIR"
mkdir -p /etc/OpenCL/vendors
touch /etc/OpenCL/vendors/amd.icd
# Try adding the full path of libamocl64.so to amd.icd with a text editor if
# this next command doesn't work
echo "$TGT_DIR/libamdocl64.so" > /etc/OpenCL/vendors/amd.icd
```

Now test Butterflow.

```
# Add the location of the OpenCL library to LD_LIBRARY_PATH If you want to
# use AMD's OpenCL library at runtime. This isn't required:
# export LD_LIBRARY_PATH=/opt/amd-opencl-icd-15.9/lib:$LD_LIBRARY_PATH
butterflow -d
```

## Debian (Jessie)
Begin by adding `non-free` components to `/etc/apt/sources.list`.

```
deb <repos> jessie main non-free
deb-src <repos> jessie main non-free
```

Refresh your package list.

```
sudo apt-get update
```

Now install a client driver:

```
# Pick a package
# Note: the AMD package provides support for both AMD and Intel devices
# apt-get install nvidia-opencl-icd
# apt-get install amd-opencl-icd
```

## Arch Linux
Just install a client driver:

```
# Pick a package
# Note: the AMD package provides support for both AMD and Intel devices
# sudo pacman -S opencl-nvidia
# sudo yaourt -S intel-opencl-runtime
# sudo yaourt -S amdapp-sdk
```
