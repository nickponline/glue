import os, json, requests, cv2, click
import numpy as np

from pathlib import Path
from dataclasses import dataclass

from .pointcloud_utils import PointCloud
from .conv_utils import enu2lla, lla2enu
from .camera_util import Camera, Sensor, Transform
from .mesh_util import Mesh
from .plan_util import Api
from .issue_utils import Issue
from .config import config

class Scene(object):

    def __init__(self, plan_id, base_cache_folder):

        self.plan_id = plan_id
        self.plan = None
        self.transform = None
        self.sensor = None
        self.cameras = []
        self.base_cache_folder = base_cache_folder

        if os.environ.get('DRONEDEPLOY', None) is None:
            print("Please set your 'DRONEDEPLOY' environment variable from the browser")
            print("JS Console -> Application -> Storage -> http://www.dronedeploy.com -> ls.prod_id_token")
            import sys
            sys.exit(0)
        else:
            self.auth = os.environ.get("DRONEDEPLOY")        
        
        self.headers = {
            "authorization": f"Bearer {self.auth}",
            "content-type": "application/json",
        }

        self.init()
        self.issue = Issue(self.plan_id, self.folder_id, self.headers, self.pointcloud, self.transform)
        self.api = Api(self.plan_id, self.headers)

    def init(self):
        self.create_cache()
        print('cache .......... ', click.style('[OK]', fg='green', bold=True), f'({self.cache_folder})')

        self.download_plan()
        print('plan ........... ', click.style('[OK]', fg='green', bold=True))
        
        self.download_cameras()
        print('cameras ........ ', click.style('[OK]', fg='green', bold=True))
    
        self.download_images()
        print('images ......... ', click.style('[OK]', fg='green', bold=True))
    
        self.download_pointcloud()
        print('pointcloud ..... ', click.style('[OK]', fg='green', bold=True))

        self.download_mesh()
        print('mesh ........... ', click.style('[OK]', fg='green', bold=True))
        

    def create_cache(self):
        path = Path(self.base_cache_folder)
        path.mkdir(exist_ok=True)
        path = Path(self.base_cache_folder) / self.plan_id
        path.mkdir(exist_ok=True)

    @property
    def cache_folder(self):
        return Path(self.base_cache_folder) / self.plan_id

    def download_plan(self):
        cache = f'{self.cache_folder}/plan.json'
        if os.path.exists(cache):
            response = json.load(open(cache))
        else:
            response = self.api.get('plan')
            json.dump(response, open(cache, mode='w'))     
        
        self.plan = response
        self.folder_id = self.plan.get('folder_id')
    
    def download_images(self):
        for camera_index, camera in enumerate(self.cameras):
            self.download_image(camera.image)

    def download_image(self, image):
        url = f'https://{config.PREFIX}.dronedeploy.com/api/v2/plans/{self.plan_id}/images/{image}/download?jwt_token={self.auth}'
        local = self.download_signed_url(url, image, ignore_404=False, guess_ext=False)
        return local

    @property
    def extent(self):
        return self.plan['geometry']
    
    @property
    def bounds(self):
        extent = self.extent
        lats = np.array([ point.get('lat') for point in extent ])
        lngs = np.array([ point.get('lng') for point in extent ])
        return [
            lngs.min(),
            lats.min(),
            lngs.max(),
            lats.max(),
        ]
        
    def download_cameras(self):
        cache = f'{self.cache_folder}/cameras.json'
        if os.path.exists(cache):
            response = json.load(open(cache))
        else:
            print("downloading cameras")
            response = requests.get(f'https://{config.PREFIX}.dronedeploy.com/api/v1/camfile/{self.plan_id}', headers=self.headers)
            response = response.json()
            json.dump(response, open(cache, mode='w'))

        sensor_dict = response['sensors'][0]
        W = int(sensor_dict['resolution'].get('width'))
        H = int(sensor_dict['resolution'].get('height'))
        fx = sensor_dict['calibration'].get('fx')
        fy = sensor_dict['calibration'].get('fy')
        cx = sensor_dict['calibration'].get('cx')
        cy = sensor_dict['calibration'].get('cy')
        k1 = sensor_dict['calibration'].get('k1', 0)
        k2 = sensor_dict['calibration'].get('k2', 0)
        k3 = sensor_dict['calibration'].get('k3', 0)
        k4 = sensor_dict['calibration'].get('k4', 0)
        p1 = sensor_dict['calibration'].get('p1', 0)
        p2 = sensor_dict['calibration'].get('p2', 0) 
        sensor = Sensor(W, H, fx, fy, cx, cy, k1, k2, k3, k4, p1, p2)
        
        camera_index = 0
        for camera_dict in response['cameras']:
            transform = camera_dict.get('transform')
            transform = transform.split(" ")
            transform = np.array(transform).astype('float32').reshape((4, 4))

            image = camera_dict.get('image')

            if camera_dict.get('enabled'):
                camera = Camera(transform, sensor, image, self.cache_folder, camera_index)
                self.cameras.append(camera)
                camera_index += 1

        self.transform = Transform(response['transform'])
        
        return self.cameras

    def get_area_annotations(self):
        url = f'https://{config.PREFIX}.dronedeploy.com/api/v2/annotations?plan_id={self.plan_id}&embed=graph'
        response = requests.get(url, headers=self.headers)
        for geometry in response.json():
            if geometry['annotation_type'] == 'AREA':
                # if geometry['color'] == '#fe9700':
                yield geometry['geometry']

    def delete_area_annotation(self):
        url = f'https://{config.PREFIX}.dronedeploy.com/api/v2/annotations?plan_id={self.plan_id}&embed=graph'
        response = requests.get(url, headers=self.headers)
        for geometry in response.json():
            if geometry['annotation_type'] != 'AREA': 
                continue
            # print(geometry['id'])
            url = f'https://{config.PREFIX}.dronedeploy.com/api/v2/annotations/{geometry["id"]}'
            # print(url)
            response = requests.delete(url, headers=self.headers)

    def enu_areas(self):
            ret = []
            for geometry in self.get_area_annotations():
                llas = [[ point['lng'], point['lat'], 0] for point in geometry]
                llas = np.array(llas)
                enu_target = lla2enu(llas, self.transform.Rinv, self.transform.Sinv, self.transform.T)
                x = np.array(enu_target[:, 0])
                y = np.array(enu_target[:, 1])
                ret.append((x, y)) 
            return ret

    def create_area_annotation_latlngs(self, geometry):
        url = f'https://{config.PREFIX}.dronedeploy.com/api/v2/annotations/'
        data = {
            "annotation_type":"AREA",
            "color":"#00ff00",
            "color_locked":False,
            "comments":[],
            "content":[],
            "deleted":False,
            "description":"AI Created Area",
            "fill_color":"#00ff00",
            "geometry":geometry,
            "plan_id": f"{self.plan_id}",
            "type":"markergroup",
            "measurements_3d":[]
        }

        response = requests.post(url, headers=self.headers,  data=json.dumps(data))
        response = response.json()
        print(response)

    def create_area_annotation_ortho(self, xys):

        geometry = []

        for xy in xys:

            lng = self.bounds[0] + (self.bounds[2]-self.bounds[0]) * (xy[0] / self.ortho_width)
            lat = self.bounds[1] + (self.bounds[3]-self.bounds[1]) * (1.0 - xy[1] / self.ortho_height)
            geometry.append(dict(lat=lat, lng=lng))
        
        url = f'https://{config.PREFIX}.dronedeploy.com/api/v2/annotations/'
        data = {
            "annotation_type":"AREA",
            "color":"#00ff00",
            "color_locked":False,
            "comments":[],
            "content":[],
            "deleted":False,
            "description":"AI Created Area",
            "fill_color":"#00ff00",
            "geometry":geometry,
            "plan_id": f"{self.plan_id}",
            "type":"markergroup",
            "measurements_3d":[]
        }

        response = requests.post(url, headers=self.headers,  data=json.dumps(data))
        response = response.json()
        print(response)
    
    def create_count_annotations_latlngs(self, geometry):
        url = f'https://{config.PREFIX}.dronedeploy.com/api/v2/annotations/'
        data = {
            "annotation_type":"COUNT",
            "color": "#f39c12",
            "color_locked":False,
            "comments":[],
            "content":[],
            "deleted":False,
            "description":"AI Count",
            "fill_color": "#e67e22",
            "geometry":geometry,
            "plan_id": f"{self.plan_id}",
            "type":"polygon",
            "measurements_3d":[]
        }

        response = requests.post(url, headers=self.headers,  data=json.dumps(data))
        response = response.json()

    def create_count_annotations(self, camera, xys, _pixel_buffer=15):

        geometry = []
        for xy in xys:
            enu = self.pointcloud.ray_cast(camera, xy)
            lla = enu2lla(enu, self.transform.R, self.transform.S, self.transform.T)
            lng, lat, alt = lla[0]
            geometry.append(dict(lat=lat, lng=lng))

        url = f'https://{config.PREFIX}.dronedeploy.com/api/v2/annotations/'
        data = {
            "annotation_type":"COUNT",
            "color": "#f39c12",
            "color_locked":False,
            "comments":[],
            "content":[],
            "deleted":False,
            "description":"AI Count",
            "fill_color": "#e67e22",
            "geometry":geometry,
            "plan_id": f"{self.plan_id}",
            "type":"polygon",
            "measurements_3d":[]
        }

        response = requests.post(url, headers=self.headers,  data=json.dumps(data))
        response = response.json()

    def download_signed_url(self, signed_url, filename, ignore_404=False, guess_ext=False) -> str:

        local = f'{self.cache_folder}/{filename}'
        if os.path.exists(local):
            # print("CACHE HIR")
            return local
        else:
            print("downloading", filename)
            r = requests.get(signed_url)
            if ignore_404:
                assert r.status_code in (200, 404)
            else:
                assert r.status_code == 200
            if r.status_code == 200:
                if guess_ext:
                    if r.headers["Content-Type"] == "image/jpeg":
                        ext = ".jpg"
                    elif r.headers["Content-Type"] == "image/png":
                        ext = ".png"
                    else:
                        raise("Unknown content-type: " + r.headers["Content-Type"])
                    local_with_ext = local + ext
                else:
                    local_with_ext = local
                open(local_with_ext, "wb").write(r.content)
            elif r.status_code == 404 and ignore_404:
                return ""
        
        if '.zip' in local_with_ext:
            print("Unzipping", local_with_ext)
            os.system(f'unzip {local_with_ext} -d {self.cache_folder}')

        return local_with_ext

    def download_export(self, plan_json, export_filename) -> str:
        cache = f'{self.cache_folder}/{export_filename}'
        if os.path.exists(cache):
            return cache
        signed_url = next( e["url"] for e in plan_json["exports"] if export_filename in e["url"] )
        return self.download_signed_url(signed_url, export_filename)

    def download_pointcloud(self):
        self.download_export(self.plan, "points.zip"),
        pointcloud = self.cache_folder / 'points.las'
        self.pointcloud = PointCloud(pointcloud, self.transform)
        
    def download_mesh(self):
        self.download_export(self.plan, "model.zip"),
        meshfile = self.cache_folder / 'scene_mesh_textured.obj'
        self.mesh = Mesh(str(meshfile))
    
    