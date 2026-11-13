"""Shared colors. Each species gets a small ramp (shadow / base / highlight)
so sprites stay in a limited, 8-bit-feeling palette."""

OUTLINE = "#140c1c"   # deep purple-black, used for every sprite outline
INK = "#140c1c"

TECH_BRO = {
    "skin": "#f0c09a", "skin_sh": "#c98f6e",
    "hair": "#4a2f1b", "hair_hi": "#7a5232",
    "vest": "#25365e", "vest_hi": "#3d5590", "vest_sh": "#172240",
    "shirt": "#9cc4f0", "shirt_sh": "#6a90c4",
    "pants": "#c7b289", "pants_sh": "#9a8662",
    "belt": "#3a2a1e", "buckle": "#d8c070",
    "shoe": "#f4f4f4", "sole": "#a8a8b0",
    "airpod": "#ffffff", "phone": "#22222a", "screen": "#5ff3ff", "logo": "#e8e8e8",
    "glow": "#dce8f0", "glow_sh": "#a8b4c8",   # skin lit by the screen
    "bubble": "#ffffff",
}

SWAMP = {
    "dark": "#1f3d1e", "base": "#3f6f2a", "hi": "#6fa33a",
    "belly": "#a3c25a", "belly_sh": "#7f9a3e",
    "moss": "#6b7a24", "slime": "#b8ff3a",
    "eye": "#ffe94a", "eye_core": "#ff7a00",
    "mouth": "#2a0f14", "teeth": "#f0eccc", "claw": "#e0dcb0",
}

SASQUATCH = {
    "fur": "#6e4428", "fur_dk": "#4a2c17", "fur_xdk": "#33200f", "fur_hi": "#96643a",
    "chest": "#8a5c38",
    "face": "#b08a6e", "face_sh": "#8a6650",
    "eye": "#f4f0e0", "foot": "#3e2c22", "foot_hi": "#5a4234",
}

SASSQUATCH = {
    "bow": "#ff6fb5", "bow_hi": "#ffb3d9", "bow_sh": "#c8407f",
    "lips": "#e0507f",
}

BANANA = {
    "yel": "#ffd93a", "hi": "#fff2a0", "sh": "#e3aa1f", "dk": "#a86e14",
    "stem": "#5a3a1a", "spot": "#8a5a1a",
    "limb": "#2a1a10", "glove": "#ffffff", "glove_sh": "#c8c8d8",
    "shoe": "#e83b3b", "shoe_hi": "#ff8a7a",
    "shades": "#101018", "shades_hi": "#6a8aff", "mouth": "#5a1a1a", "tongue": "#ff6a7a",
}

MUTANT = {
    "flesh": "#d98a8a", "flesh_hi": "#f4b8a8", "flesh_sh": "#b0606c", "flesh_dk": "#7a3048",
    "vein": "#5a1a3a", "stitch": "#f0f0e0",
    "eye_w": "#f4f4f4", "iris": "#e83b3b", "iris_alt": "#39d353",
    "tent": "#8a4aa8", "tent_hi": "#b07ad0", "tent_sh": "#5e2a7a", "sucker": "#f0a0c8",
    "glass": "#bfefff", "glass_hi": "#ffffff", "fluid": "#39ff14", "fluid_dk": "#1fb80a",
    "brain": "#ff9ab8", "brain_dk": "#d0608a",
    "metal": "#9aa0b0", "metal_dk": "#5a6070", "metal_hi": "#d0d4e0",
    "claw": "#e8603a", "claw_hi": "#ff9a6a", "claw_sh": "#a83a20",
    "mouth": "#2a0f14", "teeth": "#f0eccc",
}

FLY_MAN = {
    "coat": "#f0f0f4", "coat_sh": "#b4b8cc", "coat_dk": "#8a8ea8",
    "shirt": "#a8c4e8", "tie": "#b0303a", "pen_r": "#e83b3b", "pen_b": "#3d5590",
    "pants": "#4a4a5e", "pants_sh": "#33333f",
    "shoe": "#5a3a26", "shoe_hi": "#8a6040", "sole": "#2a1c14",
    "chit": "#4a4038", "chit_dk": "#2e2822", "chit_hi": "#6e6252", "face": "#c8b070",
    "eye": "#a8202e", "eye_dk": "#6a1020", "eye_hi": "#e8484c", "glint": "#ffd8c8",
    "prob": "#7a6248", "prob_tip": "#b09068",
    "limb": "#5a4c40", "limb_dk": "#3c3229", "bristle": "#8a7a64", "claw": "#1e1814",
    "wing": "#c8e4f0", "wing_sh": "#90aac8", "wing_hi": "#ffffff", "vein": "#6a84a8",
    "sheen_a": "#f4b0e8", "sheen_b": "#a8f4cc",
    "goo": "#c8e040", "goo_hi": "#f4ffa0", "goo_dk": "#8aa020",
}


