import multiprocessing
import time

import nxbt

# Create a Pro Controller and wait for it to connect

class SwitchController:
    connected = False
    nx = None
    controller_index = None
    leftMultiprocessing = None
    rightMultiprocessing = None
    ZLMultiprocessing = None
    ZRMultiprocessing = None
    LMultiprocessing = None
    RMultiprocessing = None
    AMultiprocessing = None

    leftRun = False
    rightRun = False
    R = False
    L = False
    ZR = False
    ZL = False
    A = False

    def __init__(self):
        self.nx = nxbt.Nxbt()
        self.controller_index = self.nx.create_controller(nxbt.PRO_CONTROLLER,
                                                          reconnect_address=self.nx.get_switch_addresses())
        self.nx.wait_for_connection(self.controller_index)
        self.connected = True
        print("Connected")

    def connected(self):
        return self.connected

    def pressAtemp(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.A], 5)

    def pressA(self):
        A = True
        while A:
            self.nx.press_buttons(self.controller_index, [nxbt.Buttons.A], 1)
            #self.endThreadA()

    def pressASingle(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.A], 0.7)

    def startSingleAPress(self):
        x = multiprocessing.Process(target=self.pressA)
        x.start()


    def startThreadA(self):
        if self.AMultiprocessing is None:
            self.AMultiprocessing = multiprocessing.Process(target=self.pressA)
            self.AMultiprocessing.start()
        else:
            self.endThreadA()
            self.startThreadA()

    def endThreadA(self):
        if self.AMultiprocessing is not None:
            self.AMultiprocessing.kill()
            self.AMultiprocessing = None
            self.A = False

    def pressB(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.B], 1)

    def threadB(self):
        thread = multiprocessing.Process(target=self.pressB)
        thread.start()

    def pressX(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.X], 1)

    def threadX(self):
        thread = multiprocessing.Process(target=self.pressX)
        thread.start()

    def pressY(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.Y], 1)

    def threadY(self):
        thread = multiprocessing.Process(target=self.pressY)
        thread.start()

    # X is between -100 and 100
    def rightStick(self, x):
        #packet_manager = multiprocessing.Manager()
        #input_packet = packet_manager.dict()
        #input_packet["packet"] = self.nx.create_input_packet()
        while self.rightRun:
            self.nx.tilt_stick(self.controller_index, nxbt.Sticks.RIGHT_STICK, x, 0, tilted=0.01)

    # X is between -100 and 100
    def leftStick(self, x):
        if (x>20 and x<-20):
            self.nx.tilt_stick(self.controller_index, nxbt.Sticks.LEFT_STICK, x, 0, tilted=0.01)
        #self.leftRun = True
        #while self.leftRun:
            #self.nx.tilt_stick(self.controller_index, nxbt.Sticks.LEFT_STICK, x, 0, tilted=0.3)
            #time.sleep(0.1)

    def pressL(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.L], 2)

        #self.L = True
        #while self.L:
            #self.nx.press_buttons(self.controller_index, [nxbt.Buttons.L], 1)

    def pressR(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.R], 2)
        #self.R = True
        #while self.R:
            #self.nx.press_buttons(self.controller_index, [nxbt.Buttons.R], 1)

    def pressZL(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.ZL], 2)
        #self.ZL = True
        #while self.ZL:
            #self.nx.press_buttons(self.controller_index, [nxbt.Buttons.ZL], 1)

    def pressZR(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.ZR], 2)
        #self.ZR = True
        #while self.ZR:
            #self.nx.press_buttons(self.controller_index, [nxbt.Buttons.ZR], 1)

    def pressCapture(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.CAPTURE], 1)

    def pressHome(self):
        self.nx.press_buttons(self.controller_index, [nxbt.Buttons.HOME], 1)

    def startLeftProcess(self, x):
        if self.leftMultiprocessing is None:
            self.leftMultiprocessing = multiprocessing.Process(target=self.leftStick, args=(x,))
            self.leftMultiprocessing.start()
            time.sleep(0.1)
            self.leftMultiprocessing.terminate()
        else:
            self.endLeftProcess()
            self.startLeftProcess(x)

    def startRightProcess(self, x):
        if self.rightMultiprocessing is None:
            self.rightMultiprocessing = multiprocessing.Process(target=self.rightStick, args=(x,))
            self.rightMultiprocessing.start()
        else:
            self.endRightProcess()
            self.startRightProcess(x)

    def startLProcess(self):
        if self.LMultiprocessing is None:
            self.LMultiprocessing = multiprocessing.Process(target=self.pressL)
            self.LMultiprocessing.start()
        else:
            self.endLProcess()
            self.startLProcess()

    def startRProcess(self):
        if self.RMultiprocessing is None:
            self.RMultiprocessing = multiprocessing.Process(target=self.pressR)
            self.RMultiprocessing.start()
        else:
            self.endRProcess()
            self.startRProcess()

    def startZLProcess(self):
        if self.ZLMultiprocessing is None:
            self.ZLMultiprocessing = multiprocessing.Process(target=self.pressZL)
            self.ZLMultiprocessing.start()
        else:
            self.endZLProcess()
            self.startZLProcess()

    def startZRProcess(self):
        if self.ZRMultiprocessing is None:
            self.ZRMultiprocessing = multiprocessing.Process(target=self.pressZR)
            self.ZRMultiprocessing.start()
        else:
            self.endZRProcess()
            self.startZRProcess()

    def endLeftProcess(self):
        if self.leftMultiprocessing is not None:
            self.leftMultiprocessing.kill()
            self.leftMultiprocessing = None
            self.leftRun = False

    def endRightProcess(self):
        if self.rightMultiprocessing is not None:
            self.rightMultiprocessing.kill()
            self.rightMultiprocessing = None
            self.rightRun = False

    def endLProcess(self):
        if self.LMultiprocessing is not None:
            self.LMultiprocessing.kill()
            self.LMultiprocessing = None
            self.L = False

    def endRProcess(self):
        if self.RMultiprocessing is not None:
            self.RMultiprocessing.kill()
            self.RMultiprocessing = None
            self.R = False


    def endZLProcess(self):
        if self.ZLMultiprocessing is not None:
            self.ZLMultiprocessing.kill()
            self.ZLMultiprocessing = None
            self.ZL = False

    def endZRProcess(self):
        if self.ZRMultiprocessing is not None:
            self.ZRMultiprocessing.kill()
            self.ZRMultiprocessing = None
            self.ZR = False
