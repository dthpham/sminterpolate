#Butterflow

*Butterflow* is a easy to use command line tool that lets you create fluid slow
motion and smooth motion videos by increasing frame rates through a process
known as motion interpolation.

####How does it work?

It works by generating intermediate frames between existing frames. For example,
given two existing frames `A` and `B`, this program can generate frames `C.1`,
`C.2`...`C.n` that are positioned between the two. This process, called
[motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation),
increases frame rates and can give the perception of smoother motion and more
fluid animation, an effect most people know as the "soap opera effect". It is
through this process that allows *butterflow* to take advantage of the increase
in frame rates to generate high fps videos that are needed to make slow motion
videos with minimal judder.

####See it for yourself

* [Video (12fps)](https://dl.dropboxusercontent.com/u/103239050/gel12-scaled.mp4)
* [Video frame rate increased with butterflow (96fps)](https://dl.dropboxusercontent.com/u/103239050/gel96-scaled.mp4)
* [Video at 30fps slowed down with butterflow (210fps)](https://www.dropbox.com/s/6gs3h030l07b5l2/side.mp4?dl=0)


##Installation

#####With pip:

```$ pip install butterflow```

#####From source:

Clone this repository or download a source package
[here](https://github.com/dthpham/butterflow/tarball/0.1.2).

`$ python setup.py install` to install.

`$ python setup.py test` to run tests.

##Dependencies:

These need to be installed before before anything else.

* [`numpy`](http://www.numpy.org/)
* [`ffmpeg`](https://github.com/FFmpeg/FFmpeg), with any codecs you may need
* [`opencv-2.4.9`](http://opencv.org/), built with `BUILD_opencv_python=ON`,
`WITH_OPENCL=ON`, and `WITH_FFMPEG=ON`
* [`libcl`](http://www.libcl.org/), or an equivalent library that provides
access to the OpenCL API

Plus at least one vendor-specific implementation of OpenCL that matches your hardware:

* [`opencl-nvidia`](https://developer.nvidia.com/opencl)
* [`intel-opencl-runtime`](https://software.intel.com/en-us/intel-opencl)
* [`amdapp-sdk`](http://developer.amd.com/tools-and-sdks/opencl-zone/)
* [`opencl-mesa`](http://www.x.org/wiki/GalliumStatus/)

For more information on how to satisfy the OpenCL requirements, please read
[this page](https://wiki.archlinux.org/index.php/Opencl).

##Usage

For a full list of options run ```$ butterflow -h```.

Now suppose you had a `24fps` video on your hands that was `10s` long...

To smooth out the motion of the video you can increase its frame rate to `96fps`:

```
$ butterflow <video> --playback-rate 96
```

To slow-mo the entire clip with a target frame rate of `400fps`:

```
$ butterflow <video> --playback-rate 59.97 -t full,fps=400
```

To slow-mo the clip to be `15s` long:

```
$ butterflow <video> --playback-rate 59.97 -t full,dur=15
```

To slow-mo to `0.25x` quarter speed:

```
$ butterflow <video> --playback-rate 59.97 -t full,factor=0.25
```

Now suppose you want to slow-mo particular parts, you can do this:

```
$ butterflow <video> --playback-rate 24000/1001 --timing-regions \
a=00:00:10,b=00:00:11,factor=0.5
```

You can also chain together multiple regions with a `,` like so:

```
a=00:00:10.0,b=00:00:11.0,factor=0.5,\
a=00:00:15.0,b=00:00:28.0,fps=400
```
