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
