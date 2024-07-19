# RPi Camera Activity

A camera activity for Raspberry Pi running Sugar, designed to provide a simple and interactive way to capture and display images using the Raspberry Pi camera.

## Features
- **Camera Preview**: Live preview from the Raspberry Pi camera.
- **Image Capture**: Capture images and save them to the `~/Pictures/Camera/` directory.
- **Grid Overlay**: Toggle a 3x3 grid overlay on the camera preview.
- **Flip Options**: Horizontal and vertical flip options for the camera preview.

## Requirements
- Raspberry Pi with a camera module
- Python 3.x
- Required Python libraries:
  - `gi`
  - `cairo`
  - `numpy`
  - `picamera2` (for Raspberry Pi)

## Installation
 - Install the required libraries:
    ```bash
    pip install -r req.txt
    ```
## Usage
- Run the activity:
    ```bash
    python3 activity.py
    ```
- **Show/Hide the grid overlay.**
- **Flip the camera preview horizontally or vertically.**
- **Capture images by clicking the "Snap" button.**

## License

This project is licensed under the GPL-2.0 License.
