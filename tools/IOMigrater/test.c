#include <stdio.h>
#include <unistd.h>
#include "debug.h"

int main(void) {
	uint64_t ts;

	ts = debug_time_usec();
	printf("Current timestamp is %lu\n", ts);

	return 0;
}
