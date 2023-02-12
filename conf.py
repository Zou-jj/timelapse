import json


class Conf:
    def __init__(self):
        self.readJSON()

    def readJSON(self):
        conf_file = open("conf.json", "r")
        conf = json.load(conf_file)
        conf_file.close()
        if "shutter" not in conf:
            self.shutter = 1000000
        else:
            self.shutter = conf["shutter"]
        self.shutter_max = 4000000
        self.shutter_min = 1000
        # shutter_upper = shutter_max
        # shutter_lower = shutter_min

        if "gain" not in conf:
            self.gain = 1
        else:
            self.gain = conf["gain"]
        self.gain_max = 16
        self.gain_min = 1
        # gain_upper = gain_max
        # gain_lower = gain_min

        self.mean_upper_bound = 160
        self.mean_lower_bound = 120

        self.ref_number = 3

    def tune_iso(self, delta):
        iso = int(self.gain * 100)
        iso_values = [100, 200, 400, 800, 1600]
        index = iso_values.index(iso)
        if delta == 0:
            return 
        if index == 0 and delta < 0:
            return 
        if index == len(iso_values) - 1 and delta > 0:
            return 
        if index + delta > len(iso_values) - 1 or index + delta < 0:
            return 
        self.gain = int(iso_values[index + delta] / 100)

    def tune_shutter(self, delta):
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
        index = shutter_values.index(self.shutter)
        if delta == 0:
            return 
        if index == 0 and delta < 0:
            return 
        if index == len(shutter_values) - 1 and delta > 0:
            return 
        if index + delta > len(shutter_values) - 1 or index + delta < 0:
            return 
        self.shutter = shutter_values[index + delta]


    def tune_param(self, delta):
        if self.shutter < self.shutter_max:
            self.tune_shutter(delta)
            return
            # return tune_shutter(self.shutter, delta), self.gain
        else:
            if self.gain > self.gain_min:
                self.tune_iso(delta)
                return
                # return self.shutter, tune_iso(self.gain, delta)
            else:
                if delta > 0:
                    self.tune_iso(delta)
                    return
                    # return self.shutter, tune_iso(self.gain, delta)
        self.tune_shutter(delta)
        return
        # return tune_shutter(self.shutter, delta), self.gain

    def updateShutter(self, shutter):
        self.shutter = shutter

    def updateGain(self, gain):
        self.gain = gain

    def toJSON(self):
        conf_file = open("conf.json", "w")
        conf_file.write(json.dumps(self, default=lambda o: o.__dict__, indent=4, separators=(", ", ": ")))
        conf_file.close()
