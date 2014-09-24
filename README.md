#Butterflow

*Butterflow* is an easy to use command line tool that lets you create fluid slow
motion and smooth motion videos.

#####How does it work?

It works by generating intermediate frames between existing frames. For example,
given two existing frames `A` and `B`, this program can generate frames `C.1`,
`C.2`...`C.n` that are positioned between the two. This process, called
[motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation),
increases frame rates and can give the perception of smoother motion and more
fluid animation, an effect most people know as the "soap opera effect". This
process allows *Butterflow* to take advantage of the increase in frame rate to
generate high fps videos that are needed to make slow motion videos with minimal
judder.

#####See it for yourself:

* [Video (12fps)](https://dl.dropboxusercontent.com/u/103239050/gel12-scaled.mp4)
* [Video frame rate increased with butterflow (96fps)](https://dl.dropboxusercontent.com/u/103239050/gel96-scaled.mp4)
* [Video at 30fps slowed down with butterflow (210fps)](https://dl.dropboxusercontent.com/u/103239050/side.mp4)

##Installation

#####With pip:

```$ pip install butterflow```

#####From source:

Clone this repository or download a source package
[here](https://github.com/dthpham/butterflow/tarball/0.1.2).

`$ python setup.py install` to install.

`$ python setup.py test` to run tests.

##Dependencies

* [`git`](http://git-scm.com)
* [`numpy`](http://www.numpy.org/)
* [`ffmpeg`](https://github.com/FFmpeg/FFmpeg), with any codecs you may need
* [`opencv-2.4.9`](http://opencv.org/), built with `BUILD_opencv_python=ON`,
`WITH_OPENCL=ON`, and `WITH_FFMPEG=ON`

Plus at least one vendor-specific implementation of OpenCL that matches your
hardware:

* [`opencl-nvidia`](https://developer.nvidia.com/opencl)
* [`intel-opencl-runtime`](https://software.intel.com/en-us/intel-opencl)
* [`amdapp-sdk`](http://developer.amd.com/tools-and-sdks/opencl-zone/)
* [`opencl-catalyst`]()
* [`opencl-mesa`](http://www.x.org/wiki/GalliumStatus/)

For more information on how to satisfy the OpenCL requirements, please read
[this page](https://wiki.archlinux.org/index.php/Opencl).

##Usage

For a full list of options run ```$ butterflow -h```.

#####Increase a video's frame rate to `120fps`:

```
$ butterflow <video> --playback-rate 120
```

#####Slow-mo a clip with a target frame rate of `400fps`:

```
$ butterflow <video> --playback-rate 59.94 -t full,fps=400
```

#####Slow-mo a clip to `0.25x` quarter speed:

```
$ butterflow <video> --playback-rate 59.94 -t full,factor=0.25
```

#####Slow-mo a clip to be `30s` long:

```
$ butterflow <video> --playback-rate 59.94 -t full,duration=30
```

#####Slow-mo a region:

```
$ butterflow <video> --playback-rate 24 -t \
a=00:00:05.0,b=00:00:06.0,factor=0.5
```

#####Slow-mo multiple regions:

```
$ butterflow <video> --playback-rate 24 -t \
"a=00:00:05.0,b=00:00:06.0,fps=200,\
a=00:00:16.0,b=00:00:18.0,fps=400,\
a=00:00:18.0,b=00:00:20.0,factor=0.5"
```
