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
        print(' '.join(args))
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

def tune_iso(gain, lower, upper):
    iso = int(gain * 100)
    if all_mean < lower:
        if iso == 0:
            iso = 100
        elif iso == 100:
            iso = 200
        elif iso == 200:
            iso = 320
        elif iso == 320:
            iso = 400
        elif iso == 400:
            iso = 500
        elif iso == 500:
            iso = 640
        elif iso == 640:
            iso = 800
        elif iso == 800:
            iso = 1600
    elif all_mean > upper:
        if iso == 100:
            iso = 0
        elif iso == 200:
            iso = 100
        elif iso == 320:
            iso = 200
        elif iso == 400:
            iso = 320
        elif iso == 500:
            iso = 400
        elif iso == 640:
            iso = 500
        elif iso == 800:
            iso = 640
        elif iso == 1600:
            iso = 800
    gain = iso / 100
    return gain

def tune_shutter(shutter, lower, upper):
    if shutter <= 1000000:
        shut_rcpl = int(1000000 / shutter)
    else:
        shut_rcpl = 1000000 / shutter
    if all_mean < lower:
        if shut_rcpl < 4:
            shut_rcpl /= 2
        elif 4 <= shut_rcpl < 10:
            shut_rcpl -= 2
        elif 10 <= shut_rcpl < 30:
            shut_rcpl -= 5
        elif 30 <= shut_rcpl < 100:
            shut_rcpl -= 10
        elif 100 <= shut_rcpl < 200:
            shut_rcpl -= 20
        elif 200 <= shut_rcpl < 500:
            shut_rcpl -= 50
        elif shut_rcpl >= 500:
            shut_rcpl -= 100
    elif all_mean > upper:
        if shut_rcpl <= 4:
            shut_rcpl *= 2
        elif 4 <= shut_rcpl < 10:
            shut_rcpl += 2
        elif 10 <= shut_rcpl < 30:
            shut_rcpl += 5
        elif 30 <= shut_rcpl < 100:
            shut_rcpl += 10
        elif 100 <= shut_rcpl < 200:
            shut_rcpl += 20
        elif 200 <= shut_rcpl < 500:
            shut_rcpl += 50
        elif 500 <= shut_rcpl < 1000:
            shut_rcpl += 100
    shutter = int(1000000 / shut_rcpl)
    return shutter

# out_path = '/media/pi-zjj/Seagate/timelapse/images/'
out_path = 'test/'
check_out_path(out_path)

def still(shutter, gain, file):
    timeout = 3
    while timeout > 0:
        retcode, time_taken = run_executable(['libcamera-still', '--shutter', str(shutter), '--gain', str(gain), '--immediate', '-o', file], 'temp/log.txt')
        if retcode == 0:
            break
        timeout -= 1

def rot(file):
    timeout = 3
    while timeout > 0:
        retcode, time_taken = run_executable(['ffmpeg', '-y', '-i', file, '-vf', 'transpose=1', file], 'temp/log.txt')
        if retcode == 0:
            break
        timeout -= 1

# "jpg test". See if the executable appears to run and write an jpg output file.
def still_all():
    print("    jpg test")
    still(conf["shutter"], conf["gain"], 'temp/temp.jpg')
    still(conf["shutter"]*2, conf["gain"], 'temp/temp_bright.jpg')
    still(conf["shutter"]*4, conf["gain"], 'temp/temp_bright2.jpg')
    still(conf["shutter"]/4, conf["gain"], 'temp/temp_dark.jpg')
    still(conf["shutter"]/16, conf["gain"], 'temp/temp_dark2.jpg')

def rot_all():
    rot('temp/temp.jpg')
    rot('temp/temp_bright.jpg')
    rot('temp/temp_bright2.jpg')
    rot('temp/temp_dark.jpg')
    rot('temp/temp_dark2.jpg')

