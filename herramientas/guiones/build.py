"""Genera el kit de producción de una parte: python3 build.py 1 /home/user/Parte-1-frutas"""
import importlib
import os
import re
import sys

from common import (CHARS, EXTRAS, LOCS, NEGATIVE, SERIE, STYLE, clean_text, expand, fit,
                    line_secs, mmss, speaker_name, ts)

ANIM_SUFFIX = ("Keep the characters' design, outfits and fruit textures exactly as in the image. "
               "Smooth, realistic cinematic motion, no morphing, no extra limbs.")

MODE_TXT = {
    "on": "en cámara → lip-sync",
    "off": "voz en off, sin lip-sync",
    "tel": "por teléfono, sin lip-sync",
    "tv": "sale de la tele, lip-sync a la presentadora en pantalla",
    "intercom": "por el altavoz, sin lip-sync",
}

PARTES = {
    1: "Sabor nuevo",
    2: "Turno de noche",
    3: "La familia Cereza",
    4: "La Cámara 7",
    5: "El último sabor",
}


def img_prompt(s):
    if s.get("raw_img"):
        body = s["raw_img"]
    else:
        loc = LOCS[s["loc"]][1]
        extra = (", " + s["set"]) if s.get("set") else ""
        img = expand(s['img'])
        body = f"{s['cam']}. {img[:1].upper() + img[1:]}. Setting: {loc}{extra}. Lighting and mood: {s['light']}"
    return f"{body}. {STYLE}. Vertical 9:16 composition. --ar 9:16"


def anim_prompt(s):
    txt = s["anim"]
    if any(l[3] == "on" for l in s.get("lines", [])):
        txt += " The speaking character talks with natural mouth and lip movement, subtle head and eyebrow motion."
    return f"{txt} {ANIM_SUFFIX}"


def chars_in(s):
    import re
    keys = re.findall(r"\{([A-Z]+)\}", s.get("img", "") + " " + s.get("raw_img", ""))
    out = []
    for k in keys:
        n = speaker_name(k)
        if n not in out:
            out.append(n)
    return out


def sub_chunks(text, limit=80):
    """Corta frases largas por la puntuación para que cada subtítulo tenga como mucho ~80 caracteres."""
    parts = re.split(r"(?<=[.?!…,:])\s+", text)
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + 1 + len(p) > limit:
            out.append(cur)
            cur = p
        else:
            cur = (cur + " " + p).strip()
    if cur:
        out.append(cur)
    return out