ALIEN = {
    "skin": "#aab4bc", "skin_sh": "#7c8694", "skin_hi": "#d4dce4",
    "eye": "#0c0c14", "eye_hi": "#3c4a6a", "glint": "#ffffff", "mouth": "#5a6270",
    "suit": "#c4c8d8", "suit_sh": "#8a8ea8", "suit_hi": "#eef2ff", "trim": "#39d3a3",
    "boot": "#5a6078", "boot_hi": "#8a90a8",
    "gun": "#e83b3b", "gun_hi": "#ff8a7a", "gun_sh": "#9a2030", "metal": "#c0c4d0",
    "glow": "#5fffd7", "beam": "#5fffd7", "beam_alt": "#b06aff",
}


ZOMBIE = {
    "skin": "#8fb07e", "skin_sh": "#6a8a5e", "skin_dk": "#4c6646", "skin_hi": "#b4cc9c",
    "socket": "#3a2c3e", "pupil": "#f4f0b0",
    "mouth": "#2a0f14", "teeth": "#e8e0b8",
    "hair": "#3e3428", "hair_hi": "#5a4a38",
    "shirt": "#7c94b0", "shirt_sh": "#566a86",
    "pants": "#6e5a44", "pants_sh": "#4e3e2e",
    "shoe": "#3a3030", "shoe_hi": "#5a4a48",
    "wound": "#b0404a", "stitch": "#ece4c8",
}


MERMAID = {
    "skin": "#f6c9a6", "skin_sh": "#d39478",
    "hair": "#e0442e", "hair_hi": "#ff8a4e", "hair_sh": "#9a2626",
    "tail": "#24a894", "tail_hi": "#86f0c8", "tail_sh": "#16706e", "tail_dk": "#0f4a52",
    "fin": "#58d6c4", "fin_sh": "#2a8f92",
    "shell": "#c48ae8", "shell_hi": "#f2c8ff", "shell_sh": "#8456b0",
    "gold": "#f4cc4a", "gold_sh": "#b08428",
    "eye": "#1f6a8a", "lips": "#e2646a",
    "water": "#5fcfff", "foam": "#effcff",
}


MEDUSA = {
    "skin": "#b6e2a2", "skin_sh": "#7aae76",
    "coil": "#3c7258", "coil_hi": "#68a47a", "coil_sh": "#2a5244", "coil_dk": "#1c3830",
    "belly": "#ecd890", "belly_sh": "#c2a660",
    "snake": "#46b83e", "snake_hi": "#8ae860", "snake_sh": "#267a30",
    "snake_eye": "#ffe94a", "tongue": "#ff4a6a",
    "wrap": "#8a44b8", "wrap_hi": "#b470e0", "wrap_sh": "#5a2a80",
    "gold": "#f4cc4a", "gold_sh": "#b08428",
    "glow": "#fff27a", "glow_core": "#ffffff", "lips": "#3e7a4a",
    "stone": "#a8a89c", "stone_hi": "#dcdcd0", "stone_sh": "#6a6a62",
}


GIANT_SLUG = {
    "body": "#e8782c", "body_hi": "#ffae5a", "body_sh": "#b4501e", "body_dk": "#7a3214",
    "spot": "#8a3a16", "gloss": "#fff4dc",
    "sole": "#f6cc9c", "sole_sh": "#c8946a",
    "slime": "#a8e4f4", "slime_hi": "#ffffff",
    "hole": "#3a1208", "mouth": "#5a1a0a", "eye_w": "#ffffff",
    "acid": "#b8ff3a", "acid_hi": "#f4ffb0", "acid_sh": "#62b81c",
}


