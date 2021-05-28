import numpy as np
import keyboard
import asyncio
import cv2
import math

def dist_squared(a, b):
    return (a[0] - b[0])**2 + (a[1] - b[1])**2  

def random_bool(p):
    return np.random.uniform() < p

async def hold_key(key, press_time=.3, randomize=True, variance_pct=.2):

    if randomize:
        variance = press_time * variance_pct
        low = press_time - variance
        hi = press_time + variance
        press_time = np.random.uniform(low, hi)

    pause_time = .03

    keyboard.press(key)
    await asyncio.sleep(.15)

    press_time -= .15

    if press_time < 0:
        keyboard.release(key)
        return

    for i in range(int(press_time / pause_time)):
        keyboard.press(key)
        await asyncio.sleep(pause_time)

    keyboard.release(key)

def crop_minimap_to_border(im):
    
    copy = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2GRAY)
    
    # crop corners out
    corner_n_px = 20
    copy[:corner_n_px,:corner_n_px] = 0
    copy[-corner_n_px:,:corner_n_px] = 0
    copy[:corner_n_px,-corner_n_px:] = 0
    copy[-corner_n_px:,-corner_n_px:] = 0

    copy[copy > 128] = 255
    copy[copy <= 128] = 0

    white = np.argwhere(copy == 255)

    [min_x, min_y] = np.min(white, axis=0)
    [max_x, max_y] = np.max(white, axis=0)

    return im[min_x:max_x,min_y:max_y], (min_x, max_x, min_y, max_y)

def warning(text):
    print(f'\033[93m{text}\033[0m')

def err(text):
    print(f'\033[91m{text}\033[0m')

def truncate(number, digits):
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper
    