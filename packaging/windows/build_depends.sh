#!/bin/bash
# Run in an MSYS2 Shell

depends=(base-devel
        msys2-devel
        mingw-w64-x86_64-toolchain
        mingw-w64-x86_64-python2
        mingw-w64-x86_64-python2-pip
        mingw-w64-x86_64-python2-numpy
        mingw-w64-x86_64-ffmpeg
        mingw-w64-x86_64-python2-cx_Freeze
        mingw-w64-x86_64-SDL2
        p7zip
        )

build_package() {
  cd mingw-packages/mingw-w64-$1

  MINGW_INSTALLS=mingw64 makepkg-mingw -sLf
  pacman -U mingw-w64-x86_64-$1-*-any.pkg.tar.xz

  cd ../..
}

pacman -S ${depends[@]}

build_package ocl-icd-git opencv2
build_package opencv2
