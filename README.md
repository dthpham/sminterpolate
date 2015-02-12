#Butterflow

*Butterflow* is an easy to use command line tool that lets you create fluid slow
motion and smooth motion videos.

####How does it work?

It works by rendering intermediate frames between existing frames. For example,
given two existing frames `A` and `B`, this program can generate frames `C.1`,
`C.2`...`C.n` that are positioned between the two. This process, called
[motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation),
increases frame rates and can give the perception of smoother motion and more
fluid animation, an effect most people know as the "soap opera effect".
Butterflow takes advantage of this increase in frame rates to make high speed
and slow motion videos with minimal judder.

##Demo

* [Slow motion with multiple sub regions](http://srv.dthpham.me/video/jet.mp4).
Butterflow rendered an additional 840 unique intermediate frames from 166 source
frames for the slow-mo video on the left.

##Installation

####OS X:

Clone this repo, then with [`homebrew`]():

```
brew tap homebrew/science
brew install ffmpeg --with-libvorbis --with-libass
brew install opencv --with-ffmpeg
cd butterflow
python setup.py install
```

####Arch Linux:

A package is available in the AUR under [butterflow](https://aur.archlinux.org/packages/butterflow/).

####Debian 8.x:

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
gpg --keyserver pgp.mit.edu --recv-keys 458C370A
gpg -a --export 458C370A | sudo apt-key add -
```
Finally install it like any other software package:

```
apt-get update
apt-get install butterflow
```

####From Source:

Satisfy all the
[dependencies](https://github.com/dthpham/butterflow/wiki/Dependencies)
and clone this repository, then:

```
cd butterflow
python2 setup.py install
```

##Setup

After installing the package, you still need to install ***at least one***
vendor-specific implementation of OpenCL that supports your hardware. If you're
on OS X, no setup is necessary because support is provided by default.

####Arch Linux:

* [`opencl-nvidia`]()
* [`opencl-nvidia-304xx`]()
* [`opencl-nvidia-340xx`]()
* [`amdapp-sdk`]()
* [`opencl-mesa`]()
* [`intel-opencl-runtime`]()
* [`beignet-git`]()

####Debian 8.x:

* [`nvidia-opencl-icd`]()
* [`amd-opencl-icd`]()
* [`amd-opencl-icd-legacy`]()
* [`mesa-opencl-icd`]()
* [`beignet`]()
* [`pocl-opencl-icd`]()

When finished, you can run `butterflow -d` to print a list of all detected
devices.

For more information on how to satisfy the OpenCL requirements, please read
[this page](http://wiki.tiker.net/OpenCLHowTo). If you're on Arch Linux, see
[this page](https://wiki.archlinux.org/index.php/Opencl).

##Usage

For a full list of options run `butterflow -h`.

####Increase a video's frame rate to `120fps`:

```
butterflow --playback-rate 120 <video>
```

####Slow-mo a clip with a target frame rate of `400fps`:

```
butterflow -r 59.94 -s full,fps=400 <video>
```

####Slow-mo a clip to `0.25x` quarter speed:

```
butterflow -r 59.94 -s full,factor=0.25 <video>
```

####Slow-mo a clip to be `30s` long:

```
butterflow -r 59.94 -s full,duration=30 <video>
```

####Slow-mo a region:

```
butterflow -r 24 -s "a=0:00:05.0,b=0:00:06.0,factor=0.5" <video>
```

####Slow-mo multiple regions:

```
butterflow -r 24 -s "a=4.3,b=5,factor=0.25;a=6,b=8.5,duration=20" <video>
```

##Filters

####Decimate:

Videos may have some judder if your source has duplicate frames. To compensate
for this, use the `--decimate` option:

```
butterflow -r 60 --decimate <video>
```

####Video Scale:

To scale the output video to `75%` of its original size:

```
butterflow -r 24 --video-scale 0.75 <video>
```

##Quality

Butterflow uses the Farneback algorithm to compute dense optical flows for frame
interpolation. You can pass in different values to the function to
fine-tune the quality (robustness of image) of the resulting videos. Run
`butterflow -h` for a list of advanced options and their default values.
