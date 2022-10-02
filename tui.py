import os
import time
import psutil
from collections import deque
import multiprocessing

import mediapipe as mp
import datetime
import cv2
from blessed import Terminal

cap = cv2.VideoCapture(0)

from nxbt import Nxbt, PRO_CONTROLLER

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
arrows = []
joystickPositionArr = []
joycon = cv2.resize(cv2.imread("./joycon.jpg"), dsize=[110, 150])


class Controller:
    def __init__(self):
        self.left_trigger = 0
        self.left_bumper = 0
        self.right_trigger = 0
        self.right_bumper = 0
        self.joystick = 0
        self.joystickY = 0
        self.Abutton = 0
        self.player = 0


    def __add__(self, other):
        ret = Controller()
        ret.left_trigger = self.left_trigger + other.left_trigger
        ret.left_bumper = self.left_bumper + other.left_bumper
        ret.right_trigger = self.right_trigger + other.right_trigger
        ret.right_bumper = self.right_bumper + other.right_bumper
        ret.joystick = self.joystick + other.joystick
        ret.joystickY = self.joystickY + other.joystickY
        ret.Abutton = self.Abutton + other.Abutton
        return ret


    def __truediv__(self, other):
        ret = Controller()
        ret.left_trigger = self.left_trigger / other
        ret.left_bumper = self.left_bumper / other
        ret.right_trigger = self.right_trigger / other
        ret.right_bumper = self.right_bumper / other
        ret.joystick = self.joystick / other
        ret.joystickY = self.joystickY / other
        ret.Abutton = self.Abutton / other
        return ret


    def __str__(self):
        ret = ""
        ret += "Left Trigger: " + str(self.left_trigger) + "\n"
        ret += "Left Bumper: " + str(self.left_bumper) + "\n"
        ret += "Right Trigger: " + str(self.right_trigger) + "\n"
        ret += "Right Bumper: " + str(self.right_bumper) + "\n"
        ret += "Joystick: " + str(self.joystick) + "\n"
        ret += "JoystickY: " + str(self.joystickY) + "\n"
        ret += "A Button: " + str(self.Abutton) + "\n"
        return ret


# switch_controller = SwitchController()
# print(switch_controller.connected)

def getDelta(newCoords, oldCoords):
    deltaArray = []  # array of delta coords
    deltaAverageX = 0
    deltaAverageY = 0
    deltaAverageZ = 0
    deltaAverage = 0

    if (
            oldCoords == [] or newCoords == [] or oldCoords == None or newCoords == None):  # base case if we dont have previous hand coords
        deltaArray.append(100)
        return 2
    else:  # Regular case where we take new coords and subtract from prev coords
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
        calibratednuckleDiff = abs(calibratedCoords[handNum].landmark[17].y - calibratedCoords[handNum].landmark[5].y)
        movementDiff = abs(curCoords[handNum].landmark[nailNumber].x - curCoords[handNum].landmark[nuckleNumber].x)
        calibratedMovementDiff = abs(
            calibratedCoords[handNum].landmark[nailNumber].x - calibratedCoords[handNum].landmark[
                nuckleNumber].x) * nuckleDiff / calibratednuckleDiff
        return (movementDiff, calibratedMovementDiff)
    return (0, 0)


def yDiff(curCoords, nailNumber, nuckleNumber, handNum):
    if (curCoords and curCoords[handNum]):
        nuckleDiff = abs(curCoords[handNum].landmark[17].y - curCoords[handNum].landmark[5].y)
        calibratednuckleDiff = abs(calibratedCoords[handNum].landmark[17].y - calibratedCoords[handNum].landmark[5].y)
        movementDiff = abs(curCoords[handNum].landmark[nailNumber].y - curCoords[handNum].landmark[nuckleNumber].y)
        calibratedMovementDiff = abs(
            calibratedCoords[handNum].landmark[nailNumber].y - calibratedCoords[handNum].landmark[
                nuckleNumber].y) * nuckleDiff / calibratednuckleDiff
        return (movementDiff, calibratedMovementDiff)
    return (0, 0)


def triggerPosition(movementDiff, calibratedMovementDiff):
    if (not movementDiff):
        return 0
    ratio = movementDiff / calibratedMovementDiff
    ratio -= 1
    ratio /= 0.75  # scaling param that has yet to be determined
    ratio = max(ratio, -1)  # bound the joystick between -1 and 1
    ratio = min(ratio, 1)
    return ratio


