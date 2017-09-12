#!/usr/bin/python
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

from __future__ import print_function
from bcc import BPF
from time import sleep, strftime
import argparse
import signal
import os
import sys
import time
from subprocess import call

# arguments
examples = """examples:
    ./biotop            # block device I/O top, 1 second refresh
    ./biotop -C         # don't clear the screen
    ./biotop 5          # 5 second summaries
    ./biotop 5 10       # 5 second summaries, 10 times only
"""
parser = argparse.ArgumentParser(
    description="Block device (disk) I/O by process",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)
parser.add_argument("-C", "--noclear", action="store_true",
    help="don't clear the screen")
parser.add_argument("-r", "--maxrows", default=20,
    help="maximum rows to print, default 20")
parser.add_argument("interval", nargs="?", default=1,
    help="output interval, in seconds")
parser.add_argument("count", nargs="?", default=99999999,
    help="number of outputs")
args = parser.parse_args()
interval = int(args.interval)
countdown = int(args.count)
maxrows = int(args.maxrows)
clear = not int(args.noclear)

# linux stats
loadavg = "/proc/loadavg"
diskstats = "/proc/diskstats"

# IOMigrater constants
host_dir = "/mnt/"
vCPU_num = 9
vCPU_start = 2
vCPU_end = 11
filer1 = "kworker"
filer2 = "mount"
filer3 = "jbd"
filer4 = "bash"

# signal handler
def signal_ignore(signal, frame):
    print()

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
    affinity = os.sched_getaffinity(pid)
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
            if vCPU_remaining_timeslice < 3:
                return 1
            else:
                return 0
        else:
            return 1		
    else:
        sys.exit("Error: Cannot find %s file." % (is_vCPU_on_path))
        return -1

# timestamp is in microseconds.
def get_available_vCPUs():
    vCPUs = []
    for i in range(vCPU_start, vCPU_end):
        is_vCPU_on_path = host_dir + "vm1_is_vcpu%d_on" % i
        vCPU_curr_ts_path = host_dir + "vm1_vcpu%d_curr_ts" % i
        vCPU_prev_timeslice_path = host_dir + "vm1_vcpu%d_ts" % i
        if os.path.exists(is_vCPU_on_path) and os.path.exists(vCPU_curr_ts_path) and os.path.exists(vCPU_prev_timeslice_path):
            is_vCPU_on = ReadFile(is_vCPU_on_path)
            if int(is_vCPU_on) == 1:
                vCPU_curr_ts = ReadFile(vCPU_curr_ts_path)
                guest_curr_ts = time.time() * pow(10, 6)
                vCPU_used_timeslice = int(guest_curr_ts) - int(vCPU_curr_ts)
                vCPU_prev_timeslice = ReadFile(vCPU_prev_timeslice_path)
                vCPU_remaining_timeslice = int(vCPU_prev_timeslice) - vCPU_used_timeslice
                vCPUs.append((vCPU_remaining_timeslice, i))
        else:
            sys.exit("Error: Cannot find %s file." % (is_vCPU_on_path))
            return -1
    vCPUs.sort()
    return vCPUs

def do_migration(pid):
    flag = migration_check(pid)
    if flag == 1:
        vCPUs = get_available_vCPUs()
        if len(vCPUs) != 0:
            vCPU = vCPUs[len(vCPUs) - 1][1]
            vCPU_remaining_timeslice = vCPUs[len(vCPUs) - 1][0]
            print("Biggest remaining timeslice vCPU is %d, and remaining timeslice is %d" % (vCPU, vCPU_remaining_timeslice))
            if vCPU_remaining_timeslice >= 9:
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
				

