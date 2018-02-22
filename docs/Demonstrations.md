# Demonstrations

### 1080p motion interpolated slow motion (+1841 frames):
![](http://srv.dthpham.me/butterflow/demos/her_day_xs.jpg)

**See:** The [input video](http://srv.dthpham.me/butterflow/demos/her_day_1.0x_23.98fps.mp4) and [output video](http://srv.dthpham.me/butterflow/demos/her_day_0.1x_r2x_48fps.mp4).

```bash
#!/bin/bash
# Video: 4.05 sec 23.976fps 96 frames to -> 40.4sec ~48fps 1937 frames
# Using a GeForce GTX 760
# Rendering took 4.86 mins on Windows
# Rendering took 3.15 mins on Arch Linux

A=her_day_1.0x_23.98fps.mp4
if [ ! -f $A ]; then wget http://srv.dthpham.me/butterflow/demos/${A}; fi
butterflow -e -v -r2x -s a=0,b=4.045,spd=0.1 $A -o her_day_0.1x_r2x_48fps.mp4
```

### 1080p 24fps to motion interpolated 144fps (+1198 frames):
![](http://srv.dthpham.me/butterflow/demos/her_night_xs_2.jpg)

**See:**  The [input video](http://srv.dthpham.me/butterflow/demos/her_night_1.0x_23.98fps.mp4) and [output video](http://srv.dthpham.me/butterflow/demos/her_night_1.0x_144fps.mp4).

```bash
#!/bin/bash
# Video: 10.01 sec 23.976fps 240 frames to -> 10.01 sec 144fps 1441 frames
# Using a GeForce GTX 760
# Rendering took 4.37 mins on Windows

A=her_night_1.0x_23.98fps.mp4
B=her_night_1.0x_144fps.mp4
if [ ! -f $A ]; then wget http://srv.dthpham.me/butterflow/demos/${A}; fi
butterflow -e -m -v -r144 $A -o $B
ffprobe -i $A
ffprobe -i $B
```

### Motion interpolated slow motion vs. scaling timestamps (+270 frames):
```bash
#!/bin/bash

generate() {
  if [ ! -f $1 ]; then wget http://srv.dthpham.me/butterflow/demos/${1}; fi

  butterflow -e -l -v -s a=0,b=end,spd=0.1 $1 -o a.mp4
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
