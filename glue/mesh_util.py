from dataclasses import dataclass
import numpy as np
import open3d as o3d

@dataclass
class Mesh:
    filename: None

    @property
    def mesh(self):
        pcd = o3d.io.read_triangle_mesh(self.filename, True)
        return pcd
    
    def display(self, cameras=None):
        import open3d as o3d

        if cameras is not None:
            vis = o3d.visualization.Visualizer()
        else:
            vis = o3d.visualization.VisualizerWithEditing()

        vis.create_window(window_name="Open3D", width= 1920, height=1080, visible=True)
        opt = vis.get_render_option()
        opt.background_color = np.asarray([0.0, 0.0, 0.0])
        vis.add_geometry(self.mesh)
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
                print(self.mesh.points[pick])


