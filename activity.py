camera_ok = True  # False: for testing without camera

from datetime import datetime
import os
import gi
import cairo
import numpy as np

gi.require_version('Gtk', '3.0')
gi.require_version('Rsvg', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

try:
    from picamera2 import Picamera2
    from picamera2.outputs import FfmpegOutput
    from picamera2.encoders import H264Encoder
    from libcamera import Transform
    camera_ok = True
except ImportError:
    camera_ok = False
    print("Error importing camera modules")

from sugar3.activity import activity
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import StopButton
from sugar3.activity.widgets import ActivityToolbarButton


class RPiCameraActivity(activity.Activity):

    #==========================================================================
    #SECTION                           INIT
    #==========================================================================
    def __init__(self, handle):
        activity.Activity.__init__(self, handle)
        self.max_participants = 1
        self.is_recording = False

        self.get_screen_size()
        # Camera config
        self._size = (640, 480)
        self._format = 'RGB888'
        self._hflip = False
        self._vflip = False
        self._timer = 0
        #=================== Toolbar UI ===================

        self.toolbar_box = ToolbarBox()
        activity_button = ActivityToolbarButton(self)
        self.toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        # grid button
        self.grid_btn = self.create_toolbar_btn('grid0', 'Show/Hide Grid',
                                                self.grid_btn_cb)
        # hflip btn
        self.hflip_btn = self.create_toolbar_btn(
            'hflip', 'Horizontal Flip',
            lambda b: self.flip_cb(b, 'hflip'))
        # vflip btn
        self.hflip_btn = self.create_toolbar_btn(
            'vflip', 'Vertical Flip',
            lambda b: self.flip_cb(b, 'vflip'))
        # timer btn
        self.timer_btn = self.create_toolbar_btn(
            'timer0', 'Timer', self.timer_cb)
        self.timer_btn.get_style_context().add_class('timer_toolbar_button')

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
        bg_color.parse("#1C1C1C")
        canvas.override_background_color(Gtk.StateType.NORMAL, bg_color)

        if camera_ok: GLib.timeout_add(1000, self.update_preview)

    #==========================================================================
    #SECTION                        MISC FNs
    #==========================================================================

    def get_screen_size(self):
        self.screen_width = Gdk.Screen.get_default().get_width()
        self.screen_height = Gdk.Screen.get_default().get_height()

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

    def flip_cb(self, b, flip_direction):
        if flip_direction == 'hflip':
            self._hflip = b.get_active()
        else:
            self._vflip = b.get_active()

        self.update_config()

    def timer_cb(self, b: Gtk.ToggleButton):
        t_list = [0, 3, 5]  # timer values
        self._timer = t_list[t_list.index(self._timer) + 1] if self._timer < 5\
            else 0
        b.set_image(self._icon('timer' + str(self._timer)))

    def get_filename(self, type):
        pictures_path = os.path.expanduser('~/Pictures/Camera/')
        if not os.path.exists(pictures_path):
            os.makedirs(pictures_path, exist_ok=True)

        now = datetime.now()
        # Format: ddmmyyyy-hhmmsstt
        filename = 'img-' if type == 'img' else 'vid-'
        filename += now.strftime("%d%m%Y-%H%M%S")
        filename += '.jpg' if type == 'img' else '.mp4'
        full_path = os.path.join(pictures_path, filename)
        return full_path

    #==========================================================================
    #SECTION                     Camera operations
    #==========================================================================
    def start_camera_preview(self):
        #* Initialize Camera
        self.picam2 = Picamera2()
        if not hasattr(self, 'preview_config'):
            self.preview_config = self.picam2.create_preview_configuration({
                'size': self._size,
                'format': self._format},
                transform=Transform(hflip=self._hflip, vflip=self._vflip))
        self.picam2.configure(self.preview_config)
        self.picam2.start()

        # Update the preview continuously: 30ms
        GLib.timeout_add(30, self.update_preview)

    def update_config(self):
        config = self.picam2.create_preview_configuration({
            'size': self._size,
            'format': self._format},
            transform=Transform(hflip=self._hflip, vflip=self._vflip))
        self.picam2.stop()
        self.picam2.configure(config)
        self.picam2.start()
        print('changed preview config')

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
        if camera_ok:
            array = self.picam2.capture_array()

            height, width, channels = array.shape
            stride, scale = self.calculate_stride_and_scale(width,
                                                            height,
                                                            widget)

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
        else:
            self.overlay_icon(icon_name='no_cam')

    def overlay_icon(self, icon_name, hide=False):
        if hide:
            self.overlay.remove(self._icon_overlay)
            del self._icon_overlay
            return
        if hasattr(self, '_icon_overlay'):
            self.overlay.remove(self._icon_overlay)

        height, width = 150, 150
        icon_path = 'icons/' + icon_name + '.svg'

        loader = GdkPixbuf.PixbufLoader.new_with_type('svg')
        with open(icon_path, 'rb') as f:
            loader.write(f.read())
        loader.close()
        raw_pixbuf = loader.get_pixbuf()

        pixbuf = raw_pixbuf.scale_simple(width,
                                         height,
                                         GdkPixbuf.InterpType.BILINEAR)

        self._icon_overlay = Gtk.Image.new_from_pixbuf(pixbuf)
        self._icon_overlay.set_halign(Gtk.Align.CENTER)
        self._icon_overlay.set_valign(Gtk.Align.CENTER)

        self.overlay.add_overlay(self._icon_overlay)
        self._icon_overlay.show()
        self.overlay.show_all()

    def run_timer(self, callback=None):
        self._timer_callback = callback
        if self._timer == 0:
            self._timer_callback()
            return
        self.update_timer()  # remove the 1sec delay before timer shows up
        GLib.timeout_add(1000, self.update_timer)

    def update_timer(self):
        if not hasattr(self, '_current_time'):
            self._current_time = self._timer
        if self._current_time != 0:
            self.overlay_icon(f'{self._current_time}s')
            self._current_time -= 1
            return True
        else:
            self.overlay_icon('', hide=True)
            del self._current_time
            if self._timer_callback:
                self._timer_callback()
            return False

    def record_overlay(self):
        if not hasattr(self, 'rec_time_sec'):
            self.rec_time_sec = 0
        if self.is_recording:
            self.rec_time_sec += 1
            minutes, seconds = divmod(self.rec_time_sec, 60)
            formatted_time = f"{minutes:02}:{seconds:02}"
            red_dot = '\u25CF'
            self.rec_overlay.set_markup(f'<span foreground="red"\
                font_desc="17px">{red_dot}</span> REC {formatted_time}')
            self.rec_overlay.get_style_context().add_class('rec-label-bg')
            self.rec_overlay.show()
            self.overlay.show_all()
            if self.rec_time_sec > 15 * 60:
                self.stop_recording()
            return True
        else:
            self.rec_overlay.set_markup('')
            self.rec_overlay.get_style_context().remove_class('rec-label-bg')
            self.rec_overlay.hide()
            return False

    # Perform cleanup before exiting
    def __del__(self):
        if hasattr(self, 'picam2'):
            self.picam2.stop()
            del self.picam2
            print("Camera stopped, memory released")

    #=================== Capture Image ===================
    def capture_image(self, _):
        def after_timer():
            filename = self.get_filename('img')
            capture_config = self.picam2.create_still_configuration()
            self.picam2.switch_mode_and_capture_file(capture_config, filename)
            print(f"Image captured: {filename}")
        self.run_timer(after_timer)

    #=================== Record Video ===================
    def record_video(self, b):
        if b.get_active():
            def after_timer():
                self.vid_btn.set_image(self.rec_on_icon)
                encoder = H264Encoder()
                self.output = FfmpegOutput(self.get_filename('vid'))
                encoder.output = self.output
                self.picam2.start_encoder(encoder)
                GLib.timeout_add(1000, self.record_overlay)
            self.is_recording = True
            self.run_timer(after_timer)
        else:
            self.stop_recording()

    def stop_recording(self):
        self.vid_btn.set_image(self.rec_off_icon)
        self.output.stop()
        self.is_recording = False
        self.picam2.stop_encoder()
        print(f"Video saved! Duration: {self.rec_time_sec} seconds")
        self.rec_time_sec = 0

    #==========================================================================
    #SECTION                             UI
    #==========================================================================
    def cameraHomeScreen(self):
        cam_window = Gtk.ScrolledWindow()
        mainVbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        secVbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        if camera_ok: secVbox.set_margin_left(80)
        mainVbox.set_margin_bottom(10)

        self.rec_off_icon = Gtk.Image.new_from_file("icons/rec-off.svg")
        self.rec_on_icon = Gtk.Image.new_from_file("icons/rec-on.svg")
        pic_icon = Gtk.Image.new_from_file("icons/snap.svg")
        
        self.vid_btn = Gtk.ToggleButton()
        self.vid_btn.set_image(self.rec_off_icon)
        self.vid_btn.connect('toggled', self.record_video)
        pic_btn = Gtk.ToggleButton()
        pic_btn.set_image(pic_icon)
        pic_btn.connect('clicked', self.capture_image)

        cam_window.add(mainVbox)
        cam_window.set_policy(
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        mainVbox.pack_start(secVbox, True, True, 0)

        # Drawing Area (camera preview)
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.connect("draw", self.on_draw)

        # Add overlay
        self.overlay = Gtk.Overlay()
        # Add the drawing area to the last layer of the overlay
        self.overlay.add(self.drawing_area)
        secVbox.pack_start(self.overlay, True, True, 0)

        # Life is boring without some css
        css = """
        .rec-label-bg {
            font-size: 14px;
            background-color: white;
            color: black;
            border-radius: 5px;
            padding: 2px 5px;
            margin-left: 10px;
            margin-top: 10px;
        }

        .action-button-bar {
            background-color: rgba(0, 0, 0, 0.2);
            border-radius: 100px;
            margin-bottom: 10px;
            padding-left: 10px;
            padding-right: 10px;
        }
        
        .timer_toolbar_button {
            padding: 3px;
            margin-left: 10px;
            margin-right: 10px;
        }

        button {
        background: none;
        border: none;
        box-shadow: none;
        }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Snap/Vid Button container
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_halign(Gtk.Align.CENTER)
        hbox.set_valign(Gtk.Align.END)
        hbox.get_style_context().add_class('action-button-bar')
        hbox.pack_start(pic_btn, False, False, 0)
        hbox.pack_start(self.vid_btn, False, False, 0)

        # Recording time overlay
        self.rec_overlay = Gtk.Label()
        self.overlay.add_overlay(self.rec_overlay)
        self.rec_overlay.set_halign(Gtk.Align.START)
        self.rec_overlay.set_valign(Gtk.Align.START)
        
        self.overlay.add_overlay(hbox)

        self.overlay.show_all()

        mainVbox.show_all()
        secVbox.show_all()
        cam_window.show()
        if camera_ok: self.start_camera_preview()

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
