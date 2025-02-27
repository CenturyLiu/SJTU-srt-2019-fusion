#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import absolute_import, division, print_function
import os
import sys
import cv2
import numpy as np
import h5py

import rospy
from std_msgs.msg import Bool
from std_msgs.msg import Float32MultiArray
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from saved_model_predictor_DL import SavedModelPredictor

class sjtu_detection:  
    def __init__(self):
        currentpath, _ = os.path.split(os.path.abspath(sys.argv[0]))
        self.modelpath = currentpath
        self.prob_threshold = 0.6
        self.nms_iou_threshold = 0.3
        #self.predict_fn = tf.contrib.predictor.from_saved_model(self.modelpath, signature_def_key='predict_object')
        self.predict_fn = SavedModelPredictor(self.modelpath, signature_def_key='predict_object')
        with h5py.File(os.path.join(self.modelpath, 'index'), 'r') as h5f:
            self.labels_list = h5f['labels_list'][:]
        #self.labels_list = ["red", "off", "green", "yellow"]

    def predict(self, img):
        img = img[np.newaxis, :, :, :]
        output = self.predict_fn({'images':img})        
        num_boxes = len(output['detection_classes'])
        classes = []
        boxes = []
        scores = []
        result_return = dict()
        for i in range(num_boxes):
            if output['detection_scores'][i] > self.prob_threshold:
                class_id = output['detection_classes'][i] - 1
                classes.append(self.labels_list[int(class_id)])
                boxes.append(output['detection_boxes'][i])
                scores.append(output['detection_scores'][i])
        ##########add NMS#######################################
        bounding_boxes = boxes
        confidence_score = scores
        # Bounding boxes
        boxes = np.array(bounding_boxes)
        picked_boxes = []
        picked_score = []
        picked_classes = []
        if len(boxes) != 0:
            # coordinates of bounding boxes
            start_x = boxes[:, 0]
            start_y = boxes[:, 1]
            end_x = boxes[:, 2]
            end_y = boxes[:, 3]
            # Confidence scores of bounding boxes
            score = np.array(confidence_score)
            # Picked bounding boxes
            # # Compute areas of bounding boxes
            areas = (end_x - start_x + 1) * (end_y - start_y + 1)
            # Sort by confidence score of bounding boxes
            order = np.argsort(score)
            # Iterate bounding boxes
            while order.size > 0:
                # The index of largest confidence score
                index = order[-1]
                # Pick the bounding box with largest confidence score
                picked_boxes.append(bounding_boxes[index])
                picked_score.append(confidence_score[index])
                picked_classes.append(classes[index])
                # Compute ordinates of intersection-over-union(IOU) 
                x1 = np.maximum(start_x[index], start_x[order[:-1]])
                x2 = np.minimum(end_x[index], end_x[order[:-1]])                
                y1 = np.maximum(start_y[index], start_y[order[:-1]])
                y2 = np.minimum(end_y[index], end_y[order[:-1]])
                # Compute areas of intersection-over-union
                w = np.maximum(0.0, x2 - x1 + 1)
                h = np.maximum(0.0, y2 - y1 + 1)
                intersection = w * h
                # Compute the ratio between intersection and union
                ratio = intersection / (areas[index] + areas[order[:-1]] - intersection)
                left = np.where(ratio < self.nms_iou_threshold) 
                order = order[left]
        
        result_return['detection_classes'] = picked_classes
        result_return['detection_boxes'] = picked_boxes
        result_return['detection_scores'] = picked_score
        return result_return

    def visualize(self, img, result):
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        detection_classes = result['detection_classes']
        detection_boxes = result['detection_boxes']
        detection_scores = result['detection_scores']
        center = []
        if detection_boxes:
            for i in range(len(detection_boxes)):
                start_x = detection_boxes[i][0]
                start_y = detection_boxes[i][1]
                end_x = detection_boxes[i][2]
                end_y = detection_boxes[i][3]
                detection_class = detection_classes[i].decode('utf-8')
                detection_score = detection_scores[i]
                cv2.rectangle(img, (start_y, start_x), (end_y, end_x), (0, 0, 255), 3)
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(img, detection_class+str(detection_score), (start_y, start_x), font, 1, (0, 0, 255), 2)
                center = [(start_y + end_y) // 2, (start_x + end_x) // 2]
                size = end_y - start_y
                #size = np.sqrt((end_x - start_x) * (end_x - start_x) + (end_y - start_y) * (end_y - start_y))
                center.append(size)
                '''
                print("\n\ncenter:")
                print(center)
                
                print("\nsize:")
                print(size)
                '''
        return img, center


class followMeDetector:
    def __init__(self):
        self.has_follow_me = Bool()
        self.cvb = CvBridge()
        self.follow_pub = rospy.Publisher('has_follow_me', Bool, queue_size=1)
        self.follow_where = rospy.Publisher('follow_where', Float32MultiArray, queue_size=1)
        self.detector = sjtu_detection()
        self.center = Float32MultiArray()
        rospy.Subscriber('images', Image, self.callback)
        rospy.init_node('follow_me_detection', anonymous=True)

    def callback(self, imgmsg):
        img = self.cvb.imgmsg_to_cv2(imgmsg)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        output = self.detector.predict(img)
        outimg, self.center.data = self.detector.visualize(img, output)
        self.has_follow_me = False
        #self.center = [640., 360., 300.]
        for detection_class in output['detection_classes']:
            detection_class = detection_class.decode('utf-8')
            if detection_class == "follow":
                self.has_follow_me = True
        self.follow_pub.publish(self.has_follow_me)
        self.follow_where.publish(self.center)
        cv2.imshow("follow_sign", outimg)
        cv2.waitKey(1)
if __name__ == "__main__":
    try:
        detector = followMeDetector()
        rospy.spin()
    except rospy.ROSInterruptException:
        cv2.destroyAllWindows()
    
