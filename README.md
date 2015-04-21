#Butterflow

*Butterflow* is an easy to use command line tool that lets you create fluid slow
motion and smooth motion videos.

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

Features, usage, and installation instructions are
[summarized on the homepage](http://app.dthpham.me/butterflow).
