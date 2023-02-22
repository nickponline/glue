import numpy as np
import pymap3d

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

