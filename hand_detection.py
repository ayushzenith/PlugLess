import datetime
from shutil import move
import mediapipe as mp
import datetime
import cv2
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

calibrate = True
prevCoords = []
calibratedCoords = []
buttonPressCounter = 0

class Controller:
	def __init__(self):
		self.left_trigger = 0
		self.left_bumper = 0
		self.right_trigger = 0
		self.right_bumper = 0
		self.joystick = 0
		self.Abutton = 0
	def __add__(self, other):
		ret = Controller()
		ret.left_trigger = self.left_trigger + other.left_trigger
		ret.left_bumper = self.left_bumper + other.left_bumper
		ret.right_trigger = self.right_trigger + other.right_trigger
		ret.right_bumper = self.right_bumper + other.right_bumper
		ret.joystick = self.joystick + other.joystick
		ret.Abutton = self.Abutton + other.Abutton
		return ret
	def __truediv__(self, other):
		ret = Controller()
		ret.left_trigger = self.left_trigger / other
		ret.left_bumper = self.left_bumper / other
		ret.right_trigger = self.right_trigger / other
		ret.right_bumper = self.right_bumper / other
		ret.joystick = self.joystick / other
		ret.Abutton = self.Abutton / other
		return ret
	def __str__(self):
		ret = ""
		ret += "Left Trigger: " + str(self.left_trigger) + "\n"
		ret += "Left Bumper: " + str(self.left_bumper) + "\n"
		ret += "Right Trigger: " + str(self.right_trigger) + "\n"
		ret += "Right Bumper: " + str(self.right_bumper) + "\n"
		ret += "Joystick: " + str(self.joystick) + "\n"
		ret += "A Button: " + str(self.Abutton) + "\n"
		return ret



def getDelta(newCoords, oldCoords):
    deltaArray = [] # array of delta coords
    deltaAverageX = 0
    deltaAverageY = 0
    deltaAverageZ = 0
    deltaAverage = 0

    if (oldCoords == [] or newCoords == [] or oldCoords == None or newCoords == None): # base case if we dont have previous hand coords
        deltaArray.append(100)
        return 2
    else: # Regular case where we take new coords and subtract from prev coords
        for i in range(len(newCoords)):
            for j in range(len(newCoords[i].landmark)):
                print("--------------------")
                deltax = abs(newCoords[i].landmark[j].x - oldCoords[i].landmark[j].x)
                deltay = abs(newCoords[i].landmark[j].y - oldCoords[i].landmark[j].y)
                deltaz = abs(newCoords[i].landmark[j].z - oldCoords[i].landmark[j].z)
                deltaArray.append({"deltax": deltax, "deltay": deltay, "deltaz": deltaz})

    for i in deltaArray:
        print(i)
        deltaAverageX += i["deltax"]
        deltaAverageY += i["deltay"]
        deltaAverageZ += i["deltaz"]

    deltaAverageX /= float(len(deltaArray))
    deltaAverageY /= float(len(deltaArray))
    deltaAverageZ /= float(len(deltaArray))

    deltaAverage = (deltaAverageX + deltaAverageY + deltaAverageZ) / 3.0

    print(deltaAverage)
    return deltaAverage



def diff(curCoords, nailNumber, nuckleNumber):
    global buttonPressCounter
    if (curCoords):
        nuckleDiff = abs(curCoords[0].landmark[17].y - curCoords[0].landmark[5].y)
        calibratednuckleDiff =  abs(calibratedCoords[0].landmark[17].y - calibratedCoords[0].landmark[5].y)
        movementDiff = abs(curCoords[0].landmark[nailNumber].x - curCoords[0].landmark[nuckleNumber].x)
        calibratedMovementDiff = abs(calibratedCoords[0].landmark[nailNumber].x - calibratedCoords[0].landmark[nuckleNumber].x) * nuckleDiff/calibratednuckleDiff
        return (movementDiff, calibratedMovementDiff)
    return None


def triggerPosition(movementDiff, calibratedMovementDiff):
    if(not movementDiff):
        return None
    ratio = movementDiff/calibratedMovementDiff 
    ratio -= 1 
    ratio /= 0.75 # scaling param that has yet to be determined
    ratio = max(ratio, -1) # bound the joystick between -1 and 1
    ratio = min(ratio, 1)
    return ratio

C = Controller()
temp_controllers = [Controller(), Controller(), Controller()]
# For webcam input:
cap = cv2.VideoCapture(0)
startTime = datetime.datetime.now()
counter = 0
with mp_hands.Hands(
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.7) as hands:
	while cap.isOpened():
		success, image = cap.read()
		if not success:
			print("Ignoring empty camera frame.")
			# If loading a video, use 'break' instead of 'continue'.
			continue
		
		counter +=1 
		# To improve performance, optionally mark the image as not writeable to
		# pass by reference.
		image.flags.writeable = False
		image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
		results = hands.process(image)

		# results.multi_hand_landmark stores each hand landmark x,y,z
		# do calibration

		curTime = datetime.datetime.now()
		if (2 < (curTime - startTime).total_seconds() < 3):
			calibratedCoords = results.multi_hand_landmarks
			print("calibration complete")

		if (len(calibratedCoords) > 0):
			# diff(results.multi_hand_landmarks, 8, 5)
			m, c = diff(results.multi_hand_landmarks, 4, 5)
			joystickPosition = triggerPosition(m,c)
			temp_controllers[counter%3].joystick = joystickPosition
			if (counter%3 == 0):
				C = (temp_controllers[0] + temp_controllers[1] + temp_controllers[2])/3
				print(C)

    # Draw the hand annotations on the image.
		image.flags.writeable = True
		image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
		if results.multi_hand_landmarks:
			for hand_landmarks in results.multi_hand_landmarks:
				mp_drawing.draw_landmarks(
					image,
					hand_landmarks,
					mp_hands.HAND_CONNECTIONS,
					mp_drawing_styles.get_default_hand_landmarks_style(),
					mp_drawing_styles.get_default_hand_connections_style())
		# Flip the image horizontally for a selfie-view display.
		cv2.imshow('MediaPipe Hands', cv2.flip(image, 1))
		if cv2.waitKey(5) & 0xFF == 27:
			break
cap.release()