# Voces · Parte 1: Sabor nuevo

Herramienta recomendada: **ElevenLabs** (modelo v3, el más expresivo). Crea cada voz **una sola vez** con *Voice Design* usando la descripción de abajo y reutilízala en las 5 partes para que suene siempre igual.

- Las etiquetas entre corchetes (`[whispers]`, `[scared]`…) son *audio tags* de ElevenLabs v3: déjalas, no se leen en voz alta. Si usas otra herramienta, usa la versión «texto limpio».
- Exporta cada frase en MP3/WAV con el nombre de archivo indicado: así el montaje es muy fácil.
- Las frases **en cámara** son las que llevan lip-sync.

## Reparto de voces

| Personaje | Cómo suena | Ajustes recomendados |
|---|---|---|
| **Narrador** (voz en off) | Hombre maduro, castellano de España. Grave, lento, de tráiler de terror. | Stability 60% · Similarity 80% · Style 25% |
| **Teo** (Plátano) | Hombre, ~30 años, castellano de España. Atlético, sin aliento, asustado. | Stability 35% · Similarity 75% · Style 40% |
| **Presentadora de TV** (Pera) | Mujer, ~40 años, castellano. Voz neutra y profesional de telediario. | Stability 65% · Similarity 75% · Style 10% |
| **Lía** (Fresa) | Mujer, ~27 años, castellano de España. Clara, enérgica, decidida; se rompe cuando tiene miedo. | Stability 40% · Similarity 80% · Style 35% |
| **Nico** (Arándano) | Niño de 10 años, castellano de España. Agudo, rápido, listo y cabezota. | Stability 40% · Similarity 75% · Style 35% |

### Descripciones para *Voice Design* (pégalas tal cual)

**Narrador**
```
Deep mature male narrator, native Castilian Spanish accent from Spain. Slow, suspenseful horror-movie-trailer delivery, warm gravelly tone. Cinematic studio quality.
```

**Teo**
```
Male, around 30, native Castilian Spanish accent from Spain. Athletic young man, breathless and frightened. Natural and realistic.
```

**Presentadora de TV**
```
Female, 40s, native Castilian Spanish accent from Spain. Neutral, professional TV news anchor voice.
```

**Lía**
```
Female, late 20s, native Castilian Spanish accent from Spain. Clear, energetic and determined young journalist, very expressive, can go from confident to terrified. Natural, realistic, studio quality.
```

**Nico**
```
10-year-old boy, native Castilian Spanish accent from Spain. Bright, fast-talking, smart and stubborn child voice, expressive. Natural and realistic, not cartoonish.
```

## Frases en orden de aparición

### 01. Narrador · plano 01 · voz en off, sin lip-sync
Archivo: `P1_01_plano01_NARRADOR.mp3` · Interpretación: lento, grave, misterioso · Duración aprox.: 5.9 s

ElevenLabs v3:
```
[slow, ominous] En Frutópolis, nadie sale a correr después de medianoche. [pause] Teo no lo sabía.
```
Texto limpio:
```
En Frutópolis, nadie sale a correr después de medianoche. Teo no lo sabía.
```

### 02. Teo · plano 03 · en cámara → lip-sync
Archivo: `P1_02_plano03_TEO.mp3` · Interpretación: nervioso, sin aliento · Duración aprox.: 2.8 s

ElevenLabs v3:
```
[nervous, out of breath] ¿Hola...? Tío, ¿quién anda ahí?
```
Texto limpio:
```
¿Hola...? Tío, ¿quién anda ahí?
```

### 03. Teo · plano 05 · en cámara → lip-sync
Archivo: `P1_03_plano05_TEO.mp3` · Interpretación: pánico, susurrando · Duración aprox.: 1.8 s

ElevenLabs v3:
```
[panicking, whispering] No, no, no, no...
```
Texto limpio:
```
No, no, no, no...
```

### 04. Narrador · plano 08 · voz en off, sin lip-sync
Archivo: `P1_04_plano08_NARRADOR.mp3` · Interpretación: lento, grave · Duración aprox.: 3.7 s

ElevenLabs v3:
```
[slow, deep] El sabor del miedo. [pause] Parte uno: Sabor nuevo.
```
Texto limpio:
```
El sabor del miedo. Parte uno: Sabor nuevo.
```

### 05. Presentadora de TV · plano 09 · sale de la tele, lip-sync a la presentadora en pantalla
Archivo: `P1_05_plano09_TV.mp3` · Interpretación: profesional, neutra · Duración aprox.: 8.4 s

ElevenLabs v3:
```
[neutral, professional] Tercer desaparecido esta semana. Teo Plátano, de treinta años, salió a correr anoche... y no ha vuelto a casa.
```
Texto limpio:
```
Tercer desaparecido esta semana. Teo Plátano, de treinta años, salió a correr anoche... y no ha vuelto a casa.
```

