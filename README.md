# Butterflow
*Butterflow* is an easy to use command-line tool that lets you create fluid slow
motion and motion interpolated videos.

It works by rendering intermediate frames between existing frames. For example,
given two existing frames `A` and `B`, this program can generate frames `C.1`,
`C.2`...`C.n` that are positioned between the two. This process, called
[motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation),
increases frame rates and can give the perception of smoother motion and more
fluid animation, an effect most people know as the "soap opera effect".
Butterflow takes advantage of this increase in frame rates to make high speed
and slow motion videos with minimal judder.

![](http://srv.dthpham.me/static/ink.gif)

In this example, Butterflow slowed down a `1s` video down by `10x`. An
additional `270` frames were interpolated from `30` original source frames
giving the video a smooth feel during playback. The same video was slowed down
with FFmpeg alone, but because it dupes frames and can't interpolate new ones
the video has a noticeable stutter.

![](http://srv.dthpham.me/static/blow.gif)

Here is another example of the same concept. Interpolated frames between
source frames are marked `Int: Y`. Opening the Butterflow'd video and frame
stepping through it would make interpolated frames.

See the [In Action](https://github.com/dthpham/butterflow/blob/master/docs/In-Action.md)
page for more demonstrations.

## Installing
### OS X:
With [Homebrew](http://brew.sh/):

```
brew install homebrew/science/butterflow
```

### Arch Linux:
A package is available in the AUR under
[`butterflow`](https://aur.archlinux.org/packages/butterflow/).

### From Source:
This is the only way to get Butterflow working on Ubuntu, Debian, and Windows.

Refer to the
[Install From Source Guide](https://github.com/dthpham/butterflow/blob/master/docs/Install-From-Source-Guide.md)
for instructions.

## Setup
Butterflow requires no additional setup to use, however you're expected to set
up a functional OpenCL environment on your machine to take advantage of hardware
accelerated methods that will make rendering significantly faster.

See [Setting up OpenCL](https://github.com/dthpham/butterflow/blob/master/docs/Setting-Up-OpenCL.md)
for details on how to do this.

## Usage
Run `butterflow -h` for a full list of options and their default values.

See [Example Usage](https://github.com/dthpham/butterflow/blob/master/docs/Example-Usage.md)
for typical commands.
