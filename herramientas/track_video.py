"""Seguimiento de caras fotograma a fotograma en un clip (MediaPipe FaceMesh).
Uso: mpenv/bin/python track_video.py clip.mp4 salida.json"""
import json
import sys

import cv2
import mediapipe as mp
import numpy as np

L_CORNER, R_CORNER, UP, LO, CHIN = 61, 291, 13, 14, 152


def main(path, out):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frames = []
    with mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=3, refine_landmarks=True,
                                         min_detection_confidence=0.25, min_tracking_confidence=0.3) as fm:
        while True:
            ok, img = cap.read()
            if not ok:
                break
            h, w = img.shape[:2]
            res = fm.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            faces = []
            for lm in res.multi_face_landmarks or []:
                P = np.array([[p.x * w, p.y * h] for p in lm.landmark])
                lc, rc = P[L_CORNER], P[R_CORNER]
                c = (lc + rc + P[UP] + P[LO]) / 4
                faces.append(dict(center=[float(c[0]), float(c[1])], width=float(np.linalg.norm(rc - lc)),
                                  angle=float(np.degrees(np.arctan2(rc[1] - lc[1], rc[0] - lc[0]))),
                                  chin=[float(P[CHIN][0]), float(P[CHIN][1])],
                                  box=[float(P[:, 0].min()), float(P[:, 1].min()), float(P[:, 0].max()), float(P[:, 1].max())]))
            frames.append(faces)
    json.dump(dict(fps=fps, size=[w, h] if frames else [0, 0], frames=frames), open(out, "w"))
    found = sum(1 for f in frames if f)
    print(f"{path}: {len(frames)} fotogramas, cara en {found}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