def balance(text, width=40):
    """Una línea si cabe; si no, dos líneas de longitud parecida."""
    if len(text) <= width:
        return [text]
    words = text.split()
    best, best_diff = None, 10 ** 9
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        diff = abs(len(a) - len(b))
        if diff < best_diff:
            best, best_diff = [a, b], diff
    return best


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def build(num, outdir):
    P = importlib.import_module(f"part{num}").PART
    shots = P["shots"]
    total = fit(shots)
    titulo = PARTES[num]
    os.makedirs(outdir, exist_ok=True)

    speakers = []
    for s in shots:
        for l in s.get("lines", []):
            if l[0] not in speakers:
                speakers.append(l[0])

    # ------------------------------------------------------------ PLANOS.md
    o = [f"# {SERIE} · Parte {num}: {titulo}", "",
         f"## Storyboard y prompts plano a plano · {len(shots)} planos · duración total ≈ {mmss(total)}", "",
         "Cómo usar este archivo:",
         "1. **Prompt de imagen** → pégalo en tu generador de imágenes (Midjourney, Nano Banana / Gemini, Flux, Leonardo, Ideogram…). "
         "Sube las **fichas de personaje** (ver `PERSONAJES.md`) como referencia para que salgan siempre iguales. "
         "El `--ar 9:16` es para Midjourney; en las demás elige formato vertical 9:16.",
         "2. **Prompt de animación** → sube la imagen generada a Kling, Hailuo, Veo, Runway o similar (imagen → vídeo) y pega este texto.",
         "3. Planos con diálogo **en cámara → lip-sync**: genera la voz con `VOCES.md` y aplica lip-sync al clip "
         "(función Lip Sync de Kling, Hedra, Sync o la que uses). Así se mueve la boca al hablar.",
         "4. Si la herramienta genera clips de 5 o 10 s, recórtalos en el montaje a la duración indicada.",
         "", f"**Prompt negativo** (si tu herramienta lo admite):", "```", NEGATIVE, "```", ""]
    for i, s in enumerate(shots, 1):
        locname = s.get("place") or (LOCS[s["loc"]][0] if s.get("loc") else s.get("locname", ""))
        o += [f"---", "", f"### Plano {i:02d} · {mmss(s['start'])}–{mmss(s['start'] + s['dur'])} ({s['dur']:g} s) · {locname}", "",
              f"**Qué pasa:** {s['es']}", ""]
        ch = chars_in(s)
        if ch:
            o += [f"**Personajes:** {', '.join(ch)}", ""]
        if s.get("overlay"):
            o += [f"**Texto en pantalla (añádelo en el montaje):** {s['overlay']}", ""]
        o += ["**🖼️ Prompt de imagen:**", "```", img_prompt(s), "```", "",
              "**🎬 Prompt de animación:**", "```", anim_prompt(s), "```", ""]
        if s.get("lines"):
            o.append("**🗣️ Voz:**")
            for spk, text, tag, mode in s["lines"]:
                o.append(f"- **{speaker_name(spk)}** · {MODE_TXT[mode]} · _{tag}_: «{clean_text(text)}»")
            o.append("")
        o += [f"**🔊 Sonido:** {s['sfx']}", ""]
    write(os.path.join(outdir, "PLANOS.md"), "\n".join(o))

    # ------------------------------------------------------------ GUION.md
    g = [f"# {SERIE}", f"## Parte {num}: {titulo}", "",
         f"**Duración:** ≈ {mmss(total)} · **Formato:** vertical 9:16 · **Género:** terror / intriga", "",
         f"> {P['sinopsis']}", "", "---", ""]
    last_loc = None
    esc = 0
    for i, s in enumerate(shots, 1):
        loc = s.get("loc") or s.get("locname")
        heading = s.get("scene")
        if heading and heading != last_loc:
            esc += 1
            g += ["", f"### ESCENA {esc} — {heading}", ""]
            last_loc = heading
        g.append(f"*[{mmss(s['start'])}] Plano {i:02d}.* {s['es']}")
        g.append("")
        for spk, text, tag, mode in s.get("lines", []):
            extra = {"off": " (V.O.)", "tel": " (por teléfono)", "tv": " (en la tele)", "intercom": " (por el altavoz)"}.get(mode, "")
            g += [f"**{speaker_name(spk).upper()}{extra}** _({tag})_", f"> {clean_text(text)}", ""]
    g += ["---", "", "**CONTINUARÁ…**" if num < 5 else "**FIN… ¿o no?**"]
    write(os.path.join(outdir, "GUION.md"), "\n".join(g))

    # ------------------------------------------------------------ VOCES.md
    v = [f"# Voces · Parte {num}: {titulo}", "",
         "Herramienta recomendada: **ElevenLabs** (modelo v3, el más expresivo). Crea cada voz **una sola vez** con *Voice Design* "
         "usando la descripción de abajo y reutilízala en las 5 partes para que suene siempre igual.", "",
         "- Las etiquetas entre corchetes (`[whispers]`, `[scared]`…) son *audio tags* de ElevenLabs v3: déjalas, no se leen en voz alta. "
         "Si usas otra herramienta, usa la versión «texto limpio».",
         "- Exporta cada frase en MP3/WAV con el nombre de archivo indicado: así el montaje es muy fácil.",
         "- Las frases **en cámara** son las que llevan lip-sync.", "",
         "## Reparto de voces", "", "| Personaje | Cómo suena | Ajustes recomendados |", "|---|---|---|"]
    for k in speakers:
        info = CHARS.get(k) or EXTRAS.get(k)
        v.append(f"| **{info['nombre']}** ({info['fruta']}) | {info['voz_es']} | {info['ajustes']} |")
    v += ["", "### Descripciones para *Voice Design* (pégalas tal cual)", ""]
    for k in speakers:
        info = CHARS.get(k) or EXTRAS.get(k)
        v += [f"**{info['nombre']}**", "```", info["voz_design"], "```", ""]
    v += ["## Frases en orden de aparición", ""]
    n = 0
    for i, s in enumerate(shots, 1):
        for spk, text, tag, mode in s.get("lines", []):
            n += 1
            fname = f"P{num}_{n:02d}_plano{i:02d}_{speaker_name(spk).split()[-1].upper()}.mp3"
            v += [f"### {n:02d}. {speaker_name(spk)} · plano {i:02d} · {MODE_TXT[mode]}",
                  f"Archivo: `{fname}` · Interpretación: {tag} · Duración aprox.: {line_secs(text):g} s", "",
                  "ElevenLabs v3:", "```", text, "```", "Texto limpio:", "```", clean_text(text), "```", ""]
    write(os.path.join(outdir, "VOCES.md"), "\n".join(v))

    # ------------------------------------------------------------ subtitulos.srt
    srt = []
    idx = 0
    for s in shots:
        t = s["start"] + 0.3
        for spk, text, tag, mode in s.get("lines", []):
            d = line_secs(text)
            end = min(t + d, s["start"] + s["dur"] - 0.05)
            chunks = [balance(c) for c in sub_chunks(clean_text(text))]
            total_chars = sum(len(" ".join(c)) for c in chunks)
            ct = t
            for c in chunks:
                cd = (end - t) * len(" ".join(c)) / total_chars
                idx += 1
                srt += [str(idx), f"{ts(ct)} --> {ts(ct + cd)}", "\n".join(c), ""]
                ct += cd
            t += d + 0.3
    write(os.path.join(outdir, f"subtitulos_parte{num}.srt"), "\n".join(srt))

    # ------------------------------------------------------------ PERSONAJES.md
    pj = ["# Personajes y localizaciones · " + SERIE, "",
          "Este archivo es igual en las 5 partes. **Haz las fichas una sola vez** (al empezar la parte 1) y guárdalas: "
          "súbelas como imagen de referencia cada vez que generes un plano. Es la clave para que los personajes sean siempre los mismos.", "",
          "Estilo visual: render 3D de película de animación de alto presupuesto, texturas de fruta hiperrealistas (fibras de coco, "
          "piel brillante de cereza, semillas de fresa…), cuerpos humanos con proporciones realistas, ropa detallada, fondos "
          "semirrealistas con iluminación de cine. Tono de terror/intriga: luces frías, niebla, fluorescentes que parpadean.", "",
          "## Protagonistas y villanos", ""]
    for k, c in CHARS.items():
        if k == "NARRADOR":
            continue
        pj += [f"### {c['nombre']} — {c['fruta']}", f"- **Quién es:** {c['rol']}", f"- **Ropa:** {c['ropa']}",
               f"- **Voz:** {c['voz_es']}", "", "Prompt de ficha de personaje (character sheet):", "```",
               f"Character reference sheet of {c['prompt']}. Full body front view, three-quarter view, side view and back view, "
               f"plus face close-ups with three expressions (neutral, scared, angry), plain light grey studio background, "
               f"consistent design, {STYLE}. --ar 16:9", "```", ""]
    pj += ["## Secundarios", ""]
    for k, c in EXTRAS.items():
        pj += [f"### {c['nombre']} — {c['fruta']}", f"- {c['rol']}", "```",
               f"Character reference sheet of {c['prompt']}. Full body front and three-quarter views, plain light grey studio "
               f"background, {STYLE}. --ar 16:9", "```", ""]
    pj += ["## Localizaciones", "",
           "Genera también una imagen de cada fondo (sin personajes) y úsala de referencia para que el lugar sea coherente entre planos.", ""]
    for k, (name, desc) in LOCS.items():
        pj += [f"### {name}", "```", f"Establishing shot, no characters: {desc}. {STYLE}. Vertical 9:16 composition. --ar 9:16", "```", ""]
    write(os.path.join(outdir, "PERSONAJES.md"), "\n".join(pj))

    # ------------------------------------------------------------ README.md
    cast = [speaker_name(k) for k in speakers if k != "NARRADOR"]
    r = [f"# {SERIE} — Parte {num} de 5: «{titulo}»", "",
         f"Miniserie de terror e intriga con frutas humanas en 3D. Formato vertical 9:16 · **≈ {mmss(total)}** · {len(shots)} planos.", "",
         "## Sinopsis", "", P["sinopsis"], "",
         "## Archivos", "",
         "| Archivo | Para qué sirve |", "|---|---|",
         "| [`GUION.md`](GUION.md) | La historia completa de esta parte: escenas, acciones y diálogos. |",
         "| [`PLANOS.md`](PLANOS.md) | Storyboard plano a plano con **prompt de imagen**, **prompt de animación**, voz y sonido. |",
         "| [`VOCES.md`](VOCES.md) | Voces realistas: descripción de cada voz para ElevenLabs y todas las frases listas para generar. |",
         f"| [`subtitulos_parte{num}.srt`](subtitulos_parte{num}.srt) | Subtítulos sincronizados; impórtalos en CapCut. |",
         "| [`PERSONAJES.md`](PERSONAJES.md) | Fichas de personaje y de fondos para que todo salga siempre igual. |", "",
         f"**Personajes que hablan en esta parte:** {', '.join(cast)} (+ narrador).", "",
         "## Cómo producirla (paso a paso)", "",
         "1. **Fichas** (solo la primera vez): genera las fichas de `PERSONAJES.md` y guarda las mejores.",
         "2. **Imágenes**: genera la imagen de cada plano de `PLANOS.md` usando las fichas como referencia.",
         "3. **Voces**: crea las voces en ElevenLabs con *Voice Design* y genera todas las frases de `VOCES.md`.",
         "4. **Animación**: pasa cada imagen a vídeo (Kling, Hailuo, Veo, Runway…) con su prompt de animación.",
         "5. **Lip-sync**: en los planos marcados *en cámara → lip-sync*, sincroniza la boca con el audio de la voz.",
         "6. **Montaje** (CapCut): ordena los clips, pon las voces, importa el `.srt`, añade efectos de sonido y música, "
         "y exporta en 1080×1920, 30 fps.", "",
         "## Música", "", P["musica"], "",
         "## Texto para publicar", "", "```", P["publicar"], "```", ""]
    write(os.path.join(outdir, "README.md"), "\n".join(r))
    print(f"Parte {num}: {len(shots)} planos, {total:.1f} s ({mmss(total)}), {idx} frases")


if __name__ == "__main__":
    build(int(sys.argv[1]), sys.argv[2])
