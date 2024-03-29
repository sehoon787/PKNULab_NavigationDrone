# echo_client.py
# -*- coding:utf-8 -*-
## 파이에 카메라 연결 후 로그와 영상 정보를 Web서버로 전송
### 차후 영상은 HPC로 전송하여 HPC에서 영상처리를 한 후 영상을 다시 Koren VM Web으로 전송할 예정

import socket
from dronekit import connect, VehicleMode, LocationGlobal, LocationGlobalRelative
from pymavlink import mavutil  # Needed for command message definitions
import time
import math
import cv2
import numpy
import threading
from socket import *
import serial

client_index = 6  # the number of client. Add 1 to use path information(for Home base and to return)
locationsTo_Web = ""    # to send TSP path to Web server
land_point = "Center"
dist = 1000

latitude = []
longitude = []

## Raspberry pi setting
ser = serial.Serial("/dev/ttyS0", 115200)

# get TSP path from TSP HCP server
## not thread
def get_TSP_path():
    global locationsTo_Web
    #   To get shortest visiting path by using HPC TSP algorithm and point
    #   Client socket connection to HPC TSP Server
    msg = tsp_client_socket.recv(256)  # get message from server

    print("Connect Drone to HPC Server!")

    msg = str(msg)
    locations = msg.split('\'')
    locations = locations[1]
    locations = locations.split('\\')
    locations = locations[0]
    locationsTo_Web = locations  # Shortest path for delivery drone
    locations = locations.split('/')
    locations.pop()
    locations = list(map(float, locations))
    print("Path from server : {}".format(locations))  # print message from server

    # to make path
    i = 0
    for i in range(len(locations)):
        if i % 2 == 0:
            latitude.append(locations[i])
        else:
            longitude.append(locations[i])

    for i in range(len(latitude)):
        print('latitude[', i, '] : ', latitude[i], '\tlongitude[', i, '] : ', longitude[i])

    tsp_client_socket.close()

# get distance from obstacle to Drone by using sonar sensor
## not thread
def distance():
    global dist
    while True:

        counter = ser.in_waiting
        if counter > 8:
            bytes_serial = ser.read(9)
            ser.reset_input_buffer()

            if bytes_serial[0] == 0x59 and bytes_serial[1] == 0x59:
                dist = bytes_serial[2] + bytes_serial[3] * 256
                time.sleep(0.5)
                return dist


def drone_fly(lati, longi):
    global dist
    try:
        msgTo_webserver("(Go)Take off!")
        i = 4  # start altitude to move 4M

        msgTo_webserver("(Go)Set default/target airspeed to 3")

        msgTo_webserver("(Go)Angle Positioning and move toward")  # move to next point

        dist = 1000

        starttime = time.time()
        flytime = 0
        while flytime <= 10:

            if 100 <= dist <= 300:  # 3M
                msgTo_webserver("(GO)Detect Obstacle")

                i = i + 1
                msgTo_webserver("(GO)Up to :" + str(i))

                msgTo_webserver("(GO)Altitude : " + str(i))

                time.sleep(1)
            else:
                msgTo_webserver("(GO)Go Forward")
                # Send a new target every two seconds
                # For a complete implementation of follow me you'd want adjust this delay
                time.sleep(1)

            distance()
            if 100 <= dist <= 300:
                msgTo_webserver("(GO)Vehicle from Obstacle : " + str(dist))
            flytime = time.time() - starttime

        drone_land(lati, longi)
        time.sleep(1)

        msgTo_webserver("(Go)Close vehicle object")
        msgTo_webserver("(Go)Ready to leave to next Landing Point")
    except Exception as e:  # when socket connection failed
        print(e)
        print("EMERGENCY LAND!!")
        time.sleep(1)
        print("Close vehicle object")
    except KeyboardInterrupt:
        msgTo_webserver("EMERGENCY LAND!!")
        time.sleep(1)
        msgTo_webserver("Close vehicle object")
