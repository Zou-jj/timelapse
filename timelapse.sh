#!/bin/bash

DATE=$(date +"%y-%m-%d_%H%M")

libcamera-still -r --shutter 10000000 -o /home/pi-zjj/Videos/timelapse/temp.jpg
ffmpeg -i /home/pi-zjj/Videos/timelapse/temp.jpg -vf "transpose=1" /home/pi-zjj/Videos/timelapse/$DATE.jpg
