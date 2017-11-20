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
vCPU_Sorted_RTS = "sorted"
vCPU_num = 9
vCPU_start = 1
vCPU_end = 9

# for do_migration_v2
time_flag = 0
vcpu_flag = 0
prev_us = 0
now_us = 0

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

def migration_check(pid):
    try:
        affinity = os.sched_getaffinity(pid)
    except ProcessLookupError:
        print("Task %d might be finished (or not I/O intensive)" % pid)
        return -1
    vcpu = affinity.pop()
    _vcpu = int(vcpu)
    print('Task %d is running on CPU %d' % (pid, _vcpu))
    is_vCPU_on_path = host_dir + "vm1_is_vcpu%d_on" % _vcpu
    vCPU_curr_ts_path = host_dir + "vm1_vcpu%d_curr_ts" % _vcpu
    vCPU_prev_timeslice_path = host_dir + "vm1_vcpu%d_ts" % _vcpu
    if os.path.exists(is_vCPU_on_path) and os.path.exists(vCPU_curr_ts_path) and os.path.exists(vCPU_prev_timeslice_path):
        is_vCPU_on = ReadFile(is_vCPU_on_path)
        if int(is_vCPU_on) == 1:
            vCPU_curr_ts = ReadFile(vCPU_curr_ts_path)
            guest_curr_ts = time.time() * pow(10, 6)
            vCPU_used_timeslice = int(guest_curr_ts) - int(vCPU_curr_ts)
            vCPU_prev_timeslice = ReadFile(vCPU_prev_timeslice_path)
            vCPU_remaining_timeslice = int(vCPU_prev_timeslice) - vCPU_used_timeslice
            if vCPU_remaining_timeslice < 2000:
                return 1
            else:
                return 0
        else:
            return 1		
    else:
        sys.exit("Error: Cannot find %s file." % (is_vCPU_on_path))
        return -1

def do_migration_v1(pid):
    flag = migration_check(pid)
    if flag == 1:
        vCPUs = get_available_vCPUs()
        if len(vCPUs) != 0:
            vCPU = vCPUs[len(vCPUs) - 1][1]
            vCPU_remaining_timeslice = vCPUs[len(vCPUs) - 1][0]
            print("Biggest remaining timeslice vCPU is %d, and remaining timeslice is %d" % (vCPU, vCPU_remaining_timeslice))
            if vCPU_remaining_timeslice >= 3000:
                try:
                    os.sched_setaffinity(pid, {vCPU})
                    return 1
                except OSError:
                    print ("Catch OSError: process %d might not be migrated" % pid)
                    return -1
            else:
                return 0
        else:
            return 0
    else:
        return 0

def do_migration_v2(pid):
    if vcpu_flag == 0:
        vCPUs = get_available_vCPUs()
        vcpu_flag = 1
        if len(vCPUs) != 0:
            vCPU = vCPUs[len(vCPUs) - 1][1]
            vCPU_remaining_timeslice = vCPUs[len(vCPUs) - 1][0]
            print("Biggest remaining timeslice vCPU is %d, and remaining timeslice is %d" % (vCPU, vCPU_remaining_timeslice))
            try:
                os.sched_setaffinity(pid, {vCPU})
                return 1
            except OSError:
                print ("Catch OSError: process %d might not be migrated" % pid)
                return -1
    if time_flag == 0:
        prev = time.monotonic()
        prev_us = int(now * pow(10, 6))
        time_flag = 1
    else:
        now = time.monotonic()
        now_us = int(now * pow(10, 6))
        diff_us = now_us - prev_us
        prev_us = now_us
    if (vCPU_remaining_timeslice - diff_us) <= 2000:
        vcpu_flag = 1

    return 0
				

#print('Tracing... Output every %d secs. Hit Ctrl-C to end' % interval)
print('vMigrater: VMM Kernel part unittest...')
#Set VMM userspace daemon to dedicated PCPU
pid=os.getpid()
os.sched_setaffinity(pid, {11})
#vCPUs = get_available_vCPUs()
#print(vCPUs)
exiting=0
while 1:
    try:
        sleep(3.0/1000.0)
    except KeyboardInterrupt:
        exiting = 1
# timestamp is in microseconds.
    #vCPUs = []
    with open(vCPU_Sorted_RTS, 'r') as infile:
        try:
            vCPUs = json.load(infile)
        except ValueError:
            pass
    #print(vCPUs)
    print("There are %d available vCPUs running!" % len(vCPUs))
    for i in vCPUs:
        #print("vCPU %d has remaining %d us" % (int(i[1]), int(i[0])))
        print("vCPU %d has remaining %d us" % (i[1], i[0]))
    if exiting:
        print("Exiting...")
        exit()
