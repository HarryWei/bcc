#!/usr/bin/python3
# iomigrater - create based on iofilter
# @lint-avoid-python-3-compatibility-imports
#
# biotop  block device (disk) I/O by process.
#         For Linux, uses BCC, eBPF.
#
# USAGE: biotop.py [-h] [-C] [-r MAXROWS] [interval] [count]
#
# This uses in-kernel eBPF maps to cache process details (PID and comm) by I/O
# request, as well as a starting timestamp for calculating I/O latency.
#
# Licensed under the Apache License, Version 2.0 (the "License")
#
# Weiwei Jia <harryxiyou@gmail.com> (python) 2017

#from __future__ import print_function
#from bcc import BPF
from time import sleep, strftime
import argparse
import signal
import os
import sys
import time
import json
#from subprocess import call


# IOMigrater constants
host_dir = "/sys/module/core/parameters/"
vCPU_Sorted_RTS = "/home/wwjia/workshop/bcc/vMigrater/shared/sorted"
vCPU_num = 9
vCPU_start = 2
vCPU_end = 8


def ReadFile(filepath):
    f = open(filepath, "r")
    try:
        contents = f.read()
    finally:
        f.close()
    return contents

print('vMigrater: VMM Kernel part unittest...')
#Set VMM userspace daemon to dedicated PCPU
pid=os.getpid()
os.sched_setaffinity(pid, {10})
exiting=0
count=0
while 1:
    try:
        #XXX:VMM userspace must sleep since it need give VM userspace to read the contents.
        sleep(30.0/1000.0)
    except KeyboardInterrupt:
        exiting = 1
# timestamp is in microseconds.
    #prev=int(time.time() * pow(10,6))
    vcpu1_ts_path = host_dir + "vm1_vcpu5_ts"
    vCPU_prev_timeslice = ReadFile(vcpu1_ts_path)
    sys.stdout.write(vCPU_prev_timeslice)
    count = count + 1
    #print("count is %d" % count)
    if count == 1001:
        exiting = 1
    if exiting:
        print("Exiting...")
        exit()
