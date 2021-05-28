import cv2
from mss import mss
import position
import numpy as np
from sklearn.cluster import KMeans

def create_arrow_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    lower_color = np.array([0,150,175])
    upper_color = np.array([90,255,255])
    mask = cv2.inRange(hsv, lower_color, upper_color)
    
    kernel = np.ones((2,2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    kernel = np.ones((2,2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    return mask

def filter_lone_coords(coords, dist_thresh=3, neighbors_thres=10):

    res = []

    for coord in coords:

        d2 = np.linalg.norm(coords - coord, axis=1)
        num_neighbors = len(d2[d2 <= dist_thresh])
        
        if num_neighbors > neighbors_thres:
            res.append(coord)
    
    return np.array(res)
 
def solve_rune(img):

    print('solving...')

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    mask = create_arrow_mask(img)    
    img[mask == 0] = 0
    
    upper = 190
    lower = 120

    # find arrow tips
    color = np.zeros(shape=img.shape)

    color[(img[:,:,0] > 175) & (img[:,:,1] < 150) & (img[:,:,2] < 75)] = (1, 0, 0)
    color[(img[:,:,0] < lower) & (img[:,:,1] > upper) & (img[:,:,2] < lower)] = (0, 1, 0)
    
    greens = np.transpose(np.where(color[:,:,1] == 1))
    reds = np.transpose(np.where(color[:,:,0] == 1))

    # filter
    filtered_greens = filter_lone_coords(greens)
    filtered_reds = filter_lone_coords(reds)

    if len(filtered_greens) == 0 or len(filtered_reds) == 0:
        print('returning none')
        return None
    
    green_mins = np.clip(np.min(filtered_greens, axis=0) - 25, 0, color.shape[:2])
    green_maxs = np.clip(np.max(filtered_greens, axis=0) + 25, 0, color.shape[:2])
    
    is_below_upper_bound = (filtered_reds[:,0] < green_maxs[0]) & (filtered_reds[:,1] < green_maxs[1])
    is_above_lower_bound = (filtered_reds[:,0] > green_mins[0]) & (filtered_reds[:,1] > green_mins[1])
    
    filtered_reds = filtered_reds[is_below_upper_bound & is_above_lower_bound]

    # cluster
    kmeans_green = KMeans(n_clusters=4).fit(filtered_greens)
    kmeans_red = KMeans(n_clusters=4).fit(filtered_reds)
    
    # sort by x
    red_clusters = np.transpose(np.array([kmeans_red.cluster_centers_[:,0], kmeans_red.cluster_centers_[:,1]]))
    red_clusters_idx = np.argsort(red_clusters[:,1])
    red_clusters =  red_clusters[red_clusters_idx]

    green_clusters = np.transpose(np.array([kmeans_green.cluster_centers_[:,0], kmeans_green.cluster_centers_[:,1]]))
    green_clusters_idx = np.argsort(green_clusters[:,1])
    green_clusters = green_clusters[green_clusters_idx]

    # categorize
    diff = red_clusters - green_clusters

    def diff_to_dir(d):
        if abs(d[0]) > abs(d[1]):
            if d[0] < 0:
                return 'up'
            else:
                return 'down'
        else:
            if d[1] < 0:
                return 'left'
            else:
                return 'right'

    return [diff_to_dir(d) for d in diff]