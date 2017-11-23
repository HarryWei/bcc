#!/bin/bash

gcc backstage.c debug.c -o backstage -lpthread -lglib-2.0
gcc test.c debug.c -o test -lpthread -lglib-2.0
