#!/bin/bash
cd "$(dirname "$0")"
python3 buffer_scheduler.py >> scheduler_log.txt 2>&1