# load BPF program
b = BPF(text="""
#include <uapi/linux/ptrace.h>
#include <linux/blkdev.h>

// for saving process info by request
struct who_t {
    u32 pid;
    char name[TASK_COMM_LEN];
};

// the key for the output summary
struct info_t {
    u32 pid;
    int rwflag;
    int major;
    int minor;
    char name[TASK_COMM_LEN];
};

// the value of the output summary
struct val_t {
    u64 bytes;
    u64 ns; //changed by Weiwei Jia
    u32 io;
};

BPF_HASH(start, struct request *);
BPF_HASH(whobyreq, struct request *, struct who_t);
BPF_HASH(counts, struct info_t, struct val_t);

// cache PID and comm by-req
int trace_pid_start(struct pt_regs *ctx, struct request *req)
{
    struct who_t who = {};

    if (bpf_get_current_comm(&who.name, sizeof(who.name)) == 0) {
        who.pid = bpf_get_current_pid_tgid();
        whobyreq.update(&req, &who);
    }

    return 0;
}

// time block I/O
int trace_req_start(struct pt_regs *ctx, struct request *req)
{
    u64 ts;

    ts = bpf_ktime_get_ns();
    start.update(&req, &ts);

    return 0;
}

// output
int trace_req_completion(struct pt_regs *ctx, struct request *req)
{
    u64 *tsp;

    // fetch timestamp and calculate delta
    tsp = start.lookup(&req);
    if (tsp == 0) {
        return 0;    // missed tracing issue
    }

    struct who_t *whop;
    struct val_t *valp, zero = {};
    u64 delta_ns = bpf_ktime_get_ns() - *tsp;

    // setup info_t key
    struct info_t info = {};
    info.major = req->rq_disk->major;
    info.minor = req->rq_disk->first_minor;
/*
 * The following deals with a kernel version change (in mainline 4.7, although
 * it may be backported to earlier kernels) with how block request write flags
 * are tested. We handle both pre- and post-change versions here. Please avoid
 * kernel version tests like this as much as possible: they inflate the code,
 * test, and maintenance burden.
 */
#ifdef REQ_WRITE
    info.rwflag = !!(req->cmd_flags & REQ_WRITE);
#elif defined(REQ_OP_SHIFT)
    info.rwflag = !!((req->cmd_flags >> REQ_OP_SHIFT) == REQ_OP_WRITE);
#else
    info.rwflag = !!((req->cmd_flags & REQ_OP_MASK) == REQ_OP_WRITE);
#endif

    whop = whobyreq.lookup(&req);
    if (whop == 0) {
        // missed pid who, save stats as pid 0
        valp = counts.lookup_or_init(&info, &zero);
    } else {
        info.pid = whop->pid;
        __builtin_memcpy(&info.name, whop->name, sizeof(info.name));
        valp = counts.lookup_or_init(&info, &zero);
    }

    // save stats
    //bpf_trace_printk("%lu\\n", valp->us);
    valp->ns += delta_ns;
    valp->bytes += req->__data_len;
    valp->io++;

    start.delete(&req);
    whobyreq.delete(&req);

    return 0;
}
""", debug=0)
b.attach_kprobe(event="blk_account_io_start", fn_name="trace_pid_start")
b.attach_kprobe(event="blk_start_request", fn_name="trace_req_start")
b.attach_kprobe(event="blk_mq_start_request", fn_name="trace_req_start")
b.attach_kprobe(event="blk_account_io_completion",
    fn_name="trace_req_completion")

#print('Tracing... Output every %d secs. Hit Ctrl-C to end' % interval)
print('Tracing... Output every 100 milliseconds. Hit Ctrl-C to end')

# cache disk major,minor -> diskname
disklookup = {}
with open(diskstats) as stats:
    for line in stats:
        a = line.split()
        disklookup[a[0] + "," + a[1]] = a[2]

# output
exiting = 0
while 1:
    try:
        sleep(100.0/1000.0)
    except KeyboardInterrupt:
        exiting = 1

    # header
    #if clear:
    #    call("clear")
    #else:
    #    print()
    #with open(loadavg) as stats:
        #print("%-8s loadavg: %s" % (strftime("%H:%M:%S"), stats.read()))
    #print("%-6s %-16s %1s %-3s %-3s %-8s %5s %7s %6s" % ("PID", "COMM",
    #    "D", "MAJ", "MIN", "DISK", "I/O", "Kbytes", "AVGms"))
    #print("%-6s %-16s %6s" % ("PID", "COMM", "IO"))

    # by-PID output
    counts = b.get_table("counts")
    line = 0
    for k, v in reversed(sorted(counts.items(),
                                key=lambda counts: counts[1].bytes)):

        # lookup disk
        disk = str(k.major) + "," + str(k.minor)
        if disk in disklookup:
            diskname = disklookup[disk]
        else:
            diskname = "?"

        # print line
        #avg_ms = (float(v.us) / 1000) / v.io
        #print("%-6d %-16s %1s %-3d %-3d %-8s %5s %7s %6.2f" % (k.pid, k.name,
        #    "W" if k.rwflag else "R", k.major, k.minor, diskname, v.io,
        #    v.bytes / 1024, avg_ms))
        io_percent = ((float(v.ns) / 1000.0)/100000.0)
        task_name = k.name.decode("utf-8")
        if io_percent > 0.5 and k.pid != 0 and (task_name.find(filer1) == -1) and (task_name.find(filer2) == -1) and (task_name.find(filer3) == -1) and (task_name.find(filer4) == -1):
            print("%-6d %-16s %6.5f %d" % (k.pid, task_name, io_percent, v.ns))
            ret = do_migration(k.pid)
            if ret == 1:
                affinity = os.sched_getaffinity(k.pid)
                print('PID %d is migrated to CPU %s' % (k.pid, affinity))
            v.ns = 0
            io_percent = 0.0

        line += 1
        if line >= maxrows:
            break
    counts.clear()

    countdown -= 1
    if exiting or countdown == 0:
        print("Detaching...")
        exit()
