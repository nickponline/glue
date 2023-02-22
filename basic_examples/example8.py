from glue.scene import Scene

if __name__ == '__main__':

   # Connect to a scene by plan id and set local cache location
   plan_id = '63e9a6e4ce3aae1d16ad5ea3'
   base_cache_folder = '/Users/nickp/data/cache'
   scene = Scene(plan_id=plan_id, base_cache_folder=base_cache_folder)

   # Create area annotations at lat lngs 
   import random
   latlngs = [
       dict(lat=random.uniform(scene.bounds[1], scene.bounds[3]), lng=random.uniform(scene.bounds[0], scene.bounds[2])) for _ in range(3)
   ]
   scene.create_area_annotation_latlngs(latlngs)
