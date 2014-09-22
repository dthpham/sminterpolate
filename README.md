#Butterflow

*Butterflow* is a easy to use command line tool that lets you create fluid slow
motion and smooth motion videos by increasing frame rates through a process
known as motion interpolation.

###How does it work?

It works by generating intermediate frames between existing frames. For example,
given two existing frames `A` and `B`, this program can generate frames `C.1`,
`C.2`...`C.n` that are positioned between the two. This process, called
[motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation),
increases frame rates and can give the perception of smoother motion and more
fluid animation, an effect most people know as the "soap opera effect". It is
through this process that allows *butterflow* takes advantage of the increase
in frame rates to generate high fps videos that are needed to make slow motion
videos with minimal judder.

###See for yourself:

* [Video (12fps)](https://dl.dropboxusercontent.com/u/103239050/gel12-scaled.mp4)
* [Video frame rate increased with butterflow (96fps)](https://dl.dropboxusercontent.com/u/103239050/gel96-scaled.mp4)
* [Video at 30fps slowed down with butterflow (210fps)](https://www.dropbox.com/s/6gs3h030l07b5l2/side.mp4?dl=0)

##Installation

###With pip:

```$ pip install butterflow```

###From source:

Clone this repository or download a source package
[here](https://github.com/dthpham/butterflow/tarball/0.1.2).

`$ python setup.py install` to install.

`$ python setup.py test` to run tests.

##Dependencies and Requirements

These need to be installed before you can install *butterflow*:

* `git`
* `ffmpeg` with any codecs that you may need
* `opencv-2.4.9` built with `BUILD_opencv_python=ON`, `WITH_OPENCL=ON`,
and `WITH_FFMPEG=ON`
* `libcl` or an equivalent library that provides access to the OpenCL API
* A vendor-specific implementation of OpenCL such as `opencl-nvidia` or
`intel-opencl-runtime`

For more information on how to satisfy the OpenCL requirements, please read this
Wiki page [here](https://wiki.archlinux.org/index.php/Opencl).

##Quickstart

For more help and full list of options run ```$ butterflow -h```.

#####Smoothing out the motion of a video by increasing its frame rate:

```
$ butterflow <video> --r <playback-rate>
```

#####Slow-mo an entire clip to fps:

```
$ butterflow <video> -r <playback-rate> -t full,fps=<fps>
```

#####Slow-mo an entire clip to a new duration:

```
$ butterflow <video> -r <playback-rate> -t full,dur=<duration>
```

#####Slow-mo an entire clip with speed factor:

```
$ butterflow <video> -r <playback-rate> -t full,factor=<factor>
```

#####Slow-mo regions:

```
$ butterflow <video> -r <rate> -t \
      "a=<time-start>,b=<time-end>,dur=<secs>;\
       a=<time-start>,b=<time-end>,dur=<secs>;\
       a=<time-start>,b=<time-end>,fps=<fps>;\
       a=<time-start>,b=<time-end>,factor=<factor>"
```


##Example Walkthrough

```
$ butterflow <video> -r 23.976 -t \
      "a=00:00:10,b=00:00:11,dur=10;\
       a=00:01:22,b=00:01:25,dur=20;\
       a=00:01:25,b=00:02:00,fps=400;\
       a=00:02:00,b=00:02:05,factor=0.5"
```

This will create a new video with four regions that will be slowed down. The
first region `a=00:00:10,b=00:00:11,dur=10` is 1s long and will be stretched out
to 10s long. The next region `a=00:01:22,b=00:01:25,dur=20` will turn into 20s
long. The third region `a=00:01:25,b=00:02:00,fps=400` will have 400fps and
since it's 5s long there will be 2,000 frames in that region being played back
at 24fps. Finally, the last region `a=00:02:00,b=00:02:05,factor=0.5` will be
rendered at half speed.


##Specifying rate and FPS

You can specify rates with fractions so `-r 23.976`, `-r 24000/1001`, and
`-r 24/1.001` are equivalent.

##Specifying time

The format of time is in `hh:mm:ss.msec`. Leading zeros are required so this
will work `01:30:15.008` but this *will not* `1:30:15.009`. This will work
`00:08:23.6` but this *will not* `8:23.6`. You can leave off trailing zeros in
the millisecond portion so `00:00:26.5` and `00:00:26` would both work.

##Notes

Please contact me by [email](mailto:dthpham@gmail.com) if you need help
installing or have any other questions.
