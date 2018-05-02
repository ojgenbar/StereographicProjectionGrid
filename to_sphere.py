from math import sqrt, sin, radians, degrees, cos, tan


class EllipsoidHolder:
    def __init__(self, ellipsoid):
        self.a = float(ellipsoid['A'])
        self.b = float(ellipsoid['B'])
        self.f1 = float(ellipsoid['F1'])
        self.alpha = 1/self.f1
        self.e = sqrt(self.a**2-self.b**2)/self.a
        self.e2 = sqrt(self.a**2-self.b**2)/self.b
        self.id = int(ellipsoid['Id'])

        self.n1 = self.__get_n1()

    def get_M(self, phi):
        phi = radians(phi)
        M = self.a*(1-self.e**2)/sqrt((1-self.e**2*sin(phi)**2)**3)
        return M

    def get_N(self, phi):
        phi = radians(phi)
        N = self.a/sqrt(1-self.e**2*sin(phi)**2)
        return N

    def get_R(self, phi):
        N = self.get_N(phi)
        M = self.get_M(phi)
        return sqrt(N*M)

    def __get_n1(self):
        a = self.a
        b = self.b
        n1 = (a-b+0.0)/(a+b)
        return n1

    def get_s(self, phi):
        # Length from point to equator

        rad_phi = radians(phi)
        n1 = self.n1
        a = self.a

        part0 = a/(1+n1)
        part1 = 1 + n1**2/4 + n1**4/64
        part2 = 3/2*n1 - 3/16*n1**3
        part3 = 15/16*n1**2 - 15/64*n1**4
        part4 = 35/42*n1**3

        s = part0 * (part1*rad_phi - part2*sin(2*rad_phi) + part3*sin(4*rad_phi) - part4*sin(6*rad_phi))
        return s

    def get_eta02(self, phi):
        n02 = self.e2**2 * cos(radians(phi))**2
        return n02


class MollweideProjector:
    def __init__(self, ellipsoid, phi0=0):
        self.ellipsoid = ellipsoid
        self.A = self.__get_A()
        self.B = self.__get_B()
        self.C = self.__get_C()
        self.r = self.ellipsoid.a

    def __get_A(self):
        e = self.ellipsoid.e
        return e**2/2 + 5*e**4/24 + 3*e**6/32

    def __get_B(self):
        e = self.ellipsoid.e
        return 5/48*e**4 + 7/80*e**6

    def __get_C(self):
        e = self.ellipsoid.e
        return 13/480*e**6

    def project(self, phi, lam=0):
        rad_phi0 = radians(phi)
        rad_phi = rad_phi0 - self.A*sin(2*rad_phi0) + self.B*sin(4*rad_phi0) - self.C*sin(6*rad_phi0)
        phi2 = degrees(rad_phi)
        return phi2, lam


class GaussFirstProjector:
    def __init__(self, ellipsoid, phi0=0):
        self.ellipsoid = ellipsoid
        self.phi0 = phi0
        self.N0 = self.ellipsoid.get_N(phi0)
        self.r = self.N0
        self.s0 = self.ellipsoid.get_s(phi0)
        self.eta02 = self.ellipsoid.get_eta02(self.phi0)

        self.P03 = self.__get_P03()
        self.P04 = self.__get_P04()
        self.P05 = self.__get_P05()

    def __get_b(self, phi):
        n0 = self.N0
        s0 = self.s0
        s = self.ellipsoid.get_s(phi)
        b = (s-s0)/n0
        return b

    def __get_P03(self):
        return self.eta02/6

    def __get_P04(self):
        p04 = self.eta02*tan(radians(self.phi0))/24 * (3+4*self.eta02)
        return p04

    def __get_P05(self):
        eta02 = self.eta02
        rad_phi0 = radians(self.phi0)
        part0 = eta02/120
        part1 = 4 - 3*tan(rad_phi0)**2 + 3*eta02 - 24*eta02*tan(rad_phi0)**2
        part2 = 4*eta02**2 - 24*eta02**2*tan(rad_phi0)**2
        p05 = part0*(part1 + part2)
        return p05

    def project(self, phi, lam=0):
        # Formula 155
        b = self.__get_b(phi)
        P03 = self.P03
        P04 = self.P04
        P05 = self.P05

        phi2 = radians(self.phi0) + b + P03*b**3 - P04*b**4 - P05*b**6
        return degrees(phi2), lam


