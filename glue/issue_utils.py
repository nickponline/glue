import requests, json
from typing import Dict, List

from .config import config
from .conv_utils import enu2lla
from .pointcloud_utils import PointCloud
from .camera_util import Camera, Transform
from .glue_types import Pixel

class Issue:

    def __init__(self, plan_id: str, folder_id: str, headers: Dict[str, str], pointcloud: PointCloud, transform: Transform):
        self.plan_id = plan_id
        self.folder_id = folder_id
        self.headers = headers
        self.pointcloud = pointcloud
        self.transform = transform

    def delete(self, issue: str):
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
        response = requests.post(f'https://{config.GQL_PREFIX}.dronedeploy.com/graphql', headers=self.headers, data=json.dumps(query))

    def list(self):
        query = {
        "operationName": "LoadPaginatedIssues",
        "variables": {
            "cursor": "",
            "project": f"Project:{self.folder_id}"
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
        response = requests.post(f'https://{config.GQL_PREFIX}.dronedeploy.com/graphql', headers=self.headers, data=json.dumps(query))
        response = response.json()
        for issue in response['data']['project']['issues']['edges']:
            yield (issue['node']['id'])

    def create(self, camera: Camera, pixels: List[Pixel], _pixel_buffer:int=5):

        for xy in pixels:
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
                        "folderId": self.folder_id,
                        "location": {
                            "lat":lat,
                            "lng":lng,
                            "alt":alt
                        },
                        "mediaBoundingPolygon": {
                            # Bounding box in image [0 .. 1] x [0 .. 1]
                            "vertices":vertices
                        },
                        "planId":self.plan_id,
                        "summary":"",
                        "typeId":config.ISSUE_TYPE
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


            response = requests.post(f'https://{config.GQL_PREFIX}.dronedeploy.com/graphql', headers=self.headers, data=json.dumps(issue))
            response = response.json()
            print(json.dumps(response, indent=2))