controllers = []
temp_controllers = []
for i in range(numPlayers):
    controllers.append(Controller())
    temp_controllers.append([Controller(), Controller(), Controller()])


class LoadingSpinner():
    SPINNER_CHARS = ['■ □ □ □', '□ ■ □ □', '□ □ ■ □', '□ □ □ ■', '□ □ □ ■', '□ □ ■ □', '□ ■ □ □', '■ □ □ □']  # noqa

    def __init__(self):

        self.creation_time = time.perf_counter()
        self.last_update_time = self.creation_time
        self.current_char_index = 0

    def get_spinner_char(self):

        current_time = time.perf_counter()
        delta = current_time - self.last_update_time

        if delta > 0.07:
            self.last_update_time = current_time

            if self.current_char_index == 7:
                self.current_char_index = 0
            else:
                self.current_char_index += 1

        return self.SPINNER_CHARS[self.current_char_index]


class ControllerTUI():
    CONTROLS = {
        "ZL": "◿□□□□",
        "L": "◿□□□□",
        "ZR": "□□□□◺",
        "R": "□□□□◺",
        "LS_UP": ".─.",
        "LS_LEFT": "(",
        "LS_RIGHT": ")",
        "LS_DOWN": "`─'",
        "RS_UP": ".─.",
        "RS_LEFT": "(",
        "RS_RIGHT": ")",
        "RS_DOWN": "`─'",
        "DPAD_UP": "△",
        "DPAD_LEFT": "◁",
        "DPAD_RIGHT": "▷",
        "DPAD_DOWN": "▽",
        "MINUS": "◎",
        "PLUS": "◎",
        "HOME": "□",
        "CAPTURE": "□",
        "A": "○",
        "B": "○",
        "X": "○",
        "Y": "○",
    }

    def __init__(self, term):

        self.term = term
        # Save a copy of the controls we can restore the
        # control text on deactivation
        self.DEFAULT_CONTROLS = self.CONTROLS.copy()

        self.CONTROL_RELEASE_TIMERS = self.CONTROLS.copy()
        for control in self.CONTROL_RELEASE_TIMERS.keys():
            self.CONTROL_RELEASE_TIMERS[control] = False

        self.auto_keypress_deactivation = True
        self.remote_connection = False

    def toggle_auto_keypress_deactivation(self, toggle):
        """Toggles whether or not the ControllerTUI should deactivate
        a control after a period of time.

        :param toggle: A True/False value that toggles auto keypress
        deactivation
        :type toggle: bool
        """

        self.auto_keypress_deactivation = toggle

    def set_remote_connection_status(self, status):
        """Sets whether or not the controller should render
        with remote connection specific controls.

        :param status: The status of the remote connection
        :type status: bool
        """

        self.remote_connection = status

    def activate_control(self, key, activated_text=None):

        if activated_text:
            self.CONTROLS[key] = activated_text
        else:
            self.CONTROLS[key] = self.term.bold_black_on_white(self.CONTROLS[key])

        # Keep track of when the key was pressed so we can release later
        if self.auto_keypress_deactivation:
            self.CONTROL_RELEASE_TIMERS[key] = time.perf_counter()

    def deactivate_control(self, key):

        self.CONTROLS[key] = self.DEFAULT_CONTROLS[key]

    def render_controller(self):

        if self.auto_keypress_deactivation:
            # Release any overdue timers
            for control in self.CONTROL_RELEASE_TIMERS.keys():
                pressed_time = self.CONTROL_RELEASE_TIMERS[control]
                current_time = time.perf_counter()
                if pressed_time is not False and current_time - pressed_time > 0.25:
                    self.deactivate_control(control)

        ZL = self.CONTROLS['ZL']
        L = self.CONTROLS['L']
        ZR = self.CONTROLS['ZR']
        R = self.CONTROLS['R']
        LU = self.CONTROLS['LS_UP']
        LL = self.CONTROLS['LS_LEFT']
        LR = self.CONTROLS['LS_RIGHT']
        LD = self.CONTROLS['LS_DOWN']
        RU = self.CONTROLS['RS_UP']
        RL = self.CONTROLS['RS_LEFT']
        RR = self.CONTROLS['RS_RIGHT']
        RD = self.CONTROLS['RS_DOWN']
        DU = self.CONTROLS['DPAD_UP']
        DL = self.CONTROLS['DPAD_LEFT']
        DR = self.CONTROLS['DPAD_RIGHT']
        DD = self.CONTROLS['DPAD_DOWN']
        MN = self.CONTROLS['MINUS']
        PL = self.CONTROLS['PLUS']
        HM = self.CONTROLS['HOME']
        CP = self.CONTROLS['CAPTURE']
        A = self.CONTROLS['A']
        B = self.CONTROLS['B']
        X = self.CONTROLS['X']
        Y = self.CONTROLS['Y']

        if self.remote_connection:
            lr_press = "L + R - - - - - - - - -▷ E"
        else:
            lr_press = "                          "

        print(self.term.home + self.term.move_y((self.term.height // 2) - 9))
        print(self.term.center(f"      {ZL}        {ZR}                                    "))
        print(self.term.center(f"    ─{L}──────────{R}─      ┌─────────────┬────────────┐"))
        print(self.term.center("  ╱                        ╲    │  Controls   │    Keys    │"))
        print(self.term.center(f" ╱   {LU}   {MN}       {PL}   {X}    ╲   └─────────────┴────────────┘"))  # noqa
        print(self.term.center(f"│   {LL}   {LR}    {CP}   {HM}   {Y}   {A}   │   Left Stick ─ ─ ─ ▷ W/A/S/D "))  # noqa
        print(self.term.center(f"│    {LD}               {B}     │   DPad ─ ─ ─ ─ ─ ─ ▷ G/V/B/N "))
        print(self.term.center(f"│        {DU}         {RU}       │   Capture/Home ─ ─ ─ ─ ▷ [/] "))
        print(self.term.center(f"│╲     {DL} □ {DR}      {RL}   {RR}     ╱│   +/- ─ ─ ─ ─ ─ ─ ─ ─ ─▷ 6/7 "))  # noqa
        print(self.term.center(f"│░░╲     {DD}         {RD}    ╱░░│   X/Y/B/A ─ ─ ─ ─ ─▷ J/I/K/L "))
        print(self.term.center("│░░░░╲ ──────────────── ╱░░░░│   L/ZL ─ ─ ─ ─ ─ ─ ─ ─ ▷ 1/2 "))
        print(self.term.center("│░░░░╱                  ╲░░░░│   R/ZR ─ ─ ─ ─ ─ ─ ─ ─ ▷ 8/9 "))
        print(self.term.center("│░░╱                      ╲░░│   Right Stick - - - ▷ Arrows "))
        print(self.term.center(f"│╱                          ╲│   {lr_press} "))


class InputTUI():
    KEYMAP = {
        # Left Stick Mapping
        "w": {
            "control": "LS_UP",
            "stick_data": {
                "stick_name": "L_STICK",
                "x": "+000",
                "y": "+100"
            }
        },
        "a": {
            "control": "LS_LEFT",
            "stick_data": {
                "stick_name": "L_STICK",
                "x": "-100",
                "y": "+000"
            }
        },
        "d": {
            "control": "LS_RIGHT",
            "stick_data": {
                "stick_name": "L_STICK",
                "x": "+100",
                "y": "+000"
            }
        },
        "s": {
            "control": "LS_DOWN",
            "stick_data": {
                "stick_name": "L_STICK",
                "x": "+000",
                "y": "-100"
            }
        },

        # Right Stick Mapping
        "KEY_UP": {
            "control": "RS_UP",
            "stick_data": {
                "stick_name": "R_STICK",
                "x": "+000",
                "y": "+100"
            }
        },
        "KEY_LEFT": {
            "control": "RS_LEFT",
            "stick_data": {
                "stick_name": "R_STICK",
                "x": "-100",
                "y": "+000"
            }
        },
        "KEY_RIGHT": {
            "control": "RS_RIGHT",
            "stick_data": {
                "stick_name": "R_STICK",
                "x": "+100",
                "y": "+000"
            }
        },
        "KEY_DOWN": {
            "control": "RS_DOWN",
            "stick_data": {
                "stick_name": "R_STICK",
                "x": "+000",
                "y": "-100"
            }
        },

        # Dpad Mapping
        "g": "DPAD_UP",
        "v": "DPAD_LEFT",
        "n": "DPAD_RIGHT",
        "b": "DPAD_DOWN",

        # Button Mapping
        "6": "MINUS",
        "7": "PLUS",
        "[": "CAPTURE",
        "]": "HOME",
        "i": "X",
        "j": "Y",
        "l": "A",
        "k": "B",

        # Triggers
        "1": "L",
        "2": "ZL",
        "8": "R",
        "9": "ZR",
    }

    def __init__(self, reconnect_target=None, debug=False, logfile=False, force_remote=False):

        self.reconnect_target = reconnect_target
        self.term = Terminal()
        if force_remote:
            self.remote_connection = True
        else:
            self.remote_connection = self.detect_remote_connection()
        self.controller = ControllerTUI(self.term)

        # Check if direct connection will fail
        if not self.remote_connection:
            try:
                # from pynput import keyboard
                pass
            except ImportError as e:
                print("Unable to import pynput for direct input.")
                print("If you're accessing NXBT over a remote shell, ", end="")
                print("please use the 'remote_tui' option instead of 'tui'.")
                print("The original pynput import is displayed below:\n")
                print(e)
                exit(1)

        self.debug = debug
        self.logfile = logfile

    def handDetectionLoop(self, cap, hands, on_press, on_release, startTime, counter):
        global calibratedCoords
        global arrows
        global joystickPositionArr
        global rt1Button
        global rt2Button
        global lt1Button
        global lt2Button
        global aButton
        success, image = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            # If loading a video, use 'break' instead of 'continue'.
            return

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
        if ((curTime - startTime).total_seconds() < 5):
            image = cv2.flip(image, 1)
            cv2.putText(image, "CALIBRATING", (int(image.shape[0] // 2), int(image.shape[1] // 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 5)
            image = cv2.flip(image, 1)
        if (4 < (curTime - startTime).total_seconds() < 5):
            calibratedCoords = results.multi_hand_landmarks
            print("calibration complete")
        if (calibratedCoords != None and len(calibratedCoords) > 0):
            if results.multi_handedness != None:
                for i in range(len(results.multi_handedness)):
                    if (results.multi_handedness[i].classification[0].label == "Left"):
                        if (leftConroller >= numPlayers):
                            print("oops 1")
                            image = cv2.flip(image, 1)
                            cv2.putText(image, "Please move your hands into view",
                                        (int(image.shape[0] // 2), int(image.shape[1] // 10)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 5)
                            image = cv2.flip(image, 1)
                            continue
                        try:
                            (rt1Movementdiff, rt1CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks,
                                                                                 8, 5, i)
                            (rt2Movementdiff, rt2CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks,
                                                                                 12, 9, i)
                            (aMovementdiff, aCalibratedMovementDiff) = yDiff(results.multi_hand_landmarks, 4, 5,
                                                                             i)
                        except IndexError:
                            print("oops 2")
                            image = cv2.flip(image, 1)
                            cv2.putText(image, "Please move your hands into view",
                                        (int(image.shape[0] // 2), int(image.shape[1] // 10)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 5)
                            image = cv2.flip(image, 1)
                            continue

                        rt1ButtonPressed = checkButtonPress(rt1Movementdiff, rt1CalibratedMovementDiff, 0.85)
                        rt2ButtonPressed = checkButtonPress(rt2Movementdiff, rt2CalibratedMovementDiff, 0.87)
                        aButtonPressed = checkButtonPress(aMovementdiff, aCalibratedMovementDiff, 0.90)

                        print(leftConroller)
                        temp_controllers[leftConroller][counter % 3].right_trigger = rt1ButtonPressed
                        temp_controllers[leftConroller][counter % 3].right_bumper = rt2ButtonPressed
                        temp_controllers[leftConroller][counter % 3].Abutton = aButtonPressed
                        if (counter % 3 == 0):
                            controllers[leftConroller] = (temp_controllers[leftConroller][0] +
                                                          temp_controllers[leftConroller][1] +
                                                          temp_controllers[leftConroller][2]) / 3

                        if (rt1ButtonPressed == 1):
                            rt1Button += 1
                            # switch_controller.startRProcess()
                            on_press('8')
                            arrows.append([(130, 13), (110, 13), (0, 0, 255), 4, 0.5])
                            if (rt1Button < 2):
                                print("R1 Pressed")
                        else:
                            rt1Button = 0
                            on_release('8')

                        if (rt2ButtonPressed == 1):
                            rt2Button += 1
                            # switch_controller.startZRProcess()
                            on_press("9")
                            arrows.append([(130, 25), (110, 25), (0, 0, 255), 4, 0.5])
                            if (rt2Button < 2):
                                print("R2 Pressed")
                        else:
                            rt2Button = 0
                            on_release("9")

                        if (aButtonPressed == 1):
                            aButton += 1
                            # switch_controller.startThreadA()
                            on_press("l")
                            arrows.append([(130, 65), (110, 65), (0, 0, 255), 4, 0.5])
                            if (aButton < 2):
                                print("A Pressed")

                        else:
                            aButton = 0
                            on_release("l")
                        leftConroller += 1
                    elif (results.multi_handedness[i].classification[0].label == "Right"):
                        if (rightConroller >= numPlayers):
                            print("oops 3")
                            image = cv2.flip(image, 1)
                            cv2.putText(image, "Please move your hands into view",
                                        (int(image.shape[0] // 2), int(image.shape[1] // 10)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 5)
                            image = cv2.flip(image, 1)
                            continue
                        try:
                            (lt1Movementdiff, lt1CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks,
                                                                                 8, 5, i)
                            (lt2Movementdiff, lt2CalibratedMovementDiff) = xDiff(results.multi_hand_landmarks,
                                                                                 12, 9, i)
                            m, c = xDiff(results.multi_hand_landmarks, 4, 5, i)
                            m_y, c_y = yDiff(results.multi_hand_landmarks, 4, 2, i)

                        except Exception as e:
                            image = cv2.flip(image, 1)
                            print(e)
                            cv2.putText(image, "Please move your hands into view",
                                        (int(image.shape[0] // 2), int(image.shape[1] // 10)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 5)
                            image = cv2.flip(image, 1)
                            continue

                        lt1ButtonPressed = checkButtonPress(lt1Movementdiff, lt1CalibratedMovementDiff, 0.90)
                        lt2ButtonPressed = checkButtonPress(lt2Movementdiff, lt2CalibratedMovementDiff, 0.90)

                        joystickPosition = triggerPosition(m, c)
                        joystickPositionY = triggerPosition(m_y, c_y)

                        joystickPositionArr.append(joystickPosition)
                        joystickPositionArr.append(joystickPositionY)

                        # switch_controller.startLeftProcess(min(max(int(joystickPosition * 100), -100), 100))
                        if joystickPosition < -0.3:
                            on_press("a")
                        elif joystickPosition > 0.3:
                            on_press("d")
                        elif joystickPosition < 0:
                            on_release('a')
                        elif joystickPosition > 0:
                            on_release('d')

                        if joystickPositionY < -0.5:
                            on_press("s")
                        elif joystickPositionY > 0.5:
                            on_press("w")
                        elif joystickPositionY < 0:
                            on_release('w')
                        elif joystickPositionY > 0:
                            on_release('w')

                        temp_controllers[rightConroller][counter % 3].left_trigger = lt1ButtonPressed
                        temp_controllers[rightConroller][counter % 3].left_bumper = lt2ButtonPressed
                        temp_controllers[rightConroller][counter % 3].joystick = joystickPosition
                        temp_controllers[rightConroller][counter % 3].joystickY = joystickPositionY

                        if (counter % 3 == 0):
                            controllers[rightConroller] = (temp_controllers[rightConroller][0] +
                                                           temp_controllers[rightConroller][1] +
                                                           temp_controllers[rightConroller][2]) / 3

                        if (lt1ButtonPressed == 1):
                            lt1Button += 1
                            # switch_controller.startLProcess()
                            on_press("1")
                            arrows.append([(55, 13), (35, 13), (0, 0, 255), 4, 0.5])
                            if (lt1Button < 2):
                                print("L1 Pressed")

                        else:
                            lt1Button = 0
                            on_release("1")

                        if (lt2ButtonPressed == 1):
                            lt2Button += 1
                            # switch_controller.startZLProcess()
                            on_press("2")
                            arrows.append([(55, 25), (35, 25), (0, 0, 255), 4, 0.5])
                            if (lt2Button < 2):
                                print("L2 Pressed")

                        else:
                            lt2Button = 0
                            on_release("2")
                        rightConroller += 1

                        """
                        if (controllers[0] is not None):
                            if(controllers[0].left_bumper == 0):
                                switch_controller.endZLProcess()
                            else:
                                switch_controller.startZLProcess()
                            if(controllers[0].right_bumper == 0):
                                switch_controller.endZRProcess()
                            else:
                                switch_controller.startZRProcess()
                            if(controllers[0].left_trigger == 0):
                                switch_controller.endLProcess()
                            else:
                                switch_controller.startLProcess()
                            if(controllers[0].right_trigger == 0):
                                switch_controller.endRProcess()
                            else:
                                switch_controller.startRProcess()
                            if(controllers[0].Abutton == 0):
                                switch_controller.endThreadA()
                            else:
                                switch_controller.startThreadA()
                        """

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
        image = cv2.flip(image, 1)
        image[0:joycon.shape[0], 0:joycon.shape[1]] = joycon

        for i in arrows:
            image = cv2.arrowedLine(image, i[0], i[1], i[2], i[3], tipLength=i[4])

        if (len(joystickPositionArr) > 0):
            image = cv2.putText(image, "x:" + str(round(joystickPositionArr[0], 5)), (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0),
                                2)
            #image = cv2.putText(image, "y: " + str(round(joystickPositionArr[1], 5)), (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0),
                                #2)

        joystickPositionArr = []
        arrows = []
        cv2.imshow('PlugLess', image)
        cv2.waitKey(1)
        # cv2.destroyAllWindows()
        if cv2.waitKey(5) & 0xFF == 27:
            pass

    def detect_remote_connection(self):
        """Traverse up the parent processes and check if any
        have their parent as a remote daemon. If so, the python
        script is running under a remote connection.

        Remote shell detection is required for this TUI, due to
        keyboard input limitations on most remote connections.
        Specifically, no "keyup" events are sent when a key is
        released. Keyup events are required for proper input to
        the Switch, thus, we need to detect if the shell is a remote
        session and workaround this.

        :return: Returns a boolean value indicating whether or not
        the current script is running as SSH
        :rtype: bool
        """

        remote_connection = False
        remote_process_names = ['sshd', 'mosh-server']
        ppid = os.getppid()
        while ppid > 0:
            process = psutil.Process(ppid)
            if process.name() in remote_process_names:
                remote_connection = True
                break
            ppid = process.ppid()

        return remote_connection

    def start(self):

        self.mainloop(self.term)

    def mainloop(self, term):
        # Initializing a controller
        if not self.debug:
            self.nx = Nxbt(disable_logging=True)
        else:
            self.nx = Nxbt(debug=self.debug, logfile=self.logfile)
        self.controller_index = self.nx.create_controller(
            PRO_CONTROLLER,
            reconnect_address=self.nx.get_switch_addresses())

        state = None
        spinner = LoadingSpinner()
        errors = None
        try:
            with term.cbreak(), term.keypad(), term.location(), term.hidden_cursor():
                print(term.home + term.clear)
                self.render_top_bar(term)
                self.render_bottom_bar(term)
                self.render_start_screen(term, "Loading")
                inp = term.inkey(timeout=0)

                # Loading Screen
                while inp != chr(113):  # Checking for q press
                    # Check key at 15hz
                    inp = term.inkey(timeout=1 / 30)
                    new_state = self.nx.state[self.controller_index]["state"]

                    if new_state != state:
                        state = new_state

                        loading_text = "Loading"
                        if state == "initializing":
                            loading_text = "Initializing Controller"
                        elif state == "connecting":
                            loading_text = "Connecting to any Nintendo Switch"
                        elif state == "reconnecting":
                            loading_text = "Reconnecting to Nintendo Switch"
                        elif state == "connected":
                            loading_text = "Connected!"
                        elif state == "crashed":
                            errors = self.nx.state[self.controller_index]["errors"]
                            exit(1)
                        self.render_start_screen(term, loading_text)

                    print(term.move_y((term.height // 2) + 6))
                    if state != "connected":
                        print(term.bold(term.center(spinner.get_spinner_char())))
                    else:
                        print(term.center(""))

                    if state == "connected":
                        time.sleep(1)
                        break

                # Main Gamepad Input Loop
                if state == "connected":
                    self.direct_input_loop(term)


        except KeyboardInterrupt:
            pass
        finally:
            print(term.clear())
            if errors:
                print("The TUI encountered the following errors:")
                print(errors)

    def remote_input_loop(self, term):

        self.controller.set_remote_connection_status(True)

        inp = term.inkey(timeout=0)
        while inp != chr(113):  # Checking for q press
            # Cutoff large buffered input from the deque
            # so that we avoid spamming the Switch after
            # a key releases from being held.
            # Increasing the size of the buffer does not
            # smooth out the jagginess of input.
            if len(term._keyboard_buf) > 1:
                term._keyboard_buf = deque([term._keyboard_buf.pop()])

            inp = term.inkey(1 / 66)

            pressed_key = None
            if inp.is_sequence:
                pressed_key = inp.name
            elif inp:
                pressed_key = inp

            if pressed_key == 'e':
                self.controller.activate_control('L')
                self.controller.activate_control('R')
                self.nx.macro(self.controller_index, "L R 0.1s")
            else:
                try:
                    control_data = self.KEYMAP[pressed_key]
                    if type(control_data) == dict and "stick_data" in control_data.keys():
                        x_value = control_data['stick_data']['x']
                        y_value = control_data['stick_data']['y']
                        stick_name = control_data['stick_data']['stick_name']

                        self.controller.activate_control(control_data["control"])
                        self.nx.macro(
                            self.controller_index,
                            f"{stick_name}@{x_value}{y_value} 0.1s")
                    else:
                        self.controller.activate_control(control_data)
                        self.nx.macro(self.controller_index, f"{control_data} 0.05s")
                except KeyError:
                    pass

            self.controller.render_controller()

            self.check_for_disconnect(term)

    def direct_input_loop(self, term):

        self.controller.toggle_auto_keypress_deactivation(False)
        self.exit_tui = False
        self.capture_input = True

        # Create a packet that is accessible from a multiprocessing Process
        # and from within threads
        packet_manager = multiprocessing.Manager()
        input_packet = packet_manager.dict()
        input_packet["packet"] = self.nx.create_input_packet()

        print(term.move_y(term.height - 5))
        print(term.center(term.bold_black_on_white(" <Press esc to toggle input capture> ")))

        def on_press(key):
            # Parse the key press event
            pressed_key = None
            try:
                pressed_key = key
            except AttributeError:
                pressed_key = str(key).replace(".", "_").upper()
            print("pressed " + pressed_key)

            if not self.capture_input:  # If we're not capturing input, pass
                print("Not inputing")
                pass
            else:
                try:
                    print("should work")
                    control_data = self.KEYMAP[pressed_key]
                    packet = input_packet["packet"]
                    if type(control_data) == dict and "stick_data" in control_data.keys():
                        stick_name = control_data['stick_data']['stick_name']
                        self.controller.activate_control(control_data["control"])
                        packet[stick_name][control_data["control"]] = True
                    else:
                        self.controller.activate_control(control_data)
                        packet[control_data] = True
                    input_packet["packet"] = packet
                except KeyError:
                    print("Problem")
                    print("Error with " + pressed_key)

        def on_release(key):

            # Parse the key release event
            released_key = None
            try:
                released_key = key
            except AttributeError:
                released_key = str(key).replace(".", "_").upper()

            # If the esc key is released, toggle input capturing
            if released_key == "KEY_ESC":
                self.capture_input = not self.capture_input

            # Exit on q key press
            if released_key == 'q':
                self.exit_tui = True
                return False

            if not self.capture_input:  # If we're not capturing input, pass
                pass
            else:
                try:
                    control_data = self.KEYMAP[released_key]
                    packet = input_packet["packet"]
                    if type(control_data) == dict and "stick_data" in control_data.keys():
                        stick_name = control_data['stick_data']['stick_name']
                        self.controller.deactivate_control(control_data["control"])
                        packet[stick_name][control_data["control"]] = False
                    else:
                        self.controller.deactivate_control(control_data)
                        packet[control_data] = False
                    input_packet["packet"] = packet
                except KeyError:
                    pass

        def input_worker(nxbt, controller_index, input_packet):

            while True:
                packet = input_packet["packet"]

                # Calculating left x/y stick values
                ls_x_value = 0
                ls_y_value = 0
                if packet["L_STICK"]["LS_LEFT"]:
                    ls_x_value -= 100
                if packet["L_STICK"]["LS_RIGHT"]:
                    ls_x_value += 100
                if packet["L_STICK"]["LS_UP"]:
                    ls_y_value += 100
                if packet["L_STICK"]["LS_DOWN"]:
                    ls_y_value -= 100
                packet["L_STICK"]["X_VALUE"] = ls_x_value
                packet["L_STICK"]["Y_VALUE"] = ls_y_value

                # Calculating right x/y stick values
                rs_x_value = 0
                rs_y_value = 0
                if packet["R_STICK"]["RS_LEFT"]:
                    rs_x_value -= 100
                if packet["R_STICK"]["RS_RIGHT"]:
                    rs_x_value += 100
                if packet["R_STICK"]["RS_UP"]:
                    rs_y_value += 100
                if packet["R_STICK"]["RS_DOWN"]:
                    rs_y_value -= 100
                packet["R_STICK"]["X_VALUE"] = rs_x_value
                packet["R_STICK"]["Y_VALUE"] = rs_y_value

                nxbt.set_controller_input(controller_index, packet)
                time.sleep(1 / 120)

        input_process = multiprocessing.Process(
            target=input_worker, args=(self.nx, self.controller_index, input_packet))
        input_process.start()

        startTime = datetime.datetime.now()
        counter = 0

        with mp_hands.Hands(
                model_complexity=1,
                max_num_hands=4,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.7) as hands:
            while cap.isOpened():
                self.handDetectionLoop(cap, hands, on_press, on_release, startTime, counter)
        cap.release()

        # Main TUI Loop
        """while True:
            if self.exit_tui:
                packet_manager.shutdown()
                input_process.terminate()
                break
            if not self.capture_input:
                print(term.home + term.move_y((term.height // 2) - 4))
                print(term.bold_black_on_white(term.center("")))
                print(term.bold_black_on_white(term.center(
                    "<Input Paused. Press ESC Again to Begin Capturing Input>"
                )))
                print(term.bold_black_on_white(term.center("")))
            else:
                self.controller.render_controller()
            self.check_for_disconnect(term)
            time.sleep(1/120)"""

    def render_start_screen(self, term, loading_text):

        print(term.home + term.move_y((term.height // 2) - 8))
        print(term.center("___╲╱___"))
        print(term.center("│╲  ╱╲  ╱│"))
        print(term.center("│ ╲╱__╲╱ │"))
        print(term.center("│╱      ╲│"))
        print(term.center("┌──────────────────┐"))
        print(term.center("│     NXBT TUI     │"))
        print(term.center("└──────────────────┘"))
        print(term.center(""))
        print(term.black_on_white(term.center("")))
        print(term.bold_black_on_white(term.center(loading_text)))
        print(term.black_on_white(term.center("")))

    def render_top_bar(self, term):

        print(term.move_y(1))
        if self.remote_connection:
            print(term.bold_black_on_white(term.center(term.bold_black_on_red("  REMOTE MODE  "))))
            warning = " WARNING: MACROS WILL BE USED ON KEYPRESS DUE TO REMOTE CLI LIMITATIONS "
            print(term.center(term.black_on_red(warning)))
        else:
            print(term.bold_black_on_white(term.center("DIRECT INPUT MODE")))
        print(term.move_y(1))
        print(term.white_on_black(" NXBT TUI 🎮 "))

    def render_bottom_bar(self, term):

        print(term.move_y(term.height))
        print(term.center(term.bold_black_on_white(" <Press q to quit> ")))

    def check_for_disconnect(self, term):

        state = self.nx.state[self.controller_index]["state"]
        if state != 'connected':
            print(term.home + term.move_y((term.height // 2) - 4))
            print(term.bold_black_on_red(term.center("")))
            print(term.bold_black_on_red(term.center(state.title())))
            print(term.bold_black_on_red(term.center("")))

            if state == 'crashed':
                time.sleep(3)
                term.clear()
                errors = self.nx.state[self.controller_index]["errors"]
                raise ConnectionError(errors)

            while True:
                inp = term.inkey(1 / 30)
                if inp == chr(113):
                    exit(1)
                elif self.nx.state[self.controller_index]["state"] == 'connected':
                    break


def main():
    """Program entry point."""

    tui = InputTUI()
    tui.start()


if __name__ == '__main__':
    main()
