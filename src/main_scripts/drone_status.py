#!/usr/bin/env python3
from sys import path_hooks
import rospy
import time
import numpy as np
from geometry_msgs.msg import *
from std_msgs.msg import Float32, Float32MultiArray, String, Bool
import os
#from termcolor import colored

#Drone Status Node
#Prints in terminal everything to monitor the drone movement
#Calculates each motors RPM for ML trainning.

#Author: Salomón Granada Ulloque
#Email: s.granada@uniandes.edu.co

pos_x, pos_y, pos_z, ang_x, ang_y, ang_z, rho, pathTime, endPos_x, endPos_y, endPos_z = 0,0,0,0,0,0,0,0,0,0,0

simTime, realTime = 0, 0

force, torque, tankMass, tankVolume, velocity = [],0,0,' ',0

restartTank = False
path_vel, route_num = 0,0

#Real-time drone position callback
def dronePose_callback(msg):
    global pos_x, pos_y, pos_z
    #_,pos=sim.simxGetObjectPosition(clientID, Quadricopter_base, -1, sim.simx_opmode_blocking)
    pos_x = msg.data[0]
    pos_y = msg.data[1]
    pos_z = msg.data[2]
    return pos_x, pos_y, pos_z

#Real-time drone orientation callback
def droneOrientation_callback(msg):
    global ang_x, ang_y, ang_z
    #_, orientation = sim.simxGetObjectOrientation(clientID,Quadricopter_base,-1,sim.simx_opmode_blocking)
    ang_x = msg.data[0]
    ang_y = msg.data[1]
    ang_z = msg.data[2]
    return ang_x, ang_y, ang_z

#Estructure : [rho, pathTime, EndPos, path_vel, route No.]
def status_callback(msg):
	global rho, pathTime, endPos_x, endPos_y, endPos_z, path_vel, route_num
	
	rho =  msg.data[0]
	pathTime = msg.data[1]
	endPos_x, endPos_y, endPos_z = msg.data[2], msg.data[3], msg.data[4]
	path_vel = msg.data[5]
	route_num = msg.data[6]

#Estructure : [delta_realTime, delta_simTime]
def times_callback(msg):
	global simTime, realTime
	realTime = msg.data[0]
	simTime = msg.data[1]

def force_callback(msg):
    global force
    force = [msg.data[0],msg.data[1],msg.data[2],msg.data[3]]

def torque_callback(msg):
    global torque
    torque = [msg.data[0],msg.data[1],msg.data[2],msg.data[3]]

def tankMass_callback(msg):
    global tankMass
    tankMass = msg.data/1000

def velocity_callback(msg):
	global velocity
	feedback_vel_x = msg.data[0]
	feedback_vel_y = msg.data[1]
	
	velocity = np.sqrt(feedback_vel_x**2 + feedback_vel_y**2)

def tankVolume_callback(msg):
	global tankVolume
	tankVolume = msg.data

def callback_restart(msg):
	global restartTank
	restartTank = msg.data

