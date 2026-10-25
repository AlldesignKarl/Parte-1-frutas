"""Datos compartidos (personajes, localizaciones, estilo) y renderizado de los kits."""
import math
import re

SERIE = "EL SABOR DEL MIEDO"

STYLE = (
    "high-end 3D animated feature film still, Pixar and DreamWorks quality CGI, "
    "hyper-detailed photorealistic fruit textures, realistic human body proportions, "
    "cinematic lighting, volumetric light, shallow depth of field, rich semi-realistic detailed background, "
    "subtle film grain, 8k"
)

NEGATIVE = (
    "2D, flat cartoon, anime, sketch, low poly, deformed hands, extra fingers, extra limbs, "
    "human head, human hair on fruit heads (except Valeria), blurry face, distorted face, "
    "text artifacts, misspelled signs, watermark, logo of real brands"
)

# ---------------------------------------------------------------- personajes
CHARS = {
    "BRUNO": dict(
        nombre="Bruno", fruta="Coco", rol="Protagonista. Vigilante nocturno del centro comercial Gran Vergel y novio de Lía. 35 años. Duro por fuera, blando por dentro.",
        ropa="Uniforme de vigilante azul marino con parche «SEGURIDAD», pantalón cargo negro, cinturón con linterna y walkie, reloj negro.",
        prompt=("Bruno, an anthropomorphic coconut man: his whole head is a real hairy brown coconut with coarse realistic fibers "
                "and three small dark 'eye' holes on top of the shell, an expressive human face sculpted into the coconut "
                "(thick dark eyebrows, warm brown eyes, human nose and mouth), muscular human body with brown skin covered in fine "
                "coconut fibers, wearing a navy-blue night security guard uniform shirt with a 'SEGURIDAD' patch, black cargo trousers, "
                "a utility belt with flashlight and walkie-talkie, black wristwatch"),
        voz_es="Hombre, ~35 años, castellano de España. Barítono grave y cálido, valiente pero cercano, textura algo rasposa.",
        voz_design=("Male, mid 30s, native Castilian Spanish accent from Spain. Deep warm baritone with a slightly rough texture. "
                    "Brave, protective and kind. Natural, realistic, cinematic studio quality."),
        ajustes="Stability 45% · Similarity 80% · Style 30%",
    ),
    "LIA": dict(
        nombre="Lía", fruta="Fresa", rol="Periodista de «El Eco de Frutópolis», 27 años. Hermana mayor de Nico. Lista, valiente, cabezota.",
        ropa="Chaqueta vaquera clara sobre camiseta blanca, vaqueros pitillo, botines marrones, cámara de fotos vintage cruzada.",
        prompt=("Lía, an anthropomorphic strawberry woman: her head is a real glossy red strawberry with tiny golden seeds and a crown "
                "of fresh green leaves on top, an expressive human face (big warm brown eyes with long lashes, small nose, soft lips), "
                "slim human body with red strawberry-textured skin, wearing a light-blue denim jacket over a white t-shirt, slim blue jeans, "
                "brown ankle boots and a vintage camera strap across her chest"),
        voz_es="Mujer, ~27 años, castellano de España. Clara, enérgica, decidida; se rompe cuando tiene miedo.",
        voz_design=("Female, late 20s, native Castilian Spanish accent from Spain. Clear, energetic and determined young journalist, "
                    "very expressive, can go from confident to terrified. Natural, realistic, studio quality."),
        ajustes="Stability 40% · Similarity 80% · Style 35%",
    ),
    "NICO": dict(
        nombre="Nico", fruta="Arándano", rol="Hermano pequeño de Lía, 10 años. Obsesionado con las conspiraciones… y esta vez tiene razón.",
        ropa="Camiseta raglán blanca con mangas verdes, vaqueros, zapatillas de lona azules con cordones blancos.",
        prompt=("Nico, a 10-year-old anthropomorphic blueberry boy: his head is a big round real blueberry with dusty matte blue skin "
                "and natural bloom, a small dark star-shaped crown on top with a green stem and two fresh green leaves, an expressive "
                "human face (big turquoise eyes, thick dark eyebrows), small blue child body, wearing a white raglan t-shirt with green "
                "sleeves, blue jeans and blue canvas sneakers with white laces"),
        voz_es="Niño de 10 años, castellano de España. Agudo, rápido, listo y cabezota.",
        voz_design=("10-year-old boy, native Castilian Spanish accent from Spain. Bright, fast-talking, smart and stubborn child voice, "
                    "expressive. Natural and realistic, not cartoonish."),
        ajustes="Stability 40% · Similarity 75% · Style 35%",
    ),
    "TEO": dict(
        nombre="Teo", fruta="Plátano", rol="Corredor de 30 años. Tercer desaparecido de la semana.",
        ropa="Camiseta de tirantes gris, pantalón corto negro, calcetines y zapatillas blancas.",
        prompt=("Teo, an anthropomorphic banana man: his head is a tall real yellow banana with a brown stem tip on top and small brown "
                "speckles, an expressive human face, athletic muscular yellow body, wearing a grey running tank top, black running shorts, "
                "white socks and white sneakers"),
        voz_es="Hombre, ~30 años, castellano de España. Atlético, sin aliento, asustado.",
        voz_design=("Male, around 30, native Castilian Spanish accent from Spain. Athletic young man, breathless and frightened. "
                    "Natural and realistic."),
        ajustes="Stability 35% · Similarity 75% · Style 40%",
    ),
    "VICENTE": dict(
        nombre="Don Vicente Cereza", fruta="Cereza", rol="Villano. Dueño de Heladerías Delicia, 55 años. Educado, elegante… y monstruoso.",
        ropa="Traje negro impecable, camisa blanca, corbata roja de seda, zapatos negros. Manos rojas brillantes.",
        prompt=("Don Vicente Cereza, an anthropomorphic cherry man: his head is a huge glossy deep-red cherry with a long thin green stem "
                "on top and polished reflective skin, an expressive human face with heavy brows, small cold eyes and a thin unsettling smile, "
                "glossy red hands, wearing an impeccable black two-piece suit, white shirt, red silk tie and black leather shoes"),
        voz_es="Hombre, ~55 años, castellano de España. Grave, lento, aterciopelado, educadísimo y escalofriante.",
        voz_design=("Male, mid 50s, native Castilian Spanish accent from Spain. Deep, slow, velvety and extremely polite voice of an elegant "
                    "villain; calm but chilling. Cinematic, realistic, studio quality."),
        ajustes="Stability 55% · Similarity 80% · Style 30%",
    ),
    "VALERIA": dict(
        nombre="Valeria Cereza", fruta="Cereza", rol="Esposa de Don Vicente y la verdadera mente del imperio Delicia. 45 años.",
        ropa="Vestido lápiz azul marino de manga larga con bordados dorados, tacones granate, pulseras y bolso de mano dorados.",
        prompt=("Valeria Cereza, an elegant anthropomorphic cherry woman: her head is a glossy dark-red cherry with a brown stem and one green "
                "leaf on top, wavy shoulder-length burgundy hair, an expressive human face with winged eyeliner, long lashes and glossy red lips, "
                "small gold hoop earrings and a gold necklace, glossy red skin, wearing a fitted navy-blue long-sleeve pencil dress with gold "
                "embroidery, gold bracelets and burgundy high heels, holding a small gold clutch"),
        voz_es="Mujer, ~45 años, castellano de España. Grave, suave, seductora y helada. Habla bajito.",
        voz_design=("Female, mid 40s, native Castilian Spanish accent from Spain. Low, smooth, seductive and ice-cold voice; speaks softly "
                    "with quiet menace. Cinematic, realistic, studio quality."),
        ajustes="Stability 50% · Similarity 80% · Style 40%",
    ),
    "ROCCO": dict(
        nombre="Rocco", fruta="Piña", rol="Encargado de la cámara frigorífica de Delicia, 40 años. Enorme y asustado: tienen a su hija.",
        ropa="Delantal de trabajo de rayas blanco y gris manchado con logo de cereza, camiseta negra, guantes térmicos azules.",
        prompt=("Rocco, a huge anthropomorphic pineapple man: his head and body have real pineapple skin texture (golden-orange diamond scales "
                "with tiny spikes) and spiky green pineapple leaves crowning his head, an expressive human face with a broad jaw, bodybuilder "
                "physique, wearing a stained white-and-grey pinstriped work apron with a small cherry logo, a black t-shirt underneath and "
                "thick blue thermal gloves"),
        voz_es="Hombre, ~40 años, castellano de España. Muy grave y ronco, nervioso, casi siempre susurrando.",
        voz_design=("Male, 40s, native Castilian Spanish accent from Spain. Very deep, husky voice of a huge man with a soft heart; nervous, "
                    "often whispering. Realistic, studio quality."),
        ajustes="Stability 45% · Similarity 80% · Style 30%",
    ),
    "ORTEGA": dict(
        nombre="Inspector Ortega", fruta="Naranja", rol="Inspector de policía, 50 años. Cansado, desconfiado… y comprado.",
        ropa="Camisa de lino blanca remangada, pantalón de lino beige, cinturón con placa dorada, funda de pistola al hombro, zapatillas blancas.",
        prompt=("Inspector Ortega, an anthropomorphic orange man in his fifties: his head is a real round orange with dimpled peel texture and a "
                "small green leaf on top, an expressive human face with a permanent frown and tired eyes, glossy orange hands, wearing a white "
                "linen shirt with rolled sleeves, beige linen trousers, a brown leather belt with a gold police badge, a shoulder holster and "
                "white sneakers"),
        voz_es="Hombre, ~50 años, castellano de España. Seco, cansado, voz rasposa de fumador.",
        voz_design=("Male, 50s, native Castilian Spanish accent from Spain. Dry, tired, raspy smoker's voice, dismissive cop. Realistic."),
        ajustes="Stability 55% · Similarity 75% · Style 25%",
    ),
    "NARRADOR": dict(
        nombre="Narrador", fruta="voz en off", rol="Voz en off. Abre y cierra cada parte.",
        ropa="—", prompt="",
        voz_es="Hombre maduro, castellano de España. Grave, lento, de tráiler de terror.",
        voz_design=("Deep mature male narrator, native Castilian Spanish accent from Spain. Slow, suspenseful horror-movie-trailer delivery, "
                    "warm gravelly tone. Cinematic studio quality."),
        ajustes="Stability 60% · Similarity 80% · Style 25%",
    ),
}

