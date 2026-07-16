# AI-Overlay-Pi
A small HDMI add-on for Raspberry Pi. It puts a graphic interface on top of your video signal in real time.

## What it does
We take the HDMI signal from your main PC using a capture card. Then we run each frame through a neural network and send the result to your monitor. The delay is very small — you almost don't notice it. This is good for custom HUDs, live text translation on screen, or other video automation.
The idea is simple: your computer doesn't know about the Pi. It just sends video through HDMI like normal. The "magic" happens in the gap between the capture card and the monitor.

## Features
- Captures video from a USB 3.0 HDMI Capture Card
- Hardware acceleration with GStreamer
- Easy to add your own model — YOLO, OCR, or any ONNX model
- Multi-threading, so the delay stays low

## What you need
- Raspberry Pi 4 or 5
- USB 3.0 HDMI Capture Card (a USB 2.0 card will be too slow)
- Python 3.10+
- opencv-python-headless, numpy, onnxruntime

## Contributing
Pull requests are welcome! Reducing the delay is still the main problem, so ideas about that are especially useful. If you have an idea for better video processing, open an issue or send a PR.
