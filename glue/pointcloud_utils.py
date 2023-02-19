import numpy as np
import pymap3d, laspy, os
from dataclasses import dataclass

def read_points(filename, is_wgs84=False):
    f = laspy.read(filename)
    points = np.vstack([ f.x, f.y, f.z, f.red / 256, f.green / 256, f.blue / 256, ]).T
    return points

def lla2enu(points, Rinv, Sinv, T):
    ecef = pymap3d.geodetic2ecef(points[:, 1], points[:, 0], points[:, 2])
    ecef = np.vstack(ecef).T
    return Rinv.dot(Sinv).dot( (ecef - T.T).T ).T

def enu2lla(points, R, S, T):
    ecef = R.dot(points.T)*S + T.reshape((3, 1))
    ecef = ecef.T
    lla = np.array(pymap3d.ecef2geodetic(ecef[:, 0], ecef[:, 1], ecef[:, 2])).T
    lla = lla[:, [1, 0, 2]]
    return lla

def las2numpy(Rinv, Sinv, T, pointsfile, numpycloud):
    if os.path.exists(numpycloud):
        return np.load(numpycloud)
    print("loading pointcloud")
    points = read_points(pointsfile)
    print(f"loaded {points.shape} points")
    print("converting to enu")
    colors = points[:, -3:]
    points = lla2enu(points, Rinv, Sinv, T)
    points = np.hstack([points, colors])
    print("saving npy", points.shape)
    np.save(numpycloud, points)
    return points

