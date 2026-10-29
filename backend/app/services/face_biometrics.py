from __future__ import annotations

import os
from pathlib import Path

from io import BytesIO


MODEL_DIR = Path(os.getenv("FACE_MODELS_DIR", str(Path(__file__).resolve().parents[2] / "models")))
YUNET = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
SFACE = MODEL_DIR / "face_recognition_sface_2021dec.onnx"
MAX_IMAGE_BYTES = 2 * 1024 * 1024
COSINE_THRESHOLD = 0.363


def _decode_image(raw: bytes):
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be between 1 byte and 2 MB")
    import numpy as np
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format not in {"JPEG", "PNG", "WEBP"} or image.width > 1920 or image.height > 1920:
                raise ValueError("Use a JPEG, PNG, or WebP image no larger than 1920 by 1920")
            image.verify()
        with Image.open(BytesIO(raw)) as image:
            rgb = np.asarray(image.convert("RGB"))
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Upload a valid image") from exc
    import cv2
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _models(image: np.ndarray):
    import cv2
    if not YUNET.is_file() or not SFACE.is_file():
        raise RuntimeError("Biometric model files are unavailable")
    detector = cv2.FaceDetectorYN.create(str(YUNET), "", (image.shape[1], image.shape[0]), 0.8, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(str(SFACE), "")
    return detector, recognizer


def create_embedding(raw: bytes) -> list[float]:
    import cv2
    import numpy as np
    image = _decode_image(raw)
    detector, recognizer = _models(image)
    _, faces = detector.detect(image)
    if faces is None or len(faces) != 1:
        raise ValueError("Capture must contain exactly one clear face")
    aligned = recognizer.alignCrop(image, faces[0])
    vector = recognizer.feature(aligned).reshape(-1).astype(np.float32)
    norm = float(np.linalg.norm(vector))
    if not norm:
        raise ValueError("Could not extract a face representation")
    vector /= norm
    return vector.tolist()


def compare_embedding(raw: bytes, reference: list[float]) -> tuple[bool, float]:
    import cv2
    import numpy as np
    image = _decode_image(raw)
    detector, recognizer = _models(image)
    _, faces = detector.detect(image)
    if faces is None or len(faces) != 1:
        return False, 0.0
    aligned = recognizer.alignCrop(image, faces[0])
    candidate = recognizer.feature(aligned).reshape(-1).astype(np.float32)
    baseline = np.asarray(reference, dtype=np.float32).reshape(1, -1)
    score = float(recognizer.match(baseline, candidate.reshape(1, -1), cv2.FaceRecognizerSF_FR_COSINE))
    return score >= COSINE_THRESHOLD, score