def drone_land(lati, longi):
    global land_point
    try:
        msgTo_webserver("(L)Setting Landing Mode!")

        msgTo_webserver("(L)Set airspeed 1m/s")

        print("Target Detect : ", land_point)
        find_point = str(land_point)

        i = 6  # current altitude

        while True:

            i = i - 1

            if i <= 1:
                msgTo_webserver("(L)Set General Landing Mode")
                time.sleep(1)
                break
            elif find_point == "Center":  # i M from Landing point
                msgTo_webserver("(L)Set Precision Landing Mode(Center)")


                msgTo_webserver("(L)Altitude: " + str(i))
                msgTo_webserver("(L)Reached target altitude")
                time.sleep(1)
            else:
                msgTo_webserver("(L)Finding Landing Point Target(Out of Target)")
                msgTo_webserver("(L)Altitude: " + str(i))
                # Send a new target every two seconds
                # For a complete implementation of follow me you'd want adjust this delay
                time.sleep(3)
    except Exception as e:  # when socket connection failed
        print(e)
        print("EMERGENCY LAND!!")
        time.sleep(1)
        print("Close vehicle object")
    except KeyboardInterrupt:
        msgTo_webserver("EMERGENCY LAND!!")
        time.sleep(1)
        msgTo_webserver("Close vehicle object")

# Using thread to connect HPC image processing server and Web server
## Thread 1
def send_To_HPCimg_server(sock):
    print("Connect to Image Processing Server")
    try:
        # to send drone cam image to HPC image processing server
        # PI camera image capture
        cam = cv2.VideoCapture(0)
        # Frame size 3 = width, 4 = height
        cam.set(3, 690);
        cam.set(4, 480);
        # image quality range : 0~100, set 90 (default = 95)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        clat = 10.1010110
        clong = 20.202202
        calt = 30.303033030

        while True:
            # get 1 frame
            # Success ret = True, Fail ret = False, frame = read frame

            ret, frame = cam.read()

            font = cv2.FONT_HERSHEY_COMPLEX

            #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            cv2.putText(frame, "Lat : " + str(clat), (20, 30), font, 0.5, (255, 255, 255), 1, cv2.LINE_4)
            cv2.putText(frame, "Long : " + str(clong), (20, 60), font, 0.5, (255, 255, 255), 1, cv2.LINE_4)
            cv2.putText(frame, "Alt : " + str(calt) + "m", (20, 90), font, 0.5, (255, 255, 255), 1, cv2.LINE_4)

            # cv2. imencode(ext, img [, params])
            # encode_param format, frame to jpg image encode
            result, frame = cv2.imencode('.jpg', frame, encode_param)
            # convert frame to String type
            data = numpy.array(frame)
            stringData = data.tobytes()

            # send data to HPC image processing server
            # (str(len(stringData))).encode().ljust(16)
            HPC_clientSocket.sendall((str(len(stringData))).encode().ljust(16) + stringData)

    except:  # when socket connection failed
        print("Socket Close!!")
        cam.release()
        HPC_clientSocket.close()
    finally:
        HPC_clientSocket.close()
## Thread 2
def recv_from_HPCimg_server(sock):
    global land_point
    while True:
        data = HPC_clientSocket.recv(1024)
        land_point = data.decode("utf-8")
        time.sleep(1)


def msgTo_webserver(msg_to_web):  # make message to HPC image processing server
    Web_clientSocket.sendall(str(msg_to_web).encode("utf-8"))
    print(str(msg_to_web))

    data = Web_clientSocket.recv(1024)
    data = data.decode("utf-8")
    print(str(data))
