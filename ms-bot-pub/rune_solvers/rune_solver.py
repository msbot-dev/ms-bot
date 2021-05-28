import cv2
from mss import mss
import position
import numpy as np
import rune_solvers.contour_solver as contour_solver
import rune_solvers.color_solver as color_solver
import pygetwindow as gw
import util
import screenshot

def solve_rune(method='color'):
    # this is so we can print COLORED text in terminal 
    print(f'Rune solver: solving with method={method}')

    ms_bb = position.get_ms_window_bb()

    # TODO: make this bounding box relative to window size
    bb = {
        'top': ms_bb['top'] + 150,
        'left': ms_bb['left'] + 375,
        'width': 690,
        'height': 200
    }
    
    img = np.array(screenshot.grab(bb))[:,:,:3]

    if method == 'contour':
        detections = contour_solver.solve_rune(img)
    elif method == 'color':
        detections = color_solver.solve_rune(img)
    else:
        print(f'Rune solver: method "{method}" unknown')
        return None

    if detections is None or len(detections) != 4:
        util.warning("Rune solver: ERROR: something wrong happened :(")
        util.warning(f"heres what we found: {detections}")
        return None
    
    return detections