import cv2
import numpy as np
import util
from mss import mss
import pygetwindow as gw
import asyncio
import commands
import json
import keyboard
from typing import List, Tuple
import screenshot

PATH_TO_CONFIGS = 'configs/maps/'

minimap_bb = None
player_template = None
rune_template = None

pl_template_matching_thresh = .5
rune_template_matching_thresh = 1e5

player_pos = None
last_player_pos = None

minimap_img = None
rune_mask = None
player_mask = None
maplestory_window_bb = None
window = None
config = None

def setup():
    global player_template, player_mask, rune_template, rune_mask, maplestory_window_bb
    player_template = cv2.imread('assets/player.png')
    player_mask = cv2.imread('assets/player_mask.png')
    rune_template = cv2.imread('assets/rune.png')
    rune_mask = cv2.imread('assets/rune_mask.png')

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

def get_ms_window_bb():
    return maplestory_window_bb

def load_config(config_filename):

    global minimap_bb, window, config

    with open(f'{PATH_TO_CONFIGS}{config_filename}', 'r') as f:
        config = json.load(f)

    if not config:
        raise RuntimeError(f'{config_filename} not found')
        exit(-1)

    windows = gw.getWindowsWithTitle('MapleStory')

    if len(windows) == 0:
        raise RuntimeError('\033[91m'+'maplestory not found')
        exit()
    else:
        window = windows[0]

    minimap_bb = {
        'top': window.top + config['y'],
        'left': window.left + config['x'],
        'width': config['w'],
        'height': config['h'],
    }

    waypoints = config['waypoints']

    return waypoints

def create_config(output_filename):

    global minimap_bb, player_template

    windows = gw.getWindowsWithTitle('MapleStory')

    if len(windows) == 0:
        raise RuntimeError('\033[91m'+'maplestory not found')
        exit()
    else:
        window = windows[0]

    ms_bb = {
        'top': window.top,
        'left': window.left,
        'width': window.width//2,
        'height': window.height//2,
    }

    # select minimap bbox
    sct_ms = np.array(screenshot.grab(ms_bb))[:,:,:3]

    w = 0
    h = 0

    print('Drag a bounding box over the minimap. Make sure the ROI selector window is not over the minimap.')
    while w == 0 or h == 0:
        [x,y,w,h] = cv2.selectROI(sct_ms)
        cv2.destroyAllWindows()
        minimap_bb = {
            'top': window.top+y,
            'left': window.left+x,
            'width': w,
            'height': h
        }

        if w == 0 or h == 0:
            print('w or h is 0, drag a bounding box over the minimap.')

    sct_img = screenshot.grab(minimap_bb)

    img = np.array(sct_img)[:,:,:3]
    waypoints = waypoint_picker(img)

    config = {
        'x': x,
        'y': y,
        'w': w,
        'h': h,
        'waypoints': waypoints
    }

    json_config = json.dumps(config)

    with open(f'{PATH_TO_CONFIGS}{output_filename}', 'w') as f:
        f.write(json_config)

    # return minimap_bb, waypoints

def get_player_pos():

    if player_pos is None:

        if last_player_pos is None:
            util.err('ERR: position.get_player_pos() returning None. Is the minimap visible?')
        else:
            util.warning('WARNING: Player not found on minimap. Returning last known location')
            return last_player_pos

    return player_pos

def get_bounds():
    # todo: make this return corrected bounds
    return minimap_bb['width'], minimap_bb['height']

async def update_minimap():

    global minimap_img

    minimap_bb = {
        'top': window.top + config['y'],
        'left': window.left + config['x'],
        'width': config['w'],
        'height': config['h'],
    }

    sct_img = screenshot.grab(minimap_bb)
    img = np.array(sct_img)[:,:,:3]
    img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

    minimap_img = img
    return img

async def update_position():
    
    global player_pos
    
    pos, top_left, bottom_right = await get_position_from_minimap()
    player_pos = pos

    if player_pos is not None:
        last_player_pos = player_pos

    return pos, top_left, bottom_right

async def get_position_from_minimap():

    img = minimap_img

    # find player
    res = cv2.matchTemplate(img, player_template, cv2.TM_SQDIFF_NORMED, mask=player_mask)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    top_left = min_loc
    bottom_right = (
        top_left[0] + player_template.shape[0],
        top_left[1] + player_template.shape[1]
    )

    if min_val >= pl_template_matching_thresh:
        return None, None, None

    pos = (top_left[0] + (player_template.shape[0] / 2), top_left[1] + (player_template.shape[1] / 2))

    return pos, top_left, bottom_right

async def get_rune_position():

    img = minimap_img
    # find rune
    res = cv2.matchTemplate(img, rune_template, cv2.TM_SQDIFF, mask=rune_mask)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    top_left = min_loc
    bottom_right = (
        top_left[0] + player_template.shape[0],
        top_left[1] + player_template.shape[1]
    )

    if min_val >= rune_template_matching_thresh:
        return None, top_left, bottom_right, min_val

    pos = (top_left[0] + (player_template.shape[0] / 2), top_left[1] + (player_template.shape[1] / 2))

    return pos, top_left, bottom_right, min_val

async def move_to(coords, thresh=20, method='tp'):

    if method == 'tp':
        await move_to_tp(coords, thresh)
    elif method == 'fj':
        await move_to_fj(coords, thresh)
    else:
        print('Unknown move_to method')

