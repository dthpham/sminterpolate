# Install FFmpeg on Debian Guide

## Instructions:
1. Add `deb http://www.deb-multimedia.org jessie main non-free` and `deb-src http://www.deb-multimedia.org jessie main non-free` to the bottom of `/etc/apt/sources.list`.
2. Update your package list with `sudo apt-get update`.
3. Update your keyring with `sudo apt-get install deb-multimedia-keyring`.
4. Re-update your package list.
5. Download dependencies with `sudo apt-get install build-essential libmp3lame-dev libvorbis-dev libtheora-dev libspeex-dev yasm pkg-config libfaac-dev libopenjpeg-dev libx264-dev`.
6. Download [FFmpeg](http://ffmpeg.org/releases/) and extract it.
7. Go into the folder.
8. Configure it with `./configure --enable-gpl --enable-postproc --enable-swscale --enable-avfilter --enable-libmp3lame --enable-libvorbis --enable-libtheora --enable-libx264 --enable-libspeex --enable-shared --enable-pthreads --enable-libopenjpeg --enable-libfaac --enable-nonfree`.
9. Build it with `make`.
10. Install it with `sudo make install`.
 * This will install FFmpeg into /usr/local.
