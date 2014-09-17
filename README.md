#Butterflow

*Butterflow* is a stand alone, easy to use command line tool that lets you
create fluid slow motion and smooth motion videos by increasing frame rates
through a process known as motion interpolation.

###How does it work?

It works by generating intermediate frames between existing frames. For example,
given two existing frames `A` and `B`, this program can generate a frames `C.1`,
`C.2`...`C.n` that are positioned between the two. This process, called
[motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation),
increases frame rates and can give the perception of smoother motion and more
fluid animation, an effect most people know as the *"soap opera effect"*. It by
this process that allows *butterflow* takes advantage of the increase in frame
rates to create high fps videos and slow motion videos with less judder.

##Installation

###With pip:

```$ pip install butterflow```

###From source:

Clone this repository or download a source package
[here](https://github.com/dthpham/butterflow/tarball/0.1).

Run `$ python setup.py install` to install.

Do `$ python setup.py test` to run tests.

##Dependencies and Requirements

These need to be installed before you can install *butterflow*:

* `git`
* `ffmpeg` with any codecs that you will need
* `opencv-2.4.9` built with `BUILD_opencv_python=YES`, `WITH_OPENCL=YES`,
and `WITH_FFMPEG=YES`
* `libcl` or equivalent library that provides access to the OpenCL API
* A vendor-specific implementation of OpenCL sunch as `opencl-nvidia` or
`intel-opencl-runtime`

For more information on how to satisfy the OpenCL requirements, please read this
Wiki page [here](https://wiki.archlinux.org/index.php/Opencl).

##Quickstart

For more help and full list of options run ```$ butterflow -h```.

#####Smoothing out the motion of a video by increasing the frame rate:

```
$ butterflow <video> --r <playback-rate>
```

#####Slow-mo an entire clip with fps:

```
$ butterflow <video> -r <playback-rate> -t full,fps=<fps>
```

#####Slow-mo an entire clip to a new duration:

```
$ butterflow <video> -r <playback-rate> -t full,dur=<duration>
```

#####Slow-mo with regions:

```
$ butterflow <video> -r <rate> -t \
      a=<time-start>,b=<time-end>,dur=<secs>;\
      a=<time-start>,b=<time-end>,dur=<secs>;\
      a=<time-start>,b=<time-end>,fps=<fps>
```


##Example Walkthrough

```
$ butterflow <video> -r 23.976 -t \
      a=00:00:10,b=00:00:11,dur=10;\
      a=00:01:22,b=00:01:25,dur=20;\
      a=00:01:25,b=00:02:00,fps=400
```

This will create a new video with three regions that will be slowed down.
The first region is only 1s long, `a=00:00:10,b=00:00:11,dur=10` will be
stretched out to 10s long. The next region `a=00:01:22,b=00:01:25,dur=20` which
is originally only 3s long will turn into 20s long. The last region
`a=00:01:25,b=00:02:00,fps=400` will have 400 frames per second and since it's
5s long there will be 2,000 frames in that region being played back at 24fps.


##Specifying rate and FPS

You can specify rates with fractions so `-r 23.976`, `-r 24000/1001`, and
`-r 24/1.001` are equivalent.

##Specifying time

The format of time is in `hh:mm:ss.msec`. Leading zeros are required so this
will work `01:30:15.008` but this *will not* `1:30:15.009`. This will work
`00:08:23.6` but this *will not* `8:23.6`. You can leave off trailing zeros in
the millisecond portion so `00:00:26.5` and `00:00:26` would both work.

##Notes

Please take a look at the *slowmoVideo* program, which doesn't require OpenCL
and  comes with a GUI interface and has some more advanced features such as
variable slow down factors and motion blur. If you want to watch movies at a
higher rate in real-time, check out the *SmoothVideo Project* for more
information.
