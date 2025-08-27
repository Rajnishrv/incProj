# gender.py — non-blocking friendly, pose-ROI aware
import cv2

try:
    from deepface import DeepFace
    _HAS_DF = True
except Exception:
    _HAS_DF = False

_FACE_IDS = [0, 1, 2, 3, 4]  # nose, eyes, ears

def _face_bbox_from_pose(landmarks, frame_shape, pad=0.35):
    """
    landmarks: (33,4) normalized (x,y,z,vis) in [0,1] from MediaPipe Pose
    frame_shape: (H, W, C)
    returns (x0,y0,x1,y1) or None
    """
    if landmarks is None or len(landmarks) < 5:
        return None
    H, W = frame_shape[:2]
    xs, ys = [], []
    for i in _FACE_IDS:
        x = float(landmarks[i, 0]); y = float(landmarks[i, 1])
        if 0 <= x <= 1 and 0 <= y <= 1:
            xs.append(x); ys.append(y)
    if len(xs) < 2:  # not enough points
        return None

    x_min, x_max = max(0.0, min(xs)), min(1.0, max(xs))
    y_min, y_max = max(0.0, min(ys)), min(1.0, max(ys))

    cx = (x_min + x_max) * 0.5
    cy = (y_min + y_max) * 0.5
    side = max(x_max - x_min, y_max - y_min)
    side *= (1.0 + pad * 2.0)

    x0 = int(W * (cx - side * 0.5)); y0 = int(H * (cy - side * 0.5))
    x1 = int(W * (cx + side * 0.5)); y1 = int(H * (cy + side * 0.5))

    x0 = max(0, min(W - 1, x0)); y0 = max(0, min(H - 1, y0))
    x1 = max(0, min(W, x1));      y1 = max(0, min(H, y1))
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)

class GenderClassifier:
    def __init__(self, detector_backend='retinaface'):
        # You can try 'opencv' or 'ssd' if retinaface is slow on your machine.
        self.backend = detector_backend if _HAS_DF else None

    def predict(self, bgr_frame, landmarks=None):
        """
        Returns: 'male' | 'female' | 'unknown'
        Uses a face ROI derived from pose landmarks to improve robustness & speed.
        """
        if not _HAS_DF or bgr_frame is None:
            return "unknown"

        roi = None
        if landmarks is not None:
            box = _face_bbox_from_pose(landmarks, bgr_frame.shape, pad=0.35)
            if box:
                x0, y0, x1, y1 = box
                roi = bgr_frame[y0:y1, x0:x1]

        img = roi if roi is not None and roi.size > 0 else bgr_frame
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        try:
            res = DeepFace.analyze(
                rgb,
                actions=['gender'],
                detector_backend=self.backend,
                enforce_detection=False
            )
            obj = res[0] if isinstance(res, list) and len(res) > 0 else res
            g = obj.get('gender')
            if isinstance(g, dict):
                return 'female' if (g.get('Woman', 0) >= g.get('Man', 0)) else 'male'
            if isinstance(g, str):
                v = g.lower()
                if 'fem' in v or v == 'woman': return 'female'
                if 'male' in v or v == 'man':  return 'male'
            return "unknown"
        except Exception:
            return "unknown"
