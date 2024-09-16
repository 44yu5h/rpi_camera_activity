# RPi Camera Activity

A camera activity for Raspberry Pi running Sugar, designed to provide a simple and interactive way to capture and display images using the Raspberry Pi camera.

## Features
- **Camera Preview**: Live preview from the Raspberry Pi camera.
- **Image Capture**: Capture images and save them to the `~/Pictures/Camera/` directory.
- **Grid Overlay**: Toggle a 3x3 grid overlay on the camera preview.
- **Flip Options**: Horizontal and vertical flip options for the camera preview.

## Requirements
- Raspberry Pi with a camera v3 module
- Python 3.x and pip
- Required Python libraries:
  - `picamera2`
- Required apt packages:
  - `libcap-dev`
  - `python3-libcamera`
  - `python3-kms++`
  - `libcamera-apps`

To install all dependencies, run command:

######
    sudo apt install python3-pip libcap-dev python3-kms++ libcamera-apps python3-libcamera && pip3 install picamera2 --break-system-packages


## License

This project is licensed under the GPL-2.0 License.
