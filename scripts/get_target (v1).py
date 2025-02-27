#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import rospy
from fusion.msg import cone_pos
from fusion.msg import cone_pos_whole
import sympy
import math
FORWARD_DISTANCE = 2.0
TRANSLATION_DISTANCE = 1.5
CRITICAL_VALUE = 3.0

def coordination_transformation1(point):
    tmp = point[0]
    point[0] = -point[1]
    point[1] = tmp
    return point

def coordination_transformation2(point):
    tmp = point[0]
    point[0] = point[1]
    point[1] = -tmp
    return point

def medLine(x1,y1,x2,y2): # Ax+By+C=0
    A = 2*(x2 - x1)
    B = 2*(y2 - y1)
    C = x1**2 - x2**2 + y1**2 -y2**2
    return A,B,C

def two_points_getaline(x1,y1,x2,y2):
    if x2==x1:
        A = 0
        B = 1
        C = x1
    else:
        k = (y2-y1)/(x2-x1)
        b = y1 - k*x1
        A = k
        B = -1
        C = b
    return A,B,C

def to_float(target):
    target_str = str(target)
    idx = target_str.find('x:')
    idy = target_str.find('y:')
    idx_stop = target_str.find(',')
    idy_stop = target_str.find('}')
    subx = target_str[idx+2:idx_stop]
    suby = target_str[idy+2:idy_stop]
    x = float(subx)
    y = float(suby) 
    #print x
    #print y
    return x,y

def get_the_point(points): #points is a list
    point1 = list(points[0])
    point2 = list(points[1])
    if point1[0] >= 0:
        return point1
    else :
        return point2

def get_target(cone_whole):
    '''
    #Requires: the input cone_whole is an array of cone_pos objects,
    #          which contains the x,y and color of a detected cone
    #Effects:  get the navigation target for the autonomous car based
    #          on given detected cones. The output target_points is 
    #          the x,y coordinate of the target.only
    #Note:     the positions of the cones and the target are under
    #          the autonomous car's local coordinate system
    '''
    lane_left = []
    lane_right = []
    for cone in cone_whole:
        cone_list = [cone.x,cone.y]
        coordination_transformation1(cone_list)
	if cone.color == 'r':
            lane_left.append(cone)
        elif cone.color == 'b':
            lane_right.append(cone)

    if len(lane_left) >= len(lane_right):
        major_lane = lane_left
        secondary_lane = lane_right
        major_lane_color = 'r'
    else:
        major_lane = lane_right
        secondary_lane = lane_left
        major_lane_color = 'b'


    if len(major_lane) >= 2:
        A,B,C = two_points_getaline(major_lane[0].x , major_lane[0].y , major_lane[1].x , major_lane[1].y)
        k = TRANSLATION_DISTANCE/math.sqrt(A**2+B**2)
        if major_lane_color == 'r':
            C = C-A*k*A-B*k*B
        else:
            C = C+A*k*A+B*k*B    
        x,y = sympy.symbols("x y")
        target_point_solve = sympy.solve([A*x+B*y+C, x**2+y**2-FORWARD_DISTANCE**2],[x,y])
        target_point1 = get_the_point(target_point_solve)
        return target_point1
        #target_point = list(to_float(target_point1))
        #return coordination_transformation2(target_point)
    elif len(major_lane) == 1:
        if len(secondary_lane) == 1:
            if math.sqrt((major_lane[0].x-secondary_lane[0].x)**2 + (major_lane[0].y-secondary_lane[0].y)**2) > CRITICAL_VALUE:
                return -1,0 
            A,B,C = medLine(major_lane[0].x , major_lane[0].y , secondary_lane[0].x , secondary_lane[0].y)
            x,y = sympy.symbols("x y")
            target_point_solve = sympy.solve([A*x+B*y+C, x**2+y**2-FORWARD_DISTANCE**2],[x,y])
            target_point1 = get_the_point(target_point_solve)
            return target_point1
            #target_point = list(to_float(target_point1))
            #return coordination_transformation2(target_point)
        else: #only one point
            return -1, 0
    else:
        return  0, 0

