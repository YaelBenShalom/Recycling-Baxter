#!/usr/bin/env python3
"""! This node is responsible for locating and classifying the sorting objects.

Subscribes:
    /cameras/right_hand_camera - Image, Photos from the baxter hand camera. 

Publishes:
    Nothing Presently. 

Services:
    Nothing Presently.


bridge = CvBridge()
cv_image = bridge.imgmsg_to_cv2(image_message, desired_encoding='passthrough')
image_message = bridge.cv2_to_imgmsg(cv_image, encoding="passthrough")
TODO

"""

import rospy
import rospkg
import sys
import os
import numpy as np
import cv2 as cv
from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import Pose
from sensor_msgs.msg import Image, CameraInfo, CompressedImage
from can_sort.msg import Object
from can_sort.srv import Board, BoardResponse
import pyrealsense2 as rs


class Detect():
    """! A class for classifying bottles and cans for sorting by baxter.
    A holding class for the node's functions. See file level doc string for 
    more detailed information about the ROS API. 
    """
    def __init__(self):
        # Identification Paramiters
        self.can_diameter_min = 21       # [units are pixels]
        self.can_diameter_max = 26       # [units are pixels]
        self.bottle_diameter_min = 10    # [units are pixels]
        self.bottle_diameter_max = 15    # [units are pixels]

        # Object Type Definitions
        #TODO: Move these to a common library or param server.
        self.ERROR = -1
        self.BOTTLE = 0
        self.CAN = 1
        
        # Info for default image 
        self.rospack = rospkg.RosPack()
        path = self.rospack.get_path(name = 'can_sort') + '/camera_images/11.10.20/'
        self.image_directory = path
        self.image_name = "bottle_top_1.jpg"
    
        #TODO: figure oout correct commenting style 
        ##! Stores the current image. 
        self.set_default_image()
        
        #self.setup_image_stream()

    def setup_image_stream(self):
        """! Initialize the ros subscript to incomming images and CVbridges. 
        This is required for normal operations since this is how the node
        gets it's images for processing. However, during unit testing other
        means of loading images may be appropriate. 
        """
        rospy.loginfo("Setting up image stream")
        self.bridge = CvBridge()
        self.image_sub = rospy.Subscriber('/cameras/right_hand_camera', Image,
                                    self.image_callback, queue_size=1)
        self.capture = cv.VideoCapture(2)  # TODO - which camera??

    def setup_services(self):
        """! Set up the the ros services provided by this node. 
        This should be called after all other setup has been performed to
        prevent invalid service calls.
        """
        rospy.loginfo("Setting up services")
        board_service = rospy.Service('get_board_state', Board, self.get_board_state)


    def set_default_image(self):
        """! Load a default image from the local files. Used for testing. 
        """  
        # Read in the image
        self.img = cv.imread(self.image_directory + self.image_name)
        # Check the file name was right
        if self.img is None: 
            rospy.logwarn("WARNING: could not read default image")


    def image_callback(self, image_message): 
        """! Handle a new incomming image from the robot. 
        This function is responsible for processing the image into a an 
        OpenCV friendly format, and for storing it as a class variable.
         
        @param image_message, a ross Image message for processing. 
         
        """         
        rospy.logdebug("Processing incomming image")               
        try:
            cv_image = self.bridge.imgmsg_to_cv2(image_message,
                                    desired_encoding='passthrough')
        except CvBridgeError as e:
            rospy.logwarn(e)

        #TODO: store centrally or remove.
        (rows,cols,channels) = cv_image.shape


    def get_board_state(self, srv):
        """! Run object detection to produce board state from last stored image.
        Currently incomplete 
        """

        # This is just the script for testing, evertying here needs to change
        # Set local so no change during run
        img = self.img
        
        objects = [] 
        objects.extend(self.detect_cans(img))
        objects.extend(self.detect_bottles(img))
        print(objects)
        
        # # Find cans - blue
        # paint_image = self.paint_circles(img, img, (0, 0, 255), 21, 26)

        # # Find bottles - red
        # paint_image = self.paint_circles(img, paint_image, (255, 0, 0), 10, 15)

        # # Show image
        # cv.namedWindow("detected_circles", cv.WINDOW_AUTOSIZE)
        # cv.imshow("detected_circles", paint_image)
        # key = cv.waitKey(1)

        # # Press esc or 'q' to close the image window
        # if key & 0xFF == ord('q') or key == 27:
        #     cv.destroyAllWindows()

        return  BoardResponse(objects)
      

    def detect_cans(self, image):
        """! This is temporary and for testign only
        """ # TODO
        rospy.loginfo("Detecting Cans")
        circles = self.detect_circles(image, self.can_diameter_min, self.can_diameter_max)
        cans = []
        for c in circles[0]:
            can = Object()
            can.type = self.CAN
            can.sorted = False 
            can.location.x = c[0]
            can.location.y = c[1]
            can.location.z = -1 #TODO: Impliment a decent vertical offset 
            cans.append(can)
        return(cans)


    def detect_bottles(self, image):
        """! This is temporary and for testing only
        """ # TODO
        rospy.loginfo("Detecting Bottles")
        circles = self.detect_circles(image, self.bottle_diameter_min, self.bottle_diameter_max)
        rospy.loginfo(f"circles = {circles}")
        cans = []
        for c in circles[0]:
            can = Object()
            can.type = self.BOTTLE
            can.sorted = False 
            can.location.x = c[0]
            can.location.y = c[1]
            can.location.z = -1 #TODO: Impliment a decent vertical offset 
            cans.append(can)
        return(cans)


    def detect_circles(self, image, min_rad = 10, max_rad = 30):
        """! Also temporary and for testing
        """  # TODO
        # Go to greyscale   
        grey = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        ret, grey = cv.threshold(grey, 200, 255, cv.THRESH_TRUNC)

        # Blur the image
        grey = cv.medianBlur(grey, 5)
        grey = cv.GaussianBlur(grey, (5,5), 0)

        # Run the algorithm, get the circles
        rows = grey.shape[0]
        circles = cv.HoughCircles(grey, cv.HOUGH_GRADIENT, 1, rows / 16, 
                                param1 = 100, param2 = 30,
                                minRadius = min_rad, maxRadius = max_rad)
        return(circles) 


    def paint_circles(self, image, paint_image, color, min_rad, max_rad = 10):
        """! This function finds all the specified circles and paints them.
        Yep, also for testing only
        """ 
        # TODO: Commeint or delete
        
        # Go to greyscale   
        grey = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        ret, grey = cv.threshold(grey, 200, 255, cv.THRESH_TRUNC)

        # Blur the image
        grey = cv.medianBlur(grey, 5)
        grey = cv.GaussianBlur(grey, (5,5), 0)

        # Run the algorithm, get the circles
        rows = grey.shape[0]
        circles = cv.HoughCircles(grey, cv.HOUGH_GRADIENT, 1, rows / 16, 
                                param1 = 100, param2 = 30,
                                minRadius = min_rad, maxRadius = max_rad)

        # Paint the circles onto our paint image
        if circles is not None: 
                circles = np.uint16(np.around(circles))
                for i in circles[0, :]:
                    print ("circle: ", i)
                    center = (i[0], i[1])
                    cv.circle(paint_image, center, 1, (0, 100, 100), 3)
                    radius = i[2]
                    cv.circle(paint_image, center, radius, color, 3)

        return(circles, paint_image)


def main():
    """ The main() function """
    rospy.init_node('object_detection', log_level = rospy.DEBUG)
    rospy.logdebug(f"classification node started")
    detect = Detect()
    detect.setup_services()
    rospy.spin()

    cv.destroyAllWindows()


if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
