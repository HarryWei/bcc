#!/bin/bash

echo 1 | sudo tee /sys/module/core/parameters/enable_vm1_flag
