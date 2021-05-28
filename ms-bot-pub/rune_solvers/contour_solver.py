import cv2
import numpy as np
import argparse
import math
import sys

    # ----------- gray scale approach --------------------------
    # w = [0.0445, 0.6568, 0.2987]
    # img = cv2.convertScaleAbs(np.sum(hsv * w, axis=2))

    # mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, (1,1))
    # mask_flippedBNW = cv2.bitwise_not(mask)
    # ----------------------------------------------------------

def near_edge(cx, cy, img_w, img_h, threshold=.1):
    # checks y borders (top and bottom)
    if cy <= img_h*threshold or cy >= img_h*(1 - threshold):
        return True
    
    # checks x borders (left and right)
    if cx <= img_w*threshold or cx >= img_w*(1 - threshold):
        return True

    return False


def create_arrow_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_color = np.array([0,50,150])
    upper_color = np.array([90,255,255])
    mask = cv2.inRange(hsv, lower_color, upper_color)
    kernel = np.ones((4, 4), np.uint8)
    mask = cv2.erode(mask, kernel, iterations=1)
    kernel = np.ones((2,2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    return mask

def tip_processing(arrow_block):
    red_mask = cv2.inRange(arrow_block, (0,0,80), (100,100,255))
    red_mask = cv2.cvtColor(red_mask, cv2.COLOR_GRAY2BGR)
    arrow_block = cv2.bitwise_and(arrow_block, red_mask)
    arrow_tip_BNW = cv2.cvtColor(arrow_block, cv2.COLOR_BGR2GRAY)
    ret, arrow_tip_BNW = cv2.threshold(arrow_tip_BNW, 100, 255, 0)
    kernel = np.ones((3,3), np.uint8)
    arrow_tip_BNW = cv2.morphologyEx(arrow_tip_BNW, cv2.MORPH_CLOSE, kernel)


    return arrow_tip_BNW


def solve_one_contour(c, colored_block, cX, cY, polydp, debugMode=False):
    # ret, thresh = cv2.threshold(b, 180, 255, cv2.THRESH_BINARY_INV)

    # find contours
    # contours, hierarchy = cv2.findContours(b, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # arrow bbox
    [x, y, w, h] = cv2.boundingRect(polydp)
    
    # get the tip of the arrow by segmenting the red out of it
    b_colored = colored_block[y:y+h, x:x+w]
    arrow_tip_BNW = tip_processing(b_colored)

    # arrow tip location (realtvie to the arrow box)
    m_tip = cv2.moments(arrow_tip_BNW)
    cX_tip = x+int(m_tip["m10"] / m_tip["m00"]) # (+x to get the x relative to the whole croped area)
    cY_tip = y+int(m_tip["m01"] / m_tip["m00"])

    if (debugMode):
        temp = colored_block.copy()
        cv2.circle(temp, (cX_tip, cY_tip), 1, (0, 0, 255), -1)
        cv2.circle(temp, (cX, cY), 1, (255, 0, 0), -1)
        cv2.rectangle(temp, (x,y), (x+w, y+h), (0,125,255), 1)
        cv2.imshow("contour", temp)
        cv2.waitKey(0)

    x_dis = (cX - cX_tip)**2
    y_dis = (cY - cY_tip)**2

    # left or right
    if (x_dis > y_dis):
        if (cX > cX_tip):
            return "left"
        else:
            return "right"
    # up or down
    else:
        if (cY > cY_tip):
            return "up"
        else:
            return "down"

def solve_rune(img, isPath=False, debugMode=False):
    """
        :param img: the CROPPED area for the runes
        NOTE: this cropped area should be very precise! every arrow bounding box should take up even space
                or this might crash :(

        :return: list of commands (List<str>)
    """
    if (isPath):
        img = cv2.imread(img)
    
    try:
        w, h, c = img.shape
    
    except:
        raise ValueError("not valid image passed in brah, it needs to be colored :(")
    
    # pre processing
    mask = create_arrow_mask(img)

    if (debugMode):
        cv2.imshow('masked', mask)
        cv2.waitKey(0)
    
    w, h = mask.shape[::-1]
    # defind four boxes
    # BLOCKWIDTH = w // 4
    # blocks = [mask[: ,i*BLOCKWIDTH:(i+1)*BLOCKWIDTH] for i in range(4)]
    # colored_blocks = [img[: ,i*BLOCKWIDTH:(i+1)*BLOCKWIDTH] for i in range(4)]

    # find contours
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    result = []
    for c in contours:
        area = cv2.contourArea(c)

        # discard noises
        if (area < 100):
            continue

        polydp = cv2.approxPolyDP(c, 3, True)
        # center point of arrow
        m = cv2.moments(polydp)

        try:
            cX = int(m["m10"] / m["m00"])
            cY = int(m["m01"] / m["m00"])
        except:
            print('Contour solver: Divide by 0 err')
            return []

        # case when there's random big blocks around the edge
        # we don't process those b/c its not an arrow
        # if (near_edge(cX, cY, w, h)):
        #     continue
        
        try:
            curr_res = solve_one_contour(c, img, cX, cY, polydp, debugMode)
            result.append((curr_res, cX))
        except Exception as e:
            if (debugMode):
                print(f'----------- detection for contour failed --------------------')
                print(f'ERR: {e}')
    
    return [arr[0] for arr in sorted(result, key=lambda x: x[1])]

    # commands = []
    # for i, b in enumerate(blocks):
    #     try:
    #         commands.append(solve_one_block(b, i, colored_blocks, debugMode))
    #     except Exception as e:
    #         if (debugMode):
    #             print(f'----------- detection for arrow {i} failed --------------------')
    #             print(e)
    #         commands.append(None)
    # return commands

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('-i', '--image')
    ap.add_argument('-db', '--debug', action="store_true", help="debug mode (ALL)")

    args = ap.parse_args()
    
    print(detect_arrows(args.image, True, args.debug))