## Thread 3
# Move drone for TSP path and send log data to Web
def send_Logdata_toWebserver(sock):
    #   To send Drone log, video and other informations to Web Server
    #   Client socket connection to Web Server
    try:
        print("Connect Drone to Web Server!")
        msgTo_webserver(locationsTo_Web)

        num = 0  # Current Target point to send Server

        msgTo_webserver("Start to move")  # convert num to string type     send 1 to server

        # 1  start Drone delivery.    The number of point(including Home base) : 12
        while num < client_index-1:  # loop 12 times, manipulate it when you test this system
            num = num + 1     # to move first(1) point
            drone_fly(latitude[num], longitude[num])
            point = str(latitude[num]) + '/' + str(longitude[num])
            msgTo_webserver(point)
            point = "Target " + str(num) + " arrive"
            msgTo_webserver(point)
            time.sleep(1)
            msgTo_webserver("Vehicle Reconnect!")
            if num == client_index - 2:
                msgTo_webserver("Return To Base")

        time.sleep(1)
        # 2(Finish Drone delivery)
        msgTo_webserver("Completed to Delivery")
        msgTo_webserver("Finish")

        msgTo_webserver("arrive")
        Web_clientSocket.close()  # close socket connection

        ### End Drone Delivery System

    except Exception as e:  # when socket connection failed
        print(e)
        print("EMERGENCY LAND!!")
        time.sleep(1)
        print("Close vehicle object")
    except KeyboardInterrupt:
        msgTo_webserver("EMERGENCY LAND!!")
        time.sleep(1)
        msgTo_webserver("Close vehicle object")
    finally:
        Web_clientSocket.close()


if __name__=="__main__":

    # connect lidar to raspberry pi 4
    if ser.isOpen() == False:
        ser.open()

    # socket connection address and port for HPC TSP server
    # get shortest path data from HPC TSP server
    TSP_SERVER_IP = "192.168.0.6"  # HPC TSP server IP
    TSP_SERVER_PORT = 22042
    SIZE = 512
    tsp_client_socket = socket(AF_INET, SOCK_STREAM)
    tsp_client_socket.connect((TSP_SERVER_IP, TSP_SERVER_PORT))
    # to get TSP path from HPC TSP server
    get_TSP_path()
    time.sleep(10)

    ######## Start flying Drone ########

    ## HPC Image processing Server(Image)
    # send drone cam image to HPC image processing server and get landing data from HPC server
    IMG_SERVER_IP = "192.168.0.6"   # Koren VM Image Processing server IP
    IMG_SERVER_PORT = 22044    # HPC external port 22043
    HPC_clientSocket = socket(AF_INET, SOCK_STREAM)
    HPC_clientSocket.connect((IMG_SERVER_IP, IMG_SERVER_PORT))


    try:
        ## Web Server(Log)
        # send drone log(altitude, arrive point point etc..) to Web server
        Web_SERVER_IP = "192.168.0.6"  # koren SDI VM IP
        Web_SERVER_PORT = 22045
        Web_clientSocket = socket(AF_INET, SOCK_STREAM)
        Web_clientSocket.connect((Web_SERVER_IP, Web_SERVER_PORT))

        try:
            ##   Declare Thread
            # Web Server Thread
            sendLog = threading.Thread(target=send_Logdata_toWebserver, args=(Web_clientSocket,))
            # HPC Image Processing Server Thread
            sendImg = threading.Thread(target=send_To_HPCimg_server, args=(HPC_clientSocket,))
            receiver = threading.Thread(target=recv_from_HPCimg_server, args=(HPC_clientSocket,))

            ##  Start Thread
            # HPC Image Processing Server Thread
            sendImg.start()
            receiver.start()
            # Web Server Thread
            sendLog.start()


            while True:
                time.sleep(1)   # thread 간의 우선순위 관계 없이 다른 thread에게 cpu를 넘겨줌(1 일때)
                pass            # sleep(0)은 cpu 선점권을 풀지 않음
        except Exception as e:  # when socket connection failed
            print(e)
            print("EMERGENCY LAND!!")
            time.sleep(1)
            print("Close vehicle object")
            HPC_clientSocket.close()
        except KeyboardInterrupt:
            msgTo_webserver("EMERGENCY LAND!!")
            time.sleep(1)
            msgTo_webserver("Close vehicle object")
            HPC_clientSocket.close()
    except Exception as e:  # when socket connection failed
        print(e)
        print("EMERGENCY LAND!!")
        time.sleep(1)
        print("Close vehicle object")
        Web_clientSocket.close()
    except KeyboardInterrupt:
        msgTo_webserver("EMERGENCY LAND!!")
        time.sleep(1)
        msgTo_webserver("Close vehicle object")
        Web_clientSocket.close()
