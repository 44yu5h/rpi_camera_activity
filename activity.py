flag = True  # False: for testing without camera

import datetime
import os
import gi
import cairo
import numpy as np
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

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

        # toolbar
        toolbar_box = ToolbarBox()
        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        # toolbar buttons
        self.items = {}

        # group radio buttons
        # [first index, last index, group]
        groups = [[0, 2, None], [2, 4, None], [4, 7, None]]

        for group_index, group_range in enumerate(groups):
            start_index, end_index, group = group_range

            for item in _lists.toolbar_items[start_index:end_index]:
                icon_name, tooltip, state = item
                button = RadioToolButton()
                button.set_tooltip(tooltip)
                button.props.icon_name = icon_name  # + ('1' if state else '0')
                if group is None:
                    group_range[2] = button
                    group = button
                button.props.group = group
                toolbar_box.toolbar.insert(button, -1)
                self.items[icon_name] = button
                button.connect('toggled', self.radiobutton_cb, item)

            # separator after each group
            if group_index < len(groups) - 1:
                tool_item = Gtk.ToolItem()
                separator = Gtk.SeparatorToolItem()
                separator.props.draw = True
                tool_item.add(separator)

                # reduce seperator length
                tool_item.set_expand(False)
                tool_item.set_homogeneous(False)
                tool_item.set_margin_top(10)
                tool_item.set_margin_bottom(10)

                toolbar_box.toolbar.insert(tool_item, -1)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        self.show_all()

        # home screen
        self.radiobutton_cb(None, 'gpio')
        if flag: GLib.timeout_add(1000, self.update_preview)

    #==========================================================================
    #SECTION                        MISC FNs
    #==========================================================================
    def radiobutton_cb(self, _b, item):
        # set canvas
        self.set_canvas(self.cameraHomeScreen())
        canvas = self.get_canvas()
        bg_color = Gdk.RGBA()
        bg_color.parse("#ECECEC" if _lists.toolbar_items[7][2]
                       else "#141414")
        canvas.override_background_color(Gtk.StateType.NORMAL, bg_color)

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
        mainVbox.set_margin_bottom(60)
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

        # Create a DrawingArea and add it to secVbox
        self.drawing_area = Gtk.DrawingArea()
        # self.drawing_area.set_size_request(300, 200)
        self.drawing_area.connect("draw", self.on_draw)

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
