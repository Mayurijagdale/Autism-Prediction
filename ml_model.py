from __future__ import annotations

import os
from typing import Tuple

import numpy as np  # type: ignore
from PIL import Image  # type: ignore

try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover
    ort = None  # type: ignore


_session = None


def get_model_path() -> str:
    path = os.environ.get("MODEL_PATH") or os.path.join("models", "model.onnx")
    return path


def load_model() -> None:
    global _session
    if _session is not None:
        return
    if ort is None:
        raise RuntimeError("onnxruntime not available. Install onnxruntime to use the CNN model.")
    model_path = get_model_path()
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")
    _session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])  # type: ignore


def _preprocess(image_path: str, size: Tuple[int, int] = (224, 224)) -> np.ndarray:
    img = Image.open(image_path).convert("RGB")
    img = img.resize(size)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    # NCHW
    arr = np.transpose(arr, (2, 0, 1))
    arr = np.expand_dims(arr, axis=0)
    return arr


def predict_image(image_path: str) -> Tuple[float, str]:
    """Return (percentage, label) using the loaded ONNX CNN model.
    The model is expected to output a probability/logit for binary classification.
    """
    load_model()
    assert _session is not None
    input_name = _session.get_inputs()[0].name  # type: ignore
    output_name = _session.get_outputs()[0].name  # type: ignore
    x = _preprocess(image_path)
    outputs = _session.run([output_name], {input_name: x})  # type: ignore
    y = outputs[0]
    # Handle shapes: (1,1) or (1,2)
    if y.ndim == 2 and y.shape[1] == 1:
        prob_autism = float(1 / (1 + np.exp(-y[0, 0])))
    elif y.ndim == 2 and y.shape[1] == 2:
        # softmax on 2 classes [not_autism, autism]
        logits = y[0]
        exp = np.exp(logits - np.max(logits))
        probs = exp / np.sum(exp)
        prob_autism = float(probs[1])
    else:
        # fallback: take first value and sigmoid
        v = float(y.flatten()[0])
        prob_autism = float(1 / (1 + np.exp(-v)))
    percentage = round(prob_autism * 100.0, 2)
    label = "Autism" if percentage >= 50.0 else "Not Autism"
    return percentage, label


