glue
====

A small Python library that can download and read assets (images, cameras, mesh, pointcloud, ortho) from a scene and create annotations (area annotations, count annotations, issues).

Installation
---
```
pip3 install -e git+https://github.com/nickponline/glue.git#egg=glue
```


Credentials
---
Set environmental variable `export DRONEDEPLOY=ey..` to your login token accessed from Chrome Javascript Console -> Application -> Storage -> http://www.dronedeploy.com -> ls.prod_id_token

Usage
---
Everything is done after instantiating a `Scene` which is associated with a single plan via the `planId` parameter. 

```python
planId = '5df3c67892e8f231d110b585'
base_cache_folder = '/Users/nickp/data/cache'
scene = Scene(planId=planId, base_cache_folder=base_cache_folder)
```

See `examples.py` for a number of usage examples.
