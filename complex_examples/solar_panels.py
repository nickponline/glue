from shapely.geometry import Polygon
from glue.scene import Scene
from shapely.ops import cascaded_union

import glob
import numpy as np
import cv2
import pylab
import shapely.wkt

def post_process(folder, wkt_folder):
   

    print(wkt_folder + "/*.wkt")
    print(folder + "/prediction-*.png")
    wkts = sorted(glob.glob(wkt_folder + "/*.wkt"))
    filenames = sorted(glob.glob(folder + "/prediction-*.png"))
    print(len(wkts), len(filenames))

    polygons = []
    bounds = []
    for index, (filename, wkt) in enumerate(zip(filenames, wkts)):
        print(index, "/", len(filenames))
        # print(filename)
        img = cv2.imread(filename, 0)
        # print(img.shape)
        bound = shapely.wkt.loads(open(wkt).read())
        x, y = bound.exterior.xy
        minx = np.min(x)
        maxx = np.max(x)
        miny = np.min(y)
        maxy = np.max(y)

        p2d = (maxy - miny)/img.shape[0]*0.5 + (maxx - minx)/img.shape[1]*0.5
        print("p2d:", p2d)
        locs = np.where(img == 76)
        mask = np.zeros_like(img)
        mask[locs] = 255
        kernel = np.ones((50, 50), np.uint8)
        # cv2.imshow("mask", mask)
        # cv2.waitKey(0)


        mask = cv2.dilate(mask, kernel, iterations=1)
        mask = cv2.erode(mask, kernel, iterations=1)
        
        # cv2.imshow("mask", mask)
        # cv2.waitKey(0)

        contours, hierarchy = cv2.findContours(mask,  cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        
        for contour in contours:
            # print(contour.shape)
            contour = np.squeeze(contour)
            contour = contour.astype('float')
            contour[:, 0] = minx + (contour[:, 0].astype('float') / img.shape[1]) * (maxx - minx)
            contour[:, 1] = miny + (1.0 - contour[:, 1].astype('float') / img.shape[0]) * (maxy - miny)

            if len(contour.shape) != 2:
                continue

            
            if contour.shape[0] < 3:
                continue
            
            polygon = Polygon(contour)

            # print("XXX")
            # print("->")
            # print("  ", len(polygon.exterior.xy[0]))
            polygon = polygon.convex_hull
            # polygon = polygon.simplify(tolerance=p2d / 5.)
            # print("  ", len(polygon.exterior.xy[0]))

            bounds.append(bound)
            polygons.append(polygon)

    # pylab.figure()
    # for polygon, bound in zip(polygons, bounds):
    #     pylab.plot(*polygon.exterior.xy, 'k-')
    #     pylab.plot(*bound.exterior.xy, 'r-')
    # pylab.axis('equal')
    # pylab.show()

    print(len(polygons))
    filtered = []

    _bs = 50 * p2d
    for pi, polygon in enumerate(polygons):
        print(pi, "->", len(polygons))

        early_add = False
        for i, f in enumerate(filtered):
            if f.buffer(_bs).intersects(polygon.buffer(_bs)):
                filtered[i] = f.buffer(_bs).union(polygon.buffer(_bs)).buffer(-_bs)
                early_add = True
                break

        if not early_add:
            filtered.append(polygon)
    
    print(len(filtered))
    pylab.figure()
    for polygon in filtered:
        pylab.plot(*polygon.exterior.xy, 'k-')
    pylab.axis('equal')
    pylab.show()

    from shapely.ops import cascaded_union
    return cascaded_union(filtered)

    ret = [ poly2latlng(polygon) for polygon in filtered ]
    return ret

def poly2latlng(polygon):

    ret = [dict(lng=x, lat=y) for x, y in zip(*polygon.exterior.xy)]
    return ret
        

if __name__ == '__main__':
    planId='5df3c67892e8f231d110b585'
    base_cache_folder = '/Users/nickp/data/cache'
    scene = Scene(planId=planId, base_cache_folder=base_cache_folder)
    A = post_process('/Users/nickp/Dropbox/solar-1-output', '/Users/nickp/Dropbox/solar-1')

    planId='5df3d00192e8f231d110b58a'
    base_cache_folder = '/Users/nickp/data/cache'
    scene = Scene(planId=planId, base_cache_folder=base_cache_folder)
    B = post_process('/Users/nickp/Dropbox/solar-2-output', '/Users/nickp/Dropbox/solar-2')

    with open('A.txt', mode='w') as f:
        f.write(A.wkt)

    with open('B.txt', mode='w') as f:
        f.write(B.wkt)

    A = shapely.wkt.loads(open("A.txt").read())
    B = shapely.wkt.loads(open("B.txt").read())

    pylab.figure()
    pylab.subplot(1, 2, 1)
    for polygon in A.geoms:
        pylab.plot(*polygon.exterior.xy, 'r-')
    pylab.subplot(1, 2, 2)
    for polygon in B.geoms:
        pylab.plot(*polygon.exterior.xy, 'b-')
    pylab.axis('equal')
    pylab.show()

    P = B.difference(A.buffer(0.00002))
    print(P)
    print(type(P))

    pylab.figure()
    for polygon in P.geoms:
        pylab.plot(*polygon.exterior.xy, 'g-')
    pylab.axis('equal')
    pylab.show()

    
  