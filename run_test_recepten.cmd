@echo off
cd /d c:\Users\gertv\Documents\maaltijdinspo
py -3 test_recepten_filter.py > test_recepten_filter_output.txt 2>&1
type test_recepten_filter_output.txt
