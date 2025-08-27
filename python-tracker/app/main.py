# main.py — same protocol, zero-freeze gender via background thread
import cv2, threading, time
from mediapipe_pose import MPose
from feature_utils import normalize_pose
from smoothing import BoneSmoother
from pose_sender import PoseSender
from gender import GenderClassifier
from person_gate import PersonGate

# How often to refresh gender (seconds). Tune as you like.
GENDER_INTERVAL_SEC = 3.0

class GenderWorker:
    """Runs DeepFace off-thread; exposes latest label in .label."""
    def __init__(self):
        self.gc = GenderClassifier()
        self.label = 'unknown'
        self._busy = threading.Event()
        self._last_ts = 0.0

    def maybe_kick(self, frame_bgr, landmarks, interval_sec=GENDER_INTERVAL_SEC):
        now = time.time()
        if self._busy.is_set(): return
        if now - self._last_ts < interval_sec: return
        self._busy.set()
        threading.Thread(
            target=self._run, args=(frame_bgr.copy(), landmarks), daemon=True
        ).start()

    def _run(self, frame_bgr, landmarks):
        try:
            self.label = self.gc.predict(frame_bgr, landmarks=landmarks) or 'unknown'
            self._last_ts = time.time()
        except Exception:
            self.label = 'unknown'
        finally:
            self._busy.clear()

def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    # If you still notice general latency, uncomment the next two lines:
    # cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    # cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    mp_pose = MPose(model_complexity=1)  # keep as-is (your mapping was fine) :contentReference[oaicite:1]{index=1}
    smoother = BoneSmoother(beta=0.7)    # :contentReference[oaicite:2]{index=2}
    sender = PoseSender(port=5056)       # :contentReference[oaicite:3]{index=3}
    gate = PersonGate(stable_frames=8, absent_timeout=0.8)  # :contentReference[oaicite:4]{index=4}
    gender = GenderWorker()              # background, non-blocking

    gender_cache = 'unknown'
    frame_i = 0

    print("[INFO] Streaming... Press Q to quit")
    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        frame_i += 1
        landmarks = mp_pose.process(frame)
        detected = landmarks is not None

        event = gate.step(detected)

        if detected:
            # Kick the gender thread occasionally (never blocks the loop)
            gender.maybe_kick(frame, landmarks, GENDER_INTERVAL_SEC)
            gender_cache = gender.label  # use the latest available label

            bones = normalize_pose(landmarks)      # :contentReference[oaicite:5]{index=5}
            bones = smoother.smooth_dict(bones)    # :contentReference[oaicite:6]{index=6}
            sender.send(gender_cache, event, bones)  # :contentReference[oaicite:7]{index=7}

            cv2.putText(frame, f"Gender: {gender_cache}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        else:
            if event == 'left':
                sender.send('unknown', event, {})

        cv2.imshow("Tracker - Press Q to quit", frame)
        if (cv2.waitKey(1) & 0xFF) in (ord('q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
