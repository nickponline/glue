from glue.scene import Scene

if __name__ == '__main__':

   # Connect to a scene by plan id and set local cache location
   planId = '5df3c67892e8f231d110b585'
   base_cache_folder = '/Users/nickp/data/cache'
   scene = Scene(planId=planId, base_cache_folder=base_cache_folder)

   
   # Create area annotations at xy pixels on preview ortho
   import random
   xys = [
       [ random.randint(0, scene.ortho_width), random.randint(0, scene.ortho_height)] for _ in range(3)
   ]
   scene.create_area_annotation_ortho(xys)
