/*
 * backstage.c
 *
 * Weiwei Jia <harryxiyou@gmail.com> (C) 2017
 *
 * Backstage program for IOMigrater project.
 *
 *
 */
#define _GNU_SOURCE
#include <sys/signalfd.h>
#include <signal.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/types.h>
#include <sched.h>
#include <sys/stat.h>
#include <fcntl.h>
#include "debug.h"
#include "glib-2.0/glib.h"
#include <pthread.h>
#include <assert.h>
#include <sys/mman.h>
#include <sys/sysinfo.h>
#include <sys/time.h>
#include <sys/stat.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <semaphore.h>
#include <signal.h>
#include <sys/shm.h>
#include <sys/ipc.h>

static int start_vcpu = 2;
static int end_vcpu = 11;

static pthread_t *p;

#define handle_error(msg) \
	do { perror(msg); exit(EXIT_FAILURE); } while (0)

uint64_t get_affinity(void) {
	cpu_set_t cpuset;
	CPU_ZERO(&cpuset);

	int s = pthread_getaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
	if (s != 0) return -1;
	uint64_t j = 0;
	uint64_t _j = 0;
	for (j = 0; j < CPU_SETSIZE; j++)
		if (CPU_ISSET(j, &cpuset)) {
			_j = j;
		}
	return _j;
}

void set_affinity(uint64_t vcpu_num) {
	cpu_set_t cpuset;
	CPU_ZERO(&cpuset);
	CPU_SET(vcpu_num, &cpuset);

	if (pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset) < 0) {
		fprintf(stderr, "Set thread to VCPU error!\n");
	}
}

void set_idle_priority(void) {
	struct sched_param param;
	param.sched_priority = 0;
	int s = pthread_setschedparam(pthread_self(), SCHED_IDLE, &param);
	if (s != 0) handle_error("Pthread_setschedparam error!\n");
}

void *thread_func(void *arg) {
	uint64_t vn = *((uint64_t *) arg);
	printf("This is %lu thread worker.\n", vn);
	uint64_t i = 0;
	set_affinity(vn);
	set_idle_priority();

	vn = get_affinity();
	printf("CPU daemon worker is on vCPU %lu\n", vn);
	//int pid = syscall(SYS_gettid);
	//printf("CPU daemon worker thread PID number is %d\n", pid);

	while(1) {
		i += 1;
	}
}

void init_cpu_thread(void) {
	int ret = 0;
	uint64_t i = 0;
	uint64_t j = 0;

	int vcpu_num = get_nprocs();
	uint64_t _vcpu_num[vcpu_num];
	printf("There are %d vCPUs in this VM.\n", vcpu_num);
	p = (pthread_t *) malloc(sizeof(pthread_t) * vcpu_num);
	if (p == NULL) handle_error("malloc error!");

	for (i = 0; i < vcpu_num; i++) {
		_vcpu_num[j] = i;
		ret = pthread_create(&(p[i]), NULL, thread_func, &(_vcpu_num[j]));
		if (ret != 0) {
			printf("Pthread create error!\n");
			exit(EXIT_SUCCESS);
		}
		j = j + 1;
	}
	
	return;
}

void sig_handler(int signo) {
	if (signo == SIGINT) {
		printf("Free resource ...\n");
		if (p != NULL) free(p);
	} else
		handle_error("Signal Error!\n");

	exit(EXIT_SUCCESS);
}


int main(int argc, char **argv) {
	int i = 0;
	
	if (signal(SIGINT, sig_handler) == SIG_ERR) {
		handle_error("SIGINT error!\n");
	}
	init_cpu_thread();
	
	for (i = 0; i < get_nprocs(); i++) {
		pthread_join(p[i], NULL);
	}
	if (p != NULL) free(p);
	return 0;
}