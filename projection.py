from math import sin, cos, tan, acos, atan, pi, radians, degrees, hypot


pi2 = pi*2

# TODO: Use decimal instead of float
DEFAULT_DEGREES_STEP = 0.5


class StereographicProjector:
    def __init__(self, to_sphere_projector, phi0, lam0):
        self.to_sphere = to_sphere_projector
        if abs(phi0) < 1e-9:
            phi0 = 1e-10
        else:
            phi0 = float(phi0)

        phi0, lam0 = to_sphere_projector.project(phi0, lam0)
        self.phi0 = float(phi0)
        self.lam0 = float(lam0)
        self.rad_phi0 = radians(phi0)
        self.rad_lam0 = radians(lam0)

    def project2spherical(self, phi, lam):
        rad_phi0 = self.rad_phi0
        rad_phi = radians(phi)

        deg_dist = norm_long(lam - self.lam0)
        if deg_dist > 180:
            deg_dist -= 180
        dlam = radians(deg_dist)

        z = acos(sin(rad_phi)*sin(rad_phi0) + cos(rad_phi)*cos(rad_phi0)*cos(dlam))

        part1 = cos(rad_phi) * sin(dlam)
        part2 = sin(rad_phi) * cos(rad_phi0)
        part3 = cos(rad_phi) * sin(rad_phi0) * cos(dlam)
        tan_a = part1 / (part2 - part3)
        rad_a = atan(tan_a)

        rad_a = self.__get_direction(rad_a, tan_a, phi, lam)

        return z, degrees(rad_a)

    def __get_direction(self, rad_a, tan_a, phi, lam):
        close = abs(rad_a) < 1e-10
        if not close and tan_a < 0.0:
            rad_a = pi - rad_a
        elif close:
            if self.phi0 >= 0:
                if self.phi0 > phi:
                    if phi < -self.phi0:
                        rad_a = pi
                    elif phi >= -self.phi0:
                        if abs(lam - self.lam0) < 1e-10:
                            rad_a = pi
            else:
                if self.phi0 >= phi:
                    rad_a = pi
                else:
                    if phi < -self.phi0:
                        if not abs(lam - self.lam0) < 1e-10:
                            rad_a = pi
        return rad_a

    def project2plane(self, phi, lam, m=1):
        phi, lam = self.to_sphere.project(phi, lam)

        lam_is_0 = abs(lam - self.lam0) < 1e-10
        lam_is_180 = abs(norm_long(lam - 180.0) - self.lam0) < 1e-10
        pole = abs(phi - self.phi0) < 1e-10 and lam_is_0
        pole2 = abs(-phi - self.phi0) < 1e-10 and lam_is_180
        if pole2:
            raise ValueError('Cannot project! Pole is reached!')
        elif pole:
            return 0.0, 0.0

        z, a = self.project2spherical(phi, lam)
        a = radians(a)

        ro = 2*self.to_sphere.r*tan(z/2)
        sig = a
        x = ro*cos(sig)
        y = ro*sin(sig)
        return x/m, y/m


class GridBuilder:
    def __init__(self, to_plane_projector, step_phi, step_lam, lat0, long0):
        self.projector = to_plane_projector
        self.step_phi = step_phi
        self.step_lam = step_lam
        self.lat0 = lat0
        self.long0 = long0

        self.__projection_cache = dict()
        self.lat_dict, self.long_dict, self.lat_dict_to_show = self.build()

    def project(self, lat, long):
        p = self.__projection_cache.get((lat, long), self.projector.project2plane(lat, long))
        return p

    def build(self):
        self.__projection_cache = dict()
        dlat = self.step_phi
        dlong = self.step_lam
        step_def = DEFAULT_DEGREES_STEP

        lat_range = xfrange(-89, 89 + step_def, step_def)
        lat_range = [norm_lat(lat) for lat in lat_range]

        lon_range = xfrange(self.long0, self.long0 + 180 + step_def, step_def)
        lon_range = [norm_long(lon) for lon in lon_range]

        main_lat_range = list(xfrange(0, 90, dlat))
        opposite_lat_range = [-lat for lat in main_lat_range[-1:0:-1]]
        opposite_lat_range.extend(main_lat_range)
        main_lat_range = [norm_lat(lat) for lat in opposite_lat_range]

        main_lon_range = list(xfrange(0, 180+dlong, dlong))
        opposit_lon_range = [-lon for lon in main_lon_range[-2:0:-1]]
        opposit_lon_range.extend(main_lon_range)
        main_lon_range = [norm_long(lon) for lon in opposit_lon_range]

        lat_dict = dict()
        lat_dict_to_show = dict()

        for lat in main_lat_range:
            points = []
            points_to_show = []
            if lat == 0:
                print()
            for long in lon_range[::-1]:
                try:
                    x, y = self.project(lat, long)
                except ValueError:
                    pass
                else:
                    abs_y = abs(y)
                    points.append((x, abs_y))
                    if long % dlong == 0:
                        points_to_show.append((long, x, abs_y))
            points.extend([(x, -y) for x, y in points[-1::-1]])
            if abs(lat) < 1e-9:
                lat = 0
            lat_dict[lat] = points
            lat_dict_to_show[lat] = points_to_show

        long_dict = dict()
        for long in lon_range:
            opposit_long = norm_lat(-2*self.long0 + long)
            if long in main_lon_range or opposit_long in main_lon_range:
                points = []
                points_left = []
                for lat in lat_range[::-1]:
                    try:
                        x, y = self.project(lat, long)
                    except ValueError:
                        pass
                    else:
                        points.append((x, abs(y)))
                        points_left.append((x, -abs(y)))
                if abs(long) < 1e-9:
                    long = 0

                if long in main_lon_range:
                    long_dict[long] = points
                if opposit_long in main_lon_range:
                    if not abs(self.long0) < 1e-9:
                        long2 = norm_long(2*self.long0-long)
                        long_dict[long2] = points_left

        return lat_dict, long_dict, lat_dict_to_show


def distance2line(x1, y1, x2, y2, x0, y0):

    try:
        h = abs(((x2-x1)*(y0-y1) - (y2-y1)*(x0-x1))/hypot(x2-x1, y2-y1))
    except ZeroDivisionError:
        return hypot(x0-x1, y0-y1)
    return h


def norm_long(deg_angle):
    if deg_angle > 180:
        return deg_angle - 360
    elif deg_angle < -180:
        return deg_angle + 360
    else:
        return deg_angle


def norm_lat(deg_angle):
    if deg_angle > 90:
        return 180 - deg_angle
    elif deg_angle < -90:
        return -(deg_angle + 180)
    else:
        return deg_angle


# Weak
def xfrange(start, stop, step):
    i = 0
    if start <= stop:
        while start + i * step < stop:
            yield start + i * step
            i += 1
    else:
        while start + i * step > stop:
            yield start + i * step
            i += 1