EXTRAS = {
    "PRESENTADORA": dict(
        nombre="Presentadora de TV", fruta="Pera", rol="Presentadora del telediario (sale en la tele de Lía, parte 1).",
        prompt=("a TV news anchor who is an anthropomorphic pear woman with a smooth green-yellow pear head and a neat human face, "
                "wearing a grey blazer, sitting at a news desk"),
        voz_es="Mujer, ~40 años, castellano. Voz neutra y profesional de telediario.",
        voz_design="Female, 40s, native Castilian Spanish accent from Spain. Neutral, professional TV news anchor voice.",
        ajustes="Stability 65% · Similarity 75% · Style 10%",
    ),
    "SANDIAS": dict(
        nombre="Los matones Sandía", fruta="Sandía", rol="Guardaespaldas de los Cereza (partes 4 y 5). No hablan.",
        prompt=("two huge anthropomorphic watermelon thugs with striped dark-green watermelon heads and stern human faces, "
                "black suits, black ties and dark sunglasses"),
    ),
    "SOL": dict(
        nombre="Sol", fruta="Piña", rol="Hija de Rocco, 8 años (parte 5). No habla.",
        prompt="Sol, a small 8-year-old anthropomorphic pineapple girl with a tiny pineapple head, short green leaves and a yellow dress",
    ),
    "POLICIAS": dict(
        nombre="Policías Limón", fruta="Limón", rol="Agentes de policía honrados (parte 5). No hablan.",
        prompt="police officers who are anthropomorphic lemons with bright yellow lemon heads and human faces, in navy-blue police uniforms",
    ),
    "CIVILES": dict(
        nombre="Vecinos de Frutópolis", fruta="Varias", rol="Gente de fondo: peras, kiwis, manzanas, sandías, mangos…",
        prompt=("a crowd of anthropomorphic fruit people (pears, kiwis, apples, mangoes, watermelons) with fruit heads, human faces "
                "and casual modern clothes"),
    ),
}

