#Butterflow

*Butterflow* is an easy to use command line tool that lets you create fluid slow
motion and smooth motion videos.

It works by rendering intermediate frames between existing frames. For example,
given two existing frames `A` and `B`, this program can generate frames `C.1`,
`C.2`...`C.n` that are positioned between the two. This process, called
[motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation),
increases frame rates and can give the perception of smoother motion and more
fluid animation, an effect most people know as the "soap opera effect".
Butterflow takes advantage of this increase in frame rates to make high speed
and slow motion videos with minimal judder.

A demo:

* [Slow-mo with multiple sub regions](http://srv.dthpham.me/video/jet.mp4)

##Installation

####OS X:

With [`homebrew`](http://brew.sh/):

```
brew tap homebrew/science
brew install --build-from-source butterflow
```

####Arch Linux:

A package is available in the AUR under
[`butterflow`](https://aur.archlinux.org/packages/butterflow/).

####Debian 8.x:

A package is available. See the [Debian Install Guide](https://github.com/dthpham/butterflow/wiki/Debian-Install-Guide) for
instructions.

####From Source:

Satisfy all the
[Dependencies](https://github.com/dthpham/butterflow/wiki/Dependencies)
and clone this repository, then:

```
cd butterflow
python2 setup.py install
```

##Setup

After installing the package, you still need to ***install at least one***
vendor-specific implementation of OpenCL that supports your hardware.  See
[Suggested OpenCL Packages](https://github.com/dthpham/butterflow/wiki/Suggested-OpenCL-Packages)
for some options. If you're on OS X, no setup is necessary because support is
provided by default.

When finished, you can run `butterflow -d` to print a list of all detected
devices.

For additional information on how to satisfy the OpenCL requirements, please
read [How to set up OpenCL in Linux](http://wiki.tiker.net/OpenCLHowTo). If
you're on Arch Linux, see
[their Wiki page](https://wiki.archlinux.org/index.php/GPGPU).

##Usage

See [Example Usage](https://github.com/dthpham/butterflow/wiki/Example-Usage)
for typical commands.

```
usage: butterflow [options] [video]

Required arguments:
  video                 Specify the input video

General arguments:
  -h, --help            Show this help message and exit
  -V, --version         Show program's version number and exit
  -d, --devices         Show detected OpenCL devices and exit
  -v, --verbose         Set to increase output verbosity
  --no-preview          Set to disable video preview
  --preview-flows       Set to preview optical flows
  --render-flows        Set to render optical flows and write them to a file
  --render-info         Set to add debugging info into the output video

Video arguments:
  -o OUTPUT_PATH, --output-path OUTPUT_PATH
                        Specify path to the output video
  -r PLAYBACK_RATE, --playback-rate PLAYBACK_RATE
                        Specify the playback rate, (default: 23.976)
  -s SUB_REGIONS, --sub-regions SUB_REGIONS
                        Specify rendering sub regions in the form:
                        "a=TIME,b=TIME,TARGET=FLOAT" where TARGET is either
                        `fps`, `duration`, `factor`. Valid TIME syntaxes are
                        [hr:m:s], [m:s], [s.xxx], or `end`. You can specify
                        multiple sub regions by separating them with a semi-
                        colon `;`. A special region format that conveniently
                        describes the entire clip is available in the form:
                        "full,TARGET=FLOAT".
  -t, --trim-regions    Set to trim subregions that are not explicitly
                        specified
  -vs VIDEO_SCALE, --video-scale VIDEO_SCALE
                        Specify the output video scale, (default: 1.0)
  -l, --lossless        Set to use lossless encoding settings
  --decimate            Set to decimate duplicate frames from the video source
  --grayscale           Set to enhance grayscale coloring

Advanced arguments:
  --fast-pyr            Set to use fast pyramids
  --pyr-scale PYR_SCALE
                        Specify pyramid scale factor, (default: 0.5)
  --levels LEVELS       Specify number of pyramid layers, (default: 3)
  --winsize WINSIZE     Specify average window size, (default: 25)
  --iters ITERS         Specify number of iterations at each pyramid level,
                        (default: 3)
  --poly-n {5,7}        Specify size of pixel neighborhood, (default: 7)
  --poly-s POLY_S       Specify standard deviation to smooth derivatives,
                        (default: 1.5)
  -ff {box,gaussian}, --flow-filter {box,gaussian}
                        Specify which filter to use for optical flow
                        estimation, (default: box)
```
