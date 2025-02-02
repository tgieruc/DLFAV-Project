import sys, os

sys.path.insert(0, os.path.join(os.path.abspath(''), "YOLOX"))

import cv2
import imutils
import time
import numpy as np

from tracker import Tracker
from pose_detector import PoseDetector
from sequence_detector import SequenceDetector
from pose_tracker import PoseTracker
from upscale import Upscaler


class Detector(object):
    """docstring for Detector"""

    def __init__(self):
        self.tracker = Tracker('person')
        self.pose_detector = PoseDetector(n_feature=8, n_output=3,
                                          checkpoint_path="pose_classification_simplified.ckpt", simple_mode=True,
                                          model_based=False)
        self.sequence_detector = SequenceDetector([1], 10)
        self.pose_tracker = PoseTracker(self.pose_detector, self.sequence_detector,
                                        self.tracker)
        self.upscaler = Upscaler(model_choice="realesrgan_s", enhance_face=False)

        self.poi = None
        self.state = "FIND_POI"
        self.poi_found = False
        self.last_detected = time.time()


    def forward(self, im):
        im = np.array(im)

        # Image preprocessing
        # im = self.upscaler.enhance(im)
        im = imutils.resize(im, height=640, inter=cv2.INTER_BITS2)
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        im = cv2.filter2D(im, -1, kernel)

        if self.state == "FIND_POI":
            outputs, self.poi = self.pose_tracker.update(im)
            pose_in_progress = False
            for i, p in self.pose_tracker.sequence_detector.people.items():
                if (p.i_seq > 0) and (i != self.poi):
                    pose_in_progress = True
                    break
            if (self.poi != None) and (not pose_in_progress):
                self.last_detected = time.time()
                self.state = "TRACK_POI"
        if self.state == "TRACK_POI":
            check_poi = 0
            outputs = np.array(self.pose_tracker.tracker.update(im))
            for i in range(outputs.shape[0]):
                if outputs[i, 4] == self.poi:
                    check_poi = 1
            if (check_poi == 0) or (time.time() - self.last_detected > 1):
                self.state = "FIND_POI"


        # # POI detection
        # if self.state == "FIND_POI":
        #     self.last_detected = time.time()
        #     pred_y_box, self.poi = self.pose_tracker.update(im)
        #     if self.poi != None:
        #         self.state = "TRACK_POI"
        #
        # # POI tracking
        # if self.state == "TRACK_POI":
        #     self.poi_found = False
        #     outputs = np.array(self.tracker.update(im))
        #
        #     for i in range(outputs.shape[0]):
        #         if outputs[i, 4] == self.poi:
        #             self.poi_found = True
        #
        #     if not self.poi_found:
        #         self.state = "FIND_POI"
        #         self.poi = None
        #
        #     if time.time() - self.last_detected > 1:
        #         self.last_detected = time.time()
        #         print("recheck")
        #         pred_y_box, self.poi = self.pose_tracker.update(im)
        if self.poi is not None and outputs.ndim == 2:
            output = outputs[np.argwhere(outputs[:, 4] == self.poi)].flatten()
            if output.shape[0] == 5:
                return 120 / 640 * self._reformat_output(output), [1.0]
            else:
                return np.zeros(4), [0]
        else:
            return np.zeros(4), [0]

    def _reformat_output(self, output):
        return np.array(
            [(output[0] + output[2]) / 2, output[1] + output[3] / 3])
