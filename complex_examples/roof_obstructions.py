from glue.scene import Scene

import numpy as np
import os, json, shapely, cv2, pylab
import shapely.wkt
if __name__ == '__main__':


    # Connect to a scene by plan id and set local cache location
    plan_id = '63ed33ed96999b8d50613e0c'
    base_cache_folder = '/Users/nickp/data/cache'
    scene = Scene(plan_id=plan_id, base_cache_folder=base_cache_folder)
    camera = scene.cameras[0]          # first camera
    pixels = [ [2500, 1500] ]          # pixel coordinates in image

    scene.delete_area_annotation()

    import glob
    pylab.figure()
    for filename in glob.glob('/Users/nickp/Desktop/Dropbox/sunrun-ortho/*.jpg'):

        img = cv2.imread(filename)

        boxes = filename.replace("jpg", "json")
        boxes = json.load(open(boxes))

        wkt = filename.replace("jpg", "wkt")
        bound = shapely.wkt.loads(open(wkt).read())
        x, y = bound.exterior.xy
        tile_minx = np.min(x)
        tile_maxx = np.max(x)
        tile_miny = np.min(y)
        tile_maxy = np.max(y)

        for box in boxes:
            minx, miny, maxx, maxy = box['box']

            minlng = tile_minx + (minx / img.shape[1])       * (tile_maxx - tile_minx)
            minlat = tile_miny + (1.0 - miny / img.shape[0]) * (tile_maxx - tile_minx)
            maxlng = tile_minx + (maxx / img.shape[1])       * (tile_maxx - tile_minx)
            maxlat = tile_miny + (1.0 - maxy / img.shape[0]) * (tile_maxx - tile_minx)

            obstruction = [
                dict(lng=minlng, lat=minlat),
                dict(lng=maxlng, lat=minlat),
                dict(lng=maxlng, lat=maxlat),
                dict(lng=minlng, lat=maxlat),
            ]

            pylab.plot(
                [minlng, maxlng, maxlng, minlng, minlng],
                [minlat, minlat, maxlat, maxlat, minlat],
                'r-'
                
            )

            print(obstruction)

            scene.create_area_annotation_latlngs(obstruction)
            # break

    pylab.xticks([])
    pylab.yticks([])
    pylab.axis('equal')
    pylab.show()