async def flashjump(direction):

    keyboard.press(direction)
    await util.hold_key('alt')
    await asyncio.sleep(.1)
    await util.hold_key('alt', press_time=.15)

    if util.random_bool(.5):
        await asyncio.sleep(.05)
        await util.hold_key('alt')
    keyboard.release(direction)

async def move_to_fj(coords, thresh=20):

    if player_pos == None:
        print('position is None!')
        return

    if coords == None:
        print('Coords is None!')
        return

    dist_sq = util.dist_squared(player_pos, coords)
    last_pos = None

    while dist_sq > thresh:

        async def move_towards_x_target():
            if player_pos[0] < coords[0]:
                cmd = 'right'
            else:
                cmd = 'left'

            if dist_sq > 500 or util.random_bool(.05):
                await flashjump(cmd)
            else:
                await util.hold_key(cmd)

        # player not on same y level
        if abs(player_pos[1] - coords[1]) > 10:
            # player below target
            if player_pos[1] > coords[1]:
                last_pos = player_pos
                await util.hold_key(commands.hotkeys['rope lift'])
                await asyncio.sleep(2)

                # cant tp up i guess
                if util.dist_squared(last_pos, player_pos) < 10:
                    print('Player cant rope up here, moving X instead.')

                    if abs(player_pos[0] - coords[0]) > 10:
                        await move_towards_x_target()
                    else:
                        print('Player cant get up here, skipping this waypoint')
                        return
            else:
                last_pos = player_pos
                await util.hold_key('down+alt')
                await asyncio.sleep(2)

                # cant go down i guess
                if util.dist_squared(last_pos, player_pos) < 10:

                    print('Player cant go down here, moving X instead.')

                    if abs(player_pos[0] - coords[0]) > 10:
                        await move_towards_x_target()
                    else:
                        print('Player cant get down here, skipping this waypoint')
                        return

        else:
            await move_towards_x_target()

        # randomly jump
        if util.random_bool(.1):
            await util.hold_key('alt')

        if util.random_bool(.3):
            keyboard.release('left')
            keyboard.release('right')

        last_pos = player_pos

        dist_sq = util.dist_squared(player_pos, coords)
        await asyncio.sleep(.1)

async def move_to_tp(coords, thresh=20):

    if player_pos == None:
        print('position is None!')
        return

    if coords == None:
        print('Coords is None!')
        return

    dist_sq = util.dist_squared(player_pos, coords)
    last_pos = None

    while dist_sq > thresh:
        
        async def move_towards_x_target():

            if player_pos[0] < coords[0]:
                cmd = 'right'
            else:
                cmd = 'left'

            if dist_sq > 200 or util.random_bool(.1):
                cmd += f'+{commands.hotkeys["tp"]}'

            await util.hold_key(cmd)
        
        # player not on same y level
        if abs(player_pos[1] - coords[1]) > 10:
            # player below target
            if player_pos[1] > coords[1]:
                last_pos = player_pos
                await util.hold_key(f'up+{commands.hotkeys["tp"]}')
                await asyncio.sleep(1)

                # cant tp up i guess
                if util.dist_squared(last_pos, player_pos) < 10:
                    print('Player cant tp up here, moving X instead.')

                    if abs(player_pos[0] - coords[0]) > 10:
                        await move_towards_x_target()
                    else:
                        print('Player cant tp up here, skipping this waypoint')
                        return
            else:

                last_pos = player_pos

                if util.random_bool(.5):
                    await util.hold_key('down+alt')
                else:
                    await util.hold_key(f'down+{commands.hotkeys["tp"]}')

                await asyncio.sleep(2)

                # cant go down i guess
                if util.dist_squared(last_pos, player_pos) < 10:

                    print('Player cant go down here, moving X instead.')

                    if abs(player_pos[0] - coords[0]) > 10:
                        await move_towards_x_target()
                    else:
                        print('Player cant get down here, skipping this waypoint')
                        return
        else:
            await move_towards_x_target()

        # randomly jump
        if util.random_bool(.1):
            await util.hold_key('alt')

        last_pos = player_pos

        dist_sq = util.dist_squared(player_pos, coords)
        await asyncio.sleep(.1)

def waypoint_picker(im) -> List[Tuple[int, int]]:
    '''
    NOTE: reset selection with r, confirm with space

    :param im: image to select points from

    :return: list of way points
    '''

    px, py = None, None
    waypoints = []
    count = 0
    def on_click(e, x, y, flags, params):
        # left click 
        nonlocal px, py, count
        if e == cv2.EVENT_LBUTTONDOWN:
            px, py = x, y
            cv2.circle(params[0], (x, y), 3, (0, 250, 50), -1)
            cv2.putText(clone, str(count), (x+5, y-5), 
                cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 50, 250), 1, cv2.LINE_AA)
            waypoints.append((x,y))
            count += 1
    
            print(x, y)
    while True:
        window_name = "way point selector"
        cv2.namedWindow(window_name)
        
        clone = im.copy()
        cv2.setMouseCallback(window_name, on_click, [clone])
            
        while True:
            cv2.imshow(window_name, clone)
            k = cv2.waitKey(20) & 0xFF
            # reset
            if k == ord('r'):
                waypoint = []
                count = 0
                break
            # confirm
            elif k == ord(' '):
                cv2.destroyAllWindows()
                return waypoints
            # quit 
            elif k == ord('q'):
                raise RuntimeError('\033[95m'+"ENDED BY USER")