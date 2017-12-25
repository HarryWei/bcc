#!/bin/bash

echo 0 | sudo tee /sys/module/core/parameters/enable_vm1_flag
