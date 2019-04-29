import configparser
import sys
import os

from PyQt4 import QtCore
from PyQt4.QtGui import QApplication, QDoubleValidator, QPainter, QTableWidgetItem, QFont
from forms import MainForm, GridForm

import to_sphere as ts
import projection as pr

PLUGIN_PATH = os.path.dirname(__file__)
SPHERE_PROJECTIONS = {
    "Равноугольное по Мольвейде": ts.MollweideProjector,
    "Равноугольное по Гауссу I": ts.GaussFirstProjector,
    "Равноугольное по Гауссу II": ts.GaussSecondProjector,
    "Равновеликое": ts.EqualAreaProjector,
    "Равнопромежуточное": ts.EquidistantProjector
}
# pixel per inch in cm
PPcM = 96 / 2.54


class Main:
    def __init__(self):
        self.main_form = MainForm()
        self.grid_form = GridForm()
        self.ellipsoids_ini = self.__parse_ellipsoids()
        self.ellipsoid = None
        self.sphere_projection_type = None
        self.sphere_projections_list = None

        self.__init_ui()

    @staticmethod
    def __parse_ellipsoids():
        path = os.path.join(PLUGIN_PATH, r'data', r'Ellipsoids.ini')
        config = configparser.ConfigParser()
        config.read(path)
        return config

    def __init_ui(self):
        self.__fill_ellipsoids()
        self.__fill_projections()

        v = QDoubleValidator(6350000, 6379000, 3)
        self.main_form.aLineEdit.setValidator(v)
        self.main_form.bLineEdit.setValidator(v)

        self.main_form.build.clicked.connect(self.__show_grid)
        self.main_form.ellipsoid.currentIndexChanged.connect(self.__ellipsoid_changed)
        self.main_form.projectType.currentIndexChanged.connect(self.__sphere_projection_changed)
        self.main_form.fixSteps.stateChanged.connect(self.__fixed_step_changed)
        self.main_form.latDeg.valueChanged.connect(self.__step_lat_deg_changed)

        self.grid_form.scale.valueChanged.connect(self.__scale_changed)
        self.grid_form.labelAxis.stateChanged.connect(self.__label_axis_changed)

        self.main_form.show()

    def __step_lat_deg_changed(self):
        form = self.main_form
        if form.fixSteps.isChecked():
            form.longDeg.setValue(form.latDeg.value())

    def __fixed_step_changed(self):
        form = self.main_form
        frame = form.frameLong
        fix_steps = form.fixSteps
        state = fix_steps.isChecked()

        if state:
            frame.setEnabled(False)
            form.longDeg.setValue(form.latDeg.value())
        else:
            frame.setEnabled(True)

    def __show_grid(self):
        form = self.main_form

        phi0 = form.latDegPole.value() + form.latMinPole.value()/60.0 + form.latSecPole.value()/3600.0
        lam0 = form.longDegPole.value() + form.longMinPole.value()/60.0 + form.longSecPole.value()/3600.0
        step_phi = form.latDeg.value()
        step_lam = form.longDeg.value()

        scale = self.grid_form.scale.value()
        sphere_projector = self.sphere_projection_type(self.ellipsoid, phi0)
        plane_projector = pr.StereographicProjector(
            to_sphere_projector=sphere_projector,
            phi0=phi0,
            lam0=lam0
        )
        grid = pr.GridBuilder(
            to_plane_projector=plane_projector,
            step_phi=step_phi,
            step_lam=step_lam,
            lat0=phi0,
            long0=lam0
        )
        label_axis = self.grid_form.labelAxis.isChecked()
        self.grid_painter = GridPainter(self.grid_form.frame, grid, scale, label_axis)
        self.grid_form.show()
        self.grid_painter.frame.update()
        self.__fill_table()

    def __fill_table(self):
        table = self.main_form.table

        lat_dict_to_show = self.grid_painter.grid.lat_dict_to_show

        table_data = []
        for phi, points in sorted(lat_dict_to_show.items(), key=lambda p: p[0]):
            for lam, x, y in points:
                table_data.append([ts.dms_str(phi), ts.dms_str(lam), '{: .3f}'.format(x), '{: .3f}'.format(y)])

        table.setRowCount(len(table_data))
        for i, row in enumerate(table_data):
            for j, value in enumerate(row):
                item = QTableWidgetItem()
                item.setText(value)
                table.setItem(i, j, item)

    def __scale_changed(self):
        scale = self.grid_form.scale.value()
        self.grid_painter.scale = scale
        self.grid_painter.scale_pix = scale * PPcM
        self.grid_painter.frame.update()

    def __label_axis_changed(self):
        label_axis = self.grid_form.labelAxis.isChecked()
        self.grid_painter.label_axis = label_axis
        self.grid_painter.frame.update()

    def __fill_ellipsoids(self):
        cbox = self.main_form.ellipsoid
        cbox.clear()
        lst = self.ellipsoids_ini.sections()
        lst.append('Пользовательский')
        cbox.addItems(lst)
        cbox.setCurrentIndex(cbox.findText('GSK_2011'))
        self.__ellipsoid_changed()

    def __fill_projections(self):
        cbox = self.main_form.projectType
        cbox.clear()
        lst = list(sorted(SPHERE_PROJECTIONS.keys()))
        cbox.addItems(lst)
        cbox.setCurrentIndex(len(lst)-1)
        self.sphere_projections_list = lst
        self.__sphere_projection_changed()

    def __sphere_projection_changed(self):
        pr_text = self.main_form.projectType.currentText()
        self.sphere_projection_type = SPHERE_PROJECTIONS[pr_text]

    def __ellipsoid_changed(self):
        el_text = self.main_form.ellipsoid.currentText()
        a_line = self.main_form.aLineEdit
        b_line = self.main_form.bLineEdit

        if el_text == 'Пользовательский':
            a_line.setEnabled(True)
            b_line.setEnabled(True)
            return

        a_line.setEnabled(False)
        b_line.setEnabled(False)
        ellipsoid = ts.EllipsoidHolder(self.ellipsoids_ini[el_text])

        a_line.setText('{:.3f}'.format(ellipsoid.a))
        b_line.setText('{:.3f}'.format(ellipsoid.b))
        self.ellipsoid = ellipsoid


