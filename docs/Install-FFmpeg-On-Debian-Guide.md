# Install FFmpeg on Debian Guide
These instructions are adapted from this
[guide](https://www.assetbank.co.uk/support/documentation/install/ffmpeg-debian-squeeze/ffmpeg-debian-jessie/).
This [gist](https://gist.github.com/holms/7009218) is more comprehensive and
will show you how to make a package that you can manage with apt-get.

First, add the multimedia source to the bottom of /etc/apt/sources.list.
```
deb http://www.deb-multimedia.org jessie main non-free
deb-src http://www.deb-multimedia.org jessie main non-free
```

Then update your package list and keyring.
```
sudo apt-get update
sudo apt-get install deb-multimedia-keyring
sudo apt-get update
```

Then download dependencies.
```
sudo apt-get install build-essential libmp3lame-dev libvorbis-dev libtheora-dev libspeex-dev yasm pkg-config libfaac-dev libopenjpeg-dev libx264-dev
```

Then download the latest package of FFmpeg from their
[releases](http://ffmpeg.org/releases/) page, extract it to a folder, go into
the directory and run:

```
# This is going to install into /usr/local
./configure --enable-gpl --enable-postproc --enable-swscale --enable-avfilter --enable-libmp3lame --enable-libvorbis --enable-libtheora --enable-libx264 --enable-libspeex --enable-shared --enable-pthreads --enable-libopenjpeg --enable-libfaac --enable-nonfree
make
sudo make install
```
