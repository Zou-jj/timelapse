#!/bin/bash

ffmpeg -r 10 -pattern_type glob -i "/home/pi-zjj/Videos/timelapse/*.jpg" -vcodec libx264 /home/pi-zjj/Videos/output/out.mp4
