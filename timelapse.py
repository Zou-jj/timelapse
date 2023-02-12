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


os.chdir(Path(__file__).parent.resolve())

conf_file = open("conf.json", "r")
conf = json.load(conf_file)
conf_file.close()

if "shutter" not in conf:
    conf["shutter"] = 1000000
shutter_max = 4000000
shutter_min = 1000
shutter_upper = shutter_max
shutter_lower = shutter_min

if "gain" not in conf:
    conf["gain"] = 1
gain_max = 16
gain_upper = gain_max
gain_min = 1
gain_lower = gain_min

mean_upper_bound = 160
mean_lower_bound = 120


def tune_iso(gain, level):
    iso = int(gain * 100)
    iso_values = [100, 200, 400, 800, 1600]
    index = iso_values.index(iso)
    if level == 0:
        return gain
    if index == 0 and level < 0:
        return gain
    if index == len(iso_values) - 1 and level > 0:
        return gain
    if index + level > len(iso_values) - 1 or index + level < 0:
        return gain
    return int(iso_values[index + level] / 100)


def tune_shutter(shutter, level):
    shutter_values = [
        1000,
        2000,
        4000,
        8000,
        16666,
        33333,
        66666,
        125000,
        250000,
        500000,
        1000000,
        2000000,
        4000000,
    ]
    index = shutter_values.index(shutter)
    if level == 0:
        return shutter
    if index == 0 and level < 0:
        return shutter
    if index == len(shutter_values) - 1 and level > 0:
        return shutter
    if index + level > len(shutter_values) - 1 or index + level < 0:
        return shutter
    return shutter_values[index + level]


def tune_param(shutter, gain, level):
    if shutter < shutter_max:
        return tune_shutter(shutter, level), gain
    else:
        if gain > gain_min:
            return shutter, tune_iso(gain, level)
        else:
            if level > 0:
                return shutter, tune_iso(gain, level)
    return tune_shutter(shutter, level), gain


out_path = "/media/pi-zjj/Seagate/timelapse/images/"
# out_path = 'test/'
check_out_path(out_path)


def still(shutter, gain, file):
    timeout = 3
    while timeout > 0:
        retcode, time_taken = run_executable(
            [
                "libcamera-still",
                "--shutter",
                str(shutter),
                "--gain",
                str(gain),
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


ref_number = 3


# "jpg test". See if the executable appears to run and write an jpg output file.
def still_all():
    print("    jpg test")
    for i in range(1, ref_number):
        bright_ref_file = "temp/bright" + str(i) + ".jpg"
        dark_ref_file = "temp/dark" + str(i) + ".jpg"
        bright_ref_shutter, bright_ref_gain = tune_param(
            conf["shutter"], conf["gain"], i
        )
        dark_ref_shutter, dark_ref_gain = tune_param(conf["shutter"], conf["gain"], -i)
        still(bright_ref_shutter, bright_ref_gain, bright_ref_file)
        still(dark_ref_shutter, dark_ref_gain, dark_ref_file)
        rot(bright_ref_file)
        rot(dark_ref_file)


def hdr(frame_ref):
    still_all()
    img_list = []
    for i in range(1, ref_number):
        dark_ref_file = "temp/dark" + str(i) + ".jpg"
        dark_ref_frame = cv2.imread(dark_ref_file)
        img_list.append(dark_ref_frame)
    img_list.append(frame_ref)
    for i in range(1, ref_number):
        bright_ref_file = "temp/bright" + str(i) + ".jpg"
        bright_ref_frame = cv2.imread(bright_ref_file)
        img_list.append(bright_ref_frame)
    merge_mertens = cv2.createMergeMertens()
    res_mertens = merge_mertens.process(img_list)
    res_mertens_8bit = np.clip(res_mertens * 255, 0, 255).astype("uint8")
    cv2.imwrite("fusion_mertens.jpg", res_mertens_8bit)
    return res_mertens_8bit


timeout_main = 10
while timeout_main > 0:
    still(conf["shutter"], conf["gain"], "temp/ref.jpg")
    rot("temp/ref.jpg")
    frame_ref = cv2.imread("temp/ref.jpg")

    gray = cv2.cvtColor(frame_ref, cv2.COLOR_BGR2GRAY)
    # cv2.imwrite('temp/outgray.jpg', gray)
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    # cv2.imwrite('temp/outgrayblu.jpg', blur)
    mean = np.mean(frame_ref, axis=(0, 1))
    print(mean)
    all_mean = np.mean(frame_ref)
    print(all_mean)
    var = np.var(gray)
    print(var)
    std = np.std(gray)
    print(std)
    gray_mean = np.mean(gray)
    print(gray_mean)
    gray_blur_mean = np.mean(blur)
    print(gray_blur_mean)

    if all_mean < mean_lower_bound:
        if conf["shutter"] >= shutter_max:
            if conf["gain"] >= gain_max:
                frame = hdr(frame_ref)
                break
            else:
                conf["shutter"], conf["gain"] = tune_param(
                    conf["shutter"], conf["gain"], 1
                )
        else:
            conf["shutter"], conf["gain"] = tune_param(conf["shutter"], conf["gain"], 1)
    elif all_mean > mean_upper_bound:
        if conf["gain"] <= gain_min:
            if conf["shutter"] <= shutter_min:
                frame = hdr(frame_ref)
                break
            else:
                conf["shutter"], conf["gain"] = tune_param(
                    conf["shutter"], conf["gain"], -1
                )
        else:
            conf["shutter"], conf["gain"] = tune_param(
                conf["shutter"], conf["gain"], -1
            )
    else:
        frame = hdr(frame_ref)
        break

    timeout_main -= 1

conf_file = open("conf.json", "w")
conf_file.write(json.dumps(conf, indent=4, separators=(", ", ": ")))
conf_file.close()

timestamp = datetime.datetime.now()
ts = timestamp.strftime("%y-%m-%d_%H%M")
cv2.putText(frame, ts, (10, frame.shape[0] - 10), 0, 0.8, (255, 255, 255), 2)
if conf["shutter"] / 1000000 >= 1:
    cv2.putText(
        frame,
        "Shutter: {}".format(str(int(conf["shutter"] / 1000000))),
        (frame.shape[1] - 250, frame.shape[0] - 10),
        0,
        0.8,
        (255, 255, 0),
        2,
    )
else:
    cv2.putText(
        frame,
        "Shutter: 1/{}".format(str(int(1000000 / conf["shutter"]))),
        (frame.shape[1] - 250, frame.shape[0] - 10),
        0,
        0.8,
        (255, 255, 0),
        2,
    )
cv2.putText(
    frame,
    "ISO: {}".format(str(conf["gain"] * 100)),
    (frame.shape[1] - 250, frame.shape[0] - 30),
    0,
    0.8,
    (255, 255, 0),
    2,
)

cv2.imwrite("temp/out.jpg", frame)
out_file = out_path + ts + ".jpg"
cv2.imwrite(out_file, frame)

while True:
    retcode, time_taken = run_executable(
        ["ffmpeg", "-y", "-i", out_file, out_file], "temp/log.txt"
    )
    if retcode == 0:
        break
