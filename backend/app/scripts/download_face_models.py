"""Download pinned OpenCV Zoo face models with SHA-256 verification."""
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen


MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://huggingface.co/opencv/opencv_zoo/resolve/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://huggingface.co/opencv/opencv_zoo/resolve/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
}


def download_models(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for filename, (url, expected_hash) in MODELS.items():
        target = destination / filename
        if target.exists() and sha256(target.read_bytes()).hexdigest() == expected_hash:
            continue
        with urlopen(url, timeout=90) as response:
            content = response.read()
        actual_hash = sha256(content).hexdigest()
        if actual_hash != expected_hash:
            raise RuntimeError(f"SHA-256 verification failed for {filename}")
        target.write_bytes(content)


if __name__ == "__main__":
    import os
    download_models(Path(os.getenv("FACE_MODELS_DIR", "/opt/recruito/models")))
