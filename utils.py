import argparse
import json
import os
import os.path
import subprocess
import sys
from timeit import default_timer as timer
import datetime
import time
import numpy as np
import cv2
from pathlib import Path

from process import *

def run_executable(args, logfile):
    start_time = timer()
    with open(logfile, "w") as logfile:
        print(" ".join(args))
        p = subprocess.Popen(args, stdout=logfile, stderr=subprocess.STDOUT)
        p.communicate()
    time_taken = timer() - start_time
    return p.returncode, time_taken


def check_retcode(retcode, preamble):
    if retcode:
        raise TestFailure(preamble + " failed, return code " + str(retcode))


def check_out_path(out_path):
    if not os.path.isdir(out_path):
        raise TestFailure(out_path + "not exist")


class TestFailure(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def still(conf, file):
    timeout = 3
    while timeout > 0:
        retcode, time_taken = run_executable(
            [
                "libcamera-still",
                "--shutter",
                str(conf.shutter),
                "--gain",
                str(conf.gain),
                "--immediate",
                "-o",
                file,
            ],
            "temp/log.txt",
        )
        if retcode == 0:
            break
        timeout -= 1


def rot(file):
    timeout = 3
    while timeout > 0:
        retcode, time_taken = run_executable(
            ["ffmpeg", "-y", "-i", file, "-vf", "transpose=1", file], "temp/log.txt"
        )
        if retcode == 0:
            break
        timeout -= 1


# "jpg test". See if the executable appears to run and write an jpg output file.
def still_all(conf, delta):
    print("    jpg test")
    for i in range(1, conf.ref_number):
        bright_ref_file = "temp/bright" + str(i) + ".jpg"
        dark_ref_file = "temp/dark" + str(i) + ".jpg"

        conf.tune_param(i)
        still(conf, bright_ref_file)
        conf.readJSON()
        conf.tune_param(-i * delta)
        still(conf, dark_ref_file)
        conf.readJSON()
        # bright_ref_shutter, bright_ref_gain = tune_param(conf.shutter, conf.gain, i)
        # dark_ref_shutter, dark_ref_gain = tune_param(conf.shutter, conf.gain, -i)
        # still(bright_ref_shutter, bright_ref_gain, bright_ref_file)
        # still(dark_ref_shutter, dark_ref_gain, dark_ref_file)
        rot(bright_ref_file)
        rot(dark_ref_file)


def hdr(frame_ref, conf, delta):
    still_all(conf, delta)
    img_list = []
    for i in range(1, conf.ref_number):
        dark_ref_file = "temp/dark" + str(i) + ".jpg"
        dark_ref_frame = cv2.imread(dark_ref_file)
        img_list.append(dark_ref_frame)
    img_list.append(frame_ref)
    for i in range(1, conf.ref_number):
        bright_ref_file = "temp/bright" + str(i) + ".jpg"
        bright_ref_frame = cv2.imread(bright_ref_file)
        img_list.append(bright_ref_frame)
    merge_mertens = cv2.createMergeMertens()
    res_mertens = merge_mertens.process(img_list)
    res_mertens_8bit = np.clip(res_mertens * 255, 0, 255).astype("uint8")
    cv2.imwrite("fusion_mertens.jpg", res_mertens_8bit)
    return res_mertens_8bit


def main(conf, test):
    out_path = "/media/pi-zjj/Seagate/timelapse/images/"
    test_path = "test/"
    if not test:
        check_out_path(out_path)

    timeout_main = 10
    while timeout_main > 0:
        ref_file = "temp/ref.jpg"
        still(conf, ref_file)
        rot(ref_file)
        process = Process()
        process.summary(ref_file, False)

        if process.all_mean < conf.mean_lower_bound:
            if conf.shutter >= conf.shutter_max:
                if conf.gain >= conf.gain_max:
                    conf.toJSON()
                    frame = hdr(process.frame_ref, conf, process.getDelta())
                    break
                else:
                    conf.tune_param(1)
                    # conf.shutter, conf.gain = tune_param(conf.shutter, conf.gain, 1)
            else:
                conf.tune_param(1)
                # conf.shutter, conf.gain = tune_param(conf.shutter, conf.gain, 1)
        elif process.all_mean > conf.mean_upper_bound:
            if conf.gain <= conf.gain_min:
                if conf.shutter <= conf.shutter_min:
                    conf.toJSON()
                    frame = hdr(process.frame_ref, conf, process.getDelta())
                    break
                else:
                    conf.tune_param(-1)
                    # conf.shutter, conf.gain = tune_param(conf.shutter, conf.gain, -1)
            else:
                conf.tune_param(-1)
                # conf.shutter, conf.gain = tune_param(conf.shutter, conf.gain, -1)
        else:
            conf.toJSON()
            frame = hdr(process.frame_ref, conf, process.getDelta())
            break

        timeout_main -= 1

    timestamp = datetime.datetime.now()
    ts = timestamp.strftime("%y-%m-%d_%H%M")
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), 0, 0.8, (255, 255, 255), 2)
    if conf.shutter / 1000000 >= 1:
        cv2.putText(
            frame,
            "Shutter: {}".format(str(int(conf.shutter / 1000000))),
            (frame.shape[1] - 250, frame.shape[0] - 10),
            0,
            0.8,
            (255, 255, 0),
            2,
        )
    else:
        cv2.putText(
            frame,
            "Shutter: 1/{}".format(str(int(1000000 / conf.shutter))),
            (frame.shape[1] - 250, frame.shape[0] - 10),
            0,
            0.8,
            (255, 255, 0),
            2,
        )
    cv2.putText(
        frame,
        "ISO: {}".format(str(conf.gain * 100)),
        (frame.shape[1] - 250, frame.shape[0] - 30),
        0,
        0.8,
        (255, 255, 0),
        2,
    )

    cv2.imwrite("temp/out.jpg", frame)
    if not test:
        out_file = out_path + ts + ".jpg"
    else:
        out_file = test_path + ts + ".jpg"
    cv2.imwrite(out_file, frame)

    while True:
        retcode, time_taken = run_executable(
            ["ffmpeg", "-y", "-i", out_file, out_file], "temp/log.txt"
        )
        if retcode == 0:
            break
    
    process.summary(out_file, True)
