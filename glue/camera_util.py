from dataclasses import dataclass
import numpy as np

@dataclass
class Sensor:
    W: int = None
    H: int  = None

    fx: float = None
    fy: float = None
    cx: float = None
    cy: float = None

    k1: float = None
    k2: float = None
    k3: float = None
    k4: float = None
    p1: float = None
    p2: float = None

    @property
    def K(self):
        return np.array([self.fx, 0, self.cx, 0, self.fy, self.cy, 0, 0, 1]).reshape((3, 3))

    @property
    def resolution(self):
        return np.array([self.W, self.H])
    
    @property
    def width(self):
        return self.W
    
    @property
    def height(self):
        return self.H
    
    @property
    def distortion(self):
        return np.array([self.k1, self.k2, self.k3, self.k4, self.p1, self.p2])


@dataclass
class Camera:
    transform: None
    sensor: Sensor
    image: str
    cache_folder: str
    index: None

    @property
    def filename(self):
        ret = self.cache_folder / self.image
        ret = str(ret)
        return ret
    
    @property
    def position(self):
        Rinv = self.transform[:3, :3].T
        t = self.transform[:3, 3]
        return -Rinv.dot(t)
    
    @property
    def orientation(self):
        Rinv = self.transform[0:3, 0:3].T
        return Rinv
    
    @property
    def up(self):
        return self.orientation[:, 1]

    @property
    def right(self):
        return self.orientation[:, 0]
    
    @property
    def look(self):
        return self.orientation[:, 2]

    @property
    def K(self):
        return self.sensor.K
    
    @property
    def resolution(self):
        return self.sensor.resolution
    
    @property
    def width(self):
        return self.sensor.width
    
    @property
    def height(self):
        return self.sensor.height
    
    @property
    def distortion(self):
        return self.sensor.distortion

    def display(self):
        import cv2
        img = cv2.imread(self.filename)
        cv2.imshow("image", img)
        cv2.waitKey(0)

    def __repr__(self):
        rep = f'camera {self.image}: {self.position}'
        return rep


class Transform(object):
    def __init__(self, json):


        self.R = None
        self.T = None
        self.S = None
        self.Rinv = None
        self.Sinv = None
        self.parse(json)
       
    def parse(self, json):

        T = json['translation']
        T = [float(t) for t in T.split(" ")]
        self.T = np.array(T).reshape((3, ))

        R = json['rotation']
        R = [float(t) for t in R.split(" ")]
        self.R = np.array(R).reshape((3, 3))

        S = json['scale']
        self.S = float(S)

        self.Rinv = self.R.T
        self.Sinv = 1.0 / self.S
