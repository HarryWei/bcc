#!/usr/bin/python
#
# Build IOMigrater script - Initialize IOMigrater Host settings
#
#
# Weiwei Jia <harryxiyou@gmail.com> (Python) 2017

import os
import sys

src = "/sys/fs/cgroup/cpuset/machine/tmp1.libvirt-qemu"
des = "/sys/module/core/parameters"
vCPU_num = 9
vCPU_start = 2
vCPU_end = 10

def ReadFile(filepath):
  f = open(filepath, "r")
  try:
    contents = f.read()
  finally:
    f.close()

  return contents
  
for i in range(vCPU_start, vCPU_end):
  print("This is vCPU %d" % i)