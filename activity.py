flag = True  # False: for testing without camera

import datetime
import os
import gi
import cairo
import numpy as np
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

import _lists
if flag: from picamera2 import Picamera2

from sugar3.activity import activity
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import StopButton
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.graphics.radiotoolbutton import RadioToolButton


class RPiCameraActivity(activity.Activity):

    #==========================================================================
    #SECTION                           INIT
    #==========================================================================
    def __init__(self, handle):
        activity.Activity.__init__(self, handle)
        self.max_participants = 1

        #=================== Toolbar UI ===================

        self.toolbar_box = ToolbarBox()
        activity_button = ActivityToolbarButton(self)
        self.toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        # grid button
        self.grid_btn = self.create_toolbar_btn('grid0', 'Show/Hide Grid',
                                                self.grid_btn_cb)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        self.toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        self.toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(self.toolbar_box)
        self.show_all()

        self.set_canvas(self.cameraHomeScreen())
        canvas = self.get_canvas()
        bg_color = Gdk.RGBA()
        bg_color.parse("#ECECEC")
        canvas.override_background_color(Gtk.StateType.NORMAL, bg_color)

        if flag: GLib.timeout_add(1000, self.update_preview)

    #==========================================================================
    #SECTION                        MISC FNs
    #==========================================================================

    def create_toolbar_btn(self, icon, tooltip, callback):
        button = Gtk.ToggleButton()
        button.set_image(self._icon(icon))
        button.set_tooltip_text(tooltip)
        button.connect('toggled', callback)
        tool_item = Gtk.ToolItem()
        tool_item.add(button)
        self.toolbar_box.toolbar.insert(tool_item, -1)
        return button

    def _icon(self, icon_name):
        icon = Gtk.Image()
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            'icons/' + icon_name + '.svg', 50, 50, True)
        icon.set_from_pixbuf(pixbuf)
        return icon

    def grid_btn_cb(self, b):
        self.draw_grid = b.get_active()
        self.grid_btn.set_image(self._icon('grid1' if self.draw_grid
                                           else 'grid0'))
        self.drawing_area.queue_draw()

    #==========================================================================
    #SECTION                     Camera operations
    #==========================================================================
    def start_camera_preview(self):
        _format = 'RGB888'
        _size = (640, 480)

        #* Initialize Camera
        self.picam2 = Picamera2()
        preview_config = self.picam2.create_preview_configuration({
            'size': _size, 'format': _format})
        self.picam2.configure(preview_config)
        self.picam2.start()

        # Update the preview continuously: 30ms
        GLib.timeout_add(30, self.update_preview)

    def update_preview(self):
        self.drawing_area.queue_draw()
        return True

    def calculate_stride_and_scale(self, width, height, widget):
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_RGB24,
                                                            width)
        alloc = widget.get_allocation()
        scale_x = alloc.width / width
        scale_y = alloc.height / height
        scale = min(scale_x, scale_y)
        return stride, scale

    def on_draw(self, widget, cr):
        array = self.picam2.capture_array()

        height, width, channels = array.shape
        stride, scale = self.calculate_stride_and_scale(width, height, widget)

        if array.nbytes < stride * height:
            array = np.pad(array, ((0, 0), (0, 0), (0, 1)), 'constant',
                           constant_values=0)

        img_surface = cairo.ImageSurface.create_for_data(
            array, cairo.FORMAT_RGB24,
            width, height, stride)

        cr.scale(scale, scale)
        cr.set_source_surface(img_surface, 0, 0)
        cr.paint()

        # draw 3x3 grid
        if getattr(self, 'draw_grid', False):
            x_spacing = width / 3
            y_spacing = height / 3

            # Set the color and line width for the grid lines
            cr.set_source_rgb(0, 0, 0)  # Black color
            cr.set_line_width(1)

            # Draw vertical lines
            for i in range(1, 3):
                cr.move_to(x_spacing * i, 0)
                cr.line_to(x_spacing * i, height)
                cr.stroke()

            # Draw horizontal lines
            for i in range(1, 3):
                cr.move_to(0, y_spacing * i)
                cr.line_to(width, y_spacing * i)
                cr.stroke()

    # Perform cleanup
    def __del__(self):
        if hasattr(self, 'picam2'):
            self.picam2.stop()
            del self.picam2
            print("Camera stopped.")
        print("Object is being destroyed, cleanup performed.")

    #=================== Capture Image ===================
    def capture_image(self, _):
        pictures_path = os.path.expanduser('~/Pictures/Camera/')
        if not os.path.exists(pictures_path):
            os.makedirs(pictures_path, exist_ok=True)

        now = datetime.datetime.now()
        # Format: img-ddmmyyyy-hhmmsstt.jpg; support: jpg, png, bmp, gif
        filename = (now.strftime("img-%d%m%Y-%H%M%S") + ".jpg")
        full_path = os.path.join(pictures_path, filename)

        capture_config = self.picam2.create_still_configuration()
        self.picam2.switch_mode_and_capture_file(capture_config, full_path)

        print(f"Image captured: {full_path}")

    #==========================================================================
    #SECTION                             UI
    #==========================================================================
    def cameraHomeScreen(self):
        cam_window = Gtk.ScrolledWindow()
        mainVbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        secVbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        secVbox.set_halign(Gtk.Align.CENTER)
        secVbox.set_size_request(640, 480)
        mainVbox.set_margin_bottom(10)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_halign(Gtk.Align.CENTER)

        vid_btn = Gtk.ToggleButton.new_with_label("Record")
        vid_btn.set_size_request(100, 20)
        pic_btn = Gtk.Button.new_with_label("Snap")
        pic_btn.set_size_request(100, 20)
        pic_btn.connect('clicked', self.capture_image)

        cam_window.add(mainVbox)
        cam_window.set_policy(
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )

        head_label = Gtk.Label()
        mainVbox.pack_start(head_label, False, False, 50)
        mainVbox.pack_start(secVbox, False, False, 0)
        mainVbox.pack_start(hbox, False, False, 20)
        hbox.pack_start(pic_btn, False, False, 5)
        hbox.pack_start(vid_btn, False, False, 5)
        head_label.set_markup('<span font="25">Camera</span>')
        head_label.set_use_markup(True)

        self.drawing_area = Gtk.DrawingArea()
        # self.drawing_area.set_size_request(300, 200)
        if flag: self.drawing_area.connect("draw", self.on_draw)

        secVbox.pack_start(self.drawing_area, True, True, 0)
        secVbox.show_all()
        mainVbox.show_all()
        secVbox.show_all()
        cam_window.show()
        if flag: self.start_camera_preview()

        return cam_window


