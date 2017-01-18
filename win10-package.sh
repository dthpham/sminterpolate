#!/bin/bash

version=$(cut -d \' -f2 butterflow/__init__.py)
pkg=butterflow-$version

# pacman -S base-devel msys2-devel mingw-w64-x86_64-toolchain  # build dependencies
# pacman -S mingw-w64-x86_64-python2 mingw-w64-x86_64-python2-pip mingw-w64-x86_64-python2-numpy mingw-w64-x86_64-ffmpeg mingw-w64-x86_64-python2-cx_Freeze  mingw-w64-x86_64-SDL2  # pkg dependencies
# pacman -S p7zip

# build_package() {
#   cd mingw-packages/mingw-w64-$1
#   MINGW_INSTALLS=mingw64 makepkg-mingw -sLf
#   pacman -U mingw-w64-x86_64-$1-*-any.pkg.tar.xz  # to uninstall: pacman -R mingw-w64-x86_64-<pkg>
#   cd ../..
# }

# build_package ocl-icd-git
# build_package opencv2

python2 setup.py build
python2 setup.py build_exe

if [ ! -f $pkg ]; then rm -rf $pkg; fi
cp -R build/exe.mingw-2.7/ $pkg

# p7zip a $pkg $pkg.7z
# shasum -a256 $pkg.7z