CENTAUR = {
    "coat": "#a7a9bd", "coat_hi": "#d6d8e4", "coat_sh": "#75778f", "coat_dk": "#5e6078",
    "leg_far": "#45465c",
    "tail": "#eceef6", "tail_sh": "#b4b6cc",
    "hoof": "#3a3036", "hoof_hi": "#6a5a60",
    "skin": "#eab48a", "skin_sh": "#b97b58",
    "hair": "#8a3c1c", "hair_hi": "#c0602c", "hair_dk": "#5a2412",
    "leaf": "#6abf3a", "leaf_dk": "#3a7a28",
    "bronze": "#d39a3c", "bronze_hi": "#f6d77c", "bronze_sh": "#9a6420",
    "tunic": "#c73b3b", "tunic_sh": "#8a2433", "leather": "#7a4a2a",
    "shaft": "#9a6a3a", "shaft_sh": "#6a4424", "tip": "#e4eaf4", "tip_sh": "#9aa4ba",
}


WYVERN = {
    "scale": "#7b4bb0", "scale_hi": "#a678d8", "scale_sh": "#55318a", "scale_dk": "#3a2064",
    "belly": "#f0c860", "belly_sh": "#c8963c",
    "mem": "#e8788a", "mem_sh": "#bc5272", "mem_dk": "#8c3a62", "mem_xdk": "#6a2c54",
    "horn": "#f2e6c8", "horn_sh": "#bfae8a", "claw": "#f2e6c8",
    "eye": "#ffe94a", "mouth": "#4a0f22", "tongue": "#ff6a8a",
    "fire_r": "#e8402a", "fire_o": "#ff9a2a", "fire_y": "#ffe45a", "fire_w": "#fff8c8",
    "smoke": "#9a90a8", "smoke_hi": "#cfc8d8",
}


KATANA_CHICK = {
    "skin": "#f2c4a0", "skin_sh": "#c99170",
    "hair": "#37334f", "hair_hi": "#6a6496",
    "band": "#e83b3b", "band_sh": "#a82434",
    "suit": "#ffd23a", "suit_hi": "#fff09a", "suit_sh": "#d49a1c", "stripe": "#1c1826",
    "shoe": "#1c1826", "sole": "#ffd23a",
    "steel": "#d8e2f0", "edge": "#ffffff",
    "wrap": "#3a2a4a", "wrap_hi": "#6a5a7a", "guard": "#e0b040",
    "trail": "#9fe0ff",
}


PAGEANT_QUEEN = {
    "skin": "#c98a62", "skin_sh": "#9a6446",
    "hair": "#f2c84a", "hair_hi": "#fff0a0", "hair_sh": "#c8902a",
    "gown": "#3f6ee8", "gown_hi": "#86a8ff", "gown_sh": "#2a46a8", "gown_dk": "#1e2f78",
    "sparkle": "#ffffff",
    "sash": "#f4f4f4", "sash_sh": "#c8c8d8", "letter": "#e8407a",
    "tiara": "#e8eef8", "gem": "#ff4a8a",
    "glove": "#ffffff", "glove_sh": "#c8c8d8",
    "lips": "#d0305a", "shoe": "#e8eef8",
    "rose": "#e8304a", "rose_hi": "#ff7a8a", "leaf": "#3aa04a", "wrap": "#f4e0f0",
}


SUCCUBUS = {
    "skin": "#d77ac4", "skin_sh": "#a8549a",
    "hair": "#4a2260", "hair_hi": "#7c4a9c",
    "horn": "#e8304a", "horn_hi": "#ff8a8a",
    "outfit": "#46305e", "outfit_hi": "#6e5090", "outfit_sh": "#2e1f40",
    "boot": "#b0203e", "boot_hi": "#e84a64",
    "wing": "#b82a5e", "wing_hi": "#e8588e", "wing_dk": "#6e1640",
    "eye": "#ffe14a", "mouth": "#6a1440", "fang": "#ffffff",
    "heart": "#ff3a6a", "heart_hi": "#ffb0c8", "heart_dk": "#c81e4e",
}


