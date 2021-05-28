import mss
import pygetwindow as gw
import keyboard
import numpy as np
import PIL
import time
import cv2

sct = None
window = None
current_screen = None

def setup():

    global window, sct
    windows = gw.getWindowsWithTitle('MapleStory')

    if len(windows) == 0:
        print('maplestory not found')
        exit()
    else:
        window = windows[0]

    sct = mss.mss()



def update_screen():

    global current_screen

    ms_bb = {
        'top': window.top,
        'left': window.left,
        'width': window.width,
        'height': window.height,
    }

    sct_img = sct.grab(ms_bb)
    img = np.array(sct_img)[:,:,:3]
    current_screen = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

def get_screen():
    return current_screen

def grab(bb):
    return sct.grab(bb)

if __name__ == '__main__':
    screenshot_dir = 'screenshots'
    setup()

    while True:
        cmd = input('shot or quit:\n')

        if cmd == 'quit':
            break
        elif cmd == 'shot':

            ms_bb = {
                'top': window.top,
                'left': window.left,
                'width': window.width,
                'height': window.height,
            }

            screenshot = sct.grab(ms_bb)
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=f'{screenshot_dir}/{int(time.time())}.png') 