# ---------------------------------------------------------------- localizaciones
LOCS = {
    "CALLE_LLUVIA": ("Calle de Frutópolis, noche de lluvia",
        "a narrow old European street at night in heavy rain, wet cobblestones reflecting warm streetlamps, old brick buildings "
        "with arched wooden doors, parked cars in the distance, puddles, low dark storm clouds"),
    "CALLEJON": ("Callejón sin salida",
        "a dark dead-end alley between brick walls at night, rain, overflowing bins, a single flickering lamp, a black delivery van "
        "with a small glossy cherry logo and the gold words 'HELADOS DELICIA' painted on its side"),
    "CASA_LIA": ("Casa de Lía y Nico — salón/cocina",
        "a cozy warm apartment living room and kitchen with wooden floor, wooden cabinets, a jute rug, potted plants, a window with "
        "soft morning sunlight, a wall-mounted TV"),
    "CUARTO_NICO": ("Habitación de Nico",
        "a kid's bedroom with warm fairy lights along the curtains, a bedside lamp, a wooden bed, and the walls covered in "
        "a conspiracy board: printed photos of a cherry-headed businessman, newspaper clippings, missing-person posters of fruit people "
        "and red string connecting them"),
    "MALL_EXT": ("Exterior del centro comercial Gran Vergel, noche",
        "a huge modern shopping mall exterior at night with a big glowing sign 'GRAN VERGEL', an empty wet parking lot, and a pink-red "
        "neon sign 'HELADOS DELICIA' with a cherry logo flickering above one entrance"),
    "COCHE_LIA": ("Coche de Lía, noche",
        "the inside of a small car driving at night in the rain, raindrops streaming on the windshield, wipers moving, "
        "blurred city lights and traffic lights outside, dashboard glow"),
    "MALL_PARKING": ("Aparcamiento del centro comercial",
        "the outdoor parking lot of a huge modern shopping mall with a big 'GRAN VERGEL' sign and a pink-red neon "
        "'HELADOS DELICIA' cherry sign on the facade, rows of parked cars, lampposts"),
    "MALL_NOCHE": ("Interior del centro comercial, noche",
        "the interior of a huge empty shopping mall at night, a three-floor atrium with stopped escalators, closed glass storefronts, "
        "half of the lights off, polished reflective floor, long dark corridors, cold blue night lighting with a few flickering fluorescents"),
    "DELICIA_FACHADA": ("Fachada de Helados Delicia (dentro del centro comercial)",
        "a luxurious ice cream shop front inside the mall, pastel pink and deep cherry-red decor, gold lettering 'HELADOS DELICIA' with a "
        "glossy cherry logo, a metal shutter half closed, frost on the glass and thick white freezing mist seeping out onto the floor"),
    "PASILLO_SERVICIO": ("Pasillo de servicio",
        "a narrow concrete service corridor behind the mall shops, pipes on the ceiling, a heavy grey door with the sign "
        "'SOLO PERSONAL - ZONA DE FRÍO', frost around its edges, cold mist on the floor"),
    "SALA_SEGURIDAD": ("Sala de seguridad",
        "a small dark security control room with a wall of CCTV monitors glowing blue, a desk with a keyboard, coffee cups and a walkie-talkie"),
    "COMISARIA": ("Comisaría, despacho del inspector",
        "a dusty old police office in daylight with venetian blinds casting striped shadows, filing cabinets, a cluttered desk with folders, "
        "an old computer and a cork board"),
    "MALL_DIA": ("Centro comercial de día, gran reapertura",
        "the same shopping mall atrium in bright daylight, crowded, with a huge hanging banner 'GRAN REAPERTURA - HELADOS DELICIA' "
        "and balloons, a press photographer, cheerful decorations"),
    "DELICIA_MOSTRADOR": ("Mostrador de Helados Delicia",
        "inside a luxurious ice cream parlor, a long glass display full of colorful ice cream tubs, pastel pink walls, gold details, "
        "a glossy cherry logo on the wall, warm pastel lighting"),
    "TUNEL": ("Túneles de servicio, medianoche",
        "an underground concrete service tunnel below the mall at midnight, pipes, red emergency lights, dripping water, a wall clock "
        "showing 00:00"),
    "FABRICA": ("Obrador industrial secreto de Delicia",
        "a secret industrial ice cream factory: stainless steel machines, giant mixing vats, conveyor belts, hanging steel hooks, "
        "flickering fluorescent tubes, cold mist on the floor, dark and clinical"),
    "CAMARA7": ("La Cámara 7",
        "inside a giant walk-in freezer: icy walls covered in frost, eerie cold blue light, rows of huge transparent ice blocks, "
        "each one holding a frozen fruit person, hanging icicles, white breath vapor"),
    "SALA_MEZCLAS": ("Sala de mezclas",
        "an industrial mixing room with a slowly moving conveyor belt leading to a gigantic industrial blender with huge spinning "
        "steel blades, a control panel with a big red lever, red warning lights, steam"),
    "LIMUSINA": ("Interior de limusina",
        "the back seat of a luxury limousine at night, black leather seats, a starlight ceiling of tiny lights, city skyline lights "
        "through the window"),
    "NUEVA_CIUDAD": ("Otra ciudad, local nuevo",
        "a new shop front on a rainy street of another city at night, windows covered with brown paper, a sign 'HELADOS DELICIA - "
        "PRÓXIMA APERTURA' and a poster 'NUEVO SABOR: COCO' with a coconut ice cream picture"),
}