FAIRY = {
    "skin": "#f8d4b4", "skin_sh": "#d89c84", "cheek": "#f48a9a",
    "hair": "#f4c84a", "hair_hi": "#fff0a0", "hair_sh": "#c08a2a",
    "leaf": "#4cb848", "leaf_hi": "#9ae46a", "leaf_sh": "#2a8040", "leaf_dk": "#1c5434",
    "slipper": "#2a8040", "pom": "#ff8ac8",
    "wing": "#c8f2ff", "wing_hi": "#ffffff", "wing_sh": "#8cc8ec", "vein": "#6aa4dc",
    "eye": "#3a8ae8", "mouth": "#c0405a",
    "wand": "#f4f0ff", "wand_sh": "#b0a8d0",
    "star": "#ffe45a", "star_hi": "#fffbd8", "star_sh": "#f0a42a",
    "dust_p": "#ff9ae0", "dust_c": "#8af4ff", "dust_y": "#fff27a",
}


GHOST = {
    "sheet": "#e6eeff", "sheet_hi": "#ffffff", "sheet_sh": "#aebce8", "sheet_dk": "#7c88c8",
    "fade": "#5a5ea8",                         # the hem, going see-through
    "hole": "#2c2052", "hole_glint": "#6a7ad8", "mouth": "#3a2a64",
    "wail": "#9af4ff", "wail_alt": "#c8a8ff", "boo": "#ffffff",
}


COWBOY = {
    "skin": "#e8b48a", "skin_sh": "#b97f5c", "stubble": "#a8785e",
    "hair": "#5a3418", "stache": "#7a4420",
    "hat": "#c8843c", "hat_hi": "#e8ac5c", "hat_sh": "#8a5424", "band": "#4a2a14",
    "bandana": "#d8343a", "bandana_sh": "#9a2030", "dot": "#ffe8e0",
    "shirt": "#7aa0d0", "shirt_sh": "#52749e",
    "vest": "#7a4626", "vest_hi": "#a0643a", "vest_sh": "#552e18",
    "jeans": "#3a5a9a", "jeans_sh": "#283e70",
    "belt": "#3a2414", "buckle": "#f4cc4a", "buckle_hi": "#fff4b0",
    "boot": "#7a4422", "boot_hi": "#a8663a", "boot_sh": "#4a2814",
    "spur": "#c8ccd8", "spur_hi": "#ffffff",
    "gun": "#9aa0b0", "gun_hi": "#e0e4ee", "gun_sh": "#545a6a", "grip": "#e8dcc0",
    "flash": "#fff27a", "flash_hot": "#ffffff", "flash_r": "#ff9a2a", "smoke": "#c8c4d4",
}


DETECTIVE = {
    "skin": "#eab894", "skin_sh": "#b98462", "stubble": "#a88068",
    "hair": "#3a2c24",
    "hat": "#5e5c6a", "hat_hi": "#868494", "hat_sh": "#3a3846", "band": "#1e1a24",
    "coat": "#c4a46a", "coat_hi": "#e2c68c", "coat_sh": "#937644", "coat_dk": "#6a522e",
    "button": "#4a3420", "shirt": "#e8e4dc", "tie": "#9a2a34",
    "pants": "#4e4a58", "pants_sh": "#36323e",
    "shoe": "#3a2a24", "shoe_hi": "#6a5248",
    "pipe": "#6a3a1c", "pipe_hi": "#9a5a2c", "ember": "#ff7a2a", "smoke": "#b4b0c0",
    "brass": "#dcae44", "brass_sh": "#9a7224", "lens": "#9ed8ec", "lens_hi": "#ffffff",
    "handle": "#4a2c1a",
    "beam": "#fff27a", "beam_hot": "#ffffff", "fire": "#ff8a2a", "fire_r": "#e8402a",
}


TECHNOVIKING = {
    "skin": "#e8b07e", "skin_sh": "#bc7c52", "skin_hi": "#ffd6aa", "skin_dk": "#8e5436",
    "beard": "#f2c84a", "beard_hi": "#fff09a", "beard_sh": "#c08a28",
    "helm": "#a8b0c4", "helm_hi": "#e8ecf4", "helm_sh": "#68708a",
    "horn": "#f2e6c8", "horn_sh": "#bfae8a",
    "fur": "#d8ccb4", "fur_sh": "#9a8c76",
    "pants": "#7a5236", "pants_sh": "#553820",
    "boot": "#3a2c2a", "boot_hi": "#5e4a44",
    "belt": "#2a1e1a", "buckle": "#e0c060",
    "neon_c": "#5ff3ff", "neon_m": "#ff4ad8", "neon_g": "#b8ff3a", "neon_y": "#fff27a",
}


