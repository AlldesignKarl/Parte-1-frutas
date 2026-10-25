# Herramientas de producción (motor de vídeo)

Código con el que se generan los vídeos de «El sabor del miedo» a partir de las imágenes o clips de cada plano.

| Archivo | Qué hace |
|---|---|
| `render.py` | Monta el vídeo vertical 1080×1920: cámara, efectos (lluvia, niebla, parpadeo de luces, interferencias, escarcha, chispas…), lip-sync, música, efectos de sonido y cartelas. Acepta imágenes fijas o clips de vídeo por plano. |
| `mouth.py` | Animación de la boca por visemas (abre, redondea y estira según cada sonido). |
| `detect_face.py` / `track_video.py` | Localizan la boca en una imagen o la siguen fotograma a fotograma en un clip (MediaPipe). |
| `voices.py` / `tts.py` | Voces en castellano con Kokoro-82M (ONNX) y tiempos de cada fonema para el lip-sync. |
| `cb_tts.py` | Voces con Chatterbox Multilingual (más realistas). |
| `sfx.py` / `music.py` | Efectos de sonido y música sintetizados. |
| `guiones/` | Guion de las 5 partes en datos (`partN.py`) y generador de los kits (`build.py`). |

Los modelos no están en el repositorio por tamaño:
- Kokoro v1.0 q8: paquete npm `kokoro-q8-shards` (unir las 6 partes); voces `.pt` del repo `remsky/Kokoro-FastAPI` (`api/src/voices/v1_0`).
- Para el lip-sync con tiempos, se añade la salida `/encoder/Clip_output_0` al grafo ONNX (ver `voices.py`).
