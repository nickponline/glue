from glue.scene import Scene

if __name__ == '__main__':

   # Connect to a scene by plan id and set local cache location
   planId = '5df3c67892e8f231d110b585'
   base_cache_folder = '/Users/nickp/data/cache'
   scene = Scene(planId=planId, base_cache_folder=base_cache_folder)
   
   # Create issue at pixel locations on first cameras image
   camera = scene.cameras[0]
   pixels_of_interest = [
       [1678, 1867],
       [1900, 1874],   
   ]
   scene.create_issue(camera, pixels_of_interest)