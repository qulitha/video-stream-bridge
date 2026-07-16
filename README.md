# VideoStreamBridge

An HDMI overlay bridge for Raspberry Pi 5: captures video from your main PC, runs AI overlay graphics on top of it, and pushes it back out to the monitor. Target is under 50ms of latency, so the whole architecture is built around that, not around clean code.

> **Status: untested on real hardware.** The pipeline is written and should work based on how each piece behaves in isolation, but I don't currently have a Pi to run it end-to-end and check the real numbers. If you try it on actual hardware - working or not - I'd genuinely appreciate hearing about it. Open an issue with your setup (Pi model, capture card, GStreamer version) and whatever latency/errors you're seeing. Bug reports are just as useful as "it works."

## How it works

```
HDMI (PC) → USB Capture Card → RPi 5 → [capture → model → overlay] → HDMI → monitor
```

Your PC has no idea the Pi is there - it just outputs video as usual. All the processing happens in the gap between the capture card and the monitor. Capture and output go straight through GStreamer (not `cv2.VideoCapture` - its internal buffering alone adds a few frames of lag), and `opencv` is only used for frame math.

## Project structure

```
├── main.py             # entry point, wires everything into one pipeline
├── config.yaml          # resolution, model path, output settings
├── src/
│   ├── capture.py        # capture via GStreamer appsink
│   ├── processor.py      # model inference + overlay drawing
│   └── display.py        # output via GStreamer appsrc
├── models/
│   └── model.onnx        # put your model here
└── scripts/
    └── autostart.sh       # sets up autostart via systemd
```

Three threads (capture / process / display), connected by single-frame queues: if processing falls behind, the stale frame just gets dropped instead of piling up. Latency matters more than completeness here.

## Requirements

- Raspberry Pi 4 or 5
- USB 3.0 HDMI Capture Card (USB 2.0 will be a bottleneck)
- Python 3.10+
- GStreamer + PyGObject - install via apt, not pip:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gstreamer-1.0 \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
```

## Setup

```bash
git clone https://github.com/yourusername/VideoStreamBridge.git
cd VideoStreamBridge

python3 -m venv venv --system-site-packages   # this flag is required, otherwise venv won't see gi
source venv/bin/activate
pip install -r requirements.txt
```

Drop your model into `models/model.onnx` and adjust `config.yaml` for your setup - especially `capture_device` (find it with `v4l2-ctl --list-devices`) and `output.sink`.

## Running it

```bash
python3 main.py --config config.yaml
```

Worth checking capture on its own first, by hand:

```bash
gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink
```

If it's already lagging here, no point going further - the problem is at the capture card or driver level.

## Autostart on the Pi

```bash
sudo bash scripts/autostart.sh
```

Sets up a systemd service that starts on boot.

```bash
sudo systemctl status videostreambridge
journalctl -u videostreambridge -f    # live logs
```

## If you're not hitting 50ms

Check these in order, this is usually the order of who's actually to blame:

1. **The model** - on RPi5's CPU with no NPU/GPU, even YOLO nano can eat 30-80ms on its own. Quantize to INT8 or go with a lighter model.
2. **The capture card** - some cards add 1-2 frames of buffering at the firmware level, and no amount of software fixes that - only swapping the card does.
3. **kmssink / output** - check for vsync delay on your specific monitor.

Best way to measure real latency isn't through logs - point a camera at an on-screen stopwatch, film it at 240fps, and count the frame difference between the live image and what comes out of the Pi.

## Contributing

Pull requests welcome. If you know how to squeeze the latency down further (zero-copy buffers, DMA-BUF between v4l2src and inference) - that's the most valuable thing you could improve here.