HEADLESS_HORSEMAN = {
    "coat": "#3a3640", "coat_hi": "#5e5a68", "coat_sh": "#29262e", "coat_dk": "#201d26",
    "eye": "#ff3a2a", "eye_hot": "#ffd84a",
    "smoke": "#6a6284", "smoke_hi": "#a69ec0", "smoke_dk": "#4a4462",
    "hoof": "#141018", "hoof_hi": "#4a4052",
    "tack": "#7a3a24", "tack_hi": "#a85a34", "bit": "#c8ccd8", "iron": "#7e8294", "blanket": "#8a2030",
    "cloak": "#5a3478", "cloak_hi": "#8456a4", "cloak_sh": "#3c2254", "cravat": "#e8e4dc",
    "lining": "#a02838", "lining_sh": "#6e1a2c",
    "brass": "#d8b048", "boot": "#2a2024", "boot_hi": "#54444a", "breeches": "#5e5448",
    "glove": "#2a2430", "glove_hi": "#4e4458",
    "stump": "#7a2a2a", "stump_hi": "#b04a3a",
    "flame": "#3ad85a", "flame_hi": "#a8ff7a", "flame_core": "#f4ffc8", "ember": "#ff9a2a",
    "pumpkin": "#f08a24", "pumpkin_hi": "#ffb84a", "pumpkin_sh": "#b85a14",
    "stem": "#4a6a24", "candle": "#ffe45a", "candle_hot": "#fff8c8",
}


DOMINATRIX = {
    "skin": "#f2d0c4", "skin_sh": "#c49a9a",
    "latex": "#33304f", "latex_hi": "#6670b8", "latex_sh": "#25223d", "gloss": "#b4c4ff",
    "hair": "#2a2036", "hair_hi": "#6e4c8e",
    "red": "#d8283e", "red_hi": "#ff6a78", "red_sh": "#8e1834",
    "silver": "#dde2f0", "silver_sh": "#8a90aa",
    "lips": "#ff2a4a",
    "whip": "#8a3a2c", "whip_hi": "#c8643e", "popper": "#f4ead0",
    "spark": "#fff27a",
}


GIMP = {
    "suit": "#3c3356", "suit_hi": "#7a66ac", "suit_sh": "#2a2340", "gloss": "#d0c0ff",
    "strap": "#221c30",
    "steel": "#dfe3ee", "steel_sh": "#8a8fa6",
    "eye": "#f4f0e4", "spark": "#fff27a",
}


STONER = {
    "skin": "#e8b48c", "skin_sh": "#c08466", "lid": "#8a4a3a",
    "hair": "#8a5a2a", "hair_hi": "#b07a3e", "hair_sh": "#5e3a1a",
    "eye": "#ffa0a0", "mouth": "#7a3428",
    "cap_r": "#d8343a", "cap_y": "#f2c83a", "cap_g": "#3aa04a", "cap_g_sh": "#26703a", "rib": "#2a2430",
    "dye_a": "#e8509a", "dye_b": "#ffa13a", "dye_c": "#ffe14a", "dye_d": "#3ac8c0", "dye_sh": "#7a4ab0",
    "shorts": "#8a8442", "shorts_hi": "#aaa45a", "shorts_sh": "#605c2c",
    "sole": "#3a8ad8", "sole_sh": "#245a98", "strap": "#f0f0f0",
    "paper": "#f4f0e0", "ember": "#ff6a2a", "ember_hi": "#ffe14a", "ash": "#8a8490",
    "smoke": "#b4c0b0", "smoke_hi": "#e6eedc", "smoke_sh": "#86907e",
}


JAZZ_SAX = {
    "skin": "#8a5a3c", "skin_sh": "#6a4028", "skin_hi": "#a87450",
    "hair": "#2a1c18", "goatee": "#3a241a",
    "hat": "#4a4a5a", "hat_hi": "#6e6e80", "hat_sh": "#32323e", "band": "#b8303a",
    "shades": "#101018", "shades_hi": "#6a8aff",
    "suit": "#444a70", "suit_hi": "#6a72a4", "suit_sh": "#2c2f4c",
    "turtle": "#1c1a24", "turtle_hi": "#3a3646", "square": "#e8e8f0",
    "shoe": "#f0ece0", "shoe_tip": "#1c1418",
    "brass": "#e8b030", "brass_hi": "#fff09a", "brass_sh": "#a8701c", "brass_dk": "#6a4410",
    "key": "#fff8e0", "reed": "#3a3646", "lig": "#d8dce8",
    "note": "#fff4c8", "wave": "#8fe3ff",
}


