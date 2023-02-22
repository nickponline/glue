from glue.scene import Scene

if __name__ == '__main__':

    # Connect to a scene by plan id and set local cache location
    plan_id = '63e9a6e4ce3aae1d16ad5ea3'
    base_cache_folder = '/Users/nickp/data/cache'
    scene = Scene(plan_id=plan_id, base_cache_folder=base_cache_folder)
    scene.pointcloud.display(scene.cameras)