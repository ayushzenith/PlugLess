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
rt1Button = 0
rt2Button = 0
aButton = 0

lt1Button = 0
lt2Button = 0

numPlayers = 1

class Controller:
	def __init__(self):
		self.left_trigger = 0
		self.left_bumper = 0
		self.right_trigger = 0
		self.right_bumper = 0
		self.joystick = 0
		self.Abutton = 0
		self.player = 0
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

def checkButtonPress(movementDiff, calibratedMovementDiff, movementRatio):
	if (movementDiff < calibratedMovementDiff * movementRatio):
		return 1
	else:
		return 0


def xDiff(curCoords, nailNumber, nuckleNumber, handNum):
	if (curCoords and curCoords[handNum]):
		nuckleDiff = abs(curCoords[handNum].landmark[17].y - curCoords[handNum].landmark[5].y)
		calibratednuckleDiff =  abs(calibratedCoords[handNum].landmark[17].y - calibratedCoords[handNum].landmark[5].y)
		movementDiff = abs(curCoords[handNum].landmark[nailNumber].x - curCoords[handNum].landmark[nuckleNumber].x)
		calibratedMovementDiff = abs(calibratedCoords[handNum].landmark[nailNumber].x - calibratedCoords[handNum].landmark[nuckleNumber].x) * nuckleDiff/calibratednuckleDiff
		return (movementDiff, calibratedMovementDiff)
	return (0,0)

def yDiff(curCoords, nailNumber, nuckleNumber, handNum):
	if (curCoords and curCoords[handNum]):
		nuckleDiff = abs(curCoords[handNum].landmark[17].y - curCoords[handNum].landmark[5].y)
		calibratednuckleDiff =  abs(calibratedCoords[handNum].landmark[17].y - calibratedCoords[handNum].landmark[5].y)
		movementDiff = abs(curCoords[handNum].landmark[nailNumber].y - curCoords[handNum].landmark[nuckleNumber].y)
		calibratedMovementDiff = abs(calibratedCoords[handNum].landmark[nailNumber].y - calibratedCoords[handNum].landmark[nuckleNumber].y) * nuckleDiff/calibratednuckleDiff
		return (movementDiff, calibratedMovementDiff)
	return (0,0)

def triggerPosition(movementDiff, calibratedMovementDiff):
	if(not movementDiff):
		return 0
	ratio = movementDiff/calibratedMovementDiff
	ratio -= 1
	ratio /= 0.75 # scaling param that has yet to be determined
	ratio = max(ratio, -1) # bound the joystick between -1 and 1
	ratio = min(ratio, 1)
	return ratio


controllers = []
temp_controllers = []
for i in range(numPlayers):
	controllers.append(Controller())
	temp_controllers.append([Controller(), Controller(), Controller()])
# For webcam input:
cap = cv2.VideoCapture(0)
startTime = datetime.datetime.now()
counter = 0
with mp_hands.Hands(
	model_complexity=1,
	max_num_hands=4,
	min_detection_confidence=0.5,
	min_tracking_confidence=0.7) as hands:
	while cap.isOpened():
		success, image = cap.read()
		if not success:
			print("Ignoring empty camera frame.")
			# If loading a video, use 'break' instead of 'continue'.
			continue

		counter += 1
		leftConroller = 0
		rightConroller = 0

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
		if (calibratedCoords != None and len(calibratedCoords) > 0):
			if results.multi_handedness != None:
				for i in range(len(results.multi_handedness)):
					if (results.multi_handedness[i].classification[0].label == "Left"):
						if(leftConroller >= numPlayers):
							print("Please move your hands into view")
							continue
						try: 
							(rt1Movementdiff, rt1CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks, 8, 5, i)
							(rt2Movementdiff, rt2CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks, 12, 9, i)
							(aMovementdiff, aCalibratedMovementDiff) = yDiff(results.multi_hand_landmarks, 4, 5, i)
						except IndexError:
							print("Please move your hands into view")
							continue


						rt1ButtonPressed = checkButtonPress(rt1Movementdiff, rt1CalibratedMovementDiff, 0.85)
						rt2ButtonPressed = checkButtonPress(rt2Movementdiff, rt2CalibratedMovementDiff, 0.87)
						aButtonPressed = checkButtonPress(aMovementdiff, aCalibratedMovementDiff, 0.90)

						print(leftConroller)
						temp_controllers[leftConroller][counter%3].right_trigger = rt1ButtonPressed
						temp_controllers[leftConroller][counter%3].right_bumper = rt2ButtonPressed
						temp_controllers[leftConroller][counter%3].Abutton = aButtonPressed
						if (counter%3 == 0):
							controllers[leftConroller] = (temp_controllers[leftConroller][0] + temp_controllers[leftConroller][1] + temp_controllers[leftConroller][2])/3

						if (rt1ButtonPressed == 1):
							rt1Button +=1
							if(rt1Button < 2):
								print("R1 Pressed")
						else:
							rt1Button = 0

						if (rt2ButtonPressed == 1):
							rt2Button += 1
							if(rt2Button < 2):
								print("R2 Pressed")
						else:
							rt2Button = 0

						if (aButtonPressed == 1):
							aButton += 1
							if(aButton < 2):
								print("A Pressed")
						else:
							aButton = 0
						leftConroller+=1
					elif (results.multi_handedness[i].classification[0].label == "Right"):
						if(rightConroller >= numPlayers):
							print("please move your hand into view")
							continue
						try:
							(lt1Movementdiff, lt1CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks, 8, 5, i)
							(lt2Movementdiff, lt2CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks, 12, 9, i)
							m, c = xDiff(results.multi_hand_landmarks, 4, 5, i)
						except:
							print("Please move your hands into view")
							continue

						lt1ButtonPressed = checkButtonPress(lt1Movementdiff, lt1CalibratedMovementDiff, 0.90)
						lt2ButtonPressed = checkButtonPress(lt2Movementdiff, lt2CalibratedMovementDiff, 0.90)

						joystickPosition = triggerPosition(m,c)

						temp_controllers[rightConroller][counter%3].left_trigger = lt1ButtonPressed
						temp_controllers[rightConroller][counter%3].left_bumper = lt2ButtonPressed
						temp_controllers[rightConroller][counter%3].joystick = joystickPosition
						if (counter%3 == 0):
							controllers[rightConroller] = (temp_controllers[rightConroller][0] + temp_controllers[rightConroller][1] + temp_controllers[rightConroller][2])/3

						if (lt1ButtonPressed == 1):
							lt1Button += 1
							if(lt1Button < 2):
								print("L1 Pressed")
						else:
							lt1Button = 0

						if (lt2ButtonPressed == 1):
							lt2Button += 1
							if(lt2Button < 2):
								print("L2 Pressed")
						else:
							lt2Button = 0
						rightConroller+=1
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