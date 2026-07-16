"""
Pushes processed frames out to the screen via GStreamer appsrc.

Using kmssink by default - it writes straight to the display without
needing X11/Wayland running, which is one less layer of latency and one
less thing to configure for a fullscreen kiosk-style setup. If you're
running a desktop session instead, swap sink to autovideosink.
"""

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

import logging

logger = logging.getLogger("display")


class VideoDisplay:
    def __init__(self, width: int, height: int, fps: int, sink: str = "kmssink",
                 fullscreen: bool = True, max_buffers: int = 1):
        Gst.init(None)

        self.width = width
        self.height = height

        sink_str = sink
        if sink == "kmssink" and fullscreen:
            sink_str = "kmssink force-modesetting=true"

        pipeline_str = (
            f"appsrc name=src is-live=true block=false format=time "
            f"caps=video/x-raw,format=BGR,width={width},height={height},framerate={fps}/1 ! "
            f"queue leaky=downstream max-size-buffers={max_buffers} ! "
            f"videoconvert ! {sink_str}"
        )
        logger.info("Display pipeline: %s", pipeline_str)

        self.pipeline = Gst.parse_launch(pipeline_str)
        self.appsrc = self.pipeline.get_by_name("src")
        self._frame_duration = Gst.util_uint64_scale_int(Gst.SECOND, 1, fps)
        self._timestamp = 0

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        logger.info("Display started")

    def push(self, frame):
        data = frame.tobytes()
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        buf.pts = self._timestamp
        buf.duration = self._frame_duration
        self._timestamp += self._frame_duration

        self.appsrc.emit("push-buffer", buf)

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        logger.info("Display stopped")
