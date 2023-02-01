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
    with open(logfile, 'w') as logfile:
        p = subprocess.Popen(args, stdout=logfile, stderr=subprocess.STDOUT)
        p.communicate()
    time_taken = timer() - start_time
    return p.returncode, time_taken
 
def check_retcode(retcode, preamble):
    if retcode:
        raise TestFailure(preamble + " failed, return code " + str(retcode))

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
gain_max = 4
gain_upper = gain_max
gain_min = 0.5
gain_lower = gain_min

# "jpg test". See if the executable appears to run and write an jpg output file.
def still():
    print("    jpg test")
    retcode, time_taken = run_executable(['libcamera-still', '-r', '--shutter', str(conf["shutter"]), '--gain', str(conf["gain"]), '-o', 'test.jpg'], 'log.txt')
    check_retcode(retcode, "test_still: jpg test")
    retcode, time_taken = run_executable(['ffmpeg', '-y', '-i', 'test.jpg', '-vf', 'transpose=1', 'test.jpg'], 'log.txt')
    check_retcode(retcode, "ffmpeg rot test")
# check_time(time_taken, 1.2, 8, "test_still: jpg test")
# check_size(output_jpg, 1024, "test_still: jpg test")

while(True):
    still()
    frame = cv2.imread('test.jpg')
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cv2.imwrite('outgray.jpg', gray)
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    cv2.imwrite('outgrayblu.jpg', blur)
    mean = np.mean(frame, axis=(0,1))
    print(mean)
    all_mean = np.mean(frame)
    print(all_mean)

    gray_mean = np.mean(gray)
    print(gray_mean)
    gray_blur_mean = np.mean(blur)
    print(gray_blur_mean)
    # for i in range(180, 190):
    #     for j in range(360, 370):
    #         frame[i, j] = [0, 255, 0]
    # for i in range(frame.shape[0]):
    #     for j in range(frame.shape[1]):
    #         if gray[i, j] < 20:
    #             frame[i, j] = frame[i, j] * 4

    def tune_shutter(shutter, lower, upper):
        shut_rev = int(1000000 / shutter)
        if all_mean < lower:
            if shut_rev < 1:
                shut_rev /= 2
            elif shut_rev < 10:
                shut_rev -= 2
            elif shut_rev in range(10, 30):
                shut_rev -= 5
            elif shut_rev in range(30, 100):
                shut_rev -= 10
            elif shut_rev in range(100, 200):
                shut_rev -= 20
            elif shut_rev in range(200, 500):
                shut_rev -= 50
            elif shut_rev >= 500:
                shut_rev -= 100
            shutter = int(1000000 / shut_rev)
        elif all_mean > upper:
            if shut_rev < 1:
                shut_rev *= 2
            elif shut_rev < 10:
                shut_rev += 2
            elif shut_rev in range(10, 30):
                shut_rev += 5
            elif shut_rev in range(30, 100):
                shut_rev += 10
            elif shut_rev in range(100, 200):
                shut_rev += 20
            elif shut_rev in range(200, 500):
                shut_rev += 50
            elif shut_rev in range(500, 1000):
                shut_rev += 100
            shutter = int(1000000 / shut_rev)
        return shutter
    
    if all_mean < 130:
        if conf["shutter"] >= shutter_max:
            if conf["gain"] >= gain_max:
                break
            else:
                conf["gain"] *= 2
        else:
            conf["shutter"] = tune_shutter(conf["shutter"], 130, 150)
    elif all_mean > 150:
        if conf["gain"] <= gain_min:
            if conf["shutter"] <= shutter_min:
                break
            else:
                conf["shutter"] = tune_shutter(conf["shutter"], 130, 150)
        else:
            conf["gain"] /= 2
    else:
        break

conf_file = open("conf.json", "w")
conf_file.write(json.dumps(conf, indent=4, separators=(", ", ": ")))
conf_file.close()

timestamp = datetime.datetime.now()
ts = timestamp.strftime("%y-%m-%d_%H%M")
cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
    0.8, (255, 255, 255), 2)
if conf["shutter"]/1000000 >= 1:
    cv2.putText(frame, "Shutter: {}".format(str(round(conf["shutter"]/1000000))),
        (frame.shape[1] - 250, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
else:
    cv2.putText(frame, "Shutter: 1/{}".format(str(round(1000000/conf["shutter"]))),
        (frame.shape[1] - 250, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
# cv2.putText(frame, "Meter: {}".format(str(camera.meter_mode)),
#     (frame.shape[1] - 250, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
# cv2.putText(frame, "Brightness: {}".format(str(camera.brightness)),
#     (frame.shape[1] - 250, frame.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
cv2.putText(frame, "ISO: {}".format(str(conf["gain"]*100)),
    (frame.shape[1] - 250, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
# cv2.putText(frame, "Contrast: {}".format(str(camera.contrast)),
#     (frame.shape[1] - 250, frame.shape[0] - 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
# cv2.putText(frame, "AWB: r:{} b:{}".format(str(float(camera.awb_gains[0].__round__(2))), str(float(camera.awb_gains[1].__round__(2)))),
    # (frame.shape[1] - 250, frame.shape[0] - 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
# cv2.putText(frame, "hello world", (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
cv2.imwrite(ts + '.jpg', frame)
