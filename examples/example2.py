from glue.scene import Scene

if __name__ == '__main__':

   # Connect to a scene by plan id and set local cache location
   planId = '5df3c67892e8f231d110b585'
   base_cache_folder = '/Users/nickp/data/cache'
   scene = Scene(planId=planId, base_cache_folder=base_cache_folder)

   # Fetch first area annotation and crop pointcloud to it   
   x, y = scene.enu_areas()[0]
   scene.pointcloud.crop_enu(x, y, approx=False)
   scene.pointcloud.display(scene.cameras)
