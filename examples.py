from glue.scene import Scene

if __name__ == '__main__':

    # Connect to a scene by plan id and set local cache location
    planId = '5df3c67892e8f231d110b585'
    base_cache_folder = '/Users/nickp/data/cache'
    scene = Scene(planId=planId, base_cache_folder=base_cache_folder)

    # Example 1. Display mesh and pointcloud    
    # scene.pointcloud.display()
    # scene.mesh.display()
    # scene.mesh.display(scene.cameras)

    # Example 2. Fetch first area annotation and crop pointcloud to it   
    # print(scene.pointcloud.points[0])
    # import glob
    # x, y = scene.enu_areas()[0]
    # scene.pointcloud.crop_enu(x, y, approx=False)
       # scene.mesh.display(scene.cameras)
  
    # Example 3. Crop pointcloud to first area annotation in each view 
    # import cv2
    # x, y = scene.enu_areas()[0]
    # scene.pointcloud.crop_enu(x, y, approx=False)
    # for camera in scene.cameras:
    #     image = scene.pointcloud.view_from(camera)
    #     cv2.imwrite(f"{camera.index}.png", image)
    
    # Example 4. Crop pointcloud to view cone near pixels in an image
    # camera = scene.cameras[0]
    # print(camera.filename)
    # pixels_of_interest = [
    #     [1678, 1867],
    #     [1900, 1874],   
    # ]
    # scene.pointcloud.crop_xy(scene.cameras[0], pixels_of_interest[0])
    # scene.pointcloud.display(scene.cameras)


    # Example 5. Create count annotations on ortho as pixel location in image
    # pixels_of_interest = [
    #     [1678, 1867],
    #     [1900, 1874],   
    # ]
    # scene.create_count_annotations(scene.cameras[0], pixels_of_interest)

    # Example 6. Create count annotations on ortho as pixel location 
    # pixels_of_interest = [
    #     [710, 560]
    # ]
    # scene.create_count_annotations_ortho(pixels_of_interest)
    
    # Example 7. Create count annotations at lat lngs 
    # import random
    # latlngs = [
    #     dict(lat=random.uniform(scene.bounds[1], scene.bounds[3]), lng=random.uniform(scene.bounds[0], scene.bounds[2])) for _ in range(5)
    # ]
    # scene.create_count_annotations_latlngs(latlngs)
    
    # Example 8. Create area annotations at lat lngs 
    # import random
    # latlngs = [
    #     dict(lat=random.uniform(scene.bounds[1], scene.bounds[3]), lng=random.uniform(scene.bounds[0], scene.bounds[2])) for _ in range(3)
    # ]
    # scene.create_area_annotation_latlngs(latlngs)

    # Example 9. Create area annotations at xy pixels on preview ortho
    # import random
    # xys = [
    #     [ random.randint(0, scene.ortho_width), random.randint(0, scene.ortho_height)] for _ in range(3)
    # ]
    # scene.create_area_annotation_ortho(xys)
    
    # Example 10. Create issue at pixel locations on first cameras image
    # camera = scene.cameras[0]
    # pixels_of_interest = [
    #     [1678, 1867],
    #     [1900, 1874],   
    # ]
    # scene.create_issue(camera, pixels_of_interest)

    # Example 11. Creat issue on ortho at pixel coordiantes
    # import random
    # xys = [
    #     [ random.randint(0, scene.ortho_width), random.randint(0, scene.ortho_height)] for _ in range(5)
    # ]
    # scene.create_issue_ortho(xys)