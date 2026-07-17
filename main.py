import argparse
import logging
import queue
import signal
import sys
import threading

import yaml

from src.capture import VideoCapture
from src.processor import FrameProcessor
from src.display import VideoDisplay

def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

class SingleSlotQueue:
    def __init__(self):
        self._q = queue.Queue(maxsize=1)

    def put(self, item):
        try:
            self._q.get_nowait()
        except queue.Empty:
            pass
        self._q.put_nowait(item)

    def get(self, timeout=1.0):
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

def main():
    parser = argparse.ArgumentParser(description="VideoStreamBridge")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg["logging"]["level"])
    logger = logging.getLogger("main")

    stop_event = threading.Event()

    capture = VideoCapture(
        device=cfg["video"]["capture_device"],
        width=cfg["video"]["width"],
        height=cfg["video"]["height"],
        fps=cfg["video"]["fps"],
        max_buffers=cfg["pipeline"]["queue_max_buffers"],
    )

    processor = FrameProcessor(
        model_path=cfg["model"]["path"],
        input_size=cfg["model"]["input_size"],
        confidence_threshold=cfg["model"]["confidence_threshold"],
        num_threads=cfg["model"]["num_threads"],
    )

    display = VideoDisplay(
        width=cfg["video"]["width"],
        height=cfg["video"]["height"],
        fps=cfg["video"]["fps"],
        sink=cfg["output"]["sink"],
        fullscreen=cfg["output"]["fullscreen"],
        max_buffers=cfg["pipeline"]["queue_max_buffers"],
    )

    to_process = SingleSlotQueue()
    to_display = SingleSlotQueue()

    def capture_loop():
        capture.start()
        while not stop_event.is_set():
            frame = capture.read(timeout=1.0)
            if frame is not None:
                to_process.put(frame)
        capture.stop()

    def process_loop():
        while not stop_event.is_set():
            frame = to_process.get(timeout=1.0)
            if frame is not None:
                processed = processor.process(frame)
                to_display.put(processed)

    threads = [
        threading.Thread(target=capture_loop, name="capture", daemon=True),
        threading.Thread(target=process_loop, name="process", daemon=True),
    ]

    def handle_sigint(sig, frame):
        logger.info("Shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    for t in threads:
        t.start()

    logger.info("VideoStreamBridge running. Ctrl+C to stop.")

    display.start()
    try:
        while not stop_event.is_set():
            frame = to_display.get(timeout=0.1)
            if frame is not None:
                display.push(frame)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_event.set()
    finally:
        display.stop()

    for t in threads:
        t.join(timeout=2.0)

    logger.info("Stopped.")

if __name__ == "__main__":
    sys.exit(main())