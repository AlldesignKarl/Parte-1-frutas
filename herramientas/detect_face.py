"""Detecta boca y ojos con MediaPipe FaceMesh. Uso: mpenv/bin/python detect_face.py img... --debug outdir
Escribe un JSON por imagen (junto a la imagen o en --out) con la lista de caras encontradas."""
import argparse
import json
import os

import cv2
import mediapipe as mp
import numpy as np

LIPS_OUT = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
UPPER_INNER, LOWER_INNER = 13, 14
L_CORNER, R_CORNER = 61, 291
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
CHIN = 152


def detect(path, scale_try=(1.0, 0.6, 1.6)):
    img = cv2.imread(path)
    h, w = img.shape[:2]
    faces = []
    with mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=4, refine_landmarks=True,
                                         min_detection_confidence=0.2) as fm:
        for s in scale_try:
            im = cv2.resize(img, None, fx=s, fy=s) if s != 1.0 else img
            res = fm.process(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
            if res.multi_face_landmarks:
                for lm in res.multi_face_landmarks:
                    P = np.array([[p.x * w, p.y * h] for p in lm.landmark])
                    faces.append(P)
                break
    out = []
    for P in faces:
        lc, rc = P[L_CORNER], P[R_CORNER]
        up, lo = P[UPPER_INNER], P[LOWER_INNER]
        center = (lc + rc + up + lo) / 4
        width = float(np.linalg.norm(rc - lc))
        angle = float(np.degrees(np.arctan2(rc[1] - lc[1], rc[0] - lc[0])))
        eyes = []
        for idx in (LEFT_EYE, RIGHT_EYE):
            E = P[idx]
            c = E.mean(0)
            ew = float(np.linalg.norm(E[0] - E[3]))
            eh = float(np.linalg.norm(E[1] - E[5]) + np.linalg.norm(E[2] - E[4])) / 2
            eyes.append(dict(center=[float(c[0]), float(c[1])], w=ew, h=eh))
        out.append(dict(mouth=dict(center=[float(center[0]), float(center[1])], width=width, angle=angle,
                                   gap=float(np.linalg.norm(lo - up))),
                        chin=[float(P[CHIN][0]), float(P[CHIN][1])], eyes=eyes,
                        face_box=[float(P[:, 0].min()), float(P[:, 1].min()), float(P[:, 0].max()), float(P[:, 1].max())]))
    return img, out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--debug")
    ap.add_argument("--out")
    a = ap.parse_args()
    for p in a.images:
        img, faces = detect(p)
        name = os.path.splitext(os.path.basename(p))[0]
        dst = os.path.join(a.out or os.path.dirname(p), name + ".face.json")
        json.dump(dict(image=p, size=[img.shape[1], img.shape[0]], faces=faces), open(dst, "w"), indent=1)
        print(name, "faces:", len(faces), [round(f["mouth"]["width"]) for f in faces])
        if a.debug:
            os.makedirs(a.debug, exist_ok=True)
            d = img.copy()
            for f in faces:
                m = f["mouth"]
                c = tuple(int(v) for v in m["center"])
                cv2.ellipse(d, c, (int(m["width"] / 2), max(3, int(m["width"] / 6))), m["angle"], 0, 360, (0, 255, 0), 2)
                for e in f["eyes"]:
                    cv2.circle(d, tuple(int(v) for v in e["center"]), int(e["w"] / 2), (255, 0, 255), 2)
                x0, y0, x1, y1 = (int(v) for v in f["face_box"])
                cv2.rectangle(d, (x0, y0), (x1, y1), (255, 255, 0), 2)
            cv2.imwrite(os.path.join(a.debug, name + "_debug.jpg"), d)
