import streamlit as st
import google.generativeai as genai
import json

# --- Konfiguration & Custom Dark-Steel-Design (Technical / Roboto) ---
st.set_page_config(page_title="Kitchen & Meal Prep OS", page_icon="🍳", layout="centered")

st.markdown("""
    <style>
    /* Google Fonts: Roboto & Roboto Mono für den technischen Look laden */
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@500;700&family=Roboto:wght@400;500;700&display=swap');

    /* Globales Theme & Schriftart erzwingen */
    html, body, [class*="css"], .stApp, p, label, div, span {
        font-family: 'Roboto', sans-serif !important;
    }
    .stApp { background-color: #121417; color: #E0E0E0; }
    [data-testid="stSidebar"] { background-color: #1a1d23; border-right: 1px solid #2a2e39; }
    
    /* Überschriften: Technischer, klarer Look */
    h1, h2, h3 { 
        color: #FFFFFF !important; 
        font-family: 'Roboto', sans-serif !important; 
        font-weight: 700 !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    
    /* Eingabefelder & Zahlenfelder */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #1a1d23 !important; color: #FFFFFF !important; border: 1px solid #2a2e39 !important; border-radius: 4px !important;
        font-family: 'Roboto', sans-serif !important;
    }
    /* Zahlen-Inputs im Digitalwaagen-Look (Monospace) */
    .stNumberInput input {
        font-family: 'Roboto Mono', monospace !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
        border-color: #00E5FF !important; box-shadow: 0 0 0 1px #00E5FF !important;
    }
    
    /* Buttons im kantigeren Edelstahl- / Zyan-Look */
    .stButton>button {
        width: 100%; background: linear-gradient(135deg, #2a2e39 0%, #1f232a 100%); color: #00E5FF; border: 1px solid #00E5FF; border-radius: 4px; 
        font-family: 'Roboto', sans-serif !important; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; transition: all 0.2s ease;
    }
    .stButton>button:hover { background: #00E5FF; color: #121417; border-color: #00E5FF; }
    
    /* Metrik-Boxen (Ergebnisse in Roboto Mono) */
    [data-testid="stMetric"] {
        background-color: #1a1d23; border: 1px solid #2a2e39; padding: 15px; border-radius: 4px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    [data-testid="stMetricLabel"] { color: #90A4AE !important; text-transform: uppercase; font-size: 0.8rem !important; letter-spacing: 0.5px; }
    [data-testid="stMetricValue"] { color: #00E5FF !important; font-family: 'Roboto Mono', monospace !important; font-weight: 700 !important; }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background-color: #121417; }
    .stTabs [data-baseweb="tab"] { background-color: #1a1d23; border-radius: 4px; color: #90A4AE; border: 1px solid #2a2e39; padding: 8px 16px; text-transform: uppercase; font-weight: 500; font-size: 0.85rem; letter-spacing: 0.5px; }
    .stTabs [aria-selected="true"] { background-color: #2a2e39 !important; color: #00E5FF !important; border-color: #00E5FF !important; }
    </style>
""", unsafe_allow_html=True)

# --- Hardware-Datenbank (Töpfe & Teller) ---
TOEPFE = {
    "Großer 9L Edelstahlkochtopf": 2093,
    "Pastatopf": 787,
    "Tefal Bräter": 1836,
    "KitchenAid 3,5L Topf": 991,
    "Gusseiserner Bräter": 4590,
    "Ohne Topf / Direkt gewogen (Tara = 0 g)": 0
}

TELLER = {
    "Tiefe Teller (schwarz)": 543,
    "Flache Teller (schwarz)": 636,
    "Frühstücksteller": 475,
    "Weiße Schüssel": 400,
    "Kleine schwarze Schüssel": 286,
    "Ohne Teller / Direkt gewogen (Tara = 0 g)": 0
}

# --- Gemini API Setup (Liest aus Secrets oder Sidebar) ---
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"].strip()
else:
    api_key_input = st.sidebar.text_input("Gemini API Key", type="password")
    if api_key_input:
        api_key = api_key_input.strip()
    else:
        st.sidebar.warning("Bitte GOOGLE_API_KEY in den Secrets oder hier hinterlegen.")