#Prints into terminal all information requiered for monitoring the drone.
#Also writes into file forces, torques and RPMs for ML model further trainning.
def info_status():
	global pos_x, pos_y, pos_z, ang_x, ang_y, ang_z, rho, pathTime,  endPos_x, endPos_y, endPos_z
	global simTime, realTime, force, torque, tankMass, tankVolume, velocity, restartTank, path_vel, route_num

	rospy.init_node('Status_Node', anonymous=True)  # Inicia el nodo status

	#Subscripcion a topicos
	rospy.Subscriber("/force", Float32MultiArray, force_callback, tcp_nodelay=True)
	rospy.Subscriber("/torque", Float32MultiArray, torque_callback, tcp_nodelay=True)
	rospy.Subscriber('/velocity', Float32MultiArray, velocity_callback, tcp_nodelay=True)
	rospy.Subscriber("/currentMass", Float32, tankMass_callback, tcp_nodelay=True)
	rospy.Subscriber('/PE/Drone/tank_volume', String, tankVolume_callback)
	rospy.Subscriber("/drone_pose", Float32MultiArray, dronePose_callback, tcp_nodelay=True)
	rospy.Subscriber("/drone_orientation", Float32MultiArray, droneOrientation_callback, tcp_nodelay=True)

	#Estructure : [rho, pathTime, Endpos, path_vel, route No.]
	rospy.Subscriber("/PE/Drone/drone_status", Float32MultiArray, status_callback, tcp_nodelay=True)
	#Estructure : [delta_realTime, delta_simTime]
	rospy.Subscriber("PE/Drone/controller_time", Float32MultiArray, times_callback, tcp_nodelay=True)
	rospy.Subscriber('/PE/Drone/restart', Bool, callback_restart)
	rate = rospy.Rate(10)

	rpm = 0
	rpm_list = [0,0,0,0]
	scriptDir = os.path.dirname(__file__)
	flight_data = scriptDir +'/' + "flight_data.txt"
	f = open(flight_data, "w")

	while not rospy.is_shutdown():

		#RPM for each motor calculation. 
		c = 0.6
		e_d = 0.88 #diameter effectiveness
		theta = 25 #blade twist angle (deg)
		p = 1.225 #air density kg/m^3
		R = (1.4974e-01)/2 #blade radio
		k = 2*c/4*R #Motor-propeller Force Constant
		C_T = (4/3)*k*theta*(1-(1-e_d)**3) - k*(np.sqrt(k*(k+1))- np.sqrt(k))*(1-(1-e_d)**2)

		#T = (1/16)*p*np.pi*(R**4)*(e_d**4)*C_T*(rpm**2)

		#For each of the motors calculates its RPM depending on the exerted force.
		for motor in range(len(force)):
			#print('motor #',motor)
			#print('force #',force[motor])
			rpm = np.sqrt(abs(force[motor])/((1/16)*p*np.pi*(R**4)*(e_d**4)*C_T))
			rpm_list[motor] = rpm

		#Builds printed message in terminal
		mensaje = '_________________________________________________________ \n \n'
		mensaje = mensaje + 'Pose Actual: ' + str(round(pos_x,4)) + ', ' + str(round(pos_y,4)) + ', ' + str(round(pos_z,4)) + ' Angulo Actual: ' + str(round(ang_x,3)) + ', ' + str(round(ang_y,3)) + ', ' + str(round(ang_z,3)) + '\n'
		mensaje = mensaje + 'Pose Final: ' + str(round(endPos_x,3)) + ', ' + str(round(endPos_y,3)) + ', ' + str(round(endPos_z,3)) + '   Path Vel: '+str(path_vel) + '\n'
		mensaje = mensaje + '\n'
		mensaje = mensaje + 'Rho: ' + str(round(rho,3)) + '  Route num: '+ str(route_num) +'\n'
		mensaje = mensaje + '\n'
		mensaje = mensaje + 'Motor Forces: ' + str(force) + '\n \n'#+ str(round(force[0],3)) + ', '+ str(round(force[1],3))+ ', '+ str(round(force[2],3))+ ', '+ str(round(force[2],3))+ '\n'
		mensaje = mensaje + 'Motor Torque: ' + str(torque) + '\n \n'
		mensaje = mensaje + 'Motor RPM: ' + str(rpm_list) + '\n \n'
		mensaje = mensaje + 'Tank Mass: ' + str(round(tankMass,3)) + ' Kg, Tank Volume: ' + tankVolume + ' Tank Restart: ' + str(restartTank) +'\n'
		mensaje = mensaje + '\n'
		mensaje = mensaje + 'RealTime: ' + str(round(realTime,4)) +' simTime: ' + str(round(simTime,4)) + ' PathTime: ' + str(round(pathTime,3))
		mensaje = mensaje + '\n \n'

		#Only print if the tank mass calculation is actually working.
		if tankMass == 0:
			print('tankMass == 0, program wont start')
		elif tankMass == 'nan':
			print('tankMass == nan, ERROR!')
		else:
			print(mensaje)
			f.write(str(route_num) + '|' + str(force) +'|'+ str(torque)  +'|'+ str(rpm_list)+ '\n')
	
		time.sleep(1)
	f.close()
	

if __name__== '__main__':
	try:
		info_status()
	except rospy.ROSInterruptException:
		print('Nodo detenido')