#!/bin/bash

ffmpeg -r 24 -pattern_type glob -i "$PWD/images/*.jpg" -vf "scale=iw/2:ih/2" -vcodec libx265 -crf 28 $PWD/out/out.mp4