if api_key:
    genai.configure(api_key=api_key)

def analyze_ingredients_with_gemini(ingredients_text):
    if not api_key:
        st.error("Kein API-Key gefunden! Bitte in den Streamlit Secrets oder links in der Sidebar eintragen.")
        return None
        
    prompt = f"""
    Du bist ein präziser Ernährungs- und Küchenassistent. Analysiere die folgende Zutatenliste für ein Gericht.
    Ermittle für jede Zutat das Gewicht in Gramm (ml bei Flüssigkeiten = g) und die Gesamtkalorien (kcal) für die angegebene Menge.
    Wenn der Nutzer Kalorienangaben pro 100g mitliefert (z.B. "1600g Hackfleisch mit 247 kcal pro 100g"), nutze exakt diese Werte zur Berechnung!
    
    Zutatenliste:
    {ingredients_text}
    
    Antworte AUSSCHLIESSLICH im folgenden JSON-Format ohne Markdown-Code-Blöcke darum, genau so:
    {{
      "zutaten_details": [
        {{"name": "Zutat 1", "gewicht_g": 1600, "kcal": 3952}},
        {{"name": "Zutat 2", "gewicht_g": 800, "kcal": 160}}
      ],
      "gesamt_rohgewicht_g": 2400,
      "gesamt_kcal": 4112
    }}
    """
    try:
        available_models = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
        
        chosen_model = None
        for preferred in ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']:
            for m in available_models:
                if preferred in m:
                    chosen_model = m
                    break
            if chosen_model:
                break
                
        if not chosen_model and available_models:
            chosen_model = available_models[0]
            
        model = genai.GenerativeModel(chosen_model)
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        st.error(f"Fehler bei der KI-Analyse: {e}")
        return None

# --- Session States ---
if "saved_sossen" not in st.session_state:
    st.session_state["saved_sossen"] = {}
if "saved_beilagen" not in st.session_state:
    st.session_state["saved_beilagen"] = {}
if "saved_mischungen" not in st.session_state:
    st.session_state["saved_mischungen"] = {}

# --- App Header ---
st.title("🍳 Kitchen & Meal Prep OS")
st.markdown("<p style='color: #90A4AE; letter-spacing: 0.3px;'>Präzise Nährwertberechnung nach dem Kochverlust & Teller-Modus</p>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🍲 Soße", "🍝 Beilagen", "🔥 Pfanne / Mix", "🍽️ Teller"])

