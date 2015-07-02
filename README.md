#Butterflow

*Butterflow* is an easy to use command-line tool that lets you create fluid slow
motion and motion interpolated videos.

It works by rendering intermediate frames between existing frames. For example,
given two existing frames `A` and `B`, this program can generate frames `C.1`,
`C.2`...`C.n` that are positioned between the two. This process, called
[motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation),
increases frame rates and can give the perception of smoother motion and more
fluid animation, an effect most people know as the "soap opera effect".
`butterflow` takes advantage of this increase in frame rates to make high speed
and slow motion videos with minimal judder.

![](http://srv.dthpham.me/video/blow_sm.gif)

In this example, `butterflow` slowed down a `1s` video down by `10x`. An
additional `208` frames were interpolated from `30` original source frames
giving the video a smooth feel during playback. The same video was slowed
down with `ffmpeg`, but because it dupes frames and can't interpolate new ones
the video has a noticeable stutter.

![](http://srv.dthpham.me/video/ink_sm.gif)

Here is another example where the speed of the video remains constant but its
frame rate has been increased from `30fps` to `60fps` with `butterflow`. The
video has been slowed down to make the interpolated frame (marked `Src:
N`) between original source frames more apparent. Playing it back in full speed
would produce a "soap opera effect".

See the [In Action](https://github.com/dthpham/butterflow/wiki/In-Action) page
for more demonstrations.

##Installation

###OS X:

With [`homebrew`](http://brew.sh/):

```
brew tap homebrew/science
brew install butterflow
```

###Arch Linux:

A package is available in the AUR under
[`butterflow`](https://aur.archlinux.org/packages/butterflow/).

###From Source:

Satisfy all the
[Dependencies](https://github.com/dthpham/butterflow/wiki/Dependencies)
and then:

```
git clone https://github.com/dthpham/butterflow.git
cd butterflow
python2 setup.py test
python2 setup.py install
```

##Setup

After installing the package, you still need to install at least one
vendor-specific implementation of OpenCL that supports your hardware. No setup
is necessary on OS X because support is provided by default. See
[Suggested OpenCL Packages](https://github.com/dthpham/butterflow/wiki/Suggested-OpenCL-Packages)
for some options.

When finished, you can run `butterflow -d` to print a list of all detected
devices.

For additional information on how to satisfy the OpenCL requirements, please
read [How to set up OpenCL in Linux](http://wiki.tiker.net/OpenCLHowTo). If
you're on Arch Linux, have a look at their
[GPGPU wiki page](https://wiki.archlinux.org/index.php/GPGPU).

##Usage

See [Example Usage](https://github.com/dthpham/butterflow/wiki/Example-Usage)
for typical commands.