@dataclass
class PointCloud:
    def __init__(self, points):
        self.points = points
        self.vote = [0] * self.points.shape[0]
        self.total = [0] * self.points.shape[0]

    @property
    def num_points(self):
        return self.points.shape[0]
    
    @property
    def colors(self):
        return self.points[:, -3:]
    
    @property
    def bounds(self):
        return [
            self.points[:, 0].min(),
            self.points[:, 1].min(),
            self.points[:, 0].max(),
            self.points[:, 1].max(),
        ]
    
    def crop_mask(self):
        perc = np.array(self.vote) / np.array(self.total)
        perc = np.where(perc > 0.8)
        self.points = self.points[perc, :]
    
    def crop_mask_update(self, camera, mask):
        projected = self.project(camera)
        projected = (0.5 + projected).astype('int')
        # k1 = projected[:, 0] > 0
        # k2 = projected[:, 0] < camera.width
        # k3 = projected[:, 1] > 0
        # k4 = projected[:, 1] < camera.height
        # projected = projected[k1 & k2 & k3 & k4, :]

        keep = []
        for index, xy in enumerate(projected):
            x, y = xy

            if x < 0 or y < 0 or x >= camera.width or y >= camera.height:
                continue
            if mask[y, x] == 255:
                self.vote[index] += 1

            self.total[index] += 1

        perc = np.array(self.vote) / np.array(self.total)
        perc = np.where(perc > 0.8)
        print(len(perc[0]), self.points.shape)
            
        # print(self.points.shape)
        # self.points = self.points[ keep, :]
        # print(self.points.shape)
        # projected = projected[:, [1, 0]]
        # print(projected)
        # print(projected.max(axis=0))
        # print(camera.width, camera.height)        
        
        # view = np.zeros_like(mask)
        # print(view.shape)
        # view[projected[:, 0], projected[:, 1]] = 255
        # import cv2
        # cv2.imwrite("view.png", view)

    def crop_xy(self, camera, xy, _pixel_buffer=15, return_value=False):
        x, y = xy

        projected = self.project(camera)

        k1 = projected[:, 0] > x - _pixel_buffer
        k2 = projected[:, 0] < x + _pixel_buffer
        k3 = projected[:, 1] > y - _pixel_buffer
        k4 = projected[:, 1] < y + _pixel_buffer

        if return_value:
            return self.points[k1 & k2 & k3 & k4, :3]
        else:
            self.points = self.points[k1 & k2 & k3 & k4, :]

    def ray_cast(self, camera, xy, _pixel_buffer=5):
        cone = self.crop_xy(camera, xy, return_value=True)
        best_ray = np.median(cone, axis=0)
        # best_ray = None
        # best_ray_distance = None
        # for cone_element in cone:
        #     if best_ray is None or np.linalg.norm(camera.position - cone_element) < best_ray_distance:
        #         best_ray_distance = np.linalg.norm(camera.position - cone_element)
        #         best_ray = cone_element
        return np.array( [ best_ray.tolist() ])
    
    def crop_enu(self, x, y, approx=True):
        
        k1 = self.points[:, 0] > x.min()
        k2 = self.points[:, 0] < x.max()
        k3 = self.points[:, 1] > y.min()
        k4 = self.points[:, 1] < y.max()
        self.points = self.points[k1 & k2 & k3 & k4, :]
        if not approx:
            from shapely.geometry import Polygon, Point
            polygon = Polygon( zip(x, y) )
            self.points = np.array([ point for point in self.points if polygon.contains(Point(point[0], point[1]))])
    
    def display(self, cameras=None):
        import open3d as o3d

        if cameras is not None:
            vis = o3d.visualization.Visualizer()
        else:
            vis = o3d.visualization.VisualizerWithEditing()

        vis.create_window(window_name="Open3D", width= 1920, height=1080, visible=True)
        opt = vis.get_render_option()
        opt.background_color = np.asarray([0.0, 0.0, 0.0])
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(self.points[:, :3])
        pcd.colors = o3d.utility.Vector3dVector(self.points[:, -3:] / 256.)
        vis.add_geometry(pcd)
        if cameras is not None:
            camera_points = []
            camera_lines = []
            camera_colors = []

            for index, camera in enumerate(cameras):
                CAMSIZE = 2.0

                position = np.array(camera.position)
                look     = np.array(camera.look)
                right    = np.array(camera.right)
                up       = np.array(camera.up)
                look  = look  / np.linalg.norm(look)
                right = right / np.linalg.norm(right)
                up    = up    / np.linalg.norm(up)

                camera_points.append( position )
                camera_points.append( position + look  )
                camera_points.append( position + CAMSIZE*up + CAMSIZE*right + 2*CAMSIZE*look )
                camera_points.append( position + CAMSIZE*up - CAMSIZE*right + 2*CAMSIZE*look )
                camera_points.append( position - CAMSIZE*up - CAMSIZE*right + 2*CAMSIZE*look )
                camera_points.append( position - CAMSIZE*up + CAMSIZE*right + 2*CAMSIZE*look )
                camera_points.append( position + right  )
                camera_points.append( position + up  )

                camera_lines.append([8*index, 8*index+2])
                camera_lines.append([8*index, 8*index+3])
                camera_lines.append([8*index, 8*index+4])
                camera_lines.append([8*index, 8*index+5])
                camera_lines.append([8*index+2, 8*index+3])
                camera_lines.append([8*index+3, 8*index+4])
                camera_lines.append([8*index+4, 8*index+5])
                camera_lines.append([8*index+5, 8*index+2])
                camera_lines.append([8*index, 8*index+1])
                camera_lines.append([8*index, 8*index+6])
                camera_lines.append([8*index, 8*index+7])

                camera_colors.append([1, 0, 0])
                camera_colors.append([1, 0, 0])
                camera_colors.append([1, 0, 0])
                camera_colors.append([1, 0, 0])
                camera_colors.append([1, 1, 0])
                camera_colors.append([1, 1, 0])
                camera_colors.append([1, 1, 0])
                camera_colors.append([1, 1, 0])
                camera_colors.append([0, 0, 1])
                camera_colors.append([1, 0, 1])
                camera_colors.append([0, 1, 0])

            line_set = o3d.geometry.LineSet()
            line_set.points = o3d.utility.Vector3dVector( np.array(camera_points))
            line_set.lines  = o3d.utility.Vector2iVector( np.array(camera_lines))
            line_set.colors = o3d.utility.Vector3dVector( np.array(camera_colors))
            vis.add_geometry(line_set)
        else:
            pass
        vis.update_renderer()
        vis.run()
        vis.destroy_window()

        if cameras is None:
            picked = vis.get_picked_points()
            print("Picked = ", picked)
            for pick in picked:
                print(pcd.points[pick])

    def project(self, camera):

        pose = camera.transform
        K = camera.K
        distortion = camera.distortion
        points = self.points[:, :3]

        p = np.hstack( (points, np.ones((self.num_points, 1)))).T

        x = pose.dot(p)
        x = x.T
        x = np.asarray(x)

        # check behind?
        x[:, 0] /= x[:, 2]
        x[:, 1] /= x[:, 2]
        x = x[:, :2]

        # distort X
        x2 = x[:, 0] * x[:, 0]
        y2 = x[:, 1] * x[:, 1]
        xy = x[:, 0] * x[:, 1]
        r2 = x2 + y2

        k1, k2, k3, k4, p1, p2 = distortion
        # radial distortion coefficient
        coeff = 1.0 + r2 * (k1 + r2 * (k2 + r2 * (k3 + r2 * k4)))
        # tangential
        x[:, 0] = x[:, 0] * coeff + p1 * xy * 2.0 + p2 * (r2 + x2 * 2.0)
        x[:, 1] = x[:, 1] * coeff + p1 * (r2 + y2 * 2.0) + p2 * xy * 2.0

        x[:, 0] = K[0, 2] + K[0, 0] * x[:, 0]
        x[:, 1] = K[1, 2] + K[1, 1] * x[:, 1]

        return x
    
    def view_from(self, camera):
        import cv2
        img = cv2.imread(camera.filename)
        pcl = np.zeros_like(img)
        projected = self.project(camera)
        
        for index, xy in enumerate(projected):
            x, y = xy
            x = int(x + 0.5)
            y = int(y + 0.5)
            if x > 0 and x < camera.width and y > 0 and y < camera.height:
                color = self.points[index, -3:]
                cv2.circle(pcl, (x, y), 3, color[::-1], -1)    
        return pcl
    
    def __repr__(self):
        rep = f'pointcloud {self.points.shape[0]} points'
        return rep
