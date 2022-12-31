# PlugLess
### HackMIT 2022 New Frontiers Track Winner

## About

This project idea came out of the problem of missing controllers when it comes to playing multiplayer games, particularly Mario Kart. The number of controllers is often a bottleneck when it comes to playing games with friends. All of us on the team have personally encountered this problem before. Not everyone has controllers, but everyone has a laptop that can be used in such a scenario. Thus we built an application to analyze finger movements to control video games like MarioKart. We have built a desktop application that uses the camera to track your finger movements and by just our finger movements we have built an application that interfaces with consoles like the switch by emulating a controller. We plan to expand this technology to other applications, such as allowing users to control any tech such as drones, virtual objects (keyboards, instruments, etc.), or smart home technology.


## Demo

![](https://github.com/ayushzenith/PlugLess/blob/main/images/demo.gif)

## Dependencies
* Linux  
* Python3
* OpenCV - `pip3 install opencv-python`
* Mediapipe- `pip3 install mediapipe`
* NXBT - `sudo pip3 install nxbt`



## Run
```bash
sudo python3 main.py
```
Running requires sudo privledges in order to use certain bluetooth modules which are required to connect and control the switch as a controller

## Future features:
* Added support for multiple users from one camera