def char_prompt(key):
    if key in CHARS:
        return CHARS[key]["prompt"]
    return EXTRAS[key]["prompt"]


def expand(text):
    """{BRUNO} -> «Bruno (descripción completa)» la primera vez; después solo el nombre."""
    seen = set()

    def rep(m):
        k = m.group(1)
        info = CHARS.get(k) or EXTRAS.get(k)
        if k in seen:
            return info["nombre"]
        seen.add(k)
        pr = char_prompt(k)
        name, _, rest = pr.partition(", ")
        if name[:1].isupper() and rest:
            return f"{name} ({rest})"
        return pr

    return re.sub(r"\{([A-Z]+)\}", rep, text)


def line_secs(text):
    clean = re.sub(r"\[[^\]]*\]", "", text)
    return round(len(clean) / 14.0 + 0.5, 1)


def fit(shots):
    """Ajusta duraciones para que quepan los diálogos y calcula tiempos de inicio."""
    t = 0.0
    for s in shots:
        need = sum(line_secs(l[1]) for l in s.get("lines", [])) + 0.3 * len(s.get("lines", [])) + 0.4
        d = max(s["dur"], math.ceil(need * 2) / 2)
        s["dur"] = d
        s["start"] = t
        t += d
    return t


def ts(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def mmss(sec):
    return f"{int(sec)//60}:{int(sec)%60:02d}"


def speaker_name(k):
    return CHARS.get(k, EXTRAS.get(k, {})).get("nombre", k)


def clean_text(text):
    return re.sub(r"\s*\[[^\]]*\]\s*", " ", text).strip()