class GaussSecondProjector:
    def __init__(self, ellipsoid, phi0=0):
        self.ellipsoid = ellipsoid
        self.phi0 = phi0
        self.R = self.ellipsoid.get_R(self.phi0)
        self.r = self.R
        self.s0 = self.ellipsoid.get_s(phi0)
        self.eta02 = self.ellipsoid.get_eta02(self.phi0)

        self.P0 = self.__get_P0()
        self.tgphi01 = self.__get_tg_phi01()
        self.P04 = self.__get_P04()
        self.P05 = self.__get_P05()

    def __get_b(self, phi):
        R = self.R
        s0 = self.s0
        s = self.ellipsoid.get_s(phi)
        b = (s-s0)/R
        return b

    def __get_P0(self):
        return sqrt(1 + self.eta02*cos(radians(self.phi0))**2)

    def __get_tg_phi01(self):
        # Tg phi0'
        v0 = sqrt(1+self.eta02)
        tg_phi01 = tan(radians(self.phi0))/v0
        return tg_phi01

    def __get_P04(self):
        return self.eta02*self.tgphi01/6

    def __get_P05(self):
        P05 = self.eta02/30 * (1 - 6*self.eta02*self.tgphi01**2)
        return P05

    def project(self, phi, lam):
        lam2 = self.P0 * lam

        P04 = self.P04
        P05 = self.P05
        b = self.__get_b(phi)
        rad_phi2 = radians(self.phi0) + b - P04*b**4 - P05*b**5
        return degrees(rad_phi2), lam2


class EqualAreaProjector:
    def __init__(self, ellipsoid, phi0=0):
        self.ellipsoid = ellipsoid
        self.A1 = self.__get_A1()
        self.B1 = self.__get_B1()
        self.R = self.__get_R()
        self.r = self.R

    def __get_R(self):
        e = self.ellipsoid.e
        a = self.ellipsoid.a

        R = a*(1 - e**2/6 - 17/360*e**4)
        return R

    def __get_A1(self):
        e = self.ellipsoid.e
        return e**2/3 + 31/180*e**4

    def __get_B1(self):
        e = self.ellipsoid.e
        return 17/360*e**4

    def project(self, phi, lam):
        rad_phi = radians(phi)
        A1 = self.A1
        B1 = self.B1
        rad_phi2 = rad_phi - A1*sin(2*rad_phi) + B1*sin(4*rad_phi)
        return degrees(rad_phi2), lam


class EquidistantProjector:
    def __init__(self, ellipsoid, phi0=0, c=0):
        self.ellipsoid = ellipsoid
        self.c = c
        self.R = self.__get_R()
        self.r = self.R

    def __get_R(self):
        a = self.ellipsoid.a
        n1 = self.ellipsoid.n1
        R = a/(1+n1)*(1 + n1**2/4 + n1**4/64)
        return R

    def project(self, phi, lam):
        s = self.ellipsoid.get_s(phi)
        rad_phi2 = s/self.R + self.c
        return degrees(rad_phi2), lam


def decdeg2dms(dd):
    is_positive = dd >= 0
    dd = abs(dd)
    minutes, seconds = divmod(dd * 3600, 60)
    degs, minutes = divmod(minutes, 60)
    degs = int(degs)
    minutes = int(minutes)
    degs = degs if is_positive else -degs
    return degs, minutes, seconds


def dms_str(dd):
    dms = decdeg2dms(dd)
    return '{: 03d}° {:02d}′  {:05.2F}″'.format(*dms)


if __name__ == '__main__':
    import os
    import configparser

    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), r'data\Ellipsoids.ini'))
    el = EllipsoidHolder(config['Krassovsky_1940'])
    mt = MollweideProjector(el)

    g1t = GaussFirstProjector(el, 0)
    print(dms_str(45 - g1t.project(45)[0]))

    g2t = GaussSecondProjector(el, 0)
    lt, ln = g2t.project(45, 0)
    print(dms_str(45 - lt))

    eat = EqualAreaProjector(el)
    deg_a = decdeg2dms(degrees(eat.A1))
    sec_a = deg_a[0]*3600 + deg_a[1]*60 + deg_a[2]
    print(sec_a)
    print(dms_str(degrees(eat.B1)))
    print(eat.R)
    lt, ln = eat.project(45, 0)
    print(dms_str(45 - lt))

    edt = EquidistantProjector(el)
    lt, ln = edt.project(45, 0)
    print(dms_str(45 - lt))
    print(edt.R)