# ==========================================
# TAB 1: SOẞE / EINTOPF
# ==========================================
with tab1:
    st.header("Soße oder Eintopf berechnen")
    sossen_name = st.text_input("Name der Soße", "Ragù alla Bolognese")
    ingredients_input = st.text_area(
        "Zutaten (Nutze die Sprachtaste der Tastatur!):", 
        placeholder="z.B. 1600g Hackfleisch mit 247 kcal pro 100g, 800g Dosentomaten, 200ml Weißwein, 20ml Olivenöl..."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        topf_sosse = st.selectbox("Topf auswählen", list(TOEPFE.keys()), key="t_sosse")
    with col2:
        brutto_sosse = st.number_input("Bruttogewicht (Topf + Soße in g):", min_value=0.0, step=10.0)

    tara_sosse = TOEPFE[topf_sosse]
    netto_sosse = brutto_sosse - tara_sosse

    if st.button("Soße berechnen", type="primary"):
        if not ingredients_input:
            st.warning("Bitte Zutaten eingeben.")
        elif brutto_sosse <= 0:
            st.warning("Bitte Bruttogewicht angeben.")
        else:
            with st.spinner("Analysiere Zutaten mit Gemini..."):
                data = analyze_ingredients_with_gemini(ingredients_input)
                if data:
                    gesamt_kcal = data["gesamt_kcal"]
                    rohgewicht_ki = data["gesamt_rohgewicht_g"]
                    
                    if netto_sosse <= 0:
                        st.error(f"Nettogewicht ist {netto_sosse}g! Das Bruttogewicht muss höher sein als das Topf-Gewicht ({tara_sosse}g).")
                    else:
                        kcal_100g = (gesamt_kcal / netto_sosse) * 100
                        verlust_g = rohgewicht_ki - netto_sosse
                        verlust_pct = (verlust_g / rohgewicht_ki) * 100 if rohgewicht_ki > 0 else 0
                        
                        st.success("Erfolgreich berechnet!")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Gesamtkalorien", f"{gesamt_kcal:,.0f} kcal")
                        c2.metric("Nettogewicht", f"{netto_sosse:,.0f} g")
                        c3.metric("Kaloriendichte", f"{kcal_100g:.1f} kcal/100g")
                        
                        st.info(f"Kochverlust (Verdunstung): {verlust_g:.0f} g ({verlust_pct:.1f}%) — Rohgewicht war ca. {rohgewicht_ki} g")
                        
                        with st.expander("Aufschlüsselung der erkannten Zutaten"):
                            for z in data.get("zutaten_details", []):
                                st.write(f"- **{z['name']}**: {z['gewicht_g']} g ({z['kcal']} kcal)")
                                
                        st.session_state["saved_sossen"][sossen_name] = {"kcal_100g": kcal_100g, "netto_g": netto_sosse}
                        st.toast(f"Soße '{sossen_name}' gespeichert!")

# ==========================================
# TAB 2: BEILAGEN (NUDELN)
# ==========================================
with tab2:
    st.header("Beilagen (Nudeln etc.)")
    beilagen_name = st.text_input("Name der Beilage", "Barilla Spaghetti")
    b1, b2 = st.columns(2)
    with b1:
        trocken_g = st.number_input("Trockengewicht vor dem Kochen (g):", min_value=0.0, step=10.0, value=500.0)
        trocken_kcal = st.number_input("kcal pro 100g (trocken, laut Packung):", min_value=0.0, step=1.0, value=350.0)
    with b2:
        topf_nudel = st.selectbox("Topf auswählen", list(TOEPFE.keys()), key="t_nudel", index=1)
        brutto_nudel = st.number_input("Bruttogewicht nach dem Abgießen (g):", min_value=0.0, step=10.0)

    tara_nudel = TOEPFE[topf_nudel]
    netto_nudel = brutto_nudel - tara_nudel

    if st.button("Gekochte Beilage berechnen", type="primary"):
        if trocken_g <= 0 or brutto_nudel <= 0:
            st.warning("Bitte Gewichte ausfüllen.")
        elif netto_nudel <= 0:
            st.error(f"Nettogewicht <= 0! Das Bruttogewicht muss höher sein als der gewählte Topf ({tara_nudel}g).")
        else:
            gesamt_kcal_n = (trocken_g / 100.0) * trocken_kcal
            kcal_100g_gekocht = (gesamt_kcal_n / netto_nudel) * 100
            st.success("Nudeln erfolgreich berechnet!")
            nc1, nc2, nc3 = st.columns(3)
            nc1.metric("Gesamtkalorien", f"{gesamt_kcal_n:,.0f} kcal")
            nc2.metric("Gekochtes Gewicht", f"{netto_nudel:,.0f} g")
            nc3.metric("Kaloriendichte", f"{kcal_100g_gekocht:.1f} kcal/100g")
            st.session_state["saved_beilagen"][beilagen_name] = {"kcal_100g": kcal_100g_gekocht}
            st.toast(f"Beilage '{beilagen_name}' gespeichert!")

# ==========================================
# TAB 3: PFANNE / MISCH-EVENT
# ==========================================
with tab3:
    st.header("Pfanne / Misch-Event")
    st.write("Kombiniere Soße, gekochte Nudeln, Nudelwasser und Extras (z.B. Parmesan) zu einer neuen Gesamtmischung.")
    misch_name = st.text_input("Name der Mischung", "Bolognese mit Spaghetti")
    s_list = list(st.session_state["saved_sossen"].keys())
    b_list = list(st.session_state["saved_beilagen"].keys())
    
    if s_list and b_list:
        chosen_s = st.selectbox("Soße wählen", s_list)
        menge_s_g = st.number_input("Menge Soße hinzugefügt (g):", min_value=0.0, step=10.0, value=600.0)
        chosen_b = st.selectbox("Beilage wählen", b_list)
        menge_b_g = st.number_input("Menge gekochte Beilage hinzugefügt (g):", min_value=0.0, step=10.0, value=1150.0)
        
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            nudelwasser_g = st.number_input("Nudelwasser hinzugefügt (ml/g):", min_value=0.0, step=10.0, value=100.0)
        with col_ex2:
            extra_kcal = st.number_input("Extras-Kalorien (z.B. 50g Parmesan = ca. 215 kcal):", min_value=0.0, step=10.0, value=215.0)
            
        if st.button("Mischung berechnen & speichern", type="primary"):
            kcal_s = (menge_s_g / 100.0) * st.session_state["saved_sossen"][chosen_s]["kcal_100g"]
            kcal_b = (menge_b_g / 100.0) * st.session_state["saved_beilagen"][chosen_b]["kcal_100g"]
            gesamt_misch_kcal = kcal_s + kcal_b + extra_kcal
            gesamt_misch_g = menge_s_g + menge_b_g + nudelwasser_g
            kcal_100g_mix = (gesamt_misch_kcal / gesamt_misch_g) * 100 if gesamt_misch_g > 0 else 0
            
            st.success("Mischung erfolgreich berechnet!")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Gesamtkalorien Mix", f"{gesamt_misch_kcal:,.0f} kcal")
            mc2.metric("Gesamtgewicht Mix", f"{gesamt_misch_g:,.0f} g")
            mc3.metric("Neue Kaloriendichte", f"{kcal_100g_mix:.1f} kcal/100g")
            st.session_state["saved_mischungen"][misch_name] = {"kcal_100g": kcal_100g_mix}
            st.toast(f"Mischung '{misch_name}' gespeichert!")
    else:
        st.info("Bitte berechne und speichere zuerst mindestens eine Soße (Reiter 1) und eine Beilage (Reiter 2).")

# ==========================================
# TAB 4: TELLER-RECHNER
# ==========================================
with tab4:
    st.header("Teller-Rechner")
    st.write("Teller auf die Waage stellen, Teller in der Liste wählen und Portion abwiegen.")
    m_list = list(st.session_state["saved_mischungen"].keys())
    if m_list:
        chosen_mix = st.selectbox("Gespeicherte Mischung", m_list)
        chosen_teller = st.selectbox("Teller auswählen (autom. Tara-Abzug)", list(TELLER.keys()))
        brutto_teller = st.number_input("Bruttogewicht auf Waage (Teller + Essen in g):", min_value=0.0, step=10.0)
        tara_teller = TELLER[chosen_teller]
        netto_essen = brutto_teller - tara_teller
        
        if st.button("Teller-Kalorien ermitteln", type="primary"):
            if brutto_teller <= 0:
                st.warning("Bitte Bruttogewicht eingeben.")
            elif netto_essen <= 0:
                st.error(f"Nettogewicht <= 0! Das Gewicht muss höher sein als der Teller ({tara_teller}g).")
            else:
                mix_kcal_100 = st.session_state["saved_mischungen"][chosen_mix]["kcal_100g"]
                portion_kcal = (netto_essen / 100.0) * mix_kcal_100
                st.markdown("### 🎯 Dein Teller-Ergebnis:")
                tc1, tc2, tc3 = st.columns(3)
                tc1.metric("Portions-Kalorien", f"{portion_kcal:,.0f} kcal")
                tc2.metric("Essen auf dem Teller", f"{netto_essen:,.0f} g")
                tc3.metric("Teller-Tara abgezogen", f"-{tara_teller} g")
    else:
        st.info("Bitte erstelle im Reiter 'Pfanne / Mix' zuerst eine fertige Mischung.")
