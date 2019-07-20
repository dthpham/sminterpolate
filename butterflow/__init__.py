#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import multiprocessing
import _winreg as winreg
import itertools


class RegistryKey(object):
    def __init__(self, name, data_type, value):
        self.name = name
        self.data_type = data_type
        self.value = value
 
    def __str__(self):
        return "keyname: %s\ttype: %d\tvalue: %d" % (self.name, self.data_type, self.value)

    def __eq__(self, other):
        if isinstance(other, RegistryKey):
           return self.__dict__ == other.__dict__ 
        return False


REG_HIVE=winreg.HKEY_CURRENT_USER
KHRONOS_REG_PATH=r"Software\Khronos\OpenCL\Vendors"

KEYS_NEEDED=[RegistryKey("amdocl64.dll", winreg.REG_DWORD, 0),
    RegistryKey("nvopencl64.dll", winreg.REG_DWORD, 0),
    RegistryKey("IntelOpenCL64.dll", winreg.REG_DWORD, 0)]

ADD_PATHS_TO_EXE=['lib', 'lib\\library.zip', 'lib\\butterflow', 'lib\\numpy\\core', 'lib\\ffmpeg', 'lib\\misc']
ADDED_PATHS=False


def add_paths_to_exe():
    global ADDED_PATHS
    if ADDED_PATHS:
        return

    if hasattr(sys, "frozen"):
        # print("Settting PATHs for executable:")
        
        executable_dir = os.path.dirname(sys.executable).replace('/', os.sep)
        os.environ['PATH'] = executable_dir
        for path in ADD_PATHS_TO_EXE:
            os.environ['PATH'] += os.pathsep+os.path.join(executable_dir, path)

        # print(os.environ['PATH'])
        ADDED_PATHS=True

def get_local_machine_registry_subkeys(name):
    # print("Keys at %s:" % name)
    try:
        with winreg.OpenKey(REG_HIVE, name, 0, winreg.KEY_READ) as key:
            for i in itertools.count():
                yield winreg.EnumValue(key, i)
    except WindowsError as error:
        # print(error)
        yield None

def add_registry_keys():
    for key in get_local_machine_registry_subkeys(KHRONOS_REG_PATH):
        if key is not None:
            key = RegistryKey(key[0], key[2], key[1])
            if key in KEYS_NEEDED:
                KEYS_NEEDED.remove(key)
            else:
                # print("?: "+str(key))
                pass

    # print("No keys left\nKeys to add: "+str(KEYS_NEEDED))

    for key_needed in KEYS_NEEDED:
        try:
            try:
                subkey = winreg.CreateKeyEx(REG_HIVE, KHRONOS_REG_PATH, 0, winreg.KEY_CREATE_SUB_KEY)
            except WindowsError as error: 
                print("Couldn't create subkeys at: %s\tReason: %s" % (KHRONOS_REG_PATH, error))
                exit(1)
            finally:
                subkey.Close()
            with winreg.OpenKey(REG_HIVE, KHRONOS_REG_PATH, 0, winreg.KEY_WRITE) as key: 
                winreg.SetValueEx(key, key_needed.name, 0, key_needed.data_type, key_needed.value)
                # print("+"+str(key_needed))
        except WindowsError as error:
            print("Couldn't create (%s)\tReason: %s" % (key_needed, error))
            exit(1)


if sys.platform.startswith("win"):
    add_paths_to_exe()
    add_registry_keys()    
    multiprocessing.freeze_support()

