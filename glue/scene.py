import os, json, requests, cv2, click
import numpy as np

from pathlib import Path
from dataclasses import dataclass

from .pointcloud_utils import PointCloud, las2numpy, enu2lla, lla2enu
from .camera_util import Camera, Sensor, Transform
from .mesh_util import Mesh
import os

PREFIX = 'www'
GQL_PREFIX = 'api'
ISSUE_TYPE = 'IssueType:624'


class Scene(object):

    def __init__(self, planId, base_cache_folder):

        self.planId = planId

        if os.environ.get('DRONEDEPLOY', None) is None:
            print("Please set your DRONEDEPLOY environment variable ")
            print("from Chrome JS Console -> Application -> Storage -> http://www.dronedeploy.com -> ls.prod_id_token")
            import sys
            sys.exit(0)
        else:
            self.auth = os.environ.get("DRONEDEPLOY")        
        
        self.headers = {
            "authorization": f"Bearer {self.auth}",
            "content-type": "application/json",
        }

        self.cameras = []
        self.plan = None
        self.transform = None
        self.sensor = None
        self.base_cache_folder = base_cache_folder

        self.create_cache()
        print('cache .......... ', click.style('[OK]', fg='green', bold=True))
    
        self.download_cameras()
        print('cameras ........ ', click.style('[OK]', fg='green', bold=True))
    
        self.download_plan()
        print('plan ........... ', click.style('[OK]', fg='green', bold=True))
        self.folderId = self.plan.get('folder_id')
        print('images ......... ', click.style('[OK]', fg='green', bold=True))
        self.download_images()
    
        self.download_pointcloud()
        print('pointcloud ..... ', click.style('[OK]', fg='green', bold=True))

        self.download_mesh()
        print('mesh ........... ', click.style('[OK]', fg='green', bold=True))
        
        self.download_preview_ortho()
        print('orthomosaic .... ', click.style('[OK]', fg='green', bold=True))

    def create_cache(self):
        path = Path(self.base_cache_folder)
        path.mkdir(exist_ok=True)
        path = Path(self.base_cache_folder) / self.planId
        path.mkdir(exist_ok=True)

    @property
    def cache_folder(self):
        return Path(self.base_cache_folder) / self.planId

    def download_plan(self):
        cache = f'{self.cache_folder}/plan.json'
        if os.path.exists(cache):
            response = json.load(open(cache))
        else:
            response = requests.get(f'https://{PREFIX}.dronedeploy.com/api/v1/plan/{self.planId}', headers=self.headers)
            response = response.json()
            json.dump(response, open(cache, mode='w'))     
        self.plan = response
    
    def download_images(self):
        for camera_index, camera in enumerate(self.cameras):
            self.download_image(camera.image)

    def download_image(self, image):
        url = f'https://{PREFIX}.dronedeploy.com/api/v2/plans/{self.planId}/images/{image}/download?jwt_token={self.auth}'
        local = self.download_signed_url(url, image, ignore_404=False, guess_ext=False)
        return local
        
    def delete_issue(self, issue):
        query = {
            "operationName":"DeleteIssue",
            "variables":{
                "input":{
                    "id": issue,
                    "deleted": True
                }
            },
            "query": """
                mutation DeleteIssue($input: UpdateIssueInput!) {
                    updateIssue(input: $input) {
                        issue {
                        id
                        }
                    }
                }
            """
        }
        response = requests.post(f'https://{GQL_PREFIX}.dronedeploy.com/graphql', headers=self.headers, data=json.dumps(query))

    def list_issues(self):
        query = {
        "operationName": "LoadPaginatedIssues",
        "variables": {
            "cursor": "",
            "project": f"Project:{self.folderId}"
        },
        "query": """query LoadPaginatedIssues($project: ID!, $cursor: String) {
            project(id: $project) {
                issues(first: 100, after: $cursor) {
                    edges {
                        node {
                            ...IssueView
                        }
                    }
        
                }
            }
        }
        fragment IssueView on Issue {
            id
            createdIn
            folder {
                id
            }
            initialPlan {
                id
            }
            location {
                lng
                lat
                alt
            }
        }
        """
        }
        response = requests.post(f'https://{GQL_PREFIX}.dronedeploy.com/graphql', headers=self.headers, data=json.dumps(query))
        response = response.json()
        for issue in response['data']['project']['issues']['edges']:
            yield (issue['node']['id'])

    def create_issue_ortho(self, xys):

        for xy in xys:

            lng = self.bounds[0] + (self.bounds[2]-self.bounds[0]) * (xy[0] / self.ortho_width)
            lat = self.bounds[1] + (self.bounds[3]-self.bounds[1]) * (1.0 - xy[1] / self.ortho_height)

            data = {   
                "annotation_type":"LOCATION",
                "color":"#00bbd3",
                "color_locked":False,
                "comments":[],
                "content":[],
                "deleted":False,
                "description":"",
                "fill_color":"#40ccde",
                "geometry":{
                    "lat":lat,
                    "lng":lng
                },
                "info":{
                    "geometry":[
                        {
                            "type":"Coords",
                            "value":{
                                "lat":lat,
                                "lng":lng
                            }
                        }
                    ],
                    "ml_assisted":False
                },
                "plan_id":self.planId,
                "type":"marker",
                "issue":{
                    "created_in":"2d",
                    "location":{
                        "lat":lat,
                        "lng":lng,
                        "alt":0
                    },
                    "type_id":ISSUE_TYPE
                },
                "measurements_3d":[]
            }

            url = f'https://{PREFIX}.dronedeploy.com/api/v2/annotations/'
            response = requests.post(url, headers=self.headers,  data=json.dumps(data))
            response = response.json()

    def create_issue(self, camera, xys, _pixel_buffer=5):

        for xy in xys:
            enu = self.pointcloud.ray_cast(camera, xy)
            lla = enu2lla(enu, self.transform.R, self.transform.S, self.transform.T)
            vertices = [
                dict(x=(xy[0] - _pixel_buffer) / camera.width, y=(xy[1] - _pixel_buffer) / camera.height),
                dict(x=(xy[0] + _pixel_buffer) / camera.width, y=(xy[1] - _pixel_buffer) / camera.height),
                dict(x=(xy[0] + _pixel_buffer) / camera.width, y=(xy[1] + _pixel_buffer) / camera.height),
                dict(x=(xy[0] - _pixel_buffer) / camera.width, y=(xy[1] + _pixel_buffer) / camera.height),
                dict(x=(xy[0] - _pixel_buffer) / camera.width, y=(xy[1] - _pixel_buffer) / camera.height),
            ]
            
            lng, lat, alt = lla[0]

            issue = {
                "operationName":"CreateIssue",
                "variables":{
                    "input":{
                        "assetName": camera.image,
                        "createdIn": "3d",
                        "folderId": self.folderId,
                        "location": {
                            # Fetch 3D coordinates from pointcloud
                            "lat":lat,
                            "lng":lng,
                            "alt":alt
                        },
                        "mediaBoundingPolygon": {
                            # Bounding box in image [0 .. 1] x [0 .. 1]
                            "vertices":vertices
                        },
                        "planId":self.planId,
                        "summary":"",
                        "typeId":ISSUE_TYPE
                    }
                },

                "query": """

                mutation CreateIssue($input: CreateIssueInput!) {
                    createIssue(input: $input) {
                        issue {
                            ...FullIssue
                        }
                    }
                }
                fragment FullIssue on Issue {
                    id
                    closedPlan {
                        id
                    }
                    createdBy {
                        id
                        firstName
                        lastName
                        username
                    }
                    createdIn
                        comments {
                            id
                            body
                            createdBy {
                                username
                                firstName
                                lastName
                            }
                            dateCreation
                        }
                    dateClosed
                    dateCreation
                    dateModified
                    folder {
                        id
                    }
                    initialPlan {
                        id
                    }
                    issueProjectNumber
                    location {
                        alt
                        lat
                        lng
                    }
                    modifiedBy {
                        id
                        firstName
                        lastName
                        username
                    }
                    organization {
                        id
                        name
                        currencyCode
                    }
                    repairCost
                    severity {
                        ...IssueSeverity
                    }
                    statusName
                    summary
                    type {
                        ...IssueType
                    }
                    views {
                        id
                        assetUrl
                        assetPath
                        dateCreation
                        dateModified
                        mediaBoundingPolygon {
                            vertices {
                                x
                                y
                            }
                        }
                    }
                    externalIssues {
                        appId
                        id
                        externalId
                        externalUrl
                        context
                    }
                }
                fragment IssueSeverity on IssueSeverity {
                    id
                    name
                    value
                }
                fragment IssueType on IssueType {
                    id
                    name
                    isDefault
                }
                """
            }


            response = requests.post(f'https://{GQL_PREFIX}.dronedeploy.com/graphql', headers=self.headers, data=json.dumps(issue))
            response = response.json()
            # print(json.dumps(response, indent=2))

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
    
    @property
    def ortho_width(self):
        filename = self.cache_folder / 'ortho_thumbnail.png'
        img = cv2.imread(str(filename))
        return img.shape[1]

    @property
    def ortho_height(self):
        filename = self.cache_folder / 'ortho_thumbnail.png'
        img = cv2.imread(str(filename))
        return img.shape[0]

    
    def download_cameras(self):
        cache = f'{self.cache_folder}/cameras.json'
        if os.path.exists(cache):
            response = json.load(open(cache))
        else:
            print("downloading cameras")
            response = requests.get(f'https://{PREFIX}.dronedeploy.com/api/v1/camfile/{self.planId}', headers=self.headers)
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
        url = f'https://{PREFIX}.dronedeploy.com/api/v2/annotations?plan_id={self.planId}&embed=graph'
        response = requests.get(url, headers=self.headers)
        for geometry in response.json():
            if geometry['annotation_type'] == 'AREA':
                # if geometry['color'] == '#fe9700':
                yield geometry['geometry']

    def delete_annotation(self):
        url = f'https://{PREFIX}.dronedeploy.com/api/v2/annotations?plan_id={self.planId}&embed=graph'
        response = requests.get(url, headers=self.headers)
        for geometry in response.json():
            # print(geometry['id'])
            url = f'https://{PREFIX}.dronedeploy.com/api/v2/annotations/{geometry["id"]}'
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

    def create_count_annotations_latlngs(self, geometry):
        url = f'https://{PREFIX}.dronedeploy.com/api/v2/annotations/'
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
            "plan_id": f"{self.planId}",
            "type":"polygon",
            "measurements_3d":[]
        }

        response = requests.post(url, headers=self.headers,  data=json.dumps(data))
        response = response.json()

    def create_area_annotation_latlngs(self, geometry):
        url = f'https://{PREFIX}.dronedeploy.com/api/v2/annotations/'
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
            "plan_id": f"{self.planId}",
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

        
        url = f'https://{PREFIX}.dronedeploy.com/api/v2/annotations/'
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
            "plan_id": f"{self.planId}",
            "type":"markergroup",
            "measurements_3d":[]
        }

        response = requests.post(url, headers=self.headers,  data=json.dumps(data))
        response = response.json()
        print(response)

    def create_count_annotations(self, camera, xys, _pixel_buffer=15):

        geometry = []
        for xy in xys:
            enu = self.pointcloud.ray_cast(camera, xy)
            lla = enu2lla(enu, self.transform.R, self.transform.S, self.transform.T)
            lng, lat, alt = lla[0]
            geometry.append(dict(lat=lat, lng=lng))

        url = f'https://{PREFIX}.dronedeploy.com/api/v2/annotations/'
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
            "plan_id": f"{self.planId}",
            "type":"polygon",
            "measurements_3d":[]
        }

        response = requests.post(url, headers=self.headers,  data=json.dumps(data))
        response = response.json()

    # TODO: This is not entirely accurate as we don't have accurate bounds
    def create_count_annotations_ortho(self, xys):

        geometry = []

        for xy in xys:
            lng = self.bounds[0] + (self.bounds[2]-self.bounds[0]) * (xy[0] / self.ortho_width)
            lat = self.bounds[1] + (self.bounds[3]-self.bounds[1]) * (1.0 - xy[1] / self.ortho_height)
            geometry.append(dict(lat=lat, lng=lng))

        url = f'https://{PREFIX}.dronedeploy.com/api/v2/annotations/'
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
            "plan_id": f"{self.planId}",
            "type":"polygon",
            "measurements_3d":[]
        }

        response = requests.post(url, headers=self.headers,  data=json.dumps(data))
        response = response.json()

    def download_preview_ortho(self) -> str:

        cache = f'{self.cache_folder}/ortho_thumbnail.png'
        if os.path.exists(cache):
            return cache

        project_resp = requests.get(
            f"https://{PREFIX}.dronedeploy.com/api/v1/folders/{self.folderId}",
            headers=self.headers,
            params={"type": "site", "include_thumbnail_urls": "ortho"},
        )


        assert project_resp.status_code == 200
        project_json = project_resp.json()
        signed_ortho_url = project_json["thumbnails"]["ortho_thumbnail_url"]
        assert ".png" in signed_ortho_url
        return self.download_signed_url(signed_ortho_url, "ortho_thumbnail.png")


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
        
        signed_url = next(
            e["url"] for e in plan_json["exports"]
            if export_filename in e["url"]
        )
        return self.download_signed_url(signed_url, export_filename)

    def download_pointcloud(self):
        self.download_export(self.plan, "points.zip"),
        pointcloud = self.cache_folder / 'points.las'
        numpycloud = self.cache_folder / 'points.npy'
        points = las2numpy(self.transform.Rinv, self.transform.Sinv, self.transform.T, pointcloud, numpycloud)
        self.pointcloud = PointCloud(points)
        
    def download_mesh(self):
        self.download_export(self.plan, "model.zip"),
        meshfile = self.cache_folder / 'scene_mesh_textured.obj'
        self.mesh = Mesh(str(meshfile))
    
    