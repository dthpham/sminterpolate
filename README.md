# Butterflow
## What it can do:
1. Make **motion interpolated videos**, increase a video's frame rate by rendering new frames based on motion (*uses a combination of pixel-warping and blending*).
2. Make **smooth motion videos** (*simple blending between frames*).
3. Leverage interpolated frames to make **fluid slow motion videos**.

## How it works:
BF works by rendering intermediate frames between existing frames using a process called [motion interpolation](http://en.wikipedia.org/wiki/Motion_interpolation). For example, given two existing frames, `A` and `B`, this program can generate frames `C.1`, `C.2`...`C.n` that are positioned between the two. In contrast to other tools that can only *blend or dupe* frames, this program *warps pixels based on motion* to generate new ones.

BF uses these interpolated frames to increase a video's frame rate, which can give the perception of smoother motion and more fluid animation, an effect that most people know as the "soap opera effect".

Here's a demo of BF leveraging motion interpolation to make a fluid slow motion video:

![](http://srv.dthpham.me/static/bf-example-1.gif)

In this example, BF has slowed a [`1s` video](https://dl.dropboxusercontent.com/u/103239050/ba12a4b.mp4) down by `10x`. An additional `270` frames were interpolated from `30` original source frames giving the video a smooth feel during playback. The same video was slowed down with FFmpeg alone (shown on the right-hand side), but because it dupes frames and can't interpolate new ones, the video has a noticeable stutter.

![](http://srv.dthpham.me/static/bf-example-2.gif)

Here's another example of the same concept. Frame-stepping through the BF'd file would make the interpolated frames, marked `Int: Y`, more evident.

**See:** [The script](https://github.com/dthpham/butterflow/tree/master/generate_side_by_side.sh) used to generate these demos.

## How to install:
**Important:** BF only works on 64-bit systems.

* **Mac OS X:** With [Homebrew](http://brew.sh/), `brew install homebrew/science/butterflow`.
* **Windows (Portable)**: Download [butterflow-0.2.2.7z](http://srv.dthpham.me/butterflow/releases/win/butterflow-0.2.2.7z).
  * Sha256: cb228ea8674f6ff29573c4f0b00a0ff513420021b51648ed6aad3099505f0ba5
* **Arch Linux:** A package is available in the AUR under [`butterflow`](https://aur.archlinux.org/packages/butterflow/).
* **From Source (Ubuntu, Debian):** Refer to the [Install From Source Guide](https://github.com/dthpham/butterflow/blob/master/docs/Install-From-Source-Guide.md) for instructions.

## Setup (for Linux users):
**Note:** No setup is necessary on OS X or Windows. Read [this](https://github.com/dthpham/butterflow/blob/master/docs/Setting-Up-OpenCL.md#os-x-mavericks-and-newer) if you run into a problem with OpenCL on OS X.

BF requires no additional setup to use, however it's too slow out of the box to do any serious work. It's recommended that you set up a functional OpenCL environment on your machine so you can take advantage of hardware accelerated methods that will make rendering significantly faster.

See: [Setting up OpenCL](https://github.com/dthpham/butterflow/blob/master/docs/Setting-Up-OpenCL.md) for details on how to do this.

## Usage:
Run `butterflow -h` for a full list of options. See: [Example Usage](https://github.com/dthpham/butterflow/blob/master/docs/Example-Usage.md) for typical commands.

## More documentation:
Check the [docs folder](https://github.com/dthpham/butterflow/tree/master/docs).