### 06. Lía · plano 10 · en cámara → lip-sync
Archivo: `P1_06_plano10_LÍA.mp3` · Interpretación: preocupada, pensativa · Duración aprox.: 3.7 s

ElevenLabs v3:
```
[worried, thoughtful] Tres en una semana... Esto no es casualidad.
```
Texto limpio:
```
Tres en una semana... Esto no es casualidad.
```

### 07. Nico · plano 11 · en cámara → lip-sync
Archivo: `P1_07_plano11_NICO.mp3` · Interpretación: urgente, gritando · Duración aprox.: 2.8 s

ElevenLabs v3:
```
[shouting, urgent] ¡Lía! ¡Ven ya! ¡Que te lo dije!
```
Texto limpio:
```
¡Lía! ¡Ven ya! ¡Que te lo dije!
```

### 08. Lía · plano 12 · en cámara → lip-sync
Archivo: `P1_08_plano12_LÍA.mp3` · Interpretación: escéptica, cansada · Duración aprox.: 5.1 s

ElevenLabs v3:
```
[sighs, skeptical] Nico, otra vez no, bro. Los Cereza no son villanos de película.
```
Texto limpio:
```
Nico, otra vez no, bro. Los Cereza no son villanos de película.
```

### 09. Nico · plano 13 · en cámara → lip-sync
Archivo: `P1_09_plano13_NICO.mp3` · Interpretación: intenso, rápido · Duración aprox.: 8.1 s

ElevenLabs v3:
```
[intense, fast] Escucha: cada vez que alguien desaparece, Delicia saca un sabor nuevo al día siguiente. ¡Es súper turbio!
```
Texto limpio:
```
Escucha: cada vez que alguien desaparece, Delicia saca un sabor nuevo al día siguiente. ¡Es súper turbio!
```

### 10. Nico · plano 14 · voz en off, sin lip-sync
Archivo: `P1_10_plano14_NICO.mp3` · Interpretación: serio, en voz baja · Duración aprox.: 2.9 s

ElevenLabs v3:
```
[serious, quiet] Mira. Lo han subido esta mañana.
```
Texto limpio:
```
Mira. Lo han subido esta mañana.
```

### 11. Lía · plano 15 · en cámara → lip-sync
Archivo: `P1_11_plano15_LÍA.mp3` · Interpretación: susurro, horrorizada · Duración aprox.: 2 s

ElevenLabs v3:
```
[whispering, horrified] Plátano... Como Teo.
```
Texto limpio:
```
Plátano... Como Teo.
```

### 12. Nico · plano 16 · voz en off, sin lip-sync
Archivo: `P1_12_plano16_NICO.mp3` · Interpretación: decidido, en voz baja · Duración aprox.: 4.9 s

ElevenLabs v3:
```
[determined, low] Esta noche me planto en el centro comercial y pillo pruebas.
```
Texto limpio:
```
Esta noche me planto en el centro comercial y pillo pruebas.
```

### 13. Lía · plano 17 · en cámara → lip-sync
Archivo: `P1_13_plano17_LÍA.mp3` · Interpretación: firme, preocupada · Duración aprox.: 4.1 s

ElevenLabs v3:
```
[firm, worried] Ni se te ocurra, Nico. ¿Me oyes? Ni se te ocurra.
```
Texto limpio:
```
Ni se te ocurra, Nico. ¿Me oyes? Ni se te ocurra.
```

### 14. Lía · plano 18 · voz en off, sin lip-sync
Archivo: `P1_14_plano18_LÍA.mp3` · Interpretación: preocupada, fuera de plano · Duración aprox.: 1.2 s

ElevenLabs v3:
```
[off-screen, worried] ¿Nico...?
```
Texto limpio:
```
¿Nico...?
```

### 15. Lía · plano 19 · en cámara → lip-sync
Archivo: `P1_15_plano19_LÍA.mp3` · Interpretación: pánico, respiración rápida · Duración aprox.: 5.1 s

ElevenLabs v3:
```
[panicked, breathing fast] Bruno, soy yo. Nico se ha escapado... Va a tu centro comercial.
```
Texto limpio:
```
Bruno, soy yo. Nico se ha escapado... Va a tu centro comercial.
```

### 16. Narrador · plano 20 · voz en off, sin lip-sync
Archivo: `P1_16_plano20_NARRADOR.mp3` · Interpretación: lento, inquietante · Duración aprox.: 6.7 s

ElevenLabs v3:
```
[slow, ominous] Nico fue a buscar pruebas. [pause] Pero esa noche... las pruebas también lo encontraron a él.
```
Texto limpio:
```
Nico fue a buscar pruebas. Pero esa noche... las pruebas también lo encontraron a él.
```
