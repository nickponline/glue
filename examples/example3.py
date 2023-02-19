from glue.scene import Scene

if __name__ == '__main__':

    # Connect to a scene by plan id and set local cache location
    planId = '5df3c67892e8f231d110b585'
    base_cache_folder = '/Users/nickp/data/cache'
    scene = Scene(planId=planId, base_cache_folder=base_cache_folder)
  
    # Crop pointcloud to first area annotation in each view 
    import cv2
    x, y = scene.enu_areas()[0]
    scene.pointcloud.crop_enu(x, y, approx=False)
    for camera in scene.cameras:
        image = scene.pointcloud.view_from(camera)
        cv2.imwrite(f"{camera.index}.png", image)