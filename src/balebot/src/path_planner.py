#!/usr/bin/env python

import numpy as np
import matplotlib.pyplot as plt
import rospy
from balebot.msg import State


DELTA = 0.15
STATE1 = None
STATE2 = None


def draw(path, label, render=True):
    # plot path
    x = [point.x for point in path]
    y = [point.y for point in path]
    plt.plot(x, y, label=label, linestyle='dashed', marker='o')

    # render graph
    if render is True:
        plt.title('State Trajectory')
        plt.xlabel('x')
        plt.ylabel('y')
        plt.legend()
        plt.show()


def polar(source_state, target_state):
    # use the source state as the reference
    x = target_state.x - source_state.x
    y = target_state.y - source_state.y
    
    # convert from Cartesian to polar coordinates
    distance = np.sqrt(np.power(x, 2) + np.power(y, 2))
    angle = np.arctan2(y, x)

    return distance, angle


def plan(initial_state, final_state, K=2, N=10):
    path = []
    
    # unpack state vectors
    xy_i = np.array([initial_state.x, initial_state.y])
    theta_i = initial_state.theta
    xy_f = np.array([final_state.x, final_state.y])
    theta_f = final_state.theta
 
    # calculate polynomial coefficients
    alpha = np.array([K * np.cos(theta_f), K * np.sin(theta_f)]) - 3 * xy_f
    beta = np.array([K * np.cos(theta_i), K * np.sin(theta_i)]) + 3 * xy_i

    # create path with N points
    for i in range(N - 1):
        s = float(i) / float(N - 1)
        point = s**3 * xy_f + s**2 * (s - 1) * alpha + s * (s - 1)**2 * beta - (s - 1)**3 * xy_i

        if i > 0:
            distance, angle = polar(path[-1], State(point[0], point[1], 0))
            heading = angle
        else:
            heading = theta_i

        path.append(State(point[0], point[1], heading))

    # force trajectory to converge
    path.append(State(0, 0, 0))

    return path


def callback1(msg):
    global STATE1
    
    STATE1 = msg


def callback2(msg):
    global STATE2
    
    STATE2 = msg


def main():
    global DELTA, STATE1, STATE2

    # initialize ROS node
    rospy.init_node('path_planner')
    
    # load data from parameter server
    try:
        robot1_config = [float(val) for val in rospy.get_param('/path_planner/robot1_config').split(',')]
        robot2_config = [float(val) for val in rospy.get_param('/path_planner/robot2_config').split(',')]
    except Exception as e:
        print("[path_planner]: could not find " + str(e) + " in parameter server")
        exit(1)

    # create ROS subscribers
    rospy.Subscriber('/state_observer/state1', State, callback1)
    rospy.Subscriber('/state_observer/state2', State, callback2)

    # create ROS publishers
    publisher1 = rospy.Publisher('/path_planner/target1', State, queue_size=1)
    publisher2 = rospy.Publisher('/path_planner/target2', State, queue_size=1)

    # wait for accurate states

    while not rospy.is_shutdown():
        if STATE1 is not None:
            break

    # estimate body frame
    #x = ((STATE1.x - robot1_config[0]) + (STATE2.x - robot2_config[0])) / 2
    #y = ((STATE1.y - robot1_config[1]) + (STATE2.y - robot2_config[1])) / 2
    #theta = (STATE1.theta + STATE2.theta) / 2
    #body_state = State(x, y, theta)

    # generate paths to target
    path = plan(STATE1, State(0, 0, 0))

    # display planned paths
    draw(path, "waypoint")

    # create a 10Hz timer
    timer = rospy.Rate(100)

    while not rospy.is_shutdown():
        # check if robot is near current waypoint
        if path:
            distance, angle = polar(STATE1, path[0])

            if distance < DELTA:
                print("[path_planner]: reached waypoint " + str(11 - len(path)))
                path.pop(0)

        # publish next waypoint
        if path:
            publisher1.publish(path[0])

        # synchronize node 
        timer.sleep()


if __name__ == '__main__':
    main()
