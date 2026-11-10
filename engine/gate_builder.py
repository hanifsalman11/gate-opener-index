import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/gate-opener-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3").strip()
CUSTOM_GATE = os.environ.get("CUSTOM_GATE", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_gates.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Opener Model / Gate Scenario, Leaf Length Ft, Physical Gate Weight Lbs, Wind Surface FillRatio, Daily Cycles, Rated Opener Lbs, Gate Style)
SEED_GATES = [
    ("Ghost Controls TDS2XP Heavy-Duty Dual Solar Gate Opener", 16, 450, 0.25, 20, 1000, "Dual Swing Tube/Wrought Iron"),
    ("Ghost Controls TSS1XP Single Automatic Solar Gate Opener", 16, 400, 0.20, 20, 1000, "Single Swing Farm/Driveway"),
    ("Ghost Controls DTP1 & HDP1 Architectural Estate Gate Opener", 14, 650, 0.35, 25, 1000, "Ornamental Steel Swing"),
    ("Mighty Mule MM371W (16 Ft / 550 Lb) Single Swing Gate Opener", 16, 320, 0.20, 15, 550, "Single Swing Tube/Chain-Link"),
    ("Mighty Mule MM372W Dual Swing Smart Driveway Gate Opener", 16, 350, 0.25, 18, 550, "Dual Swing Driveway"),
    ("Mighty Mule MM571W & MM572W (18 Ft / 850 Lb) Heavy-Duty", 18, 550, 0.30, 25, 850, "Heavy-Duty Wrought Iron"),
    ("TOPENS A8131 & A8231 Heavy-Duty Swing Gate Opener", 16, 500, 0.30, 25, 880, "Single / Dual Swing Gate"),
    ("TOPENS AT12131 & AT12132S (18 Ft / 880 Lb) 24V Gate Opener", 18, 580, 0.30, 30, 880, "24V Commercial/Estate Swing"),
    ("TOPENS RK990T & DK1000S Rack-Driven Sliding Gate Opener", 20, 1100, 0.50, 35, 1800, "Chain/Rack Sliding Gate"),
    ("TOPENS CK1200 & RK1200T (40 Ft / 2,600 Lb) Sliding Opener", 24, 1500, 0.45, 40, 2600, "Heavy Commercial Sliding"),
    ("LiftMaster LA400PKGUL (16 Ft / 850 Lb) 24VDC Swing Opener", 16, 550, 0.35, 40, 850, "UL-325 Estate Swing"),
    ("LiftMaster LA500PKGUL (18 Ft / 1,600 Lb) Commercial Swing", 18, 950, 0.45, 60, 1600, "Heavy Estate / HOA Swing"),
    ("LiftMaster CSL24UL (50 Ft / 1,500 Lb) 24VDC Slide Gate Operator", 22, 1150, 0.50, 60, 1500, "Commercial Pad-Mount Slide"),
    ("USAutomatic Ranger 500D & Patriot (16 Ft) Solar Gate Opener", 16, 480, 0.25, 30, 800, "High-Efficiency Solar Swing"),
    ("Apollo / Nice 1550ETL & 1650ETL Solar Ranch Gate Opener", 16, 520, 0.25, 30, 1000, "Ranch & Cattle Gate Swing"),
    ("Viking Access G-5 & K-2 Commercial Swing Gate Operator", 16, 750, 0.35, 50, 1300, "Continuous-Duty 24V Swing"),
    ("CO-Z 1,400 Lb & 1,800 Lb Automatic Sliding Gate Opener", 20, 950, 0.40, 25, 1400, "Chain/Gear Rack Sliding"),
    ("Aleko GG1300 & GG1700 Dual Swing Driveway Gate Opener", 16, 600, 0.30, 25, 1300, "Dual Wrought Iron Swing"),
    ("12-Foot Single Solid Wood Privacy Driveway Gate Opener Sizing", 12, 420, 0.95, 20, 1000, "High Wind-Load Privacy"),
    ("14-Foot Ornamental Wrought Iron Swing Gate Opener Sizing", 14, 520, 0.35, 25, 900, "Ornamental Picket Swing"),
    ("16-Foot 6-Bar Galvanized Farm Cattle Tube Gate Opener Sizing", 16, 185, 0.15, 20, 550, "Ranch Pasture Tube Gate"),
    ("18-Foot Heavy Steel Ranch Entrance Swing Gate Opener Sizing", 18, 620, 0.30, 25, 1100, "Long Cantilever Lever Arm"),
    ("20-Foot Dual-Leaf (2x 10 Ft) Estate Driveway Gate Sizing", 10, 380, 0.35, 25, 750, "Dual 10-Ft Leaf Swing"),
    ("24-Foot Dual-Leaf (2x 12 Ft) Solid Privacy Gate Opener Sizing", 12, 480, 0.90, 25, 1100, "Dual Solid Privacy + Lock"),
    ("20-Foot Cantilever & V-Groove Rolling Slide Gate Sizing", 20, 950, 0.40, 35, 1600, "V-Groove Track Slide Gate"),
    ("30-Foot Commercial Chain-Link Sliding Security Gate Sizing", 30, 1350, 0.25, 50, 2200, "Cantilever Roller Slide"),
    ("Solar Gate Opener Panel Wattage (20W vs 30W vs 60W) & Battery", 16, 400, 0.25, 25, 850, "14-Day Off-Grid Solar"),
    ("Automatic Electromagnetic Gate Lock & Wind-Bracing Sizing", 16, 480, 0.75, 20, 1000, "2,000-Lb Holding Force Lock"),
    ("Low-Voltage 16/2 vs 12/2 Direct-Burial Transformer Wire Run", 16, 450, 0.30, 25, 850, "Up to 1,000 Ft Wire Run"),
    ("Gate Post Hinge Shear Load & Ball-Bearing Barrel Hinge Sizing", 16, 650, 0.35, 25, 1000, "4x4 / 6x6 Steel Post & Hinge")
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=450.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_gate_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Gate Length × Weight × Fill Permutator.
    """
    discovered = []
    seeds = [
        "what size gate opener for ",
        "ghost controls gate opener ",
        "mighty mule gate opener ",
        "solar gate opener calculator "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        ft_m = re.search(r"\b(10|12|14|16|18|20)\s*ft\b", cleaned)
                        l_ft = int(ft_m.group(1)) if ft_m else 16
                        discovered.append((cleaned.title(), l_ft, 450, 0.30, 20, 850, "Automatic Swing Gate"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    gate_lengths = [10, 12, 14, 16, 18, 20]
    gate_profiles = [
        ("Farm Tube Cattle Gate (200 Lb)", 200, 0.15),
        ("Ornamental Wrought Iron Gate (500 Lb)", 500, 0.35),
        ("Wood & Steel Frame Gate (650 Lb)", 650, 0.65),
        ("Solid Wood / Metal Privacy Gate (550 Lb)", 550, 0.95)
    ]
    power_modes = ["Off-Grid Solar Kit", "120V AC Low-Voltage Wire Setup"]
    for g_len in gate_lengths:
        for prof_desc, g_wt, fill_r in gate_profiles:
            for p_mode in power_modes:
                combo_title = f"{g_len}-Ft {prof_desc} ({p_mode})"
                test_slug = slugify(f"{combo_title}-actuator-solar-calculator")
                if test_slug not in published_slugs:
                    eff_cap = int(round((g_wt * (1.0 + fill_r * 0.95) * (g_len / 12.0)), -1))
                    rec_op = max(550, min(2200, eff_cap))
                    discovered.append((combo_title, g_len, g_wt, fill_r, 25, rec_op, prof_desc))
                    if len(discovered) >= 25:
                        return discovered
    return discovered


def build_deterministic_gate_data(gate_tuple):
    """
    LAPIS 3: Mesin Fisika Mekanika Gerbang Cantilever, Beban Angin & Otonomi Solar 12V (100% Bebas Gagal).
    """
    model_name, leaf_len_ft, gate_wt_lbs, fill_ratio, daily_cycles, rated_opener_lbs, gate_style = gate_tuple

    # 1. Perhitungan Luas Permukaan Angin & Gaya Dorong Angin 30 MPH (F_wind = 0.00256 * V^2 * Area_Solid * Cd):
    gate_height_ft = 5.5
    solid_area_sqft = round(leaf_len_ft * gate_height_ft * fill_ratio, 1)
    wind_force_30mph_lbs = int(round(0.00256 * (30.0 ** 2) * solid_area_sqft * 1.28))

    # 2. Beban Efektif Aktuator (Effective Actuator Weight Rating Needed):
    # Menggabungkan berat fisik + penalti tuas panjang (>12 ft) + penalti beban angin (solid privacy gate membutuhkan 1.75x - 2.0x kapasitas!)
    leverage_mult = max(1.0, round(leaf_len_ft / 12.5, 2))
    wind_mult = round(1.0 + (fill_ratio * 0.85), 2)
    effective_actuator_lbs = max(rated_opener_lbs, int(round(gate_wt_lbs * leverage_mult * wind_mult, -1)))

    # 3. Gaya Tarik/Tekan Horizontal pada Engsel (Hinge Shear & Thrust Load):
    # F_hinge = (Gate_Weight * (Leaf_Length / 2)) / Vertical_Hinge_Spread (asumsi jarak antar engsel = 4.0 kaki)
    hinge_thrust_lbs = int(round((gate_wt_lbs * (leaf_len_ft / 2.0)) / 4.0))

    # 4. Anggaran Energi Surya Harian (Solar Wh & Battery Ah untuk 14 Hari Mendung Tanpa Matahari):
    # Quiescent standby controller + receiver + keypad = 0.040A x 24h = 0.96 Ah/day
    # Active cycle draw = daily_cycles * (22 sec open + 22 sec close = 44s) * 6.5 Amps / 3600 = Ah/day
    active_ah_day = round((daily_cycles * 44.0 * 6.5) / 3600.0, 2)
    total_ah_day = round(0.96 + active_ah_day, 2)
    total_wh_day = round(total_ah_day * 12.8, 1)
    # Panel Surya Minimum (asumsi 3.5 Peak Sun Hours di musim dingin + 35% safety buffer)
    min_solar_watts = 20 if total_wh_day <= 22 else (30 if total_wh_day <= 36 else 50)
    min_battery_ah = max(18, int(round((total_ah_day * 14.0) / 0.75, -1)))

    return {
        "gate_name": model_name,
        "gate_style": gate_style,
        "seo_title": f"{model_name} Actuator Capacity, Wind-Load & Solar Calculator (2026)",
        "meta_description": f"Calculate exact gate opener capacity ({effective_actuator_lbs:,} lb actuator rating for {leaf_len_ft} ft / {gate_wt_lbs} lb gate), 30-MPH wind drag (+{wind_force_30mph_lbs} lbs), {hinge_thrust_lbs}-lb hinge thrust, and {min_solar_watts}W solar/{min_battery_ah}Ah battery sizing for {model_name}.",
        "specs": {
            "leaf_length_ft": leaf_len_ft,
            "physical_weight_lbs": gate_wt_lbs,
            "wind_surface_fill_pct": int(fill_ratio * 100),
            "solid_wind_area_sqft": solid_area_sqft,
            "wind_drag_30mph_lbs": wind_force_30mph_lbs,
            "effective_actuator_lbs": effective_actuator_lbs,
            "hinge_thrust_load_lbs": hinge_thrust_lbs,
            "daily_open_close_cycles": daily_cycles,
            "daily_consumption_ah": total_ah_day,
            "recommended_solar_watts": min_solar_watts,
            "recommended_battery_ah": min_battery_ah,
            "gate_style": gate_style
        },
        "mechanical_verdict": f"For {model_name} ({leaf_len_ft}-ft leaf weighing {gate_wt_lbs} lbs with {int(fill_ratio*100)}% surface fill = {solid_area_sqft} sq. ft. wind sail area), a 30-MPH crosswind exerts +{wind_force_30mph_lbs} lbs of aerodynamic drag against the actuator arm while cantilever leverage generates {hinge_thrust_lbs:,} lbs of horizontal shear on the top and bottom hinges. To prevent stripped worm gears and mid-swing stall outs, select a gate operator rated for at least {effective_actuator_lbs:,} lbs paired with a 2,000-lb Automatic Electromagnetic Gate Lock. Running {daily_cycles} cycles/day consumes {total_ah_day} Ah/day ({total_wh_day} Wh/day), requiring a {min_solar_watts}W solar panel and a 12V {min_battery_ah}Ah deep-cycle battery for 14 days of cloudy autonomy.",
        "hardware_bundle": [
            {
                "badge": f"{effective_actuator_lbs:,} lb Gate Opener Kit",
                "title": f"{model_name} ({leaf_len_ft}+ Ft / {effective_actuator_lbs:,} Lb Rated Automatic Gate Operator Kit)",
                "price_range": "$329 - $1,299",
                "amazon_query": f"{model_name} Automatic Gate Opener Kit",
                "gate_note": f"High-torque 12V/24V worm-gear motor overcomes {hinge_thrust_lbs:,} lbs of cantilever torque and +{wind_force_30mph_lbs} lbs of wind drag."
            },
            {
                "badge": "2,000-Lb Magnetic Gate Lock",
                "title": "Automatic Weatherproof Electromagnetic Gate Lock (Bulldog Lock — Wired to Opener Control Board)",
                "price_range": "$119 - $199",
                "amazon_query": "Automatic Gate Lock Ghost Controls Mighty Mule TOPENS Bulldog",
                "gate_note": f"Mandatory on {leaf_len_ft}-ft gates: locks the leading edge to the strike post so wind gusts never bend the actuator tube."
            },
            {
                "badge": f"{min_solar_watts}W Solar & {min_battery_ah}Ah Battery",
                "title": f"{min_solar_watts}W Monocrystalline Solar Charging Kit + 12V {min_battery_ah}Ah Deep-Cycle AGM/LiFePO4 Gate Battery",
                "price_range": "$115 - $269",
                "amazon_query": f"{min_solar_watts}W Solar Panel Gate Opener Kit 12V {min_battery_ah}Ah Deep Cycle Battery",
                "gate_note": f"Replenishes {total_ah_day} Ah/day in 2 hours of sunlight and stores 14 days of dark-weather reserve power."
            },
            {
                "badge": "Exit Wand, Keypad & Hinges",
                "title": "Direct-Burial Electromagnetic Vehicle Exit Sensor Wand + Wireless Keypad & 2,000-Lb Ball-Bearing Hinges",
                "price_range": "$109 - $249",
                "amazon_query": "Gate Opener Electromagnetic Exit Wand Sensor Wireless Keypad Ball Bearing Hinges",
                "gate_note": "Hands-free magnetic ground probe opens the gate automatically when cars approach from inside the driveway."
            }
        ],
        "installer_checklist": [
            f"Replace friction pipe hinges with Greaseable Ball-Bearing Barrel Hinges rated for {max(1000, hinge_thrust_lbs * 2):,}+ lbs: a {leaf_len_ft}-ft, {gate_wt_lbs}-lb gate places {hinge_thrust_lbs:,} lbs of horizontal pull on the top hinge, and binding hinges are the #1 cause of burned-out gate opener control boards.",
            f"Account for Wind-Sail Area on Solid/Privacy Gates: a {leaf_len_ft}-ft solid wood or sheet-metal gate ({solid_area_sqft} sq. ft.) catches +{wind_force_30mph_lbs} lbs of wind load at 30 MPH—requiring a 2x upsized actuator ({effective_actuator_lbs:,} lbs) and an Automatic Magnetic Gate Lock.",
            "Respect UL 325 Safety Standards: install the Thru-Beam Photo-Eye Entrapment Sensor 15–20 inches above the driveway, and mount the wireless entry keypad at least 6 to 10 feet away from the moving gate so nobody can reach through the bars while operating it.",
            "If trickling power from a 120V AC house outlet via a low-voltage transformer instead of solar, run 16/2 Stranded Direct-Burial Low-Voltage Wire up to 500 feet (or 12/2 wire up to 1,000 feet) to keep charging voltage above 16V at the control box."
        ],
        "faqs": [
            {
                "q": f"What size gate opener do I need for {model_name} ({leaf_len_ft} ft, {gate_wt_lbs} lbs)?",
                "a": f"While the gate weighs {gate_wt_lbs} lbs physically, factoring in a {leaf_len_ft}-foot lever arm ({leverage_mult}x leverage) and {int(fill_ratio*100)}% wind-sail surface area (+{wind_force_30mph_lbs} lbs at 30 MPH) requires an automatic gate opener rated for at least {effective_actuator_lbs:,} lbs and {leaf_len_ft}+ feet."
            },
            {
                "q": f"What size solar panel and battery do I need for {daily_cycles} gate cycles per day?",
                "a": f"The control board's 24/7 radio receiver draws ~0.96 Ah/day in standby, plus {active_ah_day} Ah/day for {daily_cycles} open/close cycles = {total_ah_day} Ah/day ({total_wh_day} Wh/day). Install a {min_solar_watts}W solar panel facing south and a 12V {min_battery_ah}Ah deep-cycle battery."
            },
            {
                "q": f"Do I need an automatic magnetic gate lock on a {leaf_len_ft}-foot swing gate?",
                "a": f"Yes! Any swing gate 12 feet or longer acts as a giant lever arm against the opener's front mount. Installing a 2,000-lb automatic electromagnetic lock at the latching end prevents wind buffeting and stops intruders from forcing the actuator gears."
            }
        ]
    }


def generate_gate_data(gate_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_gate_data(gate_tuple)

    model_name, leaf_len_ft, gate_wt_lbs, fill_ratio, daily_cycles, rated_opener_lbs, gate_style = gate_tuple
    det_fallback = build_deterministic_gate_data(gate_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified Automated Gate System Designer (AFAA / IDEA Certified) & Mechanical Actuator Engineer (UL 325 Specialist). Create an accurate 2026 driveway gate opener actuator capacity, 30-MPH wind-load drag, hinge shear thrust, and off-grid solar/battery sizing guide for: "{model_name}".
Baseline specs: Leaf Length={leaf_len_ft} ft, Physical Weight={gate_wt_lbs} lbs, Wind Fill={sp['wind_surface_fill_pct']}% ({sp['solid_wind_area_sqft']} sq ft sail area, +{sp['wind_drag_30mph_lbs']} lbs @ 30 MPH), Effective Actuator Rating={sp['effective_actuator_lbs']} lbs, Hinge Thrust={sp['hinge_thrust_load_lbs']} lbs, Daily Cycles={daily_cycles}/day ({sp['daily_consumption_ah']} Ah/day -> {sp['recommended_solar_watts']}W Solar + 12V {sp['recommended_battery_ah']}Ah Battery).
Return ONLY a valid JSON object matching this exact schema:
{{
  "gate_name": "{model_name}",
  "gate_style": "{gate_style}",
  "seo_title": "{model_name} Actuator Capacity, Wind-Load & Solar Calculator (2026)",
  "meta_description": "Calculate exact automatic gate opener actuator capacity, wind-load penalty, hinge thrust load, and solar panel/battery sizing for {model_name}.",
  "specs": {{
    "leaf_length_ft": {leaf_len_ft},
    "physical_weight_lbs": {gate_wt_lbs},
    "wind_surface_fill_pct": {sp['wind_surface_fill_pct']},
    "solid_wind_area_sqft": {sp['solid_wind_area_sqft']},
    "wind_drag_30mph_lbs": {sp['wind_drag_30mph_lbs']},
    "effective_actuator_lbs": {sp['effective_actuator_lbs']},
    "hinge_thrust_load_lbs": {sp['hinge_thrust_load_lbs']},
    "daily_open_close_cycles": {daily_cycles},
    "daily_consumption_ah": {sp['daily_consumption_ah']},
    "recommended_solar_watts": {sp['recommended_solar_watts']},
    "recommended_battery_ah": {sp['recommended_battery_ah']},
    "gate_style": "{gate_style}"
  }},
  "mechanical_verdict": "3-sentence technical summary stating gate length/weight, 30-MPH wind drag penalty, hinge thrust lbs, required actuator rating, and solar/battery sizing for {daily_cycles} daily cycles.",
  "hardware_bundle": [
    {{
      "badge": "{sp['effective_actuator_lbs']:,} lb Gate Opener",
      "title": "{model_name} ({leaf_len_ft}+ Ft / {sp['effective_actuator_lbs']:,} Lb Automatic Gate Operator Kit)",
      "price_range": "$329 - $1,299",
      "amazon_query": "{model_name} Automatic Gate Opener Kit",
      "gate_note": "1-sentence worm-gear torque and wind resistance note"
    }},
    {{
      "badge": "2,000-Lb Magnetic Gate Lock",
      "title": "Automatic Weatherproof Electromagnetic Gate Lock (Bulldog Security Lock)",
      "price_range": "$119 - $199",
      "amazon_query": "Automatic Gate Lock Ghost Controls Mighty Mule TOPENS",
      "gate_note": "1-sentence wind-bracing and anti-pry security note"
    }},
    {{
      "badge": "{sp['recommended_solar_watts']}W Solar & {sp['recommended_battery_ah']}Ah Battery",
      "title": "{sp['recommended_solar_watts']}W Monocrystalline Solar Panel Kit + 12V {sp['recommended_battery_ah']}Ah Deep-Cycle Gate Battery",
      "price_range": "$115 - $269",
      "amazon_query": "{sp['recommended_solar_watts']}W Solar Panel Gate Opener Kit 12V {sp['recommended_battery_ah']}Ah Battery",
      "gate_note": "1-sentence daily Ah recharge and 14-day autonomy note"
    }},
    {{
      "badge": "Exit Wand, Keypad & Hinges",
      "title": "Direct-Burial Electromagnetic Vehicle Exit Wand + Wireless Keypad & Ball-Bearing Hinges",
      "price_range": "$109 - $249",
      "amazon_query": "Gate Opener Electromagnetic Exit Wand Wireless Keypad Ball Bearing Hinges",
      "gate_note": "1-sentence hands-free exit and low-friction hinge note"
    }}
  ],
  "installer_checklist": [
    "Step 1 regarding ball-bearing barrel hinges for {sp['hinge_thrust_load_lbs']} lbs of horizontal thrust",
    "Step 2 regarding wind-sail derating on solid privacy gates and mandatory magnetic lock",
    "Step 3 regarding UL 325 photo-eye entrapment beams and 6-foot keypad setback",
    "Step 4 regarding 16/2 vs 12/2 direct-burial wire length for AC transformer charging"
  ],
  "faqs": [
    {{"q": "What size gate opener do I need for {model_name}?", "a": "Exact physical weight, wind drag, leverage factor, and effective actuator lbs."}},
    {{"q": "What size solar panel and battery do I need for {daily_cycles} gate cycles a day?", "a": "Exact standby + active Ah/day consumption, solar watts, and 12V battery Ah."}},
    {{"q": "How far can I run low-voltage wire to a gate opener transformer?", "a": "Exact distance limits for 16 AWG (500 ft) vs 12 AWG (1,000 ft) direct-burial wire."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_gate_html_page(data, slug, mon_cfg):
    gate_name = data.get("gate_name", "Automatic Driveway Gate Opener")
    sp = data.get("specs", {})
    leaf_ft = int(safe_float(sp.get("leaf_length_ft", 16), 16))
    wt_lbs = int(safe_float(sp.get("physical_weight_lbs", 450), 450))
    fill_pct = int(safe_float(sp.get("wind_surface_fill_pct", 30), 30))
    wind_lbs = int(safe_float(sp.get("wind_drag_30mph_lbs", 76), 76))
    eff_lbs = int(safe_float(sp.get("effective_actuator_lbs", 850), 850))
    hinge_lbs = int(safe_float(sp.get("hinge_thrust_load_lbs", 900), 900))
    cycles = int(safe_float(sp.get("daily_open_close_cycles", 20), 20))
    sol_w = int(safe_float(sp.get("recommended_solar_watts", 30), 30))
    batt_ah = int(safe_float(sp.get("recommended_battery_ah", 35), 35))

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Automatic+Gate+Opener+Kit+Solar+Ghost+Controls+Mighty+Mule"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{gate_name} Actuator, Wind-Load & Solar Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Automatic Gate Opener Kit")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-amber-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Gate Hardware')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$109+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🚧 {item.get('gate_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Gate Length & Style vs Required Actuator Capacity, Hinge Load & Solar Matrix Table
    gate_tiers = [
        ("12 Ft Farm Tube Gate (150 lb)", "500 lb Opener", "450 lbs Thrust", "Optional Lock", "10W–20W + 12V 18Ah"),
        ("16 Ft Ranch Tube Gate (220 lb)", "600 – 850 lb Opener", "880 lbs Thrust", "Recommended Lock", "20W–30W + 12V 35Ah"),
        ("16 Ft Wrought Iron (550 lb)", "850 – 1,000 lb Opener", "2,200 lbs Thrust", "Mandatory Mag-Lock", "30W + 12V 35Ah–50Ah"),
        ("16 Ft Solid Wood Privacy (500 lb)", "1,200+ lb Opener (or Slide)", "2,000 lbs + Wind", "Mandatory Mag-Lock", "50W + 12V 50Ah AGM"),
        ("20 Ft Heavy Sliding Gate (1,200 lb)", "1,800 – 2,600 lb Slide", "V-Groove Rollers", "Gear-Rack Lock", "60W + Dual 12V/24V Bank")
    ]
    matrix_rows_html = ""
    for g_lbl, o_lbl, h_lbl, l_lbl, s_lbl in gate_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{g_lbl}</td>
          <td class="py-3 px-4 font-bold text-amber-400">{o_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{h_lbl}</td>
          <td class="py-3 px-4 text-zinc-300">{l_lbl}</td>
          <td class="py-3 px-4 text-xs text-zinc-300">{s_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("installer_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-amber-500 rounded cursor-pointer gate-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>UL 325 Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', gate_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', gate_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">GATE</span>OpenerIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Automatic Gate Openers →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-amber-500 text-zinc-950 px-3 py-1 rounded-full">{eff_lbs:,} lb Opener Rating ({leaf_ft}' Gate)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Hinge Load: {hinge_lbs:,} lbs | Wind: +{wind_lbs} lbs</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">Solar: {sol_w}W + 12V {batt_ah}Ah Battery</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', gate_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-amber-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>Cantilever Torque, Wind-Load & Solar Verdict:</strong> {data.get('mechanical_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE GATE OPENER ACTUATOR CAPACITY, WIND DRAG & SOLAR CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {gate_name} Actuator, Wind-Load & Solar Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Adjust your single gate leaf length, physical gate weight, wind-fill surface profile, and daily traffic cycles to compute required actuator capacity, hinge shear load, and off-grid solar/battery sizing.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="lenSlider" class="text-zinc-300">Gate Leaf Length (Ft)</label>
                <span class="text-amber-400 font-bold"><span id="lenVal">{leaf_ft}</span> ft</span>
              </div>
              <input id="lenSlider" type="range" min="8" max="24" step="1" value="{leaf_ft}" class="w-full accent-amber-500 cursor-pointer">
            </div>
            <div>
              <div class="flex justify-between text-xs font-medium mb-1">
                <label for="wtSlider" class="text-zinc-300">Physical Weight (Lbs)</label>
                <span class="text-amber-400 font-bold"><span id="wtVal">{wt_lbs}</span> lbs</span>
              </div>
              <input id="wtSlider" type="range" min="100" max="1800" step="25" value="{wt_lbs}" class="w-full accent-amber-500 cursor-pointer">
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="fillSelect" class="block text-xs font-medium text-zinc-400 mb-1">Gate Wind-Sail Surface Profile</label>
              <select id="fillSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="0.15" {"selected" if fill_pct <= 20 else ""}>Open Farm Tube / Chain-Link (15% Fill)</option>
                <option value="0.35" {"selected" if 20 < fill_pct <= 45 else ""}>Wrought Iron / Ornamental (35% Fill)</option>
                <option value="0.65" {"selected" if 45 < fill_pct <= 75 else ""}>Semi-Privacy Wood/Steel (65% Fill)</option>
                <option value="0.95" {"selected" if fill_pct > 75 else ""}>Solid Privacy Wood/Sheet (95% Fill!)</option>
              </select>
            </div>
            <div>
              <label for="cycleSelect" class="block text-xs font-medium text-zinc-400 mb-1">Daily Open/Close Traffic</label>
              <select id="cycleSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="10">10 Cycles/Day (Single Residence)</option>
                <option value="25" selected>25 Cycles/Day (Busy Family / Ranch)</option>
                <option value="60">60 Cycles/Day (Multi-Family / Commercial)</option>
              </select>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">Required Opener Rating</span>
            <div class="text-xl sm:text-2xl font-black text-white mt-1"><span id="effLbsOut">{eff_lbs:,}</span> <span class="text-xs font-normal text-zinc-400">lb Rated</span></div>
            <p id="hingeNoteOut" class="text-xs text-amber-400 font-semibold mt-1">Hinge Thrust: {hinge_lbs:,} lbs</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Off-Grid Solar & Lock</span>
            <div id="solarOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">{sol_w}W + {batt_ah}Ah</div>
            <p id="lockNoteOut" class="text-xs text-zinc-300 font-semibold mt-1">🔒 Mag-Lock Required</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="gateAdviceBanner" class="text-sm text-amber-100 font-medium"></div>
        <a id="dynamicGateBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Gate Opener & Lock on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {gate_name} Opener, Mag-Lock & Solar Bundle</h2>
        <span class="text-xs text-zinc-400">UL 325 Compliant & All-Weather Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Driveway Gate Size, Opener Capacity, Hinge Shear Load & Solar Sizing Chart</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">Gate Length & Style</th>
              <th class="py-3.5 px-4 text-amber-400">Min Opener Capacity</th>
              <th class="py-3.5 px-4 text-emerald-400">Top Hinge Shear Load</th>
              <th class="py-3.5 px-4">Magnetic Gate Lock</th>
              <th class="py-3.5 px-4">14-Day Off-Grid Solar</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">UL 325 Gate Safety, Ball-Bearing Hinge & Wind-Bracing Checklist</h2>
        <span id="gateBadge" class="text-xs font-bold bg-zinc-800 text-amber-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({gate_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} GateOpenerIndex. Independent Automated Gate Torque, Wind-Load & Solar Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const lenSlider = document.getElementById('lenSlider');
    const wtSlider = document.getElementById('wtSlider');
    const fillSelect = document.getElementById('fillSelect');
    const cycleSelect = document.getElementById('cycleSelect');
    const lenVal = document.getElementById('lenVal');
    const wtVal = document.getElementById('wtVal');
    const effLbsOut = document.getElementById('effLbsOut');
    const hingeNoteOut = document.getElementById('hingeNoteOut');
    const solarOut = document.getElementById('solarOut');
    const lockNoteOut = document.getElementById('lockNoteOut');
    const gateAdviceBanner = document.getElementById('gateAdviceBanner');
    const dynamicGateBtn = document.getElementById('dynamicGateBtn');

    function recalculateGate() {{
      const lenFt = parseInt(lenSlider.value, 10);
      const wtLbs = parseInt(wtSlider.value, 10);
      const fillRatio = parseFloat(fillSelect.value);
      const cycles = parseInt(cycleSelect.value, 10);

      lenVal.textContent = lenFt;
      wtVal.textContent = wtLbs.toLocaleString();

      const solidArea = lenFt * 5.5 * fillRatio;
      const windDrag30 = Math.round(0.00256 * 900.0 * solidArea * 1.28);
      const levMult = Math.max(1.0, lenFt / 12.5);
      const windMult = 1.0 + (fillRatio * 0.85);
      const effCap = Math.max(550, Math.ceil((wtLbs * levMult * windMult) / 50) * 50);

      const hingeThrust = Math.round((wtLbs * (lenFt / 2.0)) / 4.0);
      const ahPerDay = 0.96 + ((cycles * 44.0 * 6.5) / 3600.0);
      const whPerDay = ahPerDay * 12.8;
      const solWatts = whPerDay <= 22 ? 20 : (whPerDay <= 36 ? 30 : 50);
      const battAh = Math.max(18, Math.ceil(((ahPerDay * 14.0) / 0.75) / 5) * 5);

      effLbsOut.textContent = effCap.toLocaleString();
      hingeNoteOut.textContent = `Hinge Thrust: ${{hingeThrust.toLocaleString()}} lbs (+${{windDrag30}} lb Wind)`;
      solarOut.textContent = `${{solWatts}}W + ${{battAh}}Ah`;

      if (lenFt >= 12 || fillRatio >= 0.35) {{
        lockNoteOut.textContent = "🔒 Add 2,000-Lb Magnetic Lock";
        lockNoteOut.className = "text-xs text-amber-400 font-bold mt-1";
      }} else {{
        lockNoteOut.textContent = "✅ Standard Latch OK";
        lockNoteOut.className = "text-xs text-emerald-400 font-semibold mt-1";
      }}

      gateAdviceBanner.innerHTML = `🚧 <strong>Mechanical Spec:</strong> A ${{lenFt}}-ft, ${{wtLbs}}-lb gate (+${{windDrag30}} lbs wind drag) requires a <strong>${{effCap.toLocaleString()}}-lb Rated Automatic Gate Opener</strong>, <strong>2,000-lb Ball-Bearing Barrel Hinges</strong>, an <strong>Electromagnetic Gate Lock</strong>, and a <strong>${{solWatts}}W Solar + 12V ${{battAh}}Ah Battery Kit</strong>.`;
      dynamicGateBtn.href = `https://${{amzDomain}}/s?k=Automatic+Gate+Opener+Kit+${{effCap}}+lb+Solar+Ghost+Controls+Mighty+Mule+Gate+Lock&tag=${{amzTag}}`;
    }}

    lenSlider.addEventListener('input', recalculateGate);
    wtSlider.addEventListener('input', recalculateGate);
    fillSelect.addEventListener('change', recalculateGate);
    cycleSelect.addEventListener('change', recalculateGate);
    recalculateGate();

    const checks = document.querySelectorAll('.gate-check');
    const badge = document.getElementById('gateBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Automatic+Gate+Opener+Kit+Solar+Ghost+Controls+Mighty+Mule"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-amber-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-amber-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('eff_lbs', 850):,} lb Opener ({item.get('len_ft', 16)}' Gate)</span>
            <span class="text-xs text-zinc-400">Solar: {item.get('sol_w', 30)}W | {item.get('hinge_lbs', 900):,} lb Hinge</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-amber-400 transition">{item['gate_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-amber-400">Calculate Actuator, Wind-Load & Solar →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GateOpenerIndex — Automatic Driveway Gate Opener Capacity, Wind-Load & Solar Calculator (2026)</title>
  <meta name="description" content="Calculate exact automatic driveway swing and sliding gate opener actuator capacity, 30-MPH solid privacy gate wind-load penalty, ball-bearing hinge shear thrust, and 14-day solar/battery sizing for Ghost Controls, Mighty Mule, LiftMaster, and TOPENS.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="GateOpenerIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">GATE</span>OpenerIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Automatic Gate Openers →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Automatic Gate Opener Capacity, Wind-Load & Solar Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your driveway/ranch gate dimensions or opener model below to calculate wind-sail drag penalties, top hinge shear thrust, electromagnetic lock requirements, and off-grid solar/battery sizing.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search gate opener or gate size (e.g. Ghost Controls TDS2XP, Mighty Mule MM371W, LiftMaster LA400, TOPENS, 16 Ft Farm Gate...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500">
      </div>
    </div>

    <div id="gateGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} GateOpenerIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('gateGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>GateOpenerIndex Automatic Driveway Gate Opener & Solar Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Automatic Gate Opener Actuator Capacity, Wind-Load & Solar Sizing Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_GATE:
        candidates.append((CUSTOM_GATE.strip(), 16, 450, 0.30, 20, 850, "Automatic Swing Gate"))
    candidates.extend(SEED_GATES)
    candidates.extend(discover_google_gate_queries(published_slugs))

    new_urls = []
    count = 0

    for gate_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        g_name = gate_tuple[0]
        slug = slugify(f"{g_name}-actuator-solar-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating automatic gate opener & solar calculator for: {g_name}...")
        try:
            data = generate_gate_data(gate_tuple)
            build_gate_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "gate_name": data.get("gate_name", g_name),
                "slug": slug,
                "title": data.get("seo_title", f"{g_name} Gate Opener Calculator"),
                "description": data.get("meta_description", ""),
                "len_ft": int(safe_float(sp.get("leaf_length_ft", gate_tuple[1]), gate_tuple[1])),
                "eff_lbs": int(safe_float(sp.get("effective_actuator_lbs", gate_tuple[5]), gate_tuple[5])),
                "hinge_lbs": int(safe_float(sp.get("hinge_thrust_load_lbs", 900), 900)),
                "sol_w": int(safe_float(sp.get("recommended_solar_watts", 30), 30)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {g_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new automatic gate opener & solar calculator pages.")


if __name__ == "__main__":
    main()
