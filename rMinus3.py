import os
import subprocess
import time
import yaml
import numpy as np
import anglereader
import math
from lib import vrep







ANGLES_DB_PATH = "angles.json"
DEFAULT_SPEED = 200
TIME_CONST = 0.008
CLIENT_ID = None
MOTOR_HANDLES = {}
dt = 0


darwin = {1: 90, 2: -90, 3: 67.5, 4: -67.5, 7: 45, 8: -45, 9: 'i', 10: 'i', 13: 'i', 14: 'i', 17: 'i', 18: 'i'}

PROCESS_PIPELINE = [darwin]


class DarwinVrep():
    """Class to connect to V-REP simulator"""

    def __init__(self):
        self.jointNames={1:'j_shoulder_r',2:'j_shoulder_l',3:'j_high_arm_r',4:'j_high_arm_l',5:'j_low_arm_r',
                    6:'j_low_arm_l',7:'j_pelvis_r',8:'j_pelvis_l',9:'j_thigh1_r',10:'j_thigh1_l',
                    11:'j_thigh2_r',12:'j_thigh2_l',13:'j_tibia_r',14:'j_tibia_l',15:'j_ankle1_r',
                    16:'j_ankle1_l',17:'j_ankle2_r',18:'j_ankle2_l',19:'j_pan',20:'j_tilt'}

        self.objectnames = ['MP_BODY_respondable','MP_NECK_respondable','MP_HEAD_respondable']
        self.MOTOR_HANDLES = {}
        self.OBJECT_HANDLES = []
        self.CLIENT_ID= vrep.simxStart('127.0.0.1',19999,True,True,5000,5)
        #vrep.simxPauseSimulation(self.CLIENT_ID,True)


        if CLIENT_ID!=-1:
            print "Connected to V-Rep Server"
            self.get_handles()
        else:
            print "Connection Failed"
            sys.exit()

    def get_handles(self):

        for i in range(1,21):
            e,handle = vrep.simxGetObjectHandle(self.CLIENT_ID,self.jointNames[i],vrep.simx_opmode_oneshot_wait)
            if e!=0:
                print "Error  = ",e
                exit(1)
            self.MOTOR_HANDLES[i] = handle

        for i in self.objectnames:
            e,handle = vrep.simxGetObjectHandle(self.CLIENT_ID,i,vrep.simx_opmode_oneshot_wait)
            if e!=0:
                print "Error = ",e
                exit(1)
            self.OBJECT_HANDLES.append(handle)
            
     
    def getPos(self):
            angles = {}
            for i in self.MOTOR_HANDLES.keys():
                _,angle = vrep.simxGetJointPosition(self.CLIENT_ID,self.MOTOR_HANDLES[i],vrep.simx_opmode_oneshot_wait)
                angles[i] = math.degrees(angle)
            return angles
           
    def setPos(self,writ):
        for key,val in writ.items():
            vrep.simxSetJointTargetPosition(CLIENT_ID,MOTOR_HANDLES[key],math.radians(val),vrep.simx_opmode_oneshot_wait)


    def getEuler(self):
        e,handle = vrep.simxGetObjectHandle(self.CLIENT_ID,'MP_BODY_respondable',vrep.simx_opmode_oneshot_wait)
        print handle
        _,euler = vrep.simxGetObjectOrientation(self.CLIENT_ID,handle,-1,vrep.simx_opmode_oneshot_wait)
        print euler


    def getObjPos(self):
        e,handle = vrep.simxGetObjectHandle(self.CLIENT_ID,'MP_BODY_respondable',vrep.simx_opmode_oneshot_wait)
        _,pos = vrep.simxGetObjectPosition(self.CLIENT_ID,handle,-1,vrep.simx_opmode_oneshot_wait)
        return handle,pos

    def setObjPos(self):
        e,handle = vrep.simxGetObjectHandle(self.CLIENT_ID,'MP_BODY_respondable',vrep.simx_opmode_oneshot_wait)
        vrep.simxSetObjectPosition(self.CLIENT_ID,handle,-1,[0.6,0.6,0.6],vrep.simx_opmode_oneshot_wait)




    def setEuler(self):
        e,handle = vrep.simxGetObjectHandle(self.CLIENT_ID,'MP_BODY_respondable',vrep.simx_opmode_oneshot_wait)
        vrep.simxSetObjectOrientation(self.CLIENT_ID,handle,-1,[0,0,0],vrep.simx_opmode_oneshot_wait)

    def reset(self):
        e,handle = vrep.simxGetObjectHandle(self.CLIENT_ID,'MP_BODY_respondable',vrep.simx_opmode_oneshot_wait)
        vrep.simxRemoveModel(self.CLIENT_ID,handle,vrep.simx_opmode_blocking)
        vrep.simxLoadModel(self.CLIENT_ID,'darwin.ttm',0,vrep.simx_opmode_blocking)

    def execute_motion(self,vel_sets):
        #vrep.simxPauseSimulation(self.CLIENT_ID,0)
        vrep.simxSynchronous(self.CLIENT_ID,True)
        vrep.simxStartSimulation(self.CLIENT_ID,vrep.simx_opmode_oneshot)
        for dur,vels in vel_sets:
            vrep.simxPauseCommunication(self.CLIENT_ID,1)
            for key in range(1,19):
                vrep.simxSetJointTargetVelocity(self.CLIENT_ID,self.MOTOR_HANDLES[key],vels[key],vrep.simx_opmode_oneshot)

            vrep.simxPauseCommunication(self.CLIENT_ID,0)
            time.sleep(dur)
            vrep.simxSynchronousTrigger(self.CLIENT_ID)

        vrep.simxPauseCommunication(self.CLIENT_ID,1)
        for key in range(1,19):
             vrep.simxSetJointTargetVelocity(self.CLIENT_ID,self.MOTOR_HANDLES[key],0,vrep.simx_opmode_oneshot)
        vrep.simxPauseCommunication(self.CLIENT_ID,0)
        vrep.simxSynchronousTrigger(self.CLIENT_ID)
        #vrep.simxPauseSimulation(self.CLIENT_ID,1)






