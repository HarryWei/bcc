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
vCPU_Sorted_RTS = "/mnt/sorted"
				
print('vMigrater: Migrate single I/O Thread to running vCPUs...')
pid=os.getpid()
#set migrate program to dedicated VCPU
os.sched_setaffinity(pid, {1})
io_pid=int(sys.argv[1])
exiting=0
try:
    affinity = os.sched_getaffinity(io_pid)
except ProcessLookupError:
    print("Task %d might be finished (or not I/O intensive)" % io_pid)
vcpu = affinity.pop()
_vcpu = int(vcpu)
flag=0
#vCPUs=[]
while 1:
    with open(vCPU_Sorted_RTS, 'r') as infile:
        try:
            vCPUs = json.load(infile)
        except ValueError:
            pass
    if len(vCPUs) == 0:
        continue
    #print("I/O thread is on vcpu %d" % _vcpu)
    #try:
    #    affinity = os.sched_getaffinity(io_pid)
    #except ProcessLookupError:
    #    print("Task %d might be finished (or not I/O intensive)" % io_pid)
    #vcpu = affinity.pop()
    #_vcpu = int(vcpu)
    #print("I/O Thread is running on vCPU %d, flag is %d" % (_vcpu, flag))
    #for i in vCPUs:
    #    print(i)
    #    print(vCPUs[0][1])
    #print(vCPUs)
    for i in vCPUs:
        if int(i[1]) == _vcpu:
            flag=1
            if int(i[0]) < int(6000) and _vcpu != vCPUs[0][1]:
                try:
                    os.sched_setaffinity(io_pid, {vCPUs[0][1]})
                    _vcpu=vCPUs[0][1]
                except IndexError:
                    pass
                except OSError:
                    pass
                
    if flag==0 and _vcpu != vCPUs[0][1]:
        try:
            os.sched_setaffinity(io_pid, {vCPUs[0][1]})
            _vcpu=vCPUs[0][1]
        except IndexError:
            pass
        except OSError:
            pass
    flag = 0
    if exiting:
        print("Exiting...")
        exit()