#==============================================================================
#NOTE                               CAM CONFIG
#==============================================================================
#
# camera_config = [
#     {
#         'format': 'SGBRG10_CSI2P',
#         'unpacked': 'SGBRG10',
#         'bit_depth': 10,
#         'size': (640, 480),
#         'fps': 58.92,
#         'crop_limits': (16, 0, 2560, 1920),
#         'exposure_limits': (134, 1103219, None)
#     },
#     {
#         'format': 'SGBRG10_CSI2P',
#         'unpacked': 'SGBRG10',
#         'bit_depth': 10,
#         'size': (1296, 972),
#         'fps': 43.25,
#         'crop_limits': (0, 0, 2592, 1944),
#         'exposure_limits': (92, 760636, None)
#     },
#     {
#         'format': 'SGBRG10_CSI2P',
#         'unpacked': 'SGBRG10',
#         'bit_depth': 10,
#         'size': (1920, 1080),
#         'fps': 30.62,
#         'crop_limits': (348, 434, 1928, 1080),
#         'exposure_limits': (118, 969249, None)
#     },
#     {
#         'format': 'SGBRG10_CSI2P',
#         'unpacked': 'SGBRG10',
#         'bit_depth': 10,
#         'size': (2592, 1944),
#         'fps': 15.63,
#         'crop_limits': (0, 0, 2592, 1944),
#         'exposure_limits': (130, 1064891, None)
#     }
# ]
#
#==============================================================================
