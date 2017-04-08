#!/bin/bash
# Run in a MINGW64 Shell

rootdir=$(pwd)/../..
packagedir=${rootdir}/butterflow
version=$(cut -d \' -f2 ${packagedir}/__init__.py)
pkg=butterflow-$version

rm ${packagedir}/*.pyd
rm ${packagedir}/*.pyc

cd $rootdir

python2 setup.py build_ext --build-lib .
python2 setup.py build
python2 setup.py build_exe

if [ ! -f $pkg ]; then rm -rf $pkg; fi
cp -R build/exe.mingw-2.7/ $pkg

if [ ! -f ${pkg}.7z ]; then rm ${pkg}.7z; fi
7z a ${pkg}.7z $pkg

shasum -a256 ${pkg}.7z > ${pkg}.sha256sum

cat ${pkg}.sha256sum
