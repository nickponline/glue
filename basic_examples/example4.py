from glue.scene import Scene

if __name__ == '__main__':

   # Connect to a scene by plan id and set local cache location
   plan_id = '63e9a6e4ce3aae1d16ad5ea3'
   base_cache_folder = '/Users/nickp/data/cache'
   scene = Scene(plan_id=plan_id, base_cache_folder=base_cache_folder)

   # Crop pointcloud to view cone near pixels in an image
   camera = scene.cameras[0]
   print(camera.filename)
   pixels_of_interest = [
      [1678, 1867],
      [1900, 1874],   
   ]
   scene.pointcloud.crop_xy(scene.cameras[0], pixels_of_interest[0])
   scene.pointcloud.display(scene.cameras)