SPIDER = {
    "fur": "#644234", "fur_hi": "#94684c", "fur_sh": "#44302a", "fur_dk": "#2c1d1e",
    "rust": "#a85a38", "rust_hi": "#dc8c58", "rust_sh": "#743a26",
    "knee": "#f0782c", "knee_hi": "#ffb45a", "knee_sh": "#a8481e",
    "hair": "#c49a72",
    "eye": "#e8304a", "glint": "#ffd0d0",
    "fang": "#f2e6c8", "fang_sh": "#bfae8a", "venom": "#b8ff3a",
    "web": "#f4f4f8", "web_sh": "#b4bccc",
}


CRAWLING_BABY = {
    "skin": "#f6c8a8", "skin_hi": "#ffe6d4", "skin_sh": "#d8967c", "skin_dk": "#b07060",
    "blush": "#f08a8a", "hair": "#e8a83c", "hair_sh": "#b0702a",
    "diaper": "#f4f4fa", "diaper_sh": "#c4c8dc", "pin": "#5fb0ff",
    "bib": "#8adcb8", "bib_sh": "#58a88a", "bib_trim": "#ffffff",
    "paci": "#5fb0ff", "paci_hi": "#c0e4ff", "ring": "#ffe45a",
    "mouth": "#a83a4a", "tongue": "#ff8a9a", "tear": "#7fd4ff",
    "rattle": "#ff7ab8", "rattle_hi": "#ffc0dc", "rattle_sh": "#c84a8a",
    "handle": "#ffe45a", "handle_sh": "#d4a828",
}


PUPPET = {
    "wood": "#dc9c58", "wood_hi": "#f4c882", "wood_sh": "#a8662e", "wood_dk": "#6a3a1a",
    "hair": "#3a2418", "hair_hi": "#6e4630",
    "eye_w": "#f8f4ec", "cheek": "#f0707a", "cheek_hi": "#ffb0b0",
    "mouth": "#4a1418", "teeth": "#f8f4ec",
    "coat": "#d23a3c", "coat_hi": "#f2685c", "coat_sh": "#962432",
    "trim": "#f4ead2", "trim_sh": "#c8bca0", "button": "#f2c440",
    "pants": "#3a5aa8", "pants_sh": "#263c78",
    "shoe": "#2a2030", "shoe_hi": "#5a4a62",
    "bar": "#a86a3a", "bar_hi": "#d49a5c", "bar_sh": "#6e4024",
    "string": "#e8e2d2",
    "eyelet": "#c9a43b",          # string attachment points; the control bar looks for this exact color
}


STEPHEN_HAWKING = {
    "skin": "#f0c6a0", "skin_sh": "#c8927a",
    "hair": "#6a4630", "hair_hi": "#946a48",
    "frame": "#26222e", "lens": "#a8c4d8", "glint": "#ffffff",
    "mouth": "#8a4a46", "teeth": "#ffffff",
    "tweed": "#8a7652", "tweed_hi": "#ac9a70", "tweed_sh": "#605036", "fleck": "#c0ae84",
    "shirt": "#d4e4f4", "shirt_sh": "#9cb2cc", "tie": "#8a2e3a",
    "pants": "#4a4c5e", "pants_sh": "#363846", "shoe": "#2a2228", "shoe_hi": "#54485a",
    "chair": "#30344a", "chair_hi": "#4e5470", "chair_sh": "#20222e",
    "metal": "#9ca2b4", "metal_hi": "#dce0ea",
    "tire": "#1e1c26", "rim": "#8c92a4", "spoke_bg": "#3e4254", "reflector": "#ff7a3a",
    "led": "#5fff8f",
    "screen": "#164848", "screen_hi": "#5ff3c8", "screen_txt": "#c8fff0",
    "disk": "#ff8a2a", "disk_hi": "#ffd85a", "disk_w": "#fff8e0", "lensing": "#c08aff",
    "debris": "#a8aec0",
    "bubble": "#ffffff",
}


