"""
Video capture via GStreamer appsink.

Why GStreamer instead of cv2.VideoCapture: the opencv-python-headless wheel
from PyPI is usually built without GStreamer support, so cv2.VideoCapture
falls back to a V4L2 backend with a multi-frame internal buffer. That alone
adds 2-4 frames of latency before we've done anything. Going through
GStreamer directly lets us set queue leaky=downstream + max-size-buffers=1,
so we always get the newest frame instead of a growing backlog.
"""

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

import numpy as np
import threading
import logging

logger = logging.getLogger("capture")


class VideoCapture:
    def __init__(self, device: str, width: int, height: int, fps: int, max_buffers: int = 1):
        Gst.init(None)

        self.width = width
        self.height = height
        self._latest_frame = None
        self._lock = threading.Lock()
        self._new_frame_event = threading.Event()

        pipeline_str = (
            f"v4l2src device={device} ! "
            f"video/x-raw,width={width},height={height},framerate={fps}/1 ! "
            f"videoconvert ! video/x-raw,format=BGR ! "
            f"queue leaky=downstream max-size-buffers={max_buffers} ! "
            f"appsink name=sink emit-signals=true sync=false drop=true max-buffers={max_buffers}"
        )
        logger.info("Capture pipeline: %s", pipeline_str)

        self.pipeline = Gst.parse_launch(pipeline_str)
        self.appsink = self.pipeline.get_by_name("sink")
        self.appsink.connect("new-sample", self._on_new_sample)

        self._loop = GLib.MainLoop()
        self._loop_thread = None

    def _on_new_sample(self, sink):
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.OK

        buf = sample.get_buffer()
        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            return Gst.FlowReturn.ERROR

        try:
            frame = np.frombuffer(mapinfo.data, dtype=np.uint8).reshape(
                (self.height, self.width, 3)
            ).copy()  # copy out of the GStreamer buffer before it's reused
        finally:
            buf.unmap(mapinfo)

        with self._lock:
            self._latest_frame = frame
        self._new_frame_event.set()

        return Gst.FlowReturn.OK

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        self._loop_thread = threading.Thread(target=self._loop.run, daemon=True)
        self._loop_thread.start()
        logger.info("Capture started")

    def read(self, timeout: float = 1.0):
        """Blocks until a new frame arrives, returns None on timeout."""
        if self._new_frame_event.wait(timeout):
            self._new_frame_event.clear()
            with self._lock:
                return self._latest_frame
        return None

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        if self._loop.is_running():
            self._loop.quit()
        logger.info("Capture stopped")