class GridPainter:
    def __init__(self, frame, grid, scale, label_axis):
        self.frame = frame
        self.grid = grid
        self.scale = scale
        self.label_axis = label_axis
        self.scale_pix = scale * PPcM

        self.frame.paintEvent = self.print_grid
        self.height = None
        self.width = None
        self.mid_x = None
        self.mid_y = None

        self.text_scale = None

        self.__get_size()

    def print_grid(self, e):
        qp = QPainter()
        qp.begin(self.frame)
        self.draw_grid(qp)
        qp.end()

    def __get_size(self):
        size = self.frame.size()
        self.height = size.height()
        self.width = size.width()
        self.mid_x = int(self.width / 2)
        self.mid_y = int(self.height / 2)

    def convert_coords(self, proj_x, proj_y):
        m = self.scale_pix
        x = self.mid_x + proj_y / m * 100 * 1000
        y = self.mid_y - proj_x / m * 100 * 1000
        return x, y

    def __get_text_scale(self):
        q = 100000000 / self.scale
        if q > 1:
            q = 1
        self.text_scale = q
        return q

    def place_axis_label(self, qp, x, y, value, color):
        qp.setBrush(QtCore.Qt.white)
        qp.setPen(QtCore.Qt.white)

        q = self.text_scale
        w, h = 30 * q, 15 * q
        x1, y1 = x - w / 2, y - h / 2

        qp.drawRect(x1, y1, w, h)

        qp.setFont(QFont("Arial", 12 * q))
        qp.setPen(color)
        qp.drawText(x1, y1, w, h, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, value)

    def __label_lat(self, qp):
        lat_dict = self.grid.lat_dict
        lat_to_label = list(sorted(filter(lambda v: v >= 0, lat_dict.keys())))[::5]

        for lat in lat_to_label:
            x, y = self.convert_coords(*lat_dict[lat][210])
            self.place_axis_label(qp, x, y, '{}°'.format(int(lat)), QtCore.Qt.red)

            x, y = self.convert_coords(*lat_dict[-lat][210])
            self.place_axis_label(qp, x, y, '{}°'.format(int(-lat)), QtCore.Qt.red)

    def __label_long(self, qp):
        long_dict = self.grid.long_dict
        long_to_label = list(sorted(long_dict.keys()))[::5]

        for long in long_to_label:
            points = long_dict[long]
            x, y = self.convert_coords(*points[int(len(points)/2)])
            self.place_axis_label(qp, x, y, '{}°'.format(int(long)), QtCore.Qt.blue)

    def draw_curve(self, qp, points):
        src_points = points
        points = [QtCore.QPoint(*self.convert_coords(x, y)) for x, y in src_points]
        qp.drawPolyline(*points)

    def draw_grid(self, qp):
        qp.setPen(QtCore.Qt.red)
        self.__get_size()

        for lat, points in self.grid.lat_dict.items():
            self.draw_curve(qp, points)

        qp.setPen(QtCore.Qt.blue)
        for long, points in self.grid.long_dict.items():
            if long == pr.norm_long(self.grid.long0-180):
                positive = [(x, y) for x, y in points if x >= 0]
                negative = [(x, y) for x, y in points if x < 0]
                if positive:
                    self.draw_curve(qp, positive)
                if negative:
                    self.draw_curve(qp, negative)
            else:
                self.draw_curve(qp, points)

        try:
            qp.setPen(QtCore.Qt.black)
            self.draw_curve(qp, self.grid.long_dict[0])
            self.draw_curve(qp, self.grid.lat_dict[0])
        except KeyError:
            pass

        if self.label_axis:
            self.__get_text_scale()
            self.__label_lat(qp)
            self.__label_long(qp)


def main():
    app = QApplication(sys.argv)
    ex = Main()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
