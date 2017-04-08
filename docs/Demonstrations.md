# Demonstrations

### 1080p motion interpolated slowmo (+1841 frames):

![](http://srv.dthpham.me/butterflow/demos/her_day_sm.jpg)

**See:** The [input video](http://srv.dthpham.me/butterflow/demos/her_day_1.0x_23.98fps.mp4). Download the [output video](http://srv.dthpham.me/butterflow/demos/her_day_0.1x_r2x_48fps.mp4) or generate it yourself:.

```bash
#!/bin/bash
# Using a GeForce GTX 760
# Video: 4.05sec 23.976fps 96frames to -> 40.4sec ~48fps 1937frames
# Rendering took 4.86 mins.

A=her_day_1.0x_23.98fps.mp4
if [ ! -f $A ]; then wget http://srv.dthpham.me/butterflow/demos/${A}; fi
butterflow -v -r2x -s a=0,b=4.045,spd=0.1 $A -o her_day_0.1x_r2x_48fps.mp4
```

### Motion interpolated slowmo vs. scaling timestamps (+270 frames):

```bash
#!/bin/bash

BF=butterflow
#BF=./butterflow-0.2.2.dev0-alpha.1/butterflow.exe

generate() {
  if [ ! -f $1 ]; then wget http://srv.dthpham.me/butterflow/demos/${1}; fi

  $BF -v -e -l -s a=0,b=end,spd=0.1 $1 -o a.mp4
  ffmpeg -y -ss 0 -t 1 -i $1 -filter:v "setpts=10*PTS" -c:v libx264 -qp 0 b.mp4

  ffmpeg -y -i a.mp4 -i b.mp4 -filter_complex \
  "[0:v]setpts=PTS-STARTPTS, \
  pad=iw*2:ih[left]; [1:v]setpts=PTS-STARTPTS[right]; \
  [left][right]overlay=overlay_w" \
  -an -sn -c:v libx264 -preset veryslow -crf 18 side.mp4

  ffmpeg -y -i side.mp4 -vf scale=-2:200 $2
}

generate ba12a4b.mp4 1.gif
generate a9395c9.mp4 2.gif
```
