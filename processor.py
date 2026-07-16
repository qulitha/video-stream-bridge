"""
Runs the ONNX model on each frame and draws the overlay on top.

cv2 is used here only for math (resize, drawing) - not for capture or
display, both of which go through GStreamer instead.
"""

import cv2
import numpy as np
import onnxruntime as ort
import logging
import time

logger = logging.getLogger("processor")


class FrameProcessor:
    def __init__(self, model_path: str, input_size: int, confidence_threshold: float, num_threads: int = 4):
        so = ort.SessionOptions()
        so.intra_op_num_threads = num_threads
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        # CPUExecutionProvider is what you get on RPi5 - no NPU/GPU backend.
        # If inference alone is eating your latency budget, that's the model,
        # not this glue code - look at a smaller/quantized model first.
        self.session = ort.InferenceSession(model_path, sess_options=so, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

        self.input_size = input_size
        self.confidence_threshold = confidence_threshold

        logger.info("Model loaded: %s (input=%dx%d)", model_path, input_size, input_size)

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        resized = cv2.resize(frame, (self.input_size, self.input_size))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        chw = rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
        return np.expand_dims(chw, axis=0)

    def _draw_overlay(self, frame: np.ndarray, detections) -> np.ndarray:
        # Replace with your own overlay logic - this just draws boxes as a placeholder
        for det in detections:
            x1, y1, x2, y2, conf, cls = det
            if conf < self.confidence_threshold:
                continue
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, f"{int(cls)}:{conf:.2f}", (int(x1), int(y1) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return frame

    def process(self, frame: np.ndarray) -> np.ndarray:
        t0 = time.perf_counter()

        input_tensor = self._preprocess(frame)
        outputs = self.session.run(None, {self.input_name: input_tensor})

        # NOTE: parsing depends on your model's output format - adjust this
        # to match whatever your model.onnx actually returns.
        detections = outputs[0][0] if len(outputs) and len(outputs[0]) else []

        result = self._draw_overlay(frame, detections)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        if elapsed_ms > 30:
            logger.warning("Inference took %.1fms - eating into your latency budget", elapsed_ms)

        return result
