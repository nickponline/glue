from glue.scene import Scene

if __name__ == '__main__':

   # Connect to a scene by plan id and set local cache location
   plan_id = '63e9a6e4ce3aae1d16ad5ea3'
   base_cache_folder = '/Users/nickp/data/cache'
   scene = Scene(plan_id=plan_id, base_cache_folder=base_cache_folder)

   
   # Create area annotations at xy pixels on preview ortho
   import random
   xys = [
       [ random.randint(0, scene.ortho_width), random.randint(0, scene.ortho_height)] for _ in range(3)
   ]
   scene.create_area_annotation_ortho(xys)
