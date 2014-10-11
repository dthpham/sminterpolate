#Butterflow

*Butterflow* is an easy to use command line tool that lets you create fluid slow
motion and smooth motion videos.

####How does it work?

It works by generating intermediate frames between existing frames. For example,
given two existing frames `A` and `B`, this program can generate frames `C.1`,
`C.2`...`C.n` that are positioned between the two. This process, called
[motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation),
increases frame rates and can give the perception of smoother motion and more
fluid animation, an effect most people know as the "soap opera effect".
Butterflow takes advantage of this increase in frame rates to generate high fps
videos that are needed to make smooth and slow motion videos with minimal
judder.

####See it for yourself:

* [Video @30fps slowed down with butterflow (210fps)](https://dl.dropboxusercontent.com/u/103239050/INK-SIDE.mp4)
* [Video @12fps frame rate increased with butterflow (96fps)](https://dl.dropboxusercontent.com/u/103239050/GEL-SIDE.mp4)


##Installation

####Arch Linux:

A package is available in the AUR under [butterflow](https://aur.archlinux.org/packages/butterflow/).

####Debian:

Add `contrib` and `non-free` components to your `/etc/apt/sources.list`.

```
deb <repos> jessie main contrib non-free
```

Add a new repository to `/etc/apt/sources.list`.

```
deb http://repo.dthpham.me/ jessie main
```

Import key that is used to sign the release:

```
$ gpg --keyserver pgp.mit.edu --recv-keys 458C370A
$ gpg -a --export 458C370A | sudo apt-key add -
```

Finally install it like any other software package:

```
$ apt-get update
$ apt-get install butterflow
```

####From Source:

1. Satisfy all the dependencies
2. Clone this repository
3. `$ cd butterflow`
4. `$ python2 setup.py init`
5. `$ python2 setup.py install`

####With pip:

1. Satisfy all the dependencies
2. `$ pip2 install butterflow`


##Dependencies

Installing these aren't necessary if you installed using a package. See the
[Dependencies wiki page](https://github.com/dthpham/butterflow/wiki/Dependencies)
for more information.

##Setup

After installing the package, you still need to install ***at least one***
vendor-specific implementation of OpenCL that matches your hardware:

####Arch Linux:

* [`opencl-nvidia`]()
* [`opencl-nvidia-304xx`]()
* [`opencl-nvidia-340xx`]()
* [`amdapp-sdk`]()
* [`opencl-mesa`]()
* [`intel-opencl-runtime`]()
* [`beignet-git`]()

####Debian:

* [`nvidia-opencl-icd`]()
* [`amd-opencl-icd`]()
* [`amd-opencl-icd-legacy`]()
* [`mesa-opencl-icd`]()
* [`beignet`]()


For more information on how to satisfy the OpenCL requirements, please read
[this page](http://wiki.tiker.net/OpenCLHowTo). If you're on Arch Linux, see
[this page](https://wiki.archlinux.org/index.php/Opencl).


##Usage

For a full list of options run ```$ butterflow -h```.

####Increase a video's frame rate to `120fps`:

```
$ butterflow --playback-rate 120 <video>
```

####Slow-mo a clip with a target frame rate of `400fps`:

```
$ butterflow -r 59.94 -s full,fps=400 <video>
```

####Slow-mo a clip to `0.25x` quarter speed:

```
$ butterflow -r 59.94 -s full,factor=0.25 <video>
```

####Slow-mo a clip to be `30s` long:

```
$ butterflow -r 59.94 -s full,duration=30 <video>
```

####Slow-mo a region:

```
$ butterflow -r 24 -s a=0:00:05.0,b=0:00:06.0,factor=0.5 <video>
```

####Slow-mo multiple regions:

```
$ butterflow -r 24 -s \
"a=00:00:05.0,b=00:00:06.0,fps=200;\
a=00:00:16.0,b=00:00:18.0,fps=400;\
a=00:00:18.0,b=00:00:20.0,factor=0.5;\
a=00:00:20.0,b=00:00:21.0,duration=2" <video>
```

##Filters

####Decimate:

Videos may have some judder if your source has duplicate frames. To compensate
for this, use the `--decimate` option:

```
$ butterflow -r 60 --decimate <video>
```

####Video Scale:

To scale the output video to `75%` of its original size:

```
$ butterflow -r 24 --video-scale 0.75 <video>
```

##Quality

Butterflow uses the Farneback algorithm to compute dense optical flows for
frame interpolation. To fine-tune the quality (robustness of image) of the
resulting videos you can pass in different values to the function. Run
`$ butterflow -h` for a list of advanced options and their default values.
