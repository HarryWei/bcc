#!/usr/bin/python
#
# Build IOMigrater script - Initialize IOMigrater Host settings
#
#
# Weiwei Jia <harryxiyou@gmail.com> (Python) 2017

import os
import sys

src = "/sys/fs/cgroup/cpuset/machine/tmp1.libvirt-qemu/"
des = "/sys/module/core/parameters/"
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

def WriteFile(filepath, buf):
  f = open(filepath, "w")
  try:
    f.write(buf)
  finally:
    f.close()
  
for i in range(vCPU_start, vCPU_end):
  print("This is vCPU %d" % i)
  new_src = src + "vcpu%d/tasks" % i
  new_des = des + "vm1_vcpu%d_pid" % i
  if os.path.exists(new_src) and os.path.exists(new_des):
    print("new_src: %s, new_des: %s" % (new_src, new_des))
	contents = ReadFile(new_src)
	print("contents: %s" % contents)
	WriteFile(new_des, contents)
  else:
    sys.exit("Error: Cannot find %s or %s file." % (nes_src, new_des))