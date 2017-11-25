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
while 1:
    try:
        #XXX:VMM userspace must sleep since it need give VM userspace to read the contents.
        sleep(1.0/1000.0)
    except KeyboardInterrupt:
        exiting = 1
# timestamp is in microseconds.
    #prev=int(time.time() * pow(10,6))
    vCPUs = []
    for i in range(vCPU_start, vCPU_end):
        #print("This is vCPU %d" % i)
        is_vCPU_on_path = host_dir + "vm1_is_vcpu%d_on" % i
        vCPU_curr_ts_path = host_dir + "vm1_vcpu%d_curr_ts" % i
        vCPU_prev_timeslice_path = host_dir + "vm1_vcpu%d_ts" % i
        if os.path.exists(is_vCPU_on_path) and os.path.exists(vCPU_curr_ts_path) and os.path.exists(vCPU_prev_timeslice_path):
            is_vCPU_on = ReadFile(is_vCPU_on_path)
            if int(is_vCPU_on) == 1:
                vCPU_curr_ts = ReadFile(vCPU_curr_ts_path)
                guest_curr_ts = time.time() * pow(10, 6)
                #print("%s: schedule timestamp is %d" % (vCPU_curr_ts_path, int(vCPU_curr_ts)))
                #print("Current timestamp is %d" % int(guest_curr_ts))
                vCPU_used_timeslice = int(guest_curr_ts) - int(vCPU_curr_ts)
                vCPU_prev_timeslice = ReadFile(vCPU_prev_timeslice_path)
                vCPU_remaining_timeslice = int(vCPU_prev_timeslice) - vCPU_used_timeslice
                vCPUs.append((vCPU_remaining_timeslice, i))
        else:
            sys.exit("Error: Cannot find %s file." % (is_vCPU_on_path))
    vCPUs.sort()
    vCPUs.reverse()
    #_now=int(time.time() * pow(10,6))
    #print("get sorted vCPUs needs %d us" % (_now - prev))
    #print(vCPUs)
    #prev=int(time.time() * pow(10,6))
    with open(vCPU_Sorted_RTS, 'w') as outfile:
        json.dump(vCPUs, outfile)
    #print(vCPUs)
    #_now=int(time.time() * pow(10,6))
    #print("dump file cost is %d us" % (_now - prev))
    if exiting:
        print("Exiting...")
        exit()
