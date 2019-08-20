## About
BF is a video manipulation tool that can:

1. Make **motion interpolated videos** (increase a video's frame rate by rendering intermediate frames based on motion using a combination of pixel-warping and blending).
2. Make **smooth motion videos** (do simple blending between frames).
3. Leverage interpolated frames to make **fluid slow motion videos**.

## Demonstration
BF works by rendering intermediate frames between existing frames using a process called [motion interpolation](https://en.wikipedia.org/wiki/Motion_interpolation). Given two existing frames, `A` and `B`, this program can generate frames `C.1`, `C.2`...`C.n` positioned between the two. In contrast to other tools that can only *blend or dupe* frames, this program *warps pixels based on motion* to generate new ones.

The addition of interpolated frames gives the perception of more fluid animation commonly found in high frame rate videos, an effect most people know as the "soap opera effect".

Besides creating motion interpolated videos BF can leverage interpolated frames to make fluid slow motion videos:

![](docs/1.gif)

In these examples BF slowed a `1sec` video down by `10x`. An additional `270` frames were interpolated from `30` original source frames giving the video a smooth feel during playback. The same video was slowed down using FFmpeg alone, but because it dupes frames and can't interpolate new ones the video has a noticeable stutter (shown on the right-hand side).

![](docs/2.gif)

## Install
**Requirements:** A 64-bit system with a compatible graphics device.

* **Windows 10 (Portable):** Download the [latest releases](https://github.com/dthpham/butterflow/releases/latest).
  * **Preview:** butterflow-0.2.4a4-win64.zip
    * Sha256: 856ad05bafaeb9d084d6b1cbf0bdec17defeef438e610f6a3a772087acea301b
  * **Stable:** butterflow-0.2.3-win64.zip
    * Sha256: a77fbbdbdd0d85bb31feac30e53378a36ff4fb2a8a98ba15a6fa06def4b36ad1
* **macOS and Linux:** See the [Install From Source Guide](docs/Install-From-Source-Guide.md) for instructions.

## Setup
BF requires no setup to use but it's too slow out of the box to do any serious work. To take advantage of hardware accelerated methods that will make rendering significantly faster you must set up a functional OpenCL environment on your machine

You can check if your device is detected with `butterflow -d`. BF will force you to use CPU rendering if there are no compatible devices available.

### Windows

To do this on Windows you will only need to have the latest version of your graphics driver installed. If BF fails to detect your device for fails to execute, you can try specifying the location of your hardware's OpenCL client driver. Find your drivers by doing a search in your windows folder for nvopencl64.dll and nvopencl32.dll if you have NVIDA, Intel: IntelOpenCL64.dll and IntelOpenCL32.dll; AMD amdocl64.dll and amdocl32.dll. You may need to reference to the 32-bit key, even if you're on a 64-bit system.  In regedit, add the 64 bit driver in the registry at `HKEY_LOCAL_MACHINE\SOFTWARE\Khronos\OpenCL\Vendors` by adding a key with the full path to the DLL as a `REG_DWORD` type with a data value of 0. Do the same for the 32-bit driver at HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Khronos\OpenCL\Vendors

Example for NVIDIA (Use the full path to your driver you found after a search).
```
[HKEY_LOCAL_MACHINE\SOFTWARE\Khronos\OpenCL\Vendors]
"C:\Windows\System32\nvopencl64.dll"=dword:00000000  

[HKEY_LOCAL_MACHINE\SOFTWARE\Wow6432Node\Khronos\OpenCL\Vendors]
"C:\Windows\System32\nvopencl32.dll"=dword:00000000
```

### Mac 

No setup on macOS is necessary because Apple provides OpenCL support by default on all newer Macs. If you're on Linux, please seek other sources on how to satisfy the OpenCL requirement.



## Usage
Run `butterflow -h` for a full list of options. See: [Example Usage](docs/Example-Usage.md) for typical commands.

## License
[MIT License](LICENSE)
