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
with FFmpeg, but because it dupes frames and can't interpolate new ones the
video has a noticeable stutter.

![](http://srv.dthpham.me/static/blow.gif)

Here is another example of the same concept. Interpolated frames between
real frames are marked `Int: Y`. Opening the output video and frame stepping
through it would make them more obvious.

See the [In Action](https://github.com/dthpham/butterflow/wiki/In-Action) page
for more demonstrations.

# Installation

### OS X:

With [Homebrew](http://brew.sh/):

```
brew install homebrew/science/butterflow
```

### Arch Linux:

A package is available in the AUR under
[`butterflow`](https://aur.archlinux.org/packages/butterflow/).

### From Source:

Refer to the
[Install From Source Guide](https://github.com/dthpham/butterflow/wiki/Install-From-Source-Guide)
on the wiki.

# Setup

Butterflow requires no additional setup to use, however it's recommended that
you set up a functional OpenCL environment on your machine to take advantage of
hardware accelerated methods that will make rendering significantly faster.

See [Setting up OpenCL](https://github.com/dthpham/butterflow/wiki/Setting-up-OpenCL)
for details on how to do this.

# Usage

Run `butterflow -h` for a full list of options and their default values.

See [Example Usage](https://github.com/dthpham/butterflow/wiki/Example-Usage)
for typical commands.
