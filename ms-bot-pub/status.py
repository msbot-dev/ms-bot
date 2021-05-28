import pygetwindow as gw
from mss import mss
import cv2
import numpy as np
import util
import asyncio
import screenshot

window = None

def setup():

    global window
    
    windows = gw.getWindowsWithTitle('MapleStory')

    if len(windows) == 0:
        raise RuntimeError('\033[91m'+'maplestory not found')
        exit()
    else:
        window = windows[0]

    maplestory_window_bb = {
        'top': window.top,
        'left': window.left,
        'width': window.width,
        'height': window.height,
    }

async def update_stats(update_hp=False, update_mp=False):

    if not update_hp and not update_mp:
        util.warning('Update stats was called, but update_hp and update_mp are both false')
        return

    stats_bb = {
        'top': window.top + 741,
        'left': window.left + 611,
        'width': 175,
        'height': 30,
    }
    
    sct_img = screenshot.grab(stats_bb)
    img = np.array(sct_img)[:,:,:3]
    img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

    stats = np.zeros(shape=img.shape)

    # stats[(img[:,:,0] < 100) & (img[:,:,1] > 200) & (img[:,:,2] > 200)] = (0, 0, 1) # mp
    # stats[(img[:,:,0] > 200) & (img[:,:,1] < 200) & (img[:,:,2] <200)] = (1, 0, 0) # hp

    stats[(img[:,:,0] < 200) & (img[:,:,2] > 200)] = (1, 0, 0) # hp
    stats[(img[:,:,0] > 200) & (img[:,:,2] < 200)] = (0, 0, 1) # mp

    hp = 1
    mp = 1

    if update_hp:
        hp = get_bar_pct(stats[:,:,0])
    
    if update_mp:
        mp = get_bar_pct(stats[:,:,2])

    return hp, mp, stats

def get_bar_min_max(img):
    bar_max = np.max(np.transpose(np.where(img == 1)), axis=0)
    bar_min = np.min(np.transpose(np.where(img == 1)), axis=0)

    return bar_min[1], bar_max[1]

def get_bar_pct(stats_im):

    try:
        bar_min, bar_max = get_bar_min_max(stats_im)
        return bar_max / stats_im.shape[1]
    except Exception as e:
        util.err(f'Status (get_bar_pct): {e}')