# Lab-light tints used by the "irradiated" style mutations.
TINTS = {
    "radioactive": "#39ff14",
    "cryo": "#5fd7ff",
    "ultraviolet": "#a24bff",
}

# Background colors for previews.
LAB_BG = "#1b1430"
LAB_FLOOR = "#2c2350"
LAB_GRID = "#3a2f66"
LAB_TEXT = "#c8ffb0"
LAB_DIM = "#8a7ac8"


# --- Level: the "Court House" -------------------------------------------------

SPAGHETTI_JUDGE = {
    "noodle": "#f2c96a", "noodle_hi": "#fff0b0", "noodle_sh": "#c8963c", "noodle_dk": "#9a6a2a",
    "meat": "#8a4426", "meat_hi": "#c06a3a", "meat_sh": "#5a2a18",
    "sauce": "#d8302a", "sauce_hi": "#ff6a4a", "sauce_dk": "#9a1a1e",
    "eye_w": "#f4f4f4", "eye_sh": "#c8c8d8",
    "wig": "#eceaf4", "wig_sh": "#b8b4cc", "wig_dk": "#8a86a8", "ribbon": "#2a2238",
    "band": "#ffffff",
    "wood": "#8a5a2e", "wood_hi": "#c08a4a", "wood_sh": "#5a3a1c", "brass": "#e8c040",
    "plate": "#f4f4f4", "plate_sh": "#b8c0d0", "plate_rim": "#5f9fd8",
    "basil": "#3aa04a", "steam": "#dce4f0", "text": "#ffe94a",
}

COURT = {
    # far wall: dusky marble, columns, tall windows, dark wood wainscot
    "wall": "#3b3354", "wall_hi": "#4a4168", "wall_sh": "#2c2640",
    "col": "#6c6290", "col_hi": "#9a90b8", "col_sh": "#4a4268",
    "sky": "#e8805a", "sky_mid": "#b45a7a", "sky_top": "#5a3a8a", "frame": "#22182e",
    "wain": "#4a2c22", "wain_hi": "#6a4030", "wain_sh": "#341e18",
    # the floor is, naturally, a basketball court
    "wood": "#d89a5a", "wood_hi": "#ecb878", "wood_sh": "#b07840", "wood_dk": "#7a4e2a",
    "paint": "#f4f4f4", "key": "#c8402a",
    # marble blocks
    "marble": "#d8d4e4", "marble_hi": "#f4f2fa", "marble_sh": "#a8a2c0", "vein": "#8a84a8",
    # props
    "hay": "#e8c050", "hay_hi": "#fff09a", "hay_sh": "#b08a2a", "twine": "#8a3a1a",
    "badge": "#f4d040", "badge_sh": "#b08a20", "hat": "#6a4228", "hat_hi": "#8e5c38",
    "ruler": "#f4dc5a", "ruler_sh": "#c8a830", "tick": "#3a2a1e",
    "pad": "#fff27a", "pad_sh": "#e0c840", "pad_line": "#7aaee8", "pad_top": "#e8402a",
    "case": "#6a3a24", "case_hi": "#8e5636", "case_sh": "#4a2618", "strap": "#d8c070",
    "case2": "#2a5a6a", "case2_hi": "#3e7a8a", "case2_sh": "#1c3e4a",
    "peel": "#ffd93a", "peel_sh": "#e3aa1f", "peel_in": "#fff2c0",
    "water": "#2a6ac8", "water_hi": "#6ab0ff", "water_sh": "#1a4488", "foam": "#d8f0ff",
    "dock": "#8a6a48", "dock_hi": "#b08a60", "dock_sh": "#5a4430",
    "brass": "#e8c040", "brass_sh": "#a8842a",
    "red": "#e83b3b", "red_sh": "#a82434", "green": "#3aa04a", "green_sh": "#26703a",
    "white": "#f4f4f4", "grey": "#9aa0b0", "grey_sh": "#5a6070", "black": "#1e1828",
    "neon": "#ff5fd7", "neon2": "#5ff3ff", "sign": "#2a2038", "sign_text": "#ffe94a",
    "duck": "#ffd93a", "beak": "#ff8a2a", "glass": "#bfefff",
    "fish": "#7ab8c8", "fish_hi": "#c8f0f8", "fish_sh": "#4a8098",
}
