#!/bin/bash
while getopts s:g:f: flag
do
    case "${flag}" in
        s) shutter=${OPTARG};;
        g) gain=${OPTARG};;
        f) file=${OPTARG};;
    esac
done
echo "Username: $shutter";
echo "Age: $gain";
echo "Full Name: $file";
libcamera-still --shutter $shutter --gain $gain --immediate -o $file
ffmpeg -y -i $file -vf transpose=1 $file