import rospy
import cv2
import numpy as np
from math import nan
from sensor_msgs.msg import Image, CameraInfo
from geometry_msgs.msg import PointStamped, Point
from cv_bridge import CvBridge
from clover import long_callback, srv
import tf2_ros
import tf2_geometry_msgs
import image_geometry
import cv2
import numpy as np
import math
import rospy
from clover import srv
from std_srvs.srv import Trigger
import time
from clover.srv import SetLEDEffect

rospy.init_node('cv', disable_signals=True) # disable signals to allow interrupting with ctrl+c


get_telemetry = rospy.ServiceProxy('get_telemetry', srv.GetTelemetry)
navigate = rospy.ServiceProxy('navigate', srv.Navigate)
navigate_global = rospy.ServiceProxy('navigate_global', srv.NavigateGlobal)
set_position = rospy.ServiceProxy('set_position', srv.SetPosition)
set_velocity = rospy.ServiceProxy('set_velocity', srv.SetVelocity)
set_attitude = rospy.ServiceProxy('set_attitude', srv.SetAttitude)
set_rates = rospy.ServiceProxy('set_rates', srv.SetRates)
land = rospy.ServiceProxy('land', Trigger)
get_telemetry = rospy.ServiceProxy('get_telemetry', srv.GetTelemetry)
set_position = rospy.ServiceProxy('set_position', srv.SetPosition)
set_effect = rospy.ServiceProxy('led/set_effect', SetLEDEffect)

bridge = CvBridge()

tf_buffer = tf2_ros.Buffer()
tf_listener = tf2_ros.TransformListener(tf_buffer)

mask_pub = rospy.Publisher('~mask', Image, queue_size=1)
point_pub = rospy.Publisher('~red_circle', PointStamped, queue_size=1)

camera_model = image_geometry.PinholeCameraModel()
camera_model.fromCameraInfo(rospy.wait_for_message('main_camera/camera_info', CameraInfo))



def img_xy_to_point(xy, dist):
    xy_rect = camera_model.rectifyPoint(xy)
    ray = camera_model.projectPixelTo3dRay(xy_rect)
    return Point(x=ray[0] * dist, y=ray[1] * dist, z=dist)

def get_center_of_mass(mask):
    M = cv2.moments(mask)
    if M['m00'] == 0:
        return None
    return M['m10'] // M['m00'], M['m01'] // M['m00']

follow_red_circle = False

@long_callback
def image_callback(msg):
    img = bridge.imgmsg_to_cv2(msg, 'bgr8')
    img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # we need to use two ranges for red color
    mask = cv2.inRange(img_hsv, (109, 0, 0), (255, 255, 255))

    (contours, _) = cv2.findContours(mask, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    # we need to use two ranges for red color

    for cnt in contours:
        moment = cv2.moments(cnt)
        if moment['m00'] > 0:
            cx = int(moment['m10'] / moment['m00'])
            cy = int(moment['m01'] / moment['m00'])
            shape = 'chelovek'
            cv2.drawContours(img, [cnt], -1, (0, 255, 0), 2)
            cv2.putText(img, shape, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0,0),2)  #Putting name of polygon along with the shape 
        
    # publish the mask
    if mask_pub.get_num_connections() > 0:
        mask_pub.publish(bridge.cv2_to_imgmsg(img, 'bgr8'))

    # calculate x and y of the circle
    xy = get_center_of_mass(mask)
    if xy is None:
        return

    # calculate and publish the position of the circle in 3D space
    altitude = get_telemetry('terrain').z
    xy3d = img_xy_to_point(xy, altitude)
    target = PointStamped(header=msg.header, point=xy3d)
    point_pub.publish(target)

    if follow_red_circle:
        # follow the target
        setpoint = tf_buffer.transform(target, 'aruco_map', timeout=rospy.Duration(0.2))
        set_position(x=setpoint.point.x, y=setpoint.point.y, z=nan, yaw=nan, frame_id=setpoint.header.frame_id) 

image_sub = rospy.Subscriber('main_camera/image_raw', Image, image_callback, queue_size=1)
def navigate_wait(x=0, y=0, z=1, yaw=math.nan, speed=0.5, frame_id='aruco_map', tolerance=0.2, auto_arm=False):
    res = navigate(x=x, y=y, z=z, yaw=yaw, speed=speed, frame_id=frame_id, auto_arm=auto_arm)

    if not res.success:
        return res

    while not rospy.is_shutdown():
        telem = get_telemetry(frame_id='navigate_target')
        if math.sqrt(telem.x ** 2 + telem.y ** 2 + telem.z ** 2) < tolerance:
            return res
        rospy.sleep(0.2)


set_effect(r=0, g=255, b=0)
navigate_wait(z=1, frame_id='body', auto_arm=True)
set_effect(effect='blink', r=255, g=255, b=0) 
navigate_wait(x=2, y=2)
follow_red_circle = True
set_effect(effect='blink', r=255, g=255, b=255) 
time.sleep(5)
set_effect(effect='blink', r=255, g=0, b=0)
follow_red_circle = False
navigate_wait(x=0, y=0)
rospy.sleep(5)
set_effect( r=255, g=255, b=0) 
print('Land')
land()
rospy.spin()
