import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import math


class Process:
    def summary(self, file, plot):
        self.frame_ref = cv2.imread(file)
        gray = cv2.cvtColor(self.frame_ref, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (21, 21), 0)
        self.mean = np.mean(self.frame_ref, axis=(0, 1))
        print("mean: r %f, g %f, b %f" % (self.mean[0], self.mean[1], self.mean[2]))
        self.all_mean = np.mean(self.frame_ref)
        print("all_mean: %f" % self.all_mean)
        self.var = np.var(gray)
        print("var: %f" % self.var)
        self.std = np.std(gray)
        print("std: %f" % self.std)
        self.gray_mean = np.mean(gray)
        print("gray_mean: %f" % self.gray_mean)
        self.gray_blur_mean = np.mean(blur)
        print("gray_blur_mean: %f" % self.gray_blur_mean)

        # Define the threshold for over-exposure
        self.threshold = 250

        # Count the number of over-exposed pixels
        self.num_over_exposed = np.sum(gray > self.threshold)

        # Calculate the total number of pixels in the image
        self.total_pixels = gray.shape[0] * gray.shape[1]

        # Calculate the percentage of over-exposed pixels
        self.percentage = 100.0 * self.num_over_exposed / self.total_pixels

        # num_over_exposed = np.sum(mask)
        print("Pixels > %d: %d, %f" % (self.threshold, self.num_over_exposed, self.percentage))

        if plot:
            # Compute the color histograms for each channel
            color = ("b", "g", "r")
            for i, col in enumerate(color):
                histr = cv2.calcHist([self.frame_ref], [i], None, [256], [0, 256])
                plt.plot(histr, color=col)
                plt.xlim([0, 256])

            # Compute the grayscale histogram
            hist_gray = cv2.calcHist([gray], [0], None, [256], [0, 256])
            plt.plot(hist_gray, color="gray", label="gray")

            # Display the plot
            plt.show()
            fname = Path("figs", "hist.jpg")
            plt.savefig(fname)
            print("\nFigure saved as '%s'" % fname)

    
    def getDelta(self):
        return math.ceil(self.percentage / 10.0)