class Robot(object):
    """Main Class that is used to define Robot behaviour """


    def __init__(self,motor_ids,motion_script="",control="SPEED",speed=DEFAULT_SPEED,mode="VREP"):
    
        #Initialize Ids

        if type(motor_ids) == int:
            self.ids = [x for x in range(1,motor_ids+1)]
        elif type(motor_ids) == list:
            self.ids = motor_ids
        else:
            print "ERROR: Motor IDs must be specified as a list or an integer"
            exit()

        
        if mode == "VREP":
            self.vrep_connector = DarwinVrep()

        
        #Initialize Robot Internal State
        #rospy.init_node("robot_controller",anonymous=False)
        #self.pub = rospy.Publisher('actuation',Actuation,queue_size=100)
        self.state = dict.fromkeys(self.ids,0.0)
        self.primitives = {}
        self.control = control
        self.speed = speed


        #Load Primitives from Motion Script
        try:
            with open(motion_script,"r") as file:
                motion_data = yaml.load(file)
                
            for prim in motion_data:
                self.primitives[prim] = self.load_primitive(motion_data[prim])
                

        except Exception as e:
            print "Error Parsing File"
            print e
            exit()


    def reset(self):
        self.vrep_connector.reset()


    def load_primitive(self,prim_dict):
        """Merges Pages and Flows together so that a primitive is simply a set
        of motions, where each motion consists of a frame, speed, dict of
        angles """
        
        reader = anglereader.AngleReader(ANGLES_DB_PATH)
        
        primitive_angles = []
        last_frame = 0
        frame_counter = 0

        for motion in prim_dict:
            if motion["Type"] == "Page":
                angles = reader.parse(motion["Code"])
                for angle in angles:
                    angle = list(angle)
                    angle[0] += frame_counter
                    angle[1] = self.set_speed(angle[1],motion["Speed"])
                    primitive_angles.append(angle)
                    last_frame = angle[0]
                frame_counter = last_frame + 1
            elif motion["Type"] == "Flow":
                angleset = reader.setparse(motion["Code"])
                for angles in angleset:
                    for angle in angles:
                        angle = list(angle)
                        angle[0] += frame_counter
                        angle[1] = self.set_speed(angle[1],motion["Speed"])
                        primitive_angles.append(angle)
                        last_frame = angle[0]
                    frame_counter = last_frame + 1


            else:
                raise ValueError( "ERROR : Type must be Page/Flow")


        return primitive_angles




    def set_speed(self,val,modifier):
        """Modify Speed Value according to the modifier provided"""

        if modifier[0] == "x":
            return val*float(modifier[1:])
        elif modifier[0] == "a":
            return float(modifier[1:])
        else:
            raise ValueError("Speed Modifier must start with x/a")



    def execute(self,primitive):
        """Calls corresponding compute function based on control mode"""

        if self.control == "FRAME":
            self.frame_compute(primitive)
        elif self.control == "SPEED":
            self.speed_compute(primitive)



    def frame_compute(self,primitive):
        """Creates Intermediate Frames between each frame which are to be
        executed sequentially. Motor Speed is constant"""

        motion_set = []
        init = [0,1,dict(zip(self.ids,self.state.values()))]
        motion_set.append(init)


        for prim in self.primitives[primitive]:
            prim = [prim[0],prim[1],self.process_motion(prim[2])]
            motion_set.append(prim)





        for mid in range(1,len(motion_set)):
            prev = motion_set[mid-1]
            current = motion_set[mid]
            new_set = []


            n_frames = current[0] - prev[0]
            spd_factor = current[1]

            #if n_frames < 0:
                #print current[0],prev[0]
            #print n_frames

            #print current[0],prev[0]

            prev = prev[2]
            current = current[2]
            
             
            for id in self.ids:
                lin = [round(x,2) for x in np.linspace(prev[id],current[id],n_frames)]
                new_set.append(lin)

            
            new_set = zip(*new_set)

            for n in new_set:
                self.publish_frame_motion(n)
                time.sleep(TIME_CONST/spd_factor)
                self.state = dict(zip(self.ids,n))
            
            

    def speed_compute(self,primitive):
        """Calculates target velocities and the duration to achieve motions"""
        motion_set = []
        #init = [0,1,dict(zip(self.ids,self.state.values()))]
        init = [0,1,self.vrep_connector.getPos()]
        motion_set.append(init)


        for prim in self.primitives[primitive]:
            prim = [prim[0],prim[1],self.process_motion(prim[2])]
            motion_set.append(prim)



        vel_sets = []


        for mid in range(1,len(motion_set)):
            prev = motion_set[mid-1]
            current = motion_set[mid]


            n_frames = current[0] - prev[0]
            spd_factor = current[1]
            prev = prev[2]
            current = current[2]
            self.state = current
            dur = (n_frames * TIME_CONST)/spd_factor
            dur = dur
            #print dur
            

             
            vels = {}
            for id in self.ids:
                dis = math.radians(current[id]) - math.radians(prev[id])
                vels[id] = dis/dur

            vel_sets.append((dur,vels))

        self.vrep_connector.execute_motion(vel_sets)


            

    
    def process_motion(self,motion):
        """Processes each motion_dict to apply offsets/modifiers specified in
        PROCESS_PIPELINE"""

        motion = {id:motion[id] for id in self.ids}
        
         
        for process in PROCESS_PIPELINE:
            for id in self.ids:
                if id in process:
                    val = process[id]
                    if val == "i":
                        motion[id] = -1 * motion[id]
                    else:
                        motion[id] += val

                    motion[id] = round(motion[id],2)
        
        return motion

    def publish_frame_motion(self,motion):
        pass
        #msg = Actuation()
        #msg.ids = self.ids
        #msg.speeds = [self.speed for x in self.ids]
        #msg.angles = [x for x in motion]
        #self.pub.publish(msg)


r = Robot(18,"motion_script.yaml")
vrep.simxPauseSimulation(r.vrep_connector.CLIENT_ID,1)

print("1 Sit")
print("2 Fall")
print("3 Shake Hand")
print("4 Left Kick")
print("5 Right Kick")
print("6 Walk")

m = int(raw_input("Enter Motion to Execute - "))

if m==1:
    r.execute("Sit")
if m==2:
    r.execute("Fall")
if m==3:
    r.execute("Hi")
if m==4:
    r.execute("L Kick")
if m==5:
    r.execute("R Kick")

if m==6:
    r.execute("W_Init")
    for i in range(3):
        r.execute("W_Move")

vrep.simxPauseSimulation(r.vrep_connector.CLIENT_ID,0)
raw_input("Exit?")
r.reset()
