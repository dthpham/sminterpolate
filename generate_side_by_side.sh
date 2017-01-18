#!/bin/bash

BF=butterflow
#BF=./butterflow-0.2.2.dev0-alpha.1/butterflow.exe

generate() {
  $BF -e -l -s a=0,b=end,spd=0.1 $1 -o a.mp4 -v
  ffmpeg -y -ss 0 -t 1 -i $1 -filter:v "setpts=10*PTS" -c:v libx264 -qp 0 b.mp4

  ffmpeg -y -i a.mp4 -i b.mp4 -filter_complex \
  "[0:v]setpts=PTS-STARTPTS, \
  pad=iw*2:ih[left]; [1:v]setpts=PTS-STARTPTS[right]; \
  [left][right]overlay=overlay_w" \
  -an -sn -c:v libx264 -preset veryslow -crf 18 side.mp4
  ffmpeg -y -i side.mp4 -vf scale=-2:200 $2.gif
  
  rm a.mp4 b.mp4 side.mp4
}

if [ ! -f ba12a4b.mp4 ]; then wget https://dl.dropboxusercontent.com/u/103239050/ba12a4b.mp4; fi
generate ba12a4b.mp4 bf-example-1

if [ ! -f a9395c9.mp4 ]; then wget https://dl.dropboxusercontent.com/u/103239050/a9395c9.mp4; fi
generate a9395c9.mp4 bf-example-2