while(True):
    still_all()
    rot_all()
    frame_normal = cv2.imread('temp/temp.jpg')
    frame_bright = cv2.imread('temp/temp_bright.jpg')
    frame_bright2 = cv2.imread('temp/temp_bright2.jpg')
    frame_dark = cv2.imread('temp/temp_dark.jpg')
    frame_dark2 = cv2.imread('temp/temp_dark2.jpg')
    img_list = [frame_dark2, frame_dark, frame_normal, frame_bright, frame_bright2]
    # exposure_times = np.array([conf["shutter"]/8, conf["shutter"], conf["shutter"]*2])
    # merge_debevec = cv2.createMergeDebevec()
    # hdr_debevec = merge_debevec.process(img_list, times=exposure_times.copy())
    # merge_robertson = cv2.createMergeRobertson()
    # hdr_robertson = merge_robertson.process(img_list, times=exposure_times.copy())
    # tonemap1 = cv2.createTonemap(gamma=2.2)
    # res_debevec = tonemap1.process(hdr_debevec.copy())
    merge_mertens = cv2.createMergeMertens()
    res_mertens = merge_mertens.process(img_list)
    # res_debevec_8bit = np.clip(res_debevec*255, 0, 255).astype('uint8')
    # res_robertson_8bit = np.clip(res_robertson*255, 0, 255).astype('uint8')
    res_mertens_8bit = np.clip(res_mertens*255, 0, 255).astype('uint8')
    # cv2.imwrite("ldr_debevec.jpg", res_debevec_8bit)
    # cv2.imwrite("ldr_robertson.jpg", res_robertson_8bit)
    cv2.imwrite("fusion_mertens.jpg", res_mertens_8bit)
    frame = res_mertens_8bit

    gray = cv2.cvtColor(frame_normal, cv2.COLOR_BGR2GRAY)
    cv2.imwrite('temp/outgray.jpg', gray)
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    cv2.imwrite('temp/outgrayblu.jpg', blur)
    mean = np.mean(frame_normal, axis=(0,1))
    print(mean)
    all_mean = np.mean(frame_normal)
    print(all_mean)
    var = np.var(gray)
    print(var)
    gray_mean = np.mean(gray)
    print(gray_mean)
    gray_blur_mean = np.mean(blur)
    print(gray_blur_mean)

    mean_upper_bound = 140
    mean_lower_bound = 120

    if all_mean < mean_lower_bound:
        if conf["shutter"] >= shutter_max:
            if conf["gain"] >= gain_max:
                break
            else:
                conf["gain"] = tune_iso(conf["gain"], mean_lower_bound, mean_upper_bound)
        else:
            conf["shutter"] = tune_shutter(conf["shutter"], mean_lower_bound, mean_upper_bound)
    elif all_mean > mean_upper_bound:
        if conf["gain"] <= gain_min:
            if conf["shutter"] <= shutter_min:
                break
            else:
                conf["shutter"] = tune_shutter(conf["shutter"], mean_lower_bound, mean_upper_bound)
        else:
            conf["gain"] = tune_iso(conf["gain"], mean_lower_bound, mean_upper_bound)
    else:
        break

conf_file = open("conf.json", "w")
conf_file.write(json.dumps(conf, indent=4, separators=(", ", ": ")))
conf_file.close()

timestamp = datetime.datetime.now()
ts = timestamp.strftime("%y-%m-%d_%H%M")
cv2.putText(frame, ts, (10, frame.shape[0] - 10), 0,
    0.8, (255, 255, 255), 2)
if conf["shutter"]/1000000 >= 1:
    cv2.putText(frame, "Shutter: {}".format(str(int(conf["shutter"]/1000000))),
        (frame.shape[1] - 250, frame.shape[0] - 10), 0, 0.8, (255, 255, 0), 2)
else:
    cv2.putText(frame, "Shutter: 1/{}".format(str(int(1000000/conf["shutter"]))),
        (frame.shape[1] - 250, frame.shape[0] - 10), 0, 0.8, (255, 255, 0), 2)
cv2.putText(frame, "ISO: {}".format(str(conf["gain"]*100)),
    (frame.shape[1] - 250, frame.shape[0] - 30), 0, 0.8, (255, 255, 0), 2)

cv2.imwrite('temp/out.jpg', frame)
out_file = out_path + ts + '.jpg'
cv2.imwrite(out_file, frame)

while True:
    retcode, time_taken = run_executable(['ffmpeg', '-y', '-i', out_file, out_file], 'temp/log.txt')
    if retcode == 0:
        break