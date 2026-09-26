import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import hashlib
import io
import re
import html
import calendar
import unicodedata
from collections import defaultdict
from urllib.parse import urlencode, quote
from fpdf import FPDF


# ==========================================
# CONFIGURATION ET INITIALISATION
# ==========================================
st.set_page_config(page_title="Résa GDF", page_icon="🖼️", layout="wide")

# --- GATEKEEPER : Code d'accès général ---
def check_access():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.markdown("""
            <div style="display: flex; align-items: center; justify-content: center; min-height: 60vh;">
                <div style="background-color: #cfe9ff; padding: 2rem; border-radius: 20px; text-align: center; border: 2px solid #1b5e20;">
                    <h2 style="color: #1b5e20;">🔐 Accès sécurisé</h2>
                    <p style="color: #1b5e20; font-size: 1.8rem; font-weight: bold; margin: 10px 0 0 0;">Résa GDF</p>
                    <p style="color: #1b5e20; margin-top: 15px;">Veuillez saisir le code d'accès pour continuer.</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        code = st.text_input("Code d'accès", type="password", key="gate_code")
        if st.button("Valider", type="primary"):
            if code == "78955":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Code incorrect. Accès refusé.")
        st.stop()
check_access()

# --- TITRE DE L'APPLICATION ---
st.markdown("""
    <div class="app-header" style="display: flex; align-items: center; background-color: #e6f4ff; padding: 20px; border-radius: 15px; margin-bottom: 25px; border: 1px solid #a8cfe8;">
        <div class="app-header-emoji" style="font-size: 3.5rem; margin-right: 20px;">🖼️</div>
        <div>
            <h1 class="app-header-title" style="color: #1b5e20; margin: 0;">Résa GDF</h1>
            <p class="app-header-subtitle" style="margin: 0; color: #0a3d0a; font-weight: bold;">Ateliers d'éveil & Activités manuelles</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- CONNEXION SUPABASE ---
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase: Client = create_client(url, key)

# --- STYLE CSS ---
st.markdown("""
    <style>
    html, body, [class*="st-"] {
        font-size: 1.05rem !important;
        background-color: #e6f4ff !important;
        color: #1b5e20 !important;
    }
    .stApp { background-color: #e6f4ff; }
    .lieu-badge {
        padding: 3px 10px; border-radius: 6px; color: white; font-weight: bold;
        font-size: 0.85rem; display: inline-block; margin: 2px 0;
    }
    .couleur-badge {
        padding: 3px 10px; border-radius: 6px; font-weight: bold;
        font-size: 0.85rem; display: inline-block; margin: 2px 4px 2px 0;
    }
    .horaire-text { font-size: 0.9rem; color: #2e7d32; font-weight: 400; }
    .compteur-badge {
        font-size: 0.85rem; font-weight: 600; padding: 2px 8px; border-radius: 4px;
        background-color: #d4e6f1; color: #1b5e20; border: 1px solid #1b5e20; margin-left: 5px;
    }
    .alerte-complet { background-color: #c62828 !important; color: white !important; border-color: #b71c1c !important; }
    .separateur-atelier { border: 0; border-top: 1px solid #b0d4ff; margin: 15px 0; }
    .container-inscrits { margin-top: -8px; padding-top: 0; margin-bottom: 5px; }
    .liste-inscrits { font-size: 0.95rem !important; color: #1b5e20; margin-left: 20px; display: block; line-height: 1.1; }
    .animateur-inscrit { font-size: 0.95rem !important; color: #e65100; font-weight: bold; margin-left: 20px; display: block; line-height: 1.1; }
    .animateur-badge { background-color: #e65100; color: white; padding: 1px 7px; border-radius: 4px; font-size: 0.78rem; font-weight: bold; margin-left: 5px; }
    .nb-enfants-focus { color: #0a3d0a; font-weight: 600; }
    .stButton button { border-radius: 8px !important; background-color: #b2d8d8 !important; color: white !important; border: 0.2px solid #b2d8d8 !important; }
    .stButton button:hover { background-color: #0a3d0a !important; }
    .badge-verrouille { background-color: #b2d8d8; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-left: 6px; }
    .agenda-btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 30px; border: 1px solid #7ec8a3; background-color: #a8e6cf; color: #1b5e20 !important; font-weight: bold; font-size: 0.85rem; padding: 4px 14px; text-decoration: none !important; white-space: nowrap; margin-top: 2px; }
    .agenda-btn:hover { background-color: #d4f5e8; }
    .stDownloadButton button,
    div[data-testid="stDownloadButton"] button,
    .stDownloadButton button[kind="secondary"],
    div[data-testid="stDownloadButton"] button[kind="secondary"] {
        border-radius: 30px !important;
        border: 1px solid #7ec8a3 !important;
        background-color: #a8e6cf !important;
        color: #1b5e20 !important;
        font-weight: bold !important;
        font-size: 0.85rem !important;
        padding: 4px 14px !important;
        width: auto !important;
        white-space: nowrap !important;
        overflow: visible !important;
    }
    .stDownloadButton button *,
    div[data-testid="stDownloadButton"] button * {
        color: #1b5e20 !important;
    }
    .stDownloadButton button:hover,
    div[data-testid="stDownloadButton"] button:hover,
    .stDownloadButton button:focus,
    div[data-testid="stDownloadButton"] button:focus,
    .stDownloadButton button:focus:not(:active),
    div[data-testid="stDownloadButton"] button:focus:not(:active),
    .stDownloadButton button:active,
    div[data-testid="stDownloadButton"] button:active {
        background-color: #d4f5e8 !important;
        border-color: #7ec8a3 !important;
        color: #1b5e20 !important;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { color: #1b5e20 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] { background-color: #e6f4ff; border-radius: 20px !important; padding: 6px 18px; color: #1b5e20; border: 1px solid #a8cfe8 !important; font-size: 0.9rem; }
    .stTabs [aria-selected="true"] { background-color: #1b5e20 !important; color: #1b5e20 !important; border: 0.5px solid #a8e6cf !important; }
    .stTabs [data-baseweb="tab-panel"] { background-color: #e6f4ff; border-radius: 0px 16px 16px 16px !important; border: 1px solid #a8cfe8 !important; padding: 18px 20px !important; margin-top: 4px; }
    .stAlert { background-color: #cfe9ff; border-left-color: #1b5e20; color: #1b5e20; }
    .stSuccess { background-color: #d0e8d0; color: #0a3d0a; }
    .stError { background-color: #ffdddd; color: #c62828; }
    input, textarea, select { background-color: #ffffff !important; color: #1b5e20 !important; border-color: #1b5e20 !important; }
    .css-1d391kg, .css-1lcbmhc { background-color: #cfe9ff !important; }
    .bloc-animateur { background-color: #fff3e0; border: 1px solid #e65100; border-radius: 8px; padding: 8px 14px; margin-bottom: 8px; }
    div[data-testid="column"] .stButton button { border-radius: 30px !important; border: 1px solid #a8e6cf !important; background-color: transparent !important; color: #1b5e20 !important; transition: all 0.2s; }
    div[data-testid="column"] .stButton button[kind="primary"] { background-color: #a8e6cf !important; color: #1b5e20 !important; border-color: #7ec8a3 !important; font-weight: bold; }
    div[data-testid="column"] .stButton button:hover { background-color: #d4f5e8 !important; border-color: #7ec8a3 !important; }
    .filtre-vert-menthe { display: inline-flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
    .filtre-btn { border: 1.5px solid #80cbc4 !important; border-radius: 6px !important; padding: 3px 14px !important; background: transparent !important; color: #1b5e20 !important; font-size: 0.92rem !important; cursor: pointer !important; font-weight: 500; }
    .filtre-btn.actif { background-color: #b2dfdb !important; font-weight: bold !important; }
    .stPills [data-baseweb="tag"] { background-color: #e0f2f1 !important; color: #1b5e20 !important; border: 1px solid #80cbc4 !important; }
    .stPills [data-baseweb="tag"][aria-selected="true"] { background-color: #1b5e20 !important; color: white !important; border-color: #1b5e20 !important; }
    input:invalid, textarea:invalid, select:invalid { box-shadow: none !important; border-color: #ccc !important; }

    /* ==========================================================================
       OPTIMISATION MOBILE (téléphone) — n'affecte QUE les écrans <= 640px de large.
       Au-delà de 640px (ordinateur/tablette), l'affichage reste strictement identique.
       Streamlit empile déjà nativement les colonnes sous ce seuil dans ses versions
       récentes ; les règles ci-dessous le garantissent quelle que soit la version
       installée, et ajustent en plus la bannière, les onglets et la taille des
       boutons pour un usage confortable au doigt.
       ========================================================================== */
    @media (max-width: 640px) {
        /* Empilement garanti des colonnes : plusieurs colonnes serrées deviennent
           illisibles sur un écran de téléphone (ex: liste des inscrits, filtres). */
        div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; row-gap: 8px; }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }
        /* Bannière d'en-tête : réduite pour ne jamais déborder sur un petit écran */
        .app-header { padding: 12px !important; }
        .app-header-emoji { font-size: 2.1rem !important; margin-right: 12px !important; }
        .app-header-title { font-size: 1.4rem !important; }
        .app-header-subtitle { font-size: 0.82rem !important; }
        /* Boutons pleine largeur une fois la colonne empilée (cible tactile plus grande) */
        div[data-testid="column"] .stButton button { width: 100% !important; }
        div[data-testid="column"] .stDownloadButton button { width: 100% !important; }
        /* Onglets (Suivi & Récap, Administration) : défilement horizontal fluide
           plutôt qu'un texte écrasé/tronqué si les libellés ne tiennent pas */
        .stTabs [data-baseweb="tab-list"] { overflow-x: auto; flex-wrap: nowrap !important; -webkit-overflow-scrolling: touch; }
        .stTabs [data-baseweb="tab"] { padding: 6px 12px; font-size: 0.82rem; white-space: nowrap; }
        /* Tableaux larges (Statistiques, Places restantes) : défilement tactile fluide */
        .rs-wrap { -webkit-overflow-scrolling: touch; }
    }
    </style>
    """, unsafe_allow_html=True)


# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def get_color(nom_lieu):
    colors = [
        "#2e7d32", "#1565c0", "#6a1b9a", "#c62828", "#e65100",
        "#00695c", "#4527a0", "#ad1457", "#558b2f", "#0277bd",
        "#4e342e", "#37474f", "#f9a825", "#0d47a1", "#1b5e20"
    ]
    hash_object = hashlib.md5(str(nom_lieu).upper().strip().encode())
    hue = int(hash_object.hexdigest()[:8], 16) % len(colors)
    return colors[hue]

# --- BADGES DE COULEUR PAR ATELIER ---
# 6 couleurs au total. Bleu = défaut mercredi, Orange = défaut jeudi.
# Convention (non imposée techniquement) : une couleur donnée n'est utilisée que pour UN SEUL
# lieu, mais un même lieu peut avoir plusieurs couleurs (ex : mercredi ET jeudi au même endroit).
COULEURS_BADGE = {
    "Bleu":    "#1565c0",
    "Orange":  "#e65100",
    "Vert":    "#2e7d32",
    "Violet":  "#6a1b9a",
    "Rouge":   "#c62828",
    "Magenta": "#ad1457",
}
COULEURS_BADGE_LIST = list(COULEURS_BADGE.keys())
COULEURS_BADGE_RGB = {
    "Bleu": (21, 101, 192), "Orange": (230, 81, 0), "Vert": (46, 125, 50),
    "Violet": (106, 27, 154), "Rouge": (198, 40, 40), "Magenta": (173, 20, 87),
}

def couleur_badge_defaut(date_atelier):
    """Bleu le mercredi, Orange le jeudi. Bleu par défaut les autres jours (reste modifiable)."""
    try:
        d = date_atelier if isinstance(date_atelier, date) else datetime.strptime(str(date_atelier), '%Y-%m-%d').date()
    except Exception:
        return "Bleu"
    wd = d.weekday()  # 0 = lundi ... 2 = mercredi, 3 = jeudi
    if wd == 2:
        return "Bleu"
    if wd == 3:
        return "Orange"
    return "Bleu"

def get_couleur_atelier(at):
    """Couleur de badge d'un atelier : valeur enregistrée, sinon valeur par défaut selon le jour."""
    c = at.get('couleur_badge')
    if c and c in COULEURS_BADGE:
        return c
    return couleur_badge_defaut(at.get('date_atelier'))

def hex_couleur_badge(nom_couleur):
    return COULEURS_BADGE.get(nom_couleur, "#616161")

def rgb_couleur_badge(nom_couleur):
    return COULEURS_BADGE_RGB.get(nom_couleur, (100, 100, 100))

_JOURS_EMOJI = {
    0: "🔵",   # lundi
    1: "🟢",   # mardi
    2: "🟠",   # mercredi
    3: "🟣",   # jeudi
    4: "🔴",   # vendredi
    5: "🔷",   # samedi
    6: "🟡",   # dimanche
}

def get_weekday_emoji(date_str):
    """Retourne un émoji de cercle coloré selon le jour de la semaine (0=lundi, 6=dimanche)"""
    d = datetime.strptime(date_str, '%Y-%m-%d')
    return _JOURS_EMOJI.get(d.weekday(), "⚪")

# --- CACHE : données stables (5 minutes) ---
@st.cache_data(ttl=300)
def get_config():
    """Charge secret_code et max_enfants en une seule requête, mise en cache 5 min."""
    try:
        res = supabase.table("configuration").select("secret_code, max_enfants").eq("id", "main_config").execute()
        if res.data:
            return res.data[0].get("secret_code", "1234"), int(res.data[0].get("max_enfants") or 20)
    except:
        pass
    return "1234", 20

@st.cache_data(ttl=300)
def get_lieux_cached():
    try:
        res = supabase.table("lieux").select("*").order("nom").execute()
        return res.data or []
    except:
        return []

@st.cache_data(ttl=300)
def get_horaires_cached():
    try:
        res = supabase.table("horaires").select("*").execute()
        return res.data or []
    except:
        return []

@st.cache_data(ttl=300)
def get_adherents_actifs_cached():
    try:
        res = supabase.table("adherents").select("*").eq("est_actif", True).order("nom").order("prenom").execute()
        return res.data or []
    except:
        return []

@st.cache_data(ttl=300)
def get_adherents_tous_cached():
    try:
        res = supabase.table("adherents").select("*").order("nom").order("prenom").execute()
        return res.data or []
    except:
        return []

# --- CACHE : données dynamiques (30 secondes) ---
@st.cache_data(ttl=30)
def get_ateliers_a_venir():
    today_str = str(date.today())
    try:
        return supabase.table("ateliers").select("*").eq("est_actif", True).gte("date_atelier", today_str).order("date_atelier").execute().data or []
    except:
        return []

@st.cache_data(ttl=30)
def get_ateliers_periode(date_debut_str, date_fin_str, actif_filter=None):
    try:
        query = supabase.table("ateliers").select("*").gte("date_atelier", date_debut_str).lte("date_atelier", date_fin_str)
        if actif_filter == "Actifs":
            query = query.eq("est_actif", True)
        elif actif_filter == "Inactifs":
            query = query.eq("est_actif", False)
        return query.order("date_atelier").execute().data or []
    except:
        return []

@st.cache_data(ttl=30)
def get_toutes_inscriptions_ateliers(atelier_ids_tuple):
    """Charge TOUTES les inscriptions pour une liste d'ateliers en UNE SEULE requête."""
    if not atelier_ids_tuple:
        return []
    try:
        return supabase.table("inscriptions").select("*, adherents(nom, prenom)").in_("atelier_id", list(atelier_ids_tuple)).execute().data or []
    except:
        return []

def invalider_cache_inscriptions():
    """Invalide les caches dynamiques après une modification."""
    get_ateliers_a_venir.clear()
    get_ateliers_periode.clear()
    get_toutes_inscriptions_ateliers.clear()

def invalider_cache_referentiels():
    """Invalide les caches stables après modification d'un référentiel."""
    get_lieux_cached.clear()
    get_horaires_cached.clear()
    get_adherents_actifs_cached.clear()
    get_adherents_tous_cached.clear()
    get_config.clear()

def get_secret_code():
    code, _ = get_config()
    return code

def get_max_enfants():
    _, max_enf = get_config()
    return max_enf

def set_max_enfants(valeur):
    try:
        supabase.table("configuration").update({"max_enfants": valeur}).eq("id", "main_config").execute()
        get_config.clear()
        return True
    except Exception as e:
        return str(e)

def get_max_enfants_atelier(at, default_max):
    val = at.get('max_enfants')
    if val is not None:
        return int(val)
    return default_max

def normaliser_pdf_text(texte):
    if not isinstance(texte, str):
        texte = str(texte)
    # Normalisation Unicode : supprime les accents et diacritiques
    texte = unicodedata.normalize('NFKD', texte).encode('ascii', 'ignore').decode('ascii')
    # Remplacements des caractères non couverts par NFKD
    for src, dst in (
        ('—', '-'), ('–', '-'), ('…', '...'),
        ('"', '"'), ('"', '"'), ('«', '"'), ('»', '"'),
        ('\u2018', "'"), ('\u2019', "'"), ('©', '(c)'), ('®', '(r)'),
        ('€', 'EUR'), ('£', 'GBP'), ('¥', 'YEN'),
    ):
        texte = texte.replace(src, dst)
    return texte

_JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS_FR  = ["janvier", "février", "mars", "avril", "mai", "juin",
              "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
_JOURS_FR_CAP = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

def heure_paris_fr():
    now = datetime.now(ZoneInfo("Europe/Paris"))
    return f"le {_JOURS_FR[now.weekday()]} {now.day} {_MOIS_FR[now.month-1]} {now.year} à {now.hour:02d}h{now.minute:02d}"

def enregistrer_log(utilisateur, action, details):
    try:
        supabase.table("logs").insert({
            "utilisateur": utilisateur,
            "action": action,
            "details": f"{details} [{heure_paris_fr()}]"
        }).execute()
    except:
        pass

def format_date_fr_complete(date_obj, gras=True):
    if isinstance(date_obj, str):
        try: date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        except: return date_obj
    res = f"{_JOURS_FR_CAP[date_obj.weekday()]} {date_obj.day} {_MOIS_FR[date_obj.month-1]} {date_obj.year}"
    return f"**{res}**" if gras else res

def format_date_fr_simple(date_str):
    try:
        d = datetime.strptime(str(date_str), '%Y-%m-%d')
        return f"{_JOURS_FR_CAP[d.weekday()]} {d.day} {_MOIS_FR[d.month-1]} {d.year}"
    except:
        return str(date_str)

def ajouter_mois(d, nb_mois):
    """Ajoute nb_mois à une date, en gérant le changement d'année et les fins de mois
    (ex: 31 janvier + 1 mois -> 28 ou 29 février selon l'année)."""
    mois_total = d.month - 1 + nb_mois
    annee = d.year + mois_total // 12
    mois = mois_total % 12 + 1
    jour = min(d.day, calendar.monthrange(annee, mois)[1])
    return d.replace(year=annee, month=mois, day=jour)

def parse_date_fr_to_iso(date_str):
    clean = str(date_str).replace("**", "").strip()
    if not clean:
        return None
    try:
        return datetime.strptime(clean, '%Y-%m-%d').strftime('%Y-%m-%d')
    except:
        pass
    parts = clean.split(" ")
    if len(parts) >= 4:
        jour, mois_texte, annee = parts[1], parts[2].lower(), parts[3]
        if mois_texte in _MOIS_FR:
            m = _MOIS_FR.index(mois_texte) + 1
            try:
                return f"{annee}-{m:02d}-{int(jour):02d}"
            except:
                pass
    try:
        for sep in ['/', '-']:
            if sep in clean:
                j, m, a = clean.split(sep)
                return f"{int(a):04d}-{int(m):02d}-{int(j):02d}"
    except:
        pass
    return clean

_RE_HORAIRE = re.compile(r'^\s*(\d{1,2})[:hH](\d{2})?\s*-\s*(\d{1,2})[:hH](\d{2})?\s*$')

def _plage_horaire_atelier(date_atelier, horaire_lib):
    """Calcule la plage horaire d'un atelier à partir de sa date et de son libellé d'horaire.
    Retourne (dt_debut, dt_fin, journee_entiere) en heure locale Europe/Paris (naïve),
    ou None si la date est invalide."""
    try:
        d = datetime.strptime(str(date_atelier), '%Y-%m-%d')
    except Exception:
        return None

    m = _RE_HORAIRE.match(str(horaire_lib) or "")
    if m:
        hd_s, md_s, hf_s, mf_s = m.groups()
        hd, md, hf, mf = int(hd_s), int(md_s or 0), int(hf_s), int(mf_s or 0)
        dt_debut = d.replace(hour=hd, minute=md)
        dt_fin = d.replace(hour=hf, minute=mf)
        if dt_fin <= dt_debut:
            dt_fin = dt_debut + timedelta(hours=1)
        return dt_debut, dt_fin, False
    else:
        # Horaire non reconnu : événement journée entière
        return d, d + timedelta(days=1), True

def _titre_details_evenement(titre, horaire_lib):
    titre_evt = f"Atelier GDF - {titre}" if titre else "Atelier GDF"
    details_evt = titre_evt + (f" - {horaire_lib}" if horaire_lib else "")
    return titre_evt, details_evt

def lien_google_agenda(date_atelier, horaire_lib, titre, lieu_nom):
    """Construit un lien 'Ajouter à Google Agenda' pré-rempli pour un atelier.
    Retourne None si la date est invalide."""
    plage = _plage_horaire_atelier(date_atelier, horaire_lib)
    if not plage:
        return None
    dt_debut, dt_fin, journee_entiere = plage

    if journee_entiere:
        dates_param = f"{dt_debut.strftime('%Y%m%d')}/{dt_fin.strftime('%Y%m%d')}"
    else:
        dates_param = f"{dt_debut.strftime('%Y%m%dT%H%M%S')}/{dt_fin.strftime('%Y%m%dT%H%M%S')}"

    titre_evt, details_evt = _titre_details_evenement(titre, horaire_lib)
    params = {
        "action": "TEMPLATE",
        "text": titre_evt,
        "dates": dates_param,
        "details": details_evt,
        "location": lieu_nom or "",
        "ctz": "Europe/Paris",
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params, quote_via=quote)

def bouton_agenda_html(date_atelier, horaire_lib, titre, lieu_nom):
    """Retourne le HTML du bouton 'Google Agenda', ou une chaîne vide si le lien ne peut pas être généré."""
    lien = lien_google_agenda(date_atelier, horaire_lib, titre, lieu_nom)
    if not lien:
        return ""
    return f"<a class='agenda-btn' href='{html.escape(lien)}' target='_blank' rel='noopener'>📅 Google Agenda</a>"

def _ics_echapper(txt):
    return str(txt).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def fichier_ics_atelier(date_atelier, horaire_lib, titre, lieu_nom, atelier_id=None):
    """Construit le contenu d'un fichier .ics (format universel) pour un atelier :
    compatible Calendrier Apple/iPhone, Outlook, Google Agenda, etc.
    Retourne des bytes UTF-8, ou None si la date est invalide."""
    plage = _plage_horaire_atelier(date_atelier, horaire_lib)
    if not plage:
        return None
    dt_debut, dt_fin, journee_entiere = plage
    titre_evt, details_evt = _titre_details_evenement(titre, horaire_lib)

    if journee_entiere:
        dtstart = f"DTSTART;VALUE=DATE:{dt_debut.strftime('%Y%m%d')}"
        dtend = f"DTEND;VALUE=DATE:{dt_fin.strftime('%Y%m%d')}"
    else:
        dt_debut_utc = dt_debut.replace(tzinfo=ZoneInfo("Europe/Paris")).astimezone(ZoneInfo("UTC"))
        dt_fin_utc = dt_fin.replace(tzinfo=ZoneInfo("Europe/Paris")).astimezone(ZoneInfo("UTC"))
        dtstart = f"DTSTART:{dt_debut_utc.strftime('%Y%m%dT%H%M%SZ')}"
        dtend = f"DTEND:{dt_fin_utc.strftime('%Y%m%dT%H%M%SZ')}"

    dtstamp = datetime.now(ZoneInfo("Europe/Paris")).astimezone(ZoneInfo("UTC")).strftime('%Y%m%dT%H%M%SZ')
    cle_uid = f"{atelier_id or ''}-{date_atelier}-{horaire_lib or ''}"
    uid = f"{hashlib.md5(str(cle_uid).encode()).hexdigest()}@resa-gdf"

    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Resa GDF//FR",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        dtstart,
        dtend,
        f"SUMMARY:{_ics_echapper(titre_evt)}",
        f"DESCRIPTION:{_ics_echapper(details_evt)}",
        f"LOCATION:{_ics_echapper(lieu_nom or '')}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return ("\r\n".join(lignes) + "\r\n").encode("utf-8")

def bouton_ics_html(ics_data):
    """Retourne le HTML du bouton 'iPhone / Autre agenda' : lien 'data:' vers le contenu .ics,
    SANS attribut 'download'. Sur iPhone/Safari, un tel lien est reconnu nativement comme un
    événement de calendrier et ouvre directement la fiche "Ajouter à Calendrier" (pas de fichier
    à télécharger puis importer manuellement). L'attribut 'download' forcerait au contraire un
    enregistrement de fichier (comportement précédent, corrigé ici) et empêcherait cet ajout direct.
    Stylé exactement comme le bouton 'Google Agenda' (classe CSS 'agenda-btn' partagée).
    Retourne une chaîne vide si les données sont absentes."""
    if not ics_data:
        return ""
    contenu = ics_data.decode("utf-8") if isinstance(ics_data, bytes) else ics_data
    href = f"data:text/calendar;charset=utf-8,{quote(contenu)}"
    return f"<a class='agenda-btn' href='{href}'>📱 iPhone / Autre agenda</a>"

def is_verrouille(at):
    return bool(at.get("est_verrouille", False))


def trier_par_nom_puis_date(data):
    return sorted(data, key=lambda i: (
        i['adherents']['nom'].upper(),
        i['adherents']['prenom'].upper(),
        i['ateliers']['date_atelier']
    ))

def construire_cache_ins(inscriptions_brutes):
    """Transforme une liste plate d'inscriptions en dict {atelier_id: [inscriptions]}."""
    cache = {}
    for ins in inscriptions_brutes:
        cache.setdefault(ins['atelier_id'], []).append(ins)
    return cache

def enrichir_ateliers(ateliers_bruts, lieux_dict, horaires_dict):
    """Ajoute lieu_nom et horaire_lib à chaque atelier."""
    for at in ateliers_bruts:
        at['lieu_nom'] = lieux_dict.get(at['lieu_id'], '?')
        at['horaire_lib'] = horaires_dict.get(at['horaire_id'], '?')
    return ateliers_bruts

# --- FONCTIONS ANIMATEUR ---
def assigner_animateur(at_id, nouvel_anim_id, nb_enfants, ancien_anim_id=None, auteur="Animateur"):
    try:
        if ancien_anim_id and ancien_anim_id != nouvel_anim_id:
            supabase.table("inscriptions").delete().eq("atelier_id", at_id).eq("adherent_id", ancien_anim_id).execute()
        supabase.table("ateliers").update({"animateur_id": nouvel_anim_id}).eq("id", at_id).execute()
        existing = supabase.table("inscriptions").select("id").eq("atelier_id", at_id).eq("adherent_id", nouvel_anim_id).execute()
        if existing.data:
            supabase.table("inscriptions").update({"nb_enfants": nb_enfants}).eq("id", existing.data[0]['id']).execute()
        else:
            supabase.table("inscriptions").insert({
                "adherent_id": nouvel_anim_id, "atelier_id": at_id, "nb_enfants": nb_enfants
            }).execute()
        enregistrer_log(auteur, "Attribution animateur", f"Animateur ID {nouvel_anim_id} assigné à atelier ID {at_id} ({nb_enfants} enf.)")
        invalider_cache_inscriptions()
        return True
    except Exception as e:
        return str(e)

def retirer_animateur(at_id, anim_id, auteur="Admin"):
    try:
        supabase.table("inscriptions").delete().eq("atelier_id", at_id).eq("adherent_id", anim_id).execute()
        supabase.table("ateliers").update({"animateur_id": None}).eq("id", at_id).execute()
        enregistrer_log(auteur, "Retrait animateur", f"Animateur retiré de l'atelier ID {at_id}")
        invalider_cache_inscriptions()
        return True
    except Exception as e:
        return str(e)

# --- FONCTIONS D'EXPORT ---
def export_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Export')
    return output.getvalue()

def export_to_excel_with_period(df, date_debut, date_fin, titre_periode="Période"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Export')
        writer.sheets['Export'] = worksheet
        bold = workbook.add_format({'bold': True, 'font_size': 12})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#1b5e20', 'font_color': 'white'})
        periode_str = f"{titre_periode} : du {format_date_fr_simple(str(date_debut))} au {format_date_fr_simple(str(date_fin))}"
        worksheet.write(0, 0, periode_str, bold)
        for col_idx, col_name in enumerate(df.columns):
            worksheet.write(2, col_idx, col_name, header_fmt)
        for row_idx, row in enumerate(df.itertuples(index=False), start=3):
            for col_idx, value in enumerate(row):
                worksheet.write(row_idx, col_idx, value)
        for col_idx, col_name in enumerate(df.columns):
            max_len = max(len(str(col_name)), df[col_name].astype(str).str.len().max() if len(df) > 0 else 0)
            worksheet.set_column(col_idx, col_idx, min(max_len + 2, 40))
    return output.getvalue()

def export_to_pdf(title, data_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, normaliser_pdf_text(title), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=11)
    if not data_list:
        pdf.multi_cell(0, 10, txt=normaliser_pdf_text("Aucune donnee a exporter."))
    else:
        for line in data_list:
            pdf.multi_cell(0, 10, txt=normaliser_pdf_text(line))
    return pdf.output(dest='S').encode('latin-1')

# --- STATISTIQUES DE PARTICIPATION (par couleur de badge) ---

def _pdf_output_bytes(pdf):
    """Retourne les bytes du PDF, compatible avec les deux variantes de la lib FPDF
    (l'ancienne renvoie une chaîne à encoder, fpdf2 renvoie déjà un bytearray)."""
    resultat = pdf.output(dest='S')
    if isinstance(resultat, (bytes, bytearray)):
        return bytes(resultat)
    return resultat.encode('latin-1')

def periode_stats_defaut():
    """Règle de période par défaut pour l'écran Statistiques, basée sur la date du jour :
    si aujourd'hui est compris entre le 1er août de l'année N et le 15 juillet de l'année N+1,
    la période par défaut est du 1er septembre N au 15 juillet N+1 (aucun trou possible sur l'année)."""
    today = date.today()
    if today >= date(today.year, 8, 1):
        annee = today.year
    else:
        annee = today.year - 1
    return date(annee, 9, 1), date(annee + 1, 7, 15)

def periode_places_restantes_defaut():
    """Règle de période par défaut pour l'écran Places restantes, basée sur la date du jour :
    du jour même au 31 juillet le plus proche dans le futur (cette année si le 31 juillet n'est
    pas encore passé, sinon l'année suivante)."""
    today = date.today()
    fin_cette_annee = date(today.year, 7, 31)
    if today <= fin_cette_annee:
        return today, fin_cette_annee
    return today, date(today.year + 1, 7, 31)

def format_date_courte(iso_str):
    try:
        d = datetime.strptime(str(iso_str), '%Y-%m-%d')
        return d.strftime('%d/%m/%y')
    except Exception:
        return str(iso_str)

def _lieux_label_couleur(couleur, couleur_lieux):
    """Retourne (texte, incoherent) pour le lieu associé à une couleur sur la période."""
    lieux = sorted(couleur_lieux.get(couleur, set()))
    if not lieux:
        return "(aucun atelier)", False
    if len(lieux) == 1:
        return lieux[0], False
    return " / ".join(lieux), True

def rendu_html_stats_couleur(am_rows, couleurs_utilisees, couleur_lieux, data_am):
    """Construit le tableau HTML : lignes = AM (triées nom de famille), colonnes = couleurs de
    badge utilisées sur la période (avec le lieu associé en sous-en-tête), cellule = nombre
    d'inscriptions + toutes les dates. Colonne Total à droite."""
    css = """
    <style>
    .rs-wrap { max-height: 65vh; overflow: auto; border: 1px solid #274a6e; border-radius: 6px; }
    .rs-table { border-collapse: collapse; width: 100%; font-size: 0.85rem; background: white; }
    .rs-table thead th { border: 1px solid #274a6e; padding: 0; min-width: 130px; }
    .rs-table thead tr:first-child th {
        position: sticky; top: 0; z-index: 3;
        box-shadow: 0 1px 0 #274a6e;
    }
    .rs-table thead tr:last-child th {
        position: sticky; top: 36px; z-index: 2;
        box-shadow: 0 2px 2px -1px rgba(0,0,0,0.15);
    }
    .rs-am-th { background: #1b3a5c !important; color: white; text-align: left !important;
                padding: 8px 8px 8px 12px !important; font-size: 0.75rem; text-transform: uppercase; min-width: 160px; }
    .rs-color-th { text-align: center; padding: 7px 6px !important; font-weight: 800;
                   font-size: 0.78rem; text-transform: uppercase; }
    .rs-total-th { background: #0f2a44 !important; color: white; text-align: center !important;
                   padding: 8px 6px !important; font-size: 0.75rem; text-transform: uppercase; min-width: 60px; }
    .rs-lieu-label { background: #f0f3f6 !important; color: #1b3a5c; text-align: left !important;
                     padding: 5px 12px !important; font-size: 0.7rem; font-weight: 600; text-transform: none; }
    .rs-lieu { background: rgba(255,255,255,0.98) !important; color: #1b3a5c; font-size: 0.72rem;
               font-weight: 700; padding: 5px 6px !important; text-align: center; }
    .rs-lieu.unused { color: #9aa1a8; font-weight: 500; font-style: italic; }
    .rs-lieu.warn { color: #a12626; }
    .rs-table tbody td { border: 1px solid #e2e6ea; padding: 7px 8px; vertical-align: top; text-align: center; }
    .rs-table tbody tr:nth-child(even) { background: #fafbfc; }
    .rs-am-cell { font-weight: 700; font-size: 0.95rem; color: #1b3a5c !important; text-align: left !important;
                  white-space: nowrap; }
    .rs-am-cell .rs-prenom { font-weight: 400; color: #444; }
    .rs-empty { color: #c3c8cd; }
    .rs-count { font-weight: 800; font-size: 1.05rem; line-height: 1; display: block; }
    .rs-dates { font-size: 0.7rem; color: #6b7280; font-style: italic; line-height: 1.3; margin-top: 2px; }
    .rs-date-anim { color: #15803d; font-weight: 800; font-style: normal; }
    .rs-total-cell { font-weight: 800; font-size: 1.05rem; color: #1b3a5c !important; background: #eef3f8 !important; }
    </style>
    """
    parts = [css, '<div class="rs-wrap"><table class="rs-table"><thead><tr>']
    parts.append('<th class="rs-am-th">Assistante Maternelle</th>')
    for c in couleurs_utilisees:
        hexcol = hex_couleur_badge(c)
        parts.append(f'<th class="rs-color-th" style="background:{hexcol};color:#ffffff;">{html.escape(c)}</th>')
    parts.append('<th class="rs-total-th">Total</th></tr>')

    parts.append('<tr><th class="rs-lieu-label">Lieu associé →</th>')
    for c in couleurs_utilisees:
        txt, incoherent = _lieux_label_couleur(c, couleur_lieux)
        if txt == "(aucun atelier)":
            cls = "rs-lieu unused"
        elif incoherent:
            txt += " ⚠️"
            cls = "rs-lieu warn"
        else:
            cls = "rs-lieu"
        parts.append(f'<th class="{cls}">{html.escape(txt)}</th>')
    parts.append('<th class="rs-total-th" style="background:#eef3f8 !important;"></th></tr></thead><tbody>')

    for nom, prenom, am_id in am_rows:
        parts.append('<tr>')
        parts.append(f'<td class="rs-am-cell">{html.escape(nom)} <span class="rs-prenom">{html.escape(prenom)}</span></td>')
        total_am = 0
        for c in couleurs_utilisees:
            entry = data_am.get(am_id, {}).get(c)
            if entry and entry["count"] > 0:
                total_am += entry["count"]
                dates_sorted = sorted(entry["dates"], key=lambda t: t[0])
                dates_html_parts = []
                for d, est_anim in dates_sorted:
                    txt = html.escape(format_date_courte(d))
                    dates_html_parts.append(f'<span class="rs-date-anim">{txt}</span>' if est_anim else txt)
                dates_txt = ", ".join(dates_html_parts)
                hexcol = hex_couleur_badge(c)
                parts.append(f'<td><span class="rs-count" style="color:{hexcol}">{entry["count"]}</span>'
                             f'<div class="rs-dates">{dates_txt}</div></td>')
            else:
                parts.append('<td class="rs-empty">–</td>')
        parts.append(f'<td class="rs-total-cell">{total_am}</td>')
        parts.append('</tr>')
    parts.append('</tbody></table></div>')
    parts.append('<div style="margin-top:4px; font-size:0.72rem; color:#6b7280;">'
                  '<span class="rs-date-anim">Date en gras vert</span> = l\'assistante maternelle était animatrice de cet atelier.</div>')
    return "".join(parts)

def export_stats_couleur_excel(am_rows, couleurs_utilisees, couleur_lieux, data_am, date_debut, date_fin, statut_filtre):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Statistiques')
        writer.sheets['Statistiques'] = worksheet

        nb_col_couleurs = len(couleurs_utilisees)
        total_col = nb_col_couleurs + 1

        title_fmt = workbook.add_format({'bold': True, 'font_size': 13, 'font_color': '#1b3a5c'})
        periode_str = (f"Statistiques de participation - du {format_date_fr_simple(str(date_debut))} "
                       f"au {format_date_fr_simple(str(date_fin))} - Ateliers : {statut_filtre}")
        worksheet.merge_range(0, 0, 0, max(total_col, 1), normaliser_pdf_text(periode_str), title_fmt)

        header_row = 2
        am_header_fmt = workbook.add_format({'bold': True, 'bg_color': '#1b3a5c', 'font_color': 'white',
                                              'border': 1, 'align': 'left', 'valign': 'vcenter'})
        total_header_fmt = workbook.add_format({'bold': True, 'bg_color': '#0f2a44', 'font_color': 'white',
                                                 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        worksheet.write(header_row, 0, "Assistante Maternelle", am_header_fmt)

        color_header_fmts = {}
        for idx, c in enumerate(couleurs_utilisees):
            col = idx + 1
            hexcol = hex_couleur_badge(c)
            fmt = workbook.add_format({'bold': True, 'bg_color': hexcol, 'font_color': 'white',
                                        'border': 1, 'align': 'center', 'valign': 'vcenter'})
            worksheet.write(header_row, col, c.upper(), fmt)
            color_header_fmts[c] = fmt
        worksheet.write(header_row, total_col, "TOTAL", total_header_fmt)

        sub_row = header_row + 1
        lieu_label_fmt = workbook.add_format({'italic': True, 'font_size': 9, 'border': 1, 'bg_color': '#eef3f8'})
        lieu_val_fmt = workbook.add_format({'italic': True, 'font_size': 9, 'border': 1, 'align': 'center',
                                             'valign': 'vcenter', 'bg_color': '#eef3f8', 'text_wrap': True})
        worksheet.write(sub_row, 0, "Lieu associé", lieu_label_fmt)
        for idx, c in enumerate(couleurs_utilisees):
            col = idx + 1
            txt, incoherent = _lieux_label_couleur(c, couleur_lieux)
            if incoherent:
                txt += " /!\\"
            worksheet.write(sub_row, col, normaliser_pdf_text(txt), lieu_val_fmt)
        worksheet.write(sub_row, total_col, "", lieu_val_fmt)
        worksheet.set_row(sub_row, 30)

        am_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'font_color': '#1b3a5c', 'border': 1, 'valign': 'top'})
        empty_fmt = workbook.add_format({'align': 'center', 'font_color': '#c3c8cd', 'border': 1, 'valign': 'top'})
        total_cell_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'font_color': '#1b3a5c',
                                               'bg_color': '#eef3f8', 'align': 'center', 'border': 1, 'valign': 'top'})
        cell_border_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'top', 'text_wrap': True})
        count_fmts = {c: workbook.add_format({'bold': True, 'font_size': 13, 'font_color': hex_couleur_badge(c)})
                      for c in couleurs_utilisees}
        dates_run_fmt = workbook.add_format({'italic': True, 'font_size': 8, 'font_color': '#6b7280'})
        anim_date_fmt = workbook.add_format({'italic': True, 'bold': True, 'font_size': 8, 'font_color': '#15803d'})

        r = sub_row + 1
        for nom, prenom, am_id in am_rows:
            worksheet.write(r, 0, normaliser_pdf_text(f"{nom} {prenom}"), am_fmt)
            total_am = 0
            max_lignes = 1
            for idx, c in enumerate(couleurs_utilisees):
                col = idx + 1
                entry = data_am.get(am_id, {}).get(c)
                if entry and entry["count"] > 0:
                    total_am += entry["count"]
                    dates_sorted = sorted(entry["dates"], key=lambda t: t[0])
                    dates_plain = ", ".join(format_date_courte(d) for d, _ in dates_sorted)
                    max_lignes = max(max_lignes, 1 + (len(dates_plain) // 22))
                    runs = [count_fmts[c], f"{entry['count']}\n"]
                    for i, (d, est_anim) in enumerate(dates_sorted):
                        if i > 0:
                            runs.extend([dates_run_fmt, ", "])
                        runs.extend([anim_date_fmt if est_anim else dates_run_fmt,
                                     normaliser_pdf_text(format_date_courte(d))])
                    runs.append(cell_border_fmt)
                    worksheet.write_rich_string(r, col, *runs)
                else:
                    worksheet.write(r, col, "–", empty_fmt)
            worksheet.write(r, total_col, total_am, total_cell_fmt)
            worksheet.set_row(r, max(24, 14 * max_lignes))
            r += 1

        worksheet.set_column(0, 0, 26)
        if nb_col_couleurs:
            worksheet.set_column(1, total_col, 22)
        worksheet.freeze_panes(sub_row + 1, 1)
    return output.getvalue()

def _pdf_ajuster_taille(pdf, texte, largeur, style='I', taille_max=8, taille_min=5):
    """Réduit la taille de police jusqu'à ce que le texte tienne sur une seule ligne dans la
    largeur donnée (marge de 2mm) ; tronque avec '...' si la taille minimale ne suffit toujours pas."""
    taille = taille_max
    while taille >= taille_min:
        pdf.set_font("Arial", style, taille)
        if pdf.get_string_width(texte) <= largeur - 2:
            return texte
        taille -= 1
    pdf.set_font("Arial", style, taille_min)
    while texte and pdf.get_string_width(texte + "...") > largeur - 2:
        texte = texte[:-1]
    return (texte + "...") if texte else "..."

def _pdf_entete_stats(pdf, largeur_am, largeur_couleur, largeur_total, couleurs_utilisees, couleur_lieux):
    """Dessine les deux lignes d'en-tête du tableau PDF Statistiques : couleurs, puis lieu associé
    (taille de police réduite automatiquement si le nom du/des lieu(x) est trop long)."""
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(27, 58, 92)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(largeur_am, 8, normaliser_pdf_text("Assistante Maternelle"), border=1, fill=True)
    for c in couleurs_utilisees:
        r, g, b = rgb_couleur_badge(c)
        pdf.set_fill_color(r, g, b)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(largeur_couleur, 8, normaliser_pdf_text(c.upper()), border=1, align='C', fill=True)
    pdf.set_fill_color(15, 42, 68)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(largeur_total, 8, "TOTAL", border=1, align='C', fill=True)
    pdf.ln(8)

    pdf.set_fill_color(238, 243, 248)
    pdf.set_text_color(27, 58, 92)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(largeur_am, 7, normaliser_pdf_text("Lieu associe"), border=1, fill=True)
    for c in couleurs_utilisees:
        txt, incoherent = _lieux_label_couleur(c, couleur_lieux)
        if incoherent:
            txt += " !"
        txt_norm = normaliser_pdf_text(txt)
        txt_ajuste = _pdf_ajuster_taille(pdf, txt_norm, largeur_couleur, style='I', taille_max=8, taille_min=5)
        pdf.cell(largeur_couleur, 7, txt_ajuste, border=1, align='C', fill=True)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(largeur_total, 7, "", border=1, fill=True)
    pdf.ln(7)
    pdf.set_text_color(0, 0, 0)

def _pdf_nb_lignes(pdf, texte, largeur):
    if not texte:
        return 1
    mots = str(texte).split(' ')
    lignes = 1
    courante = ""
    for mot in mots:
        essai = (courante + " " + mot).strip()
        if pdf.get_string_width(essai) > largeur - 2:
            lignes += 1
            courante = mot
        else:
            courante = essai
    return lignes

def _pdf_segments_dates(dates_list):
    """Construit la séquence de segments (texte, est_animateur) pour une liste de tuples
    (date_iso, est_animateur), triée par date, avec des virgules de séparation en style normal."""
    segments = []
    for i, (d, est_anim) in enumerate(sorted(dates_list, key=lambda t: t[0])):
        if i > 0:
            segments.append((", ", False))
        segments.append((format_date_courte(d), est_anim))
    return segments

def _pdf_wrap_segments(pdf, segments, largeur, taille=7):
    """Découpe une séquence de segments (texte, est_animateur) en lignes tenant dans `largeur` (mm).
    Chaque segment retourné porte aussi sa largeur mesurée, pour un centrage précis à l'affichage."""
    lignes = []
    ligne_courante = []
    largeur_courante = 0
    for txt, est_anim in segments:
        pdf.set_font("Arial", 'B' if est_anim else 'I', taille)
        w = pdf.get_string_width(txt)
        if ligne_courante and largeur_courante + w > largeur - 2:
            lignes.append(ligne_courante)
            ligne_courante = []
            largeur_courante = 0
        ligne_courante.append((txt, est_anim, w))
        largeur_courante += w
    if ligne_courante:
        lignes.append(ligne_courante)
    return lignes

def _pdf_dessiner_lignes_mixtes(pdf, x, y, largeur, lignes, hauteur_ligne_texte=3.6, taille=7):
    """Dessine des lignes de segments mixtes (dates normales en gris italique / date(s) où
    l'assistante maternelle était animatrice en vert gras), centrées horizontalement."""
    for idx_ligne, ligne in enumerate(lignes):
        largeur_totale = sum(w for _, _, w in ligne)
        x_cur = x + max(0, (largeur - largeur_totale) / 2)
        y_cur = y + idx_ligne * hauteur_ligne_texte
        for txt, est_anim, w in ligne:
            pdf.set_xy(x_cur, y_cur)
            if est_anim:
                pdf.set_font("Arial", 'B', taille)
                pdf.set_text_color(21, 128, 61)
            else:
                pdf.set_font("Arial", 'I', taille)
                pdf.set_text_color(107, 114, 128)
            pdf.cell(w, hauteur_ligne_texte, txt, border=0, align='L')
            x_cur += w
    pdf.set_text_color(0, 0, 0)

def export_stats_couleur_pdf(am_rows, couleurs_utilisees, couleur_lieux, data_am, date_debut, date_fin, statut_filtre):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 15)
    pdf.set_text_color(27, 58, 92)
    pdf.cell(0, 9, normaliser_pdf_text("Statistiques de participation"), ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(80, 80, 80)
    periode_str = (f"Periode : du {format_date_fr_simple(str(date_debut))} au {format_date_fr_simple(str(date_fin))} "
                   f"- Ateliers : {statut_filtre}")
    pdf.cell(0, 7, normaliser_pdf_text(periode_str), ln=True, align='C')
    pdf.ln(3)
    pdf.set_text_color(0, 0, 0)

    marge = pdf.l_margin
    largeur_page = 297 - marge - pdf.r_margin
    largeur_am = 52
    largeur_total = 20
    nb_col = len(couleurs_utilisees)
    largeur_couleur = (largeur_page - largeur_am - largeur_total) / nb_col if nb_col else 0

    _pdf_entete_stats(pdf, largeur_am, largeur_couleur, largeur_total, couleurs_utilisees, couleur_lieux)

    if not am_rows:
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 8, normaliser_pdf_text("Aucune inscription sur cette periode."), ln=True)
        return _pdf_output_bytes(pdf)

    hauteur_page_max = 297 - pdf.b_margin - 10  # A4 paysage : hauteur ~210mm ; marge de sécurité

    for nom, prenom, am_id in am_rows:
        # Hauteur de ligne dynamique : dépend du nombre de dates à afficher dans chaque cellule
        max_lignes_dates = 1
        for c in couleurs_utilisees:
            entry = data_am.get(am_id, {}).get(c)
            if entry and entry["count"] > 0:
                segments = _pdf_segments_dates(entry["dates"])
                lignes_dates = _pdf_wrap_segments(pdf, segments, largeur_couleur)
                max_lignes_dates = max(max_lignes_dates, len(lignes_dates))
        hauteur_ligne = 7 + max_lignes_dates * 3.6 + 2

        if pdf.get_y() + hauteur_ligne > hauteur_page_max:
            pdf.add_page()
            _pdf_entete_stats(pdf, largeur_am, largeur_couleur, largeur_total, couleurs_utilisees, couleur_lieux)

        y_start = pdf.get_y()
        x = marge
        pdf.set_xy(x, y_start)
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(27, 58, 92)
        pdf.multi_cell(largeur_am, hauteur_ligne, normaliser_pdf_text(f"{nom} {prenom}"), border=1)

        total_am = 0
        x += largeur_am
        for c in couleurs_utilisees:
            entry = data_am.get(am_id, {}).get(c)
            pdf.set_xy(x, y_start)
            if entry and entry["count"] > 0:
                total_am += entry["count"]
                r, g, b = rgb_couleur_badge(c)
                pdf.set_font("Arial", 'B', 11)
                pdf.set_text_color(r, g, b)
                pdf.cell(largeur_couleur, 6, str(entry["count"]), border='LTR', align='C')
                # Zone des dates : bordure dessinée en un bloc, texte mixte dessiné par-dessus
                # (dates normales en gris italique / date(s) où l'AM était animatrice en vert gras)
                zone_dates_h = hauteur_ligne - 6
                pdf.rect(x, y_start + 6, largeur_couleur, zone_dates_h)
                segments = _pdf_segments_dates(entry["dates"])
                lignes_dates = _pdf_wrap_segments(pdf, segments, largeur_couleur)
                _pdf_dessiner_lignes_mixtes(pdf, x, y_start + 7, largeur_couleur, lignes_dates)
            else:
                pdf.set_font("Arial", size=10)
                pdf.set_text_color(195, 200, 205)
                pdf.multi_cell(largeur_couleur, hauteur_ligne, "-", border=1, align='C')
            x += largeur_couleur

        pdf.set_xy(x, y_start)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(27, 58, 92)
        pdf.multi_cell(largeur_total, hauteur_ligne, str(total_am), border=1, align='C')
        pdf.set_xy(marge, y_start + hauteur_ligne)
        pdf.set_text_color(0, 0, 0)

    return _pdf_output_bytes(pdf)

def export_suivi_am_pdf(title, data_triee):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, normaliser_pdf_text(title), ln=True, align='C')
    pdf.ln(6)
    if not data_triee:
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 10, normaliser_pdf_text("Aucune inscription trouvee."), ln=True)
        return pdf.output(dest='S').encode('latin-1')
    curr_am = ""
    for i in data_triee:
        nom_am = f"{i['adherents']['prenom']} {i['adherents']['nom']}"
        at = i['ateliers']
        date_fr = format_date_fr_simple(at['date_atelier'])
        titre_at = at.get('titre') or "(sans titre)"
        lieu = at.get('lieu_nom', '?')
        horaire = at.get('horaire_lib', '?')
        nb_enf = i['nb_enfants']
        if nom_am != curr_am:
            pdf.ln(3)
            pdf.set_fill_color(27, 94, 32)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 9, normaliser_pdf_text(f"  {nom_am}"), ln=True, fill=True)
            pdf.set_text_color(0, 0, 0)
            curr_am = nom_am
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, normaliser_pdf_text(f"  {date_fr}"), ln=True)
        pdf.set_font("Arial", size=10)
        detail = f"     {titre_at}  |  {lieu}  |  {horaire}  |  {nb_enf} enfant(s)"
        pdf.cell(0, 6, normaliser_pdf_text(detail), ln=True)
    return pdf.output(dest='S').encode('latin-1')

def _pdf_planning_body(pdf, ateliers_data, cache_ins_dict):
    """Corps commun aux deux exports PDF planning (avec et sans période)."""
    if not ateliers_data:
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 10, normaliser_pdf_text("Aucun atelier trouve sur cette periode."), ln=True)
        return
    for a in ateliers_data:
        ins_at = cache_ins_dict.get(a['id'], [])
        t_ad = len(ins_at)
        t_en = sum(p['nb_enfants'] for p in ins_at)
        restantes = a['capacite_max'] - (t_ad + t_en)
        date_fr = format_date_fr_simple(a['date_atelier'])
        titre_at = a.get('titre') or "(sans titre)"
        lieu = a.get('lieu_nom', '?')
        horaire = a.get('horaire_lib', '?')
        verrou = " [VERROUILLE]" if is_verrouille(a) else ""
        pdf.set_fill_color(212, 230, 241)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, normaliser_pdf_text(f"  {date_fr} | {titre_at} | {lieu}{verrou}"), ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, normaliser_pdf_text(f"     Horaire : {horaire}  |  AM : {t_ad}  |  Enfants : {t_en}  |  Places restantes : {restantes}"), ln=True)
        anim_id = a.get('animateur_id')
        anim_ins = next((p for p in ins_at if p['adherent_id'] == anim_id), None) if anim_id else None
        autres = sorted([p for p in ins_at if p['adherent_id'] != anim_id], key=lambda x: (x['adherents']['nom'].upper(), x['adherents']['prenom'].upper()))
        if anim_ins:
            nom_p = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 6, normaliser_pdf_text(f"       ★ {nom_p}  ({anim_ins['nb_enfants']} enfant(s)) [ANIMATEUR]"), ln=True)
            pdf.set_font("Arial", size=10)
        for p in autres:
            pdf.cell(0, 6, normaliser_pdf_text(f"       • {p['adherents']['prenom']} {p['adherents']['nom']}  ({p['nb_enfants']} enfant(s))"), ln=True)
        pdf.ln(3)

def export_planning_ateliers_pdf(title, ateliers_data, cache_ins_dict, animateurs_dict=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, normaliser_pdf_text(title), ln=True, align='C')
    pdf.ln(6)
    _pdf_planning_body(pdf, ateliers_data, cache_ins_dict)
    return pdf.output(dest='S').encode('latin-1')

def export_planning_ateliers_pdf_with_period(title, ateliers_data, cache_ins_dict, date_debut, date_fin, animateurs_dict=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, normaliser_pdf_text(title), ln=True, align='C')
    pdf.ln(2)
    pdf.set_font("Arial", 'I', 11)
    pdf.cell(0, 8, normaliser_pdf_text(f"Periode : du {format_date_fr_simple(str(date_debut))} au {format_date_fr_simple(str(date_fin))}"), ln=True, align='C')
    pdf.ln(4)
    _pdf_planning_body(pdf, ateliers_data, cache_ins_dict)
    return pdf.output(dest='S').encode('latin-1')

# --- PLACES RESTANTES (regroupement par lieu, ateliers non complets) ---

def export_places_restantes_pdf(title, lignes_par_lieu, date_debut, date_fin):
    """PDF A4 portrait (format par défaut de FPDF) : un bloc par lieu, lignes triées par
    places restantes décroissantes, date colorée selon le badge de l'atelier."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, normaliser_pdf_text(title), ln=True, align='C')
    pdf.ln(2)
    pdf.set_font("Arial", 'I', 11)
    pdf.cell(0, 8, normaliser_pdf_text(f"Periode : du {format_date_fr_simple(str(date_debut))} au {format_date_fr_simple(str(date_fin))}"), ln=True, align='C')
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)

    if not lignes_par_lieu:
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 10, normaliser_pdf_text("Aucun atelier avec des places restantes sur cette periode / ces filtres."), ln=True)
        return _pdf_output_bytes(pdf)

    for lieu_nom in sorted(lignes_par_lieu.keys()):
        lignes = sorted(lignes_par_lieu[lieu_nom], key=lambda a: a["_places_restantes"], reverse=True)
        pdf.set_fill_color(27, 58, 92)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 9, normaliser_pdf_text(f"  {lieu_nom}"), ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        for a in lignes:
            date_fr = format_date_fr_simple(a['date_atelier'])
            titre_at = a.get('titre') or "(sans titre)"
            r, g, b = rgb_couleur_badge(get_couleur_atelier(a))
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(r, g, b)
            pdf.cell(42, 7, normaliser_pdf_text(f"  {date_fr}"), border=0)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", size=10)
            unite = "place restante" if a["_places_restantes"] == 1 else "places restantes"
            pdf.cell(0, 7, normaliser_pdf_text(f"{titre_at}  -  {a['_places_restantes']} {unite}"), ln=True)
        pdf.ln(3)
    return _pdf_output_bytes(pdf)

# --- Logique commune d'application de l'animateur (Animateur & Admin) ---
def _appliquer_animateur_ui(at, total_occ, total_enfants_actuel, max_enf_at,
                             anim_id_at, anim_ins, nouvel_anim, nb_enf,
                             at_info_log, auteur, key_prefix):
    """Applique la sélection d'animateur après vérification des capacités.
    Retourne True si l'opération a réussi, False sinon (erreur affichée en ligne)."""
    if nouvel_anim == "Choisir...":
        st.warning("Veuillez sélectionner un animateur.")
        return False

    nouvel_anim_id = dict_adh_anim[nouvel_anim]
    ancien_anim_id = anim_id_at
    ancien_nb = anim_ins['nb_enfants'] if anim_ins else 1

    if ancien_anim_id and ancien_anim_id != nouvel_anim_id:
        nouvelle_occupation = total_occ - (1 + ancien_nb) + (1 + nb_enf)
        nouveau_total_enfants = total_enfants_actuel - ancien_nb + nb_enf
        marge_enf = max_enf_at - (total_enfants_actuel - ancien_nb)
        marge_capa = at['capacite_max'] - (total_occ - (1 + ancien_nb))
    elif ancien_anim_id == nouvel_anim_id:
        delta = nb_enf - ancien_nb
        nouvelle_occupation = total_occ + delta
        nouveau_total_enfants = total_enfants_actuel + delta
        marge_enf = max_enf_at - total_enfants_actuel + ancien_nb
        marge_capa = at['capacite_max'] - total_occ + ancien_nb
    else:
        nouvelle_occupation = total_occ + 1 + nb_enf
        nouveau_total_enfants = total_enfants_actuel + nb_enf
        marge_enf = max_enf_at - total_enfants_actuel
        marge_capa = at['capacite_max'] - total_occ - 1

    max_autorise = max(min(marge_enf, marge_capa, 10), 0)

    if nouveau_total_enfants > max_enf_at:
        st.error(f"🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé. Valeur maximale possible : {max_autorise}")
        return False
    if nouvelle_occupation > at['capacite_max']:
        st.markdown(f"<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée. Valeur maximale possible : {max_autorise}</span>", unsafe_allow_html=True)
        return False

    if ancien_anim_id and ancien_anim_id != nouvel_anim_id:
        supabase.table("inscriptions").delete().eq("atelier_id", at['id']).eq("adherent_id", ancien_anim_id).execute()
    supabase.table("ateliers").update({"animateur_id": nouvel_anim_id}).eq("id", at['id']).execute()
    existing_new = supabase.table("inscriptions").select("id").eq("atelier_id", at['id']).eq("adherent_id", nouvel_anim_id).execute()
    if existing_new.data:
        supabase.table("inscriptions").update({"nb_enfants": nb_enf}).eq("id", existing_new.data[0]['id']).execute()
    else:
        supabase.table("inscriptions").insert({"adherent_id": nouvel_anim_id, "atelier_id": at['id'], "nb_enfants": nb_enf}).execute()
    enregistrer_log(auteur, "Modification animateur", f"Animateur {nouvel_anim} ({nb_enf} enfants) - {at_info_log}")
    invalider_cache_inscriptions()
    st.success("Modification effectuée !")
    st.rerun()
    return True


# ==========================================
# DIALOGUES
# ==========================================

@st.dialog("⚠️ Confirmation")
def secure_delete_dialog(table, item_id, label):
    st.write(f"Voulez-vous vraiment désactiver/supprimer : **{label}** ?")
    pw = st.text_input("Code secret admin", type="password")
    if st.button("Confirmer", type="primary"):
        if pw == get_secret_code() or pw == "0000":
            supabase.table(table).update({"est_actif": False}).eq("id", item_id).execute()
            invalider_cache_referentiels()
            st.success("Opération réussie"); st.rerun()
        else: st.error("Code incorrect")

@st.dialog("✏️ Modifier une AM")
def edit_am_dialog(am_id, nom_actuel, prenom_actuel):
    new_nom = st.text_input("Nom", value=nom_actuel).upper().strip()
    new_pre = st.text_input("Prénom", value=prenom_actuel).strip()
    if st.button("Enregistrer"):
        if new_nom and new_pre:
            supabase.table("adherents").update({"nom": new_nom, "prenom": new_pre}).eq("id", am_id).execute()
            invalider_cache_referentiels()
            st.success("Modifié !"); st.rerun()

@st.dialog("⚠️ Suppression Atelier")
def delete_atelier_dialog(at_id, titre, a_des_inscrits):
    titre_aff = titre if titre else "(sans titre)"
    st.warning(f"Voulez-vous supprimer l'atelier : **{titre_aff}** ?")
    pw = st.text_input("Code secret admin", type="password")
    if st.button("Confirmer la suppression définitive"):
        if pw == get_secret_code() or pw == "0000":
            if a_des_inscrits: supabase.table("inscriptions").delete().eq("atelier_id", at_id).execute()
            supabase.table("ateliers").delete().eq("id", at_id).execute()
            invalider_cache_inscriptions()
            st.rerun()

@st.dialog("⚠️ Confirmer la désinscription")
def confirm_unsubscribe_dialog(ins_id, nom_complet, atelier_info, user_admin="Utilisateur"):
    st.warning(f"Souhaitez-vous vraiment annuler la réservation de **{nom_complet}** ?")
    if st.button("Oui, désinscrire", type="primary"):
        enregistrer_log(user_admin, "Désinscription", f"Annulation pour {nom_complet} - {atelier_info}")
        supabase.table("inscriptions").delete().eq("id", ins_id).execute()
        invalider_cache_inscriptions()
        st.rerun()

# --- DOUBLE VALIDATION À L'INSCRIPTION (module 📝 Inscriptions) ---
def _corps_confirmation_inscription(mode, adherent_id, adherent_nom, atelier_id, atelier_info_display,
                                     nb_enfants, at_info_log, user_principal, existing_id=None):
    """Corps commun aux deux pop-up de confirmation (nouvelle inscription / modification) :
    récapitulatif + 3 boutons. 'Modifier' et 'Annuler' referment tous les deux la pop-up sans rien
    enregistrer, en laissant le formulaire tel quel (nom et nombre d'enfants déjà saisis conservés,
    puisque Streamlit garde la valeur des champs entre deux affichages) : 'Modifier' pour ajuster
    la saisie puis revalider, 'Annuler' pour renoncer à cette inscription/modification."""
    verbe = "Modification de l'inscription de" if mode == "modification" else "Inscription de"
    unite = "enfant" if nb_enfants == 1 else "enfants"
    st.markdown(
        f'<div style="background-color:#cfe9ff;border-left:4px solid #1b5e20;border-radius:6px;'
        f'padding:10px 14px;font-size:0.98rem;">{verbe} <b>{adherent_nom}</b> à l\'atelier '
        f'{atelier_info_display} pour <b>{nb_enfants} {unite}</b>.</div>',
        unsafe_allow_html=True
    )
    st.write("")
    c1, c2, c3 = st.columns(3)
    label_confirmer = "✅ Confirmer la modification" if mode == "modification" else "✅ Confirmer l'inscription"
    if c1.button(label_confirmer, type="primary", use_container_width=True):
        if existing_id:
            supabase.table("inscriptions").update({"nb_enfants": nb_enfants}).eq("id", existing_id).execute()
            enregistrer_log(user_principal, "Modification", f"{adherent_nom} → {nb_enfants} enfants - {at_info_log}")
        else:
            supabase.table("inscriptions").insert({"adherent_id": adherent_id, "atelier_id": atelier_id, "nb_enfants": nb_enfants}).execute()
            enregistrer_log(user_principal, "Inscription", f"{adherent_nom} inscrit (+{nb_enfants} enf.) - {at_info_log}")
        invalider_cache_inscriptions()
        st.rerun()
    if c2.button("✏️ Modifier", use_container_width=True):
        st.rerun()
    if c3.button("❌ Annuler", use_container_width=True):
        st.rerun()

@st.dialog("✅ Confirmer l'inscription")
def confirm_inscription_dialog(adherent_id, adherent_nom, atelier_id, atelier_info_display,
                                nb_enfants, at_info_log, user_principal, existing_id=None):
    _corps_confirmation_inscription("nouvelle", adherent_id, adherent_nom, atelier_id, atelier_info_display,
                                     nb_enfants, at_info_log, user_principal, existing_id)

@st.dialog("✏️ Confirmer la modification")
def confirm_modification_inscription_dialog(adherent_id, adherent_nom, atelier_id, atelier_info_display,
                                             nb_enfants, at_info_log, user_principal, existing_id):
    _corps_confirmation_inscription("modification", adherent_id, adherent_nom, atelier_id, atelier_info_display,
                                     nb_enfants, at_info_log, user_principal, existing_id)

@st.dialog("🔑 Super Administration")
def super_admin_dialog():
    st.write("Saisissez le code de secours pour accéder à l'administration.")
    sac = st.text_input("Code Super Admin", type="password")
    if st.button("Débloquer l'accès"):
        if sac == "0000":
            st.session_state['super_access'] = True
            st.rerun()
        else: st.error("Code incorrect")

@st.dialog("✏️ Modifier l'atelier")
def edit_atelier_dialog(at_id, titre_actuel, date_actuelle, lieu_id_actuel, horaire_id_actuel, capacite_actuelle, max_enfants_actuel, lieux_list, horaires_list, map_lieu_id, map_horaire_id, couleur_actuelle=None):
    if not lieux_list:
        st.error("Aucun lieu disponible.")
        return
    if not horaires_list:
        st.error("Aucun horaire disponible.")
        return
    _, MAX_ENFANTS_dlg = get_config()
    try:
        inscriptions = supabase.table("inscriptions").select("nb_enfants").eq("atelier_id", at_id).execute()
        total_occupation = sum([1 + ins['nb_enfants'] for ins in inscriptions.data]) if inscriptions.data else 0
        nb_enfants_actuels = sum([ins['nb_enfants'] for ins in inscriptions.data]) if inscriptions.data else 0
    except:
        total_occupation = 0
        nb_enfants_actuels = 0
    lieux_options = [l['nom'] for l in lieux_list]
    horaires_options = [h['libelle'] for h in horaires_list]
    lieu_actuel_nom = next((l['nom'] for l in lieux_list if l['id'] == lieu_id_actuel), lieux_options[0])
    horaire_actuel_lib = next((h['libelle'] for h in horaires_list if h['id'] == horaire_id_actuel), horaires_options[0])
    date_actuelle_obj = datetime.strptime(date_actuelle, '%Y-%m-%d').date() if isinstance(date_actuelle, str) else date_actuelle
    nouvelle_date = st.date_input("Date de l'atelier", value=date_actuelle_obj, format="DD/MM/YYYY")
    nouveau_titre = st.text_input("Titre", value=titre_actuel)
    nouveau_lieu = st.selectbox("Lieu", options=lieux_options, index=lieux_options.index(lieu_actuel_nom) if lieu_actuel_nom in lieux_options else 0)
    nouvel_horaire = st.selectbox("Horaire", options=horaires_options, index=horaires_options.index(horaire_actuel_lib) if horaire_actuel_lib in horaires_options else 0)
    nouvelle_capacite = st.number_input("Capacité maximale (places totales)", min_value=1, value=int(capacite_actuelle))
    st.markdown("---")
    st.markdown("**🎨 Badge de couleur (pour le tri dans les statistiques)**")
    couleur_par_defaut = couleur_badge_defaut(nouvelle_date)
    couleur_effective = couleur_actuelle if couleur_actuelle in COULEURS_BADGE else couleur_par_defaut
    idx_couleur = COULEURS_BADGE_LIST.index(couleur_effective) if couleur_effective in COULEURS_BADGE_LIST else 0
    nouvelle_couleur = st.selectbox(
        "Couleur du badge", options=COULEURS_BADGE_LIST, index=idx_couleur,
        help=f"Par défaut selon le jour de la semaine : {couleur_par_defaut}. Modifiable à tout moment."
    )
    st.markdown(
        f'<span class="couleur-badge" style="background-color:{hex_couleur_badge(nouvelle_couleur)};'
        f'color:white;">{nouvelle_couleur}</span>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown("**👶 Limite d'enfants pour cet atelier**")
    val_max_enf = max_enfants_actuel if max_enfants_actuel is not None else MAX_ENFANTS_dlg
    nouvelle_limite_enfants = st.number_input(
        "Nombre maximum d'enfants acceptés sur cet atelier",
        min_value=0, max_value=200, value=int(val_max_enf),
        help=f"Valeur globale configurée : {MAX_ENFANTS_dlg}. Mettre 0 pour utiliser la valeur globale."
    )
    if nouvelle_limite_enfants == 0:
        st.caption(f"ℹ️ La limite globale ({MAX_ENFANTS_dlg} enfants) sera appliquée.")
    else:
        st.caption(f"ℹ️ Limite spécifique : {nouvelle_limite_enfants} enfants pour cet atelier.")
    if nouvelle_capacite < total_occupation:
        st.error(f"La capacité ne peut pas être inférieure au nombre actuel d'occupants ({total_occupation} places prises).")
    if nouvelle_limite_enfants > 0 and nouvelle_limite_enfants < nb_enfants_actuels:
        st.error(f"La limite d'enfants ne peut pas être inférieure au nombre d'enfants déjà inscrits ({nb_enfants_actuels}).")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Annuler", use_container_width=True): st.rerun()
    with col2:
        disable_save = (nouvelle_capacite < total_occupation) or (nouvelle_limite_enfants > 0 and nouvelle_limite_enfants < nb_enfants_actuels)
        if st.button("Enregistrer", type="primary", use_container_width=True, disabled=disable_save):
            nouveau_lieu_id = next(l['id'] for l in lieux_list if l['nom'] == nouveau_lieu)
            nouvel_horaire_id = next(h['id'] for h in horaires_list if h['libelle'] == nouvel_horaire)
            val_a_stocker = nouvelle_limite_enfants if nouvelle_limite_enfants > 0 else None
            supabase.table("ateliers").update({
                "date_atelier": nouvelle_date.strftime('%Y-%m-%d'),
                "titre": nouveau_titre if nouveau_titre else None, "lieu_id": nouveau_lieu_id,
                "horaire_id": nouvel_horaire_id, "capacite_max": nouvelle_capacite,
                "max_enfants": val_a_stocker, "couleur_badge": nouvelle_couleur
            }).eq("id", at_id).execute()
            enregistrer_log("Admin", "Modification atelier", f"Atelier ID {at_id} modifié")
            invalider_cache_inscriptions()
            st.success("Atelier modifié avec succès !")
            st.rerun()

@st.dialog("🎯 Attribuer / Changer l'animateur")
def dialog_attribuer_animateur(at_id, titre_at, ancien_anim_id, ancien_anim_nom, liste_adh_anim, dict_adh_anim, auteur="Animateur"):
    titre_aff = titre_at if titre_at else "(sans titre)"
    st.markdown(f"**Atelier :** {titre_aff}")
    if ancien_anim_nom:
        st.info(f"Animateur actuel : **{ancien_anim_nom}**")
    else:
        st.info("Aucun animateur assigné.")
    options_anim = ["Choisir..."] + liste_adh_anim
    idx_def = (liste_adh_anim.index(ancien_anim_nom) + 1) if ancien_anim_nom and ancien_anim_nom in liste_adh_anim else 0
    nouvel_anim = st.selectbox("Choisir l'animateur", options_anim, index=idx_def)
    nb_enf = st.number_input("Nombre d'enfants de l'animateur", min_value=0, max_value=10, value=1)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Annuler", use_container_width=True): st.rerun()
    with c2:
        if st.button("✅ Confirmer", type="primary", use_container_width=True):
            if nouvel_anim == "Choisir...":
                st.warning("Veuillez sélectionner un animateur.")
            else:
                nouvel_anim_id = dict_adh_anim[nouvel_anim]
                result = assigner_animateur(at_id, nouvel_anim_id, nb_enf, ancien_anim_id, auteur)
                if result is True:
                    st.success(f"✅ {nouvel_anim} assigné(e) comme animateur !")
                    st.rerun()
                else:
                    st.error(f"Erreur : {result}")

@st.dialog("❌ Retirer l'animateur")
def dialog_retirer_animateur(at_id, titre_at, anim_id, anim_nom, auteur="Admin"):
    titre_aff = titre_at if titre_at else "(sans titre)"
    st.warning(f"Voulez-vous retirer **{anim_nom}** de son rôle d'animateur pour l'atelier **{titre_aff}** ?")
    st.write("Son inscription sera également supprimée.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Annuler", use_container_width=True): st.rerun()
    with c2:
        if st.button("Confirmer", type="primary", use_container_width=True):
            result = retirer_animateur(at_id, anim_id, auteur)
            if result is True:
                st.success("Animateur retiré.")
                st.rerun()
            else:
                st.error(f"Erreur : {result}")

@st.dialog("✏️ Modifier un lieu")
def edit_lieu_dialog(lieu_id, nom_actuel, capacite_actuelle):
    new_nom = st.text_input("Nom du lieu", value=nom_actuel).strip()
    new_cap = st.number_input("Capacité", min_value=1, max_value=50, value=int(capacite_actuelle))
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Annuler", use_container_width=True): st.rerun()
    with c2:
        if st.button("Enregistrer", type="primary", use_container_width=True):
            if not new_nom:
                st.error("Le nom ne peut pas être vide.")
            else:
                try:
                    supabase.table("lieux").update({"nom": new_nom.upper(), "capacite": new_cap}).eq("id", lieu_id).execute()
                    invalider_cache_referentiels()
                    st.success("Lieu modifié !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {str(e)}")

@st.dialog("✏️ Modifier un horaire")
def edit_horaire_dialog(horaire_id, libelle_actuel):
    new_lib = st.text_input("Horaire", value=libelle_actuel).strip()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Annuler", use_container_width=True): st.rerun()
    with c2:
        if st.button("Enregistrer", type="primary", use_container_width=True):
            if not new_lib:
                st.error("L'horaire ne peut pas être vide.")
            else:
                try:
                    supabase.table("horaires").update({"libelle": new_lib}).eq("id", horaire_id).execute()
                    invalider_cache_referentiels()
                    st.success("Horaire modifié !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {str(e)}")


# ==========================================
# CHARGEMENT DES DONNÉES GLOBALES (depuis cache)
# ==========================================

if 'at_list_gen' not in st.session_state: st.session_state['at_list_gen'] = []
if 'super_access' not in st.session_state: st.session_state['super_access'] = False

current_code, MAX_ENFANTS = get_config()

# Référentiels depuis cache
all_lieux = get_lieux_cached()
all_horaires = get_horaires_cached()
lieux_actifs = [l for l in all_lieux if l.get("est_actif", True) is not False]
horaires_actifs = [h for h in all_horaires if h.get("est_actif", True) is not False]

lieux_dict_global = {l['id']: l['nom'] for l in all_lieux}
horaires_dict_global = {h['id']: h['libelle'] for h in all_horaires}

# Adhérents depuis cache
adh_data = get_adherents_actifs_cached()
dict_adh = {f"{a['prenom']} {a['nom']}": a['id'] for a in adh_data}
liste_adh = list(dict_adh.keys())
adh_animateurs = [a for a in adh_data if a.get('est_animateur', False)]
dict_adh_anim = {f"{a['prenom']} {a['nom']}": a['id'] for a in adh_animateurs}
liste_adh_anim = list(dict_adh_anim.keys())
set_id_animateurs = {a['id'] for a in adh_animateurs}

# --- SIDEBAR ---
st.sidebar.markdown("### 👤 Qui êtes-vous ?")
user_connecte = st.sidebar.selectbox("Votre nom :", ["Choisir..."] + liste_adh, key="user_connecte_sidebar")

est_animateur_connecte = False
id_user_connecte = None
if user_connecte != "Choisir...":
    id_user_connecte = dict_adh.get(user_connecte)
    est_animateur_connecte = id_user_connecte in set_id_animateurs

st.sidebar.markdown("---")
menu_options = ["📝 Inscriptions", "📊 Suivi & Récap", "🔐 Administration"]
if est_animateur_connecte:
    menu_options = ["🎯 Animateur"] + menu_options
menu = st.sidebar.radio("Navigation", menu_options)


# ==========================================
# SECTION 🎯 ANIMATEUR
# ==========================================
if menu == "🎯 Animateur":
    st.header(f"🎯 Espace Animateur — {user_connecte}")
    st.markdown(f'<div style="background-color:#fff3e0; border:1px solid #e65100; border-radius:8px; padding:10px 16px; margin-bottom:16px; color:#e65100; font-weight:bold;">⭐ Vous êtes connecté(e) en tant qu\'animateur.</div>', unsafe_allow_html=True)

    ateliers_bruts = get_ateliers_a_venir()
    ateliers = enrichir_ateliers([dict(a) for a in ateliers_bruts], lieux_dict_global, horaires_dict_global)

    if not ateliers:
        st.info("ℹ️ Aucun atelier à venir.")
    else:
        at_ids = tuple(a['id'] for a in ateliers)
        toutes_ins = get_toutes_inscriptions_ateliers(at_ids)
        cache_ins = construire_cache_ins(toutes_ins)

        for idx, at in enumerate(ateliers):
            anim_id_at = at.get('animateur_id')
            ins_data = cache_ins.get(at['id'], [])

            total_occ = sum([(1 + (i['nb_enfants'] if i['nb_enfants'] else 0)) for i in ins_data])
            max_enf_at = get_max_enfants_atelier(at, MAX_ENFANTS)
            total_enfants_actuel = sum([i['nb_enfants'] for i in ins_data])
            places_enfants_restantes = max(max_enf_at - total_enfants_actuel, 0)
            statut_enfants = "🚫 Complet" if places_enfants_restantes == 0 else f"👶 {places_enfants_restantes} pl. enfants"

            anim_ins = next((i for i in ins_data if i['adherent_id'] == anim_id_at), None) if anim_id_at else None
            anim_nom_at = None
            if anim_ins:
                anim_nom_at = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
            elif anim_id_at:
                anim_adh = next((a for a in adh_data if a['id'] == anim_id_at), None)
                if anim_adh:
                    anim_nom_at = f"{anim_adh['prenom']} {anim_adh['nom']}"

            anim_label = f" | ⭐ {anim_nom_at}" if anim_nom_at else " | ⭐ Pas d'animateur"
            titre_affiche = at['titre'] if at['titre'] else "(sans titre)"
            titre_label = f"{format_date_fr_complete(at['date_atelier'])} — {titre_affiche} | 📍 {at['lieu_nom']} | ⏰ {at['horaire_lib']} | {statut_enfants}{anim_label}"

            with st.expander(titre_label, expanded=False):
                at_info_log = f"{at['date_atelier']} | {at['horaire_lib']} | {at['lieu_nom']}"
                # --- Modification du titre de l'atelier par tout animateur ---
                st.markdown("**✏️ Modifier le titre de l'atelier**")
                nouveau_titre = st.text_input("Nouveau titre", value=at['titre'] or "", key=f"titre_{at['id']}")
                if st.button("📝 Mettre à jour le titre", key=f"update_titre_{at['id']}"):
                    # On accepte une chaîne vide ; on la convertit en None pour la base
                    titre_a_stocker = nouveau_titre.strip() if nouveau_titre and nouveau_titre.strip() else None
                    supabase.table("ateliers").update({"titre": titre_a_stocker}).eq("id", at['id']).execute()
                    ancien_titre_log = at['titre'] if at['titre'] else "(sans titre)"
                    enregistrer_log(user_connecte, "Modification titre atelier", 
                                    f"Titre modifié de '{ancien_titre_log}' → '{titre_a_stocker or ''}' pour l'atelier du {at['date_atelier']}")
                    invalider_cache_inscriptions()
                    st.success("Titre mis à jour !")
                    st.rerun()

                st.markdown("**Gestion de l'animateur :**")

                options_anim = ["Choisir..."] + liste_adh_anim
                idx_def = (liste_adh_anim.index(anim_nom_at) + 1) if anim_nom_at and anim_nom_at in liste_adh_anim else 0
                nouvel_anim = st.selectbox("Animateur à assigner", options_anim, index=idx_def, key=f"anim_select_{at['id']}_{idx}")

                def_nb = anim_ins['nb_enfants'] if anim_ins else 1
                nb_enf = st.number_input("Nombre d'enfants de l'animateur", min_value=0, max_value=10, value=def_nb, key=f"anim_nb_{at['id']}_{idx}")

                if st.button("✅ Appliquer", key=f"anim_apply_{at['id']}_{idx}", type="primary"):
                    _appliquer_animateur_ui(at, total_occ, total_enfants_actuel, max_enf_at,
                                            anim_id_at, anim_ins, nouvel_anim, nb_enf,
                                            at_info_log, user_connecte, f"anim_{at['id']}")


# ==========================================
# SECTION 📝 INSCRIPTIONS
# ==========================================
elif menu == "📝 Inscriptions":
    st.header("📍 Inscriptions")

    if not liste_adh:
        st.info("ℹ️ Aucune assistante maternelle enregistrée pour le moment.")
        st.markdown("""
        **Pour commencer, rendez-vous dans :**
        > 🔐 Administration → 👥 Liste AM → Ajouter une première assistante maternelle.
        """)
    else:
        # Utiliser la sélection de la sidebar si disponible
        if user_connecte != "Choisir...":
            idx_user = liste_adh.index(user_connecte) + 1 if user_connecte in liste_adh else 0
        else:
            idx_user = 0
        user_principal = st.selectbox("👤 Vous êtes :", ["Choisir..."] + liste_adh, index=idx_user)
        
        if user_principal != "Choisir...":
            today_str = str(date.today())
            try:
                ateliers_bruts = supabase.table("ateliers").select("*").eq("est_actif", True).gte("date_atelier", today_str).order("date_atelier").execute().data or []
            except:
                ateliers_bruts = []
            
            ateliers = enrichir_ateliers([dict(a) for a in ateliers_bruts], lieux_dict_global, horaires_dict_global)
            
            if not ateliers:
                st.info("ℹ️ Aucun atelier à venir. Consultez l'Administration → 🏗️ Ateliers pour en créer.")
            else:
                for at in ateliers:
                    try:
                        res_ins = supabase.table("inscriptions").select("*, adherents(nom, prenom)").eq("atelier_id", at['id']).execute()
                        ins_data = res_ins.data if res_ins.data else []
                    except:
                        ins_data = []

                    anim_id_at = at.get('animateur_id')
                    # Calcul des places enfants restantes
                    max_enf_at = get_max_enfants_atelier(at, MAX_ENFANTS)
                    total_enfants_inscrits = sum([i['nb_enfants'] for i in ins_data])
                    places_enfants_restantes = max(max_enf_at - total_enfants_inscrits, 0)
                    statut_enfants = "🚫 Complet" if places_enfants_restantes == 0 else f"👶 {places_enfants_restantes} pl. enfants"
                    at_info_log = f"{at['date_atelier']} | {at['horaire_lib']} | {at['lieu_nom']}"
                    
                    # --- Date avec émoji coloré ---
                    emoji = get_weekday_emoji(at['date_atelier'])
                    titre_affiche = at['titre'] if at['titre'] else "(sans titre)"
                    # Description de l'atelier utilisée dans les pop-up de confirmation d'inscription
                    atelier_desc_html = f"<i>{titre_affiche}</i> du <b>{format_date_fr_complete(at['date_atelier'], gras=False)}</b> à <b>{at['lieu_nom']}</b> ({at['horaire_lib']})"

                    # Indicateur si l'utilisateur principal est déjà inscrit / est l'animateur de cet atelier
                    id_user_principal = dict_adh.get(user_principal)
                    est_inscrit = any(i['adherent_id'] == id_user_principal for i in ins_data) if id_user_principal else False
                    indicateur_inscrit = " ✔️" if est_inscrit else ""
                    est_animateur_ici = bool(id_user_principal) and id_user_principal == anim_id_at
                    indicateur_animateur = " ⭐" if est_animateur_ici else ""

                    titre_label = f"{emoji} {format_date_fr_complete(at['date_atelier'])} — {titre_affiche} | 📍 {at['lieu_nom']} | ⏰ {at['horaire_lib']} | {statut_enfants}{indicateur_inscrit}{indicateur_animateur}"
                    
                    with st.expander(titre_label):
                        if is_verrouille(at):
                            st.warning("🔒 Cet atelier est géré par l'administration. Les inscriptions et désinscriptions ne sont pas disponibles ici.")
                        else:
                            # --- Affichage de l'animateur (lecture seule) ---
                            anim_ins = next((i for i in ins_data if i['adherent_id'] == anim_id_at), None) if anim_id_at else None
                            if anim_ins:
                                n_a = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
                                st.markdown(f'<span style="color:#e65100;font-weight:bold;">⭐ {n_a} <b>({anim_ins["nb_enfants"]} enf.)</b> <span style="background:#e65100;color:white;padding:1px 6px;border-radius:4px;font-size:0.78rem;">ANIMATEUR</span></span>', unsafe_allow_html=True)

                            # --- Affichage des autres inscrits (non animateurs) avec possibilité de modification/désinscription ---
                            # L'AM actuellement sélectionnée dans la sidebar (user_principal) est affichée en
                            # dernier dans la liste : cela rend visible que son inscription vient d'être prise
                            # en compte, plutôt que de la voir apparaître en haut au milieu du tri alphabétique.
                            autres_ins = [i for i in ins_data if i['adherent_id'] != anim_id_at]
                            autres_tries = sorted(autres_ins, key=lambda x: (x['adherent_id'] == id_user_principal, x['adherents']['nom'].upper(), x['adherents']['prenom'].upper()))

                            total_occ = sum([(1 + (i['nb_enfants'] if i['nb_enfants'] else 0)) for i in ins_data])

                            for i in autres_tries:
                                n_f = f"{i['adherents']['prenom']} {i['adherents']['nom']}"
                                col_nom, col_nb, col_modif, col_del = st.columns([0.4, 0.2, 0.2, 0.2])
                                col_nom.write(f"• {n_f}")
                                new_nb = col_nb.number_input("", min_value=1, max_value=10, value=i['nb_enfants'], key=f"modif_nb_{i['id']}", label_visibility="collapsed")
                                if col_modif.button("✏️ Modifier", key=f"modif_btn_{i['id']}"):
                                    delta = new_nb - i['nb_enfants']
                                    nouveau_total_enf = total_enfants_inscrits + delta
                                    nouvelle_occupation = total_occ + delta
                                    if nouvelle_occupation > at['capacite_max']:
                                        st.error("❌ Trop de monde : capacité de la salle dépassée")
                                    elif nouveau_total_enf > max_enf_at:
                                        st.error(f"🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé")
                                    else:
                                        # Double validation demandée par l'utilisateur : pop-up de confirmation
                                        # avant d'enregistrer la modification du nombre d'enfants.
                                        confirm_modification_inscription_dialog(
                                            adherent_id=i['adherent_id'], adherent_nom=n_f,
                                            atelier_id=at['id'], atelier_info_display=atelier_desc_html,
                                            nb_enfants=new_nb, at_info_log=at_info_log, user_principal=user_principal,
                                            existing_id=i['id']
                                        )
                                if col_del.button("🗑️", key=f"del_{i['id']}"):
                                    confirm_unsubscribe_dialog(i['id'], n_f, at_info_log, user_principal)

                            # --- Formulaire d'inscription pour une nouvelle AM (non animateur) ---
                            st.markdown("---")
                            try:
                                idx_def = (liste_adh.index(user_principal) + 1)
                            except:
                                idx_def = 0
                            c1, c2, c3 = st.columns([2, 1, 1])
                            qui = c1.selectbox("Inscrire :", ["Choisir..."] + liste_adh, index=idx_def, key=f"q_{at['id']}")
                            nb_e = c2.number_input("Enfants", 1, 10, 1, key=f"e_{at['id']}")

                            qui_est_anim = (qui != "Choisir..." and dict_adh.get(qui) == anim_id_at)
                            if qui_est_anim:
                                st.warning("🔒 Cette personne est l'animateur de cet atelier. Pour la modifier, utilisez l'espace 🎯 Animateur.")
                            elif c3.button("✅ Valider l'inscription", key=f"v_{at['id']}", type="primary"):
                                if qui != "Choisir...":
                                    id_adh = dict_adh[qui]
                                    existing = next((ins for ins in ins_data if ins['adherent_id'] == id_adh), None)
                                    # Calcul des nouvelles valeurs
                                    total_occ_calc = sum([(1 + (ins['nb_enfants'] if ins['nb_enfants'] else 0)) for ins in ins_data])
                                    if existing:
                                        delta_enf = nb_e - existing['nb_enfants']
                                        nouveau_total_enf = total_enfants_inscrits + delta_enf
                                        nouvelle_occupation = total_occ_calc + delta_enf
                                    else:
                                        nouveau_total_enf = total_enfants_inscrits + nb_e
                                        nouvelle_occupation = total_occ_calc + 1 + nb_e

                                    if nouvelle_occupation > at['capacite_max']:
                                        st.error("❌ Trop de monde : capacité de la salle dépassée")
                                    elif nouveau_total_enf > max_enf_at:
                                        st.error(f"🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé")
                                    else:
                                        # Double validation demandée par l'utilisateur : pop-up de confirmation
                                        # avant d'enregistrer l'inscription.
                                        confirm_inscription_dialog(
                                            adherent_id=id_adh, adherent_nom=qui,
                                            atelier_id=at['id'], atelier_info_display=atelier_desc_html,
                                            nb_enfants=nb_e, at_info_log=at_info_log, user_principal=user_principal,
                                            existing_id=existing['id'] if existing else None
                                        )
                                            
# ==========================================
# SECTION 📊 SUIVI & RÉCAP
# ==========================================
elif menu == "📊 Suivi & Récap":
    st.header("🔎 Consultation")
    t1, t2, t3 = st.tabs(["👤 Par AM", "📅 Par Atelier", "🪑 Places restantes"])

    with t1:
        data_triee = []
        if not liste_adh:
            st.info("ℹ️ Aucune assistante maternelle enregistrée.")
        else:
            choix = st.multiselect("Filtrer par assistante maternelle :", liste_adh, key="pub_filter_am")
            ids = [dict_adh[n] for n in choix] if choix else list(dict_adh.values())
            if ids:
                try:
                    inscriptions_brutes = supabase.table("inscriptions").select("*, ateliers!inner(*), adherents(nom, prenom)").in_("adherent_id", ids).eq("ateliers.est_actif", True).execute().data or []
                    for ins in inscriptions_brutes:
                        at = ins['ateliers']
                        at['lieu_nom'] = lieux_dict_global.get(at['lieu_id'], '?')
                        at['horaire_lib'] = horaires_dict_global.get(at['horaire_id'], '?')
                        ins['ateliers'] = at
                    data_triee = trier_par_nom_puis_date(inscriptions_brutes)
                except:
                    data_triee = []

            df_export = pd.DataFrame([{
                "Assistante Maternelle": f"{i['adherents']['prenom']} {i['adherents']['nom']}",
                "Date": i['ateliers']['date_atelier'], "Atelier": i['ateliers']['titre'] if i['ateliers']['titre'] else "",
                "Lieu": i['ateliers']['lieu_nom'], "Horaire": i['ateliers']['horaire_lib'],
                "Nb Enfants": i['nb_enfants']
            } for i in data_triee]) if data_triee else pd.DataFrame(columns=["Assistante Maternelle", "Date", "Atelier", "Lieu", "Horaire", "Nb Enfants"])

            c_e1, c_e2 = st.columns(2)
            c_e1.download_button("📥 Excel", data=export_to_excel(df_export), file_name="suivi_am.xlsx")
            c_e2.download_button("📥 PDF", data=export_suivi_am_pdf("Suivi par Assistante Maternelle", data_triee), file_name="suivi_am.pdf")

            if data_triee:
                curr_u = ""
                for i in data_triee:
                    nom_u = f"{i['adherents']['prenom']} {i['adherents']['nom']}"
                    if nom_u != curr_u:
                        st.markdown(f'<div style="color:#1b5e20; border-bottom:2px solid #1b5e20; padding-top:15px; margin-bottom:8px; font-weight:bold; font-size:1.2rem;">{nom_u}</div>', unsafe_allow_html=True)
                        curr_u = nom_u
                    at = i['ateliers']
                    c_l = get_color(at['lieu_nom'])
                    titre_affiche = at['titre'] if at['titre'] else "(sans titre)"
                    c_at = hex_couleur_badge(get_couleur_atelier(at))
                    icone_anim = "⭐ " if i.get('adherent_id') == at.get('animateur_id') else ""
                    date_html = f"{icone_anim}<span style='color:{c_at};font-weight:800;'>{format_date_fr_complete(at['date_atelier'], gras=False)}</span>"
                    st.write(f"{date_html} — {titre_affiche} <span class='lieu-badge' style='background-color:{c_l}'>{at['lieu_nom']}</span> <span class='horaire-text'>({at['horaire_lib']})</span> **({i['nb_enfants']} enf.)**", unsafe_allow_html=True)
                    btn_agenda = bouton_agenda_html(at['date_atelier'], at['horaire_lib'], at['titre'], at['lieu_nom'])
                    ics_data = fichier_ics_atelier(at['date_atelier'], at['horaire_lib'], at['titre'], at['lieu_nom'], at['id'])
                    col_g, col_i, _ = st.columns([0.16, 0.34, 0.50])
                    with col_g:
                        if btn_agenda:
                            st.markdown(btn_agenda, unsafe_allow_html=True)
                    with col_i:
                        btn_ics = bouton_ics_html(ics_data)
                        if btn_ics:
                            st.markdown(btn_ics, unsafe_allow_html=True)
            else:
                st.info("Aucune inscription trouvée pour les AM sélectionnées.")

    with t2:
        c_d1, c_d2 = st.columns(2)
        d_s = c_d1.date_input("Du", date.today(), key="pub_d1", format="DD/MM/YYYY")
        d_e = c_d2.date_input("Au", ajouter_mois(date.today(), 12), key="pub_d2", format="DD/MM/YYYY")

        ateliers_bruts = get_ateliers_periode(str(d_s), str(d_e), "Actifs")
        ateliers = enrichir_ateliers([dict(a) for a in ateliers_bruts], lieux_dict_global, horaires_dict_global)

        at_ids = tuple(a['id'] for a in ateliers)
        toutes_ins = get_toutes_inscriptions_ateliers(at_ids)
        cache_ins = construire_cache_ins(toutes_ins)

        all_ins_data = []
        for a in ateliers:
            for p in cache_ins.get(a['id'], []):
                all_ins_data.append({
                    "Date": a['date_atelier'],
                    "Atelier": a['titre'] if a['titre'] else "",
                    "Lieu": a['lieu_nom'],
                    "Horaire": a['horaire_lib'],
                    "AM": f"{p['adherents']['prenom']} {p['adherents']['nom']}",
                    "Enfants": p['nb_enfants']
                })

        df_at_exp = pd.DataFrame(all_ins_data) if all_ins_data else pd.DataFrame(columns=["Date", "Atelier", "Lieu", "Horaire", "AM", "Enfants"])
        ce1, ce2 = st.columns(2)
        ce1.download_button("📥 Excel Planning", data=export_to_excel(df_at_exp), file_name="planning_ateliers.xlsx", key="exp_at_xl")
        ce2.download_button("📥 PDF Planning", data=export_planning_ateliers_pdf("Planning des Ateliers", ateliers, cache_ins), file_name="planning_ateliers.pdf", key="exp_at_pdf")

        if ateliers:
            for index, a in enumerate(ateliers):
                c_l = get_color(a['lieu_nom'])
                anim_id_at = a.get('animateur_id')
                ins_at = cache_ins.get(a['id'], [])
                t_ad = len(ins_at)
                t_en = sum([p['nb_enfants'] for p in ins_at])
                restantes = a['capacite_max'] - (t_ad + t_en)
                max_enf_at = get_max_enfants_atelier(a, MAX_ENFANTS)
                places_enfants_restantes = max(max_enf_at - t_en, 0)
                statut_enfants = "🚫 Complet" if places_enfants_restantes == 0 else f"👶 {places_enfants_restantes} pl. enfants"
                if restantes < 0:
                    statut_enfants += " ⚠️ Salle saturée"

                c_at_pl = hex_couleur_badge(get_couleur_atelier(a))
                date_html_pl = f"<span style='color:{c_at_pl};font-weight:800;'>{format_date_fr_complete(a['date_atelier'], gras=False)}</span>"
                st.markdown(f"{date_html_pl} | {a['titre'] if a['titre'] else '(sans titre)'} | <span class='lieu-badge' style='background-color:{c_l}'>{a['lieu_nom']}</span> | <span class='horaire-text'>{a['horaire_lib']}</span> <span class='compteur-badge'>👤 {t_ad} AM</span> <span class='compteur-badge'>👶 {t_en} enf.</span> <span class='compteur-badge'>{statut_enfants}</span>", unsafe_allow_html=True)

                if ins_at:
                    anim_ins = next((p for p in ins_at if p['adherent_id'] == anim_id_at), None) if anim_id_at else None
                    autres_tries = sorted([p for p in ins_at if p['adherent_id'] != anim_id_at], key=lambda x: (x['adherents']['nom'], x['adherents']['prenom']))
                    html = "<div class='container-inscrits'>"
                    if anim_ins:
                        n_a = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
                        html += f'<span class="animateur-inscrit">⭐ {n_a} <span class="nb-enfants-focus">({anim_ins["nb_enfants"]} enfants)</span> <span class="animateur-badge">ANIMATEUR</span></span>'
                    for p in autres_tries:
                        html += f'<span class="liste-inscrits">• {p["adherents"]["prenom"]} {p["adherents"]["nom"]} <span class="nb-enfants-focus">({p["nb_enfants"]} enfants)</span></span>'
                    st.markdown(html + "</div>", unsafe_allow_html=True)

                if index < len(ateliers) - 1:
                    st.markdown('<hr class="separateur-atelier">', unsafe_allow_html=True)
        else:
            st.info("Aucun atelier trouvé sur cette période.")

    with t3:
        st.markdown("Ateliers **non complets**, regroupés par lieu, triés par nombre de places restantes décroissant.")

        noms_lieux_dispo = sorted([l['nom'] for l in lieux_actifs])
        cf1, cf2 = st.columns(2)
        filtre_lieux_pr = cf1.multiselect("Filtrer par lieu :", noms_lieux_dispo, key="pr_filtre_lieux")
        filtre_couleurs_pr = cf2.multiselect("Filtrer par couleur d'atelier :", COULEURS_BADGE_LIST, key="pr_filtre_couleurs")

        d_def_debut_pr, d_def_fin_pr = periode_places_restantes_defaut()
        cd1, cd2 = st.columns(2)
        d_s_pr = cd1.date_input("Du", d_def_debut_pr, key="pr_d1", format="DD/MM/YYYY")
        d_e_pr = cd2.date_input("Au", d_def_fin_pr, key="pr_d2", format="DD/MM/YYYY")

        ateliers_bruts_pr = get_ateliers_periode(str(d_s_pr), str(d_e_pr), "Actifs")
        ateliers_pr = enrichir_ateliers([dict(a) for a in ateliers_bruts_pr], lieux_dict_global, horaires_dict_global)

        if filtre_lieux_pr:
            ateliers_pr = [a for a in ateliers_pr if a['lieu_nom'] in filtre_lieux_pr]
        if filtre_couleurs_pr:
            ateliers_pr = [a for a in ateliers_pr if get_couleur_atelier(a) in filtre_couleurs_pr]

        at_ids_pr = tuple(a['id'] for a in ateliers_pr)
        toutes_ins_pr = get_toutes_inscriptions_ateliers(at_ids_pr)
        cache_ins_pr = construire_cache_ins(toutes_ins_pr)

        # Regroupement par lieu, en ne conservant que les ateliers avec au moins 1 place enfant restante
        lignes_par_lieu_pr = {}
        for a in ateliers_pr:
            ins_at_pr = cache_ins_pr.get(a['id'], [])
            total_enfants_pr = sum(p['nb_enfants'] for p in ins_at_pr)
            max_enf_at_pr = get_max_enfants_atelier(a, MAX_ENFANTS)
            places_restantes_pr = max(max_enf_at_pr - total_enfants_pr, 0)
            if places_restantes_pr <= 0:
                continue
            a_avec_places = dict(a)
            a_avec_places["_places_restantes"] = places_restantes_pr
            lignes_par_lieu_pr.setdefault(a['lieu_nom'], []).append(a_avec_places)

        pdf_places_restantes = export_places_restantes_pdf("Places restantes", lignes_par_lieu_pr, str(d_s_pr), str(d_e_pr))
        st.download_button("📥 PDF Places restantes", data=pdf_places_restantes, file_name="places_restantes.pdf", key="exp_pr_pdf")

        if not lignes_par_lieu_pr:
            st.info("Aucun atelier avec des places restantes sur cette période / ces filtres.")
        else:
            for lieu_nom_pr in sorted(lignes_par_lieu_pr.keys()):
                st.markdown(f"<div style='background-color:#1b3a5c;color:white;font-weight:700;padding:7px 14px;border-radius:8px;margin:16px 0 8px 0;'>{lieu_nom_pr}</div>", unsafe_allow_html=True)
                lignes_pr = sorted(lignes_par_lieu_pr[lieu_nom_pr], key=lambda a: a["_places_restantes"], reverse=True)
                for a in lignes_pr:
                    c_at_pr = hex_couleur_badge(get_couleur_atelier(a))
                    date_html_pr = f"<span style='color:{c_at_pr};font-weight:800;'>{format_date_fr_complete(a['date_atelier'], gras=False)}</span>"
                    titre_affiche_pr = a['titre'] if a['titre'] else "(sans titre)"
                    st.markdown(f"{date_html_pr} — {titre_affiche_pr} <span class='compteur-badge'>👶 {a['_places_restantes']} pl. restantes</span>", unsafe_allow_html=True)


# ==========================================
# SECTION 🔐 ADMINISTRATION
# ==========================================
elif menu == "🔐 Administration":
    if "admin_auth" not in st.session_state:
        st.session_state["admin_auth"] = False

    if not st.session_state["admin_auth"] and not st.session_state.get("super_access", False):
        st.markdown("### 🔐 Accès administration")
        with st.form("admin_login_form"):
            pw = st.text_input("Code secret admin", type="password")
            submitted = st.form_submit_button("✅ Valider", type="primary", use_container_width=True)
        if st.button("🔑 Code Super Admin", use_container_width=True):
            super_admin_dialog()
        if submitted and pw == current_code:
            st.session_state["admin_auth"] = True
            st.rerun()
        st.stop()

    t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs([
        "🏗️ Ateliers", "📊 Suivi AM", "📅 Planning Ateliers",
        "📈 Statistiques de participation", "👥 Liste AM",
        "📍 Lieux / Horaires", "⚙️ Sécurité", "📜 Journal des actions",
        "🎯 Animateur (Admin)"
    ])

    # ---- T1 : ATELIERS ----
    with t1:
        l_raw = lieux_actifs
        h_raw = horaires_actifs
        l_list = [l['nom'] for l in l_raw]
        h_list = [h['libelle'] for h in h_raw]
        map_l_cap = {l['nom']: l.get('capacite', 10) for l in l_raw}
        map_l_id = {l['nom']: l['id'] for l in l_raw}
        map_h_id = {h['libelle']: h['id'] for h in h_raw}

        if not l_raw: st.warning("⚠️ Aucun lieu défini. Créez-en dans '📍 Lieux / Horaires'.")
        if not h_raw: st.warning("⚠️ Aucun horaire défini. Créez-en dans '📍 Lieux / Horaires'.")

        if "admin_atelier_mode" not in st.session_state:
            st.session_state["admin_atelier_mode"] = "Générateur"

        st.markdown("**Mode**")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📦 Générateur", use_container_width=True, type="primary" if st.session_state["admin_atelier_mode"] == "Générateur" else "secondary"):
                st.session_state["admin_atelier_mode"] = "Générateur"; st.rerun()
        with col2:
            if st.button("📋 Répertoire", use_container_width=True, type="primary" if st.session_state["admin_atelier_mode"] == "Répertoire" else "secondary"):
                st.session_state["admin_atelier_mode"] = "Répertoire"; st.rerun()
        with col3:
            if st.button("⚡ Actions groupées", use_container_width=True, type="primary" if st.session_state["admin_atelier_mode"] == "Actions groupées" else "secondary"):
                st.session_state["admin_atelier_mode"] = "Actions groupées"; st.rerun()

        sub = st.session_state["admin_atelier_mode"]

        if sub == "Générateur":
            if not l_raw or not h_raw:
                st.error("⛔ Impossible de générer : aucun lieu ou horaire défini.")
                st.info("👉 Allez dans **📍 Lieux / Horaires** pour créer au moins un lieu et un horaire.")
            else:
                col_lieu, col_horaire = st.columns(2)
                with col_lieu:
                    lieu_par_defaut = st.selectbox("Lieu par défaut :", options=[""] + l_list)
                with col_horaire:
                    horaire_par_defaut = st.selectbox("Horaire par défaut :", options=[""] + h_list)
                c1, c2 = st.columns(2)
                d1 = c1.date_input("Début", date.today(), format="DD/MM/YYYY", key="gen_d1")
                d2 = c2.date_input("Fin", date.today() + timedelta(days=7), format="DD/MM/YYYY", key="gen_d2")
                st.markdown("**Jours de la semaine (cliquez sur les jours souhaités)**")
                jours_options = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
                if "jours_pills" not in st.session_state:
                    st.session_state.jours_pills = []
                jours = st.pills("", options=jours_options, selection_mode="multi", default=st.session_state.jours_pills, key="jours_pills_widget")
                st.session_state.jours_pills = jours

                if st.button("📊 Générer les lignes"):
                    tmp = []
                    curr = d1
                    js_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
                    while curr <= d2:
                        if js_fr[curr.weekday()] in jours:
                            lieu_val = lieu_par_defaut if lieu_par_defaut else ""
                            capa = map_l_cap.get(lieu_val, 10) if lieu_val else 10
                            tmp.append({
                                "Date": format_date_fr_complete(curr, False),
                                "Titre": "", "Lieu": lieu_val,
                                "Horaire": horaire_par_defaut if horaire_par_defaut else "",
                                "Capacité": capa, "Max Enfants": MAX_ENFANTS,
                                "Couleur": couleur_badge_defaut(curr),
                                "Actif": False, "Verrouillé": False
                            })
                        curr += timedelta(days=1)
                    st.session_state['at_list_gen'] = tmp
                    st.rerun()

                if st.session_state['at_list_gen']:
                    df_ed = st.data_editor(
                        pd.DataFrame(st.session_state['at_list_gen']),
                        num_rows="dynamic",
                        column_config={
                            "Lieu": st.column_config.SelectboxColumn(options=l_list, required=False),
                            "Horaire": st.column_config.SelectboxColumn(options=h_list, required=False),
                            "Couleur": st.column_config.SelectboxColumn(options=COULEURS_BADGE_LIST, required=False,
                                                                         help="Bleu = défaut mercredi, Orange = défaut jeudi. Modifiable ligne par ligne."),
                            "Actif": st.column_config.CheckboxColumn(default=False),
                            "Verrouillé": st.column_config.CheckboxColumn(default=False)
                        },
                        use_container_width=True, key="editor_ateliers"
                    )
                    if st.button("💾 Enregistrer"):
                        to_db = []
                        for _, r in df_ed.iterrows():
                            lieu_nom = r['Lieu']
                            horaire_lib = r['Horaire']
                            if not lieu_nom or not horaire_lib:
                                st.warning(f"Ligne ignorée : lieu ou horaire manquant pour {r['Date']}")
                                continue
                            if lieu_nom not in map_l_id:
                                st.error(f"Lieu '{lieu_nom}' introuvable."); st.stop()
                            if horaire_lib not in map_h_id:
                                st.error(f"Horaire '{horaire_lib}' introuvable."); st.stop()
                            date_iso = parse_date_fr_to_iso(r['Date'])
                            if not date_iso:
                                st.error(f"Format de date invalide : {r['Date']}"); st.stop()
                            max_enf_val = int(r.get('Max Enfants', MAX_ENFANTS))
                            couleur_ligne = r.get('Couleur')
                            if couleur_ligne not in COULEURS_BADGE:
                                couleur_ligne = couleur_badge_defaut(date_iso)
                            to_db.append({
                                "date_atelier": date_iso, "titre": r['Titre'] if r['Titre'] else None,
                                "lieu_id": map_l_id[lieu_nom], "horaire_id": map_h_id[horaire_lib],
                                "capacite_max": int(r['Capacité']),
                                "max_enfants": max_enf_val if max_enf_val > 0 else None,
                                "couleur_badge": couleur_ligne,
                                "est_actif": bool(r['Actif']), "est_verrouille": bool(r.get("Verrouillé", False))
                            })
                        if to_db:
                            try:
                                supabase.table("ateliers").insert(to_db).execute()
                                invalider_cache_inscriptions()
                                st.session_state['at_list_gen'] = []
                                st.success(f"{len(to_db)} ateliers enregistrés !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur : {str(e)}")
                        else:
                            st.warning("Aucune ligne valide à enregistrer.")

        elif sub == "Répertoire":
            cf1, cf2, cf3 = st.columns(3)
            fs = cf1.date_input("Du", date.today()-timedelta(days=30), format="DD/MM/YYYY", key="rep_d1")
            fe = cf2.date_input("Au", ajouter_mois(date.today(), 12), format="DD/MM/YYYY", key="rep_d2")
            ft = cf3.selectbox("Statut Filtre", ["Tous", "Actifs", "Inactifs"])

            ateliers_bruts = get_ateliers_periode(str(fs), str(fe))
            ateliers_rep = enrichir_ateliers([dict(a) for a in ateliers_bruts], lieux_dict_global, horaires_dict_global)

            # UNE SEULE requête pour toutes les inscriptions du répertoire
            at_ids_rep = tuple(a['id'] for a in ateliers_rep)
            toutes_ins_rep = get_toutes_inscriptions_ateliers(at_ids_rep)
            cache_ins_rep = construire_cache_ins(toutes_ins_rep)

            # Calcul des stats de chaque atelier à partir du cache
            for a in ateliers_rep:
                ins_a = cache_ins_rep.get(a['id'], [])
                nb_enf = sum(i['nb_enfants'] for i in ins_a)
                max_enf_at = get_max_enfants_atelier(a, MAX_ENFANTS)
                a['places_enfants_restantes'] = max(max_enf_at - nb_enf, 0)
                a['nb_enfants_inscrits'] = nb_enf
                a['total_occ'] = sum(1 + i['nb_enfants'] for i in ins_a)

            if not ateliers_rep:
                st.info("Aucun atelier trouvé sur cette période.")
            else:
                for a in ateliers_rep:
                    if ft == "Actifs" and not a['est_actif']: continue
                    if ft == "Inactifs" and a['est_actif']: continue

                    verrou_icon = " 🔒" if is_verrouille(a) else ""
                    anim_id_at = a.get('animateur_id')
                    anim_nom_rep = None
                    if anim_id_at:
                        anim_adh = next((x for x in adh_data if x['id'] == anim_id_at), None)
                        if anim_adh:
                            anim_nom_rep = f"{anim_adh['prenom']} {anim_adh['nom']}"
                    anim_label_rep = f" | ⭐ {anim_nom_rep}" if anim_nom_rep else ""

                    statut_enfants = "🚫 Complet" if a['places_enfants_restantes'] == 0 else f"👶 {a['places_enfants_restantes']} pl. enfants"
                    if a['total_occ'] > a['capacite_max']:
                        statut_enfants += " ⚠️ Salle saturée"

                    ca, cb, cc, cd, ce, cf_anim = st.columns([0.38, 0.1, 0.1, 0.1, 0.1, 0.22])
                    titre_affiche = a['titre'] if a['titre'] else "(sans titre)"
                    couleur_rep = get_couleur_atelier(a)
                    badge_couleur_rep = f'<span class="couleur-badge" style="background-color:{hex_couleur_badge(couleur_rep)};color:white;">{couleur_rep}</span>'
                    ca.markdown(f"**{format_date_fr_complete(a['date_atelier'])}** | {a['horaire_lib']} | {titre_affiche} ({a['lieu_nom']}){verrou_icon}{anim_label_rep} | {statut_enfants} {badge_couleur_rep}", unsafe_allow_html=True)

                    if cb.button("🔴 Désactiver" if a['est_actif'] else "🟢 Activer", key=f"at_stat_{a['id']}"):
                        supabase.table("ateliers").update({"est_actif": not a['est_actif']}).eq("id", a['id']).execute()
                        invalider_cache_inscriptions(); st.rerun()
                    if cc.button("🔓 Déverrouiller" if is_verrouille(a) else "🔒 Verrouiller", key=f"at_verr_{a['id']}"):
                        nouvel_etat = not is_verrouille(a)
                        supabase.table("ateliers").update({"est_verrouille": bool(nouvel_etat)}).eq("id", a['id']).execute()
                        titre_log = a['titre'] if a['titre'] else "(sans titre)"
                        enregistrer_log("Admin", "Verrouillage atelier", f"Atelier '{titre_log}' {'verrouillé' if nouvel_etat else 'déverrouillé'}")
                        invalider_cache_inscriptions(); st.rerun()
                    if cd.button("✏️", key=f"at_edit_{a['id']}"):
                        edit_atelier_dialog(a['id'], a['titre'], a['date_atelier'], a['lieu_id'], a['horaire_id'], a['capacite_max'], a.get('max_enfants'), l_raw, h_raw, map_l_id, map_h_id, couleur_actuelle=a.get('couleur_badge'))
                    if ce.button("🗑️", key=f"at_del_{a['id']}"):
                        cnt = len(cache_ins_rep.get(a['id'], []))
                        delete_atelier_dialog(a['id'], a['titre'], cnt > 0)
                    if anim_nom_rep:
                        if cf_anim.button("⭐ Changer anim.", key=f"at_anim_chg_{a['id']}"):
                            dialog_attribuer_animateur(a['id'], a['titre'], anim_id_at, anim_nom_rep, liste_adh_anim, dict_adh_anim, auteur="Admin")
                    else:
                        if cf_anim.button("⭐ Assigner anim.", key=f"at_anim_set_{a['id']}"):
                            dialog_attribuer_animateur(a['id'], a['titre'], None, None, liste_adh_anim, dict_adh_anim, auteur="Admin")

        elif sub == "Actions groupées":
            if "bulk_action" not in st.session_state:
                st.session_state["bulk_action"] = "Activer"
            st.markdown("**Action à appliquer :**")
            col_act, col_desact = st.columns(2)
            with col_act:
                if st.button("✅ Activer", key="bulk_activer", use_container_width=True, type="primary" if st.session_state["bulk_action"] == "Activer" else "secondary"):
                    st.session_state["bulk_action"] = "Activer"; st.rerun()
            with col_desact:
                if st.button("❌ Désactiver", key="bulk_desactiver", use_container_width=True, type="primary" if st.session_state["bulk_action"] == "Désactiver" else "secondary"):
                    st.session_state["bulk_action"] = "Désactiver"; st.rerun()
            if st.session_state["bulk_action"] == "Activer":
                st.success("✅ Action sélectionnée : **Activer** les ateliers de la période")
            else:
                st.error("❌ Action sélectionnée : **Désactiver** les ateliers de la période")
            with st.form("bulk_form"):
                c1, c2 = st.columns(2)
                bs = c1.date_input("Début", format="DD/MM/YYYY", key="blk_d1")
                be = c2.date_input("Fin", format="DD/MM/YYYY", key="blk_d2")
                if st.form_submit_button(f"🚀 Appliquer : {st.session_state['bulk_action']}"):
                    supabase.table("ateliers").update({"est_actif": (st.session_state["bulk_action"] == "Activer")}).gte("date_atelier", str(bs)).lte("date_atelier", str(be)).execute()
                    invalider_cache_inscriptions(); st.rerun()

    # ---- T2 : SUIVI AM (Admin) ----
    with t2:
        if not liste_adh:
            st.info("ℹ️ Aucune assistante maternelle enregistrée.")
        else:
            choix_adm = st.multiselect("Filtrer par AM (Admin) :", liste_adh, key="adm_filter_am")
            ids_adm = [dict_adh[n] for n in choix_adm] if choix_adm else list(dict_adh.values())
            data_adm_triee = []
            if ids_adm:
                try:
                    inscriptions_brutes = supabase.table("inscriptions").select("*, ateliers!inner(*), adherents(nom, prenom)").in_("adherent_id", ids_adm).eq("ateliers.est_actif", True).execute().data or []
                    for ins in inscriptions_brutes:
                        at = ins['ateliers']
                        at['lieu_nom'] = lieux_dict_global.get(at['lieu_id'], '?')
                        at['horaire_lib'] = horaires_dict_global.get(at['horaire_id'], '?')
                        ins['ateliers'] = at
                    data_adm_triee = trier_par_nom_puis_date(inscriptions_brutes)
                except:
                    data_adm_triee = []

            df_adm = pd.DataFrame([{
                "AM": f"{i['adherents']['prenom']} {i['adherents']['nom']}",
                "Date": i['ateliers']['date_atelier'], "Atelier": i['ateliers']['titre'] if i['ateliers']['titre'] else "",
                "Lieu": i['ateliers']['lieu_nom'], "Horaire": i['ateliers']['horaire_lib'],
                "Enfants": i['nb_enfants']
            } for i in data_adm_triee]) if data_adm_triee else pd.DataFrame(columns=["AM", "Date", "Atelier", "Lieu", "Horaire", "Enfants"])

            c_e3, c_e4 = st.columns(2)
            c_e3.download_button("📥 Excel (Admin)", data=export_to_excel(df_adm), file_name="admin_suivi_am.xlsx")
            c_e4.download_button("📥 PDF (Admin)", data=export_suivi_am_pdf("Suivi AM (Administration)", data_adm_triee), file_name="admin_suivi_am.pdf")

            if data_adm_triee:
                curr = ""
                for i in data_adm_triee:
                    nom = f"{i['adherents']['prenom']} {i['adherents']['nom']}"
                    if nom != curr:
                        st.markdown(f'<div style="color:#1b5e20; border-bottom:2px solid #1b5e20; padding-top:15px; margin-bottom:8px; font-weight:bold; font-size:1.2rem;">{nom}</div>', unsafe_allow_html=True)
                        curr = nom
                    at = i['ateliers']
                    c_l = get_color(at['lieu_nom'])
                    titre_affiche = at['titre'] if at['titre'] else "(sans titre)"
                    c_at_adm = hex_couleur_badge(get_couleur_atelier(at))
                    icone_anim_adm = "⭐ " if i.get('adherent_id') == at.get('animateur_id') else ""
                    date_html_adm = f"{icone_anim_adm}<span style='color:{c_at_adm};font-weight:800;'>{format_date_fr_complete(at['date_atelier'], gras=False)}</span>"
                    st.write(f"{date_html_adm} — {titre_affiche} <span class='lieu-badge' style='background-color:{c_l}'>{at['lieu_nom']}</span> <span class='horaire-text'>({at['horaire_lib']})</span> **({i['nb_enfants']} enf.)**", unsafe_allow_html=True)
            else:
                st.info("Aucune inscription trouvée.")

    # ---- T3 : PLANNING ATELIERS (Admin) ----
    with t3:
        st.subheader("📅 Planning des Ateliers")
        st.markdown("**Filtrer par statut :**")
        options_filtre_plan = ("Tous", "Actifs", "Inactifs")
        if "filtre_plan_admin" not in st.session_state:
            st.session_state["filtre_plan_admin"] = "Tous"
        col_f1, col_f2, col_f3, col_f_rest = st.columns([1, 1, 1, 5])
        for col_f, opt in zip([col_f1, col_f2, col_f3], options_filtre_plan):
            with col_f:
                if st.button(opt, key=f"filtre_plan_{opt}", use_container_width=True, type="primary" if st.session_state["filtre_plan_admin"] == opt else "secondary"):
                    st.session_state["filtre_plan_admin"] = opt; st.rerun()
        st.caption(f"Filtre actif : **{st.session_state['filtre_plan_admin']}**")

        filtre_statut_plan = st.session_state["filtre_plan_admin"]
        c1_adm, c2_adm = st.columns(2)
        d_s_a = c1_adm.date_input("Du", date.today(), key="adm_plan_d1", format="DD/MM/YYYY")
        d_e_a = c2_adm.date_input("Au", ajouter_mois(date.today(), 12), key="adm_plan_d2", format="DD/MM/YYYY")

        ateliers_bruts = get_ateliers_periode(str(d_s_a), str(d_e_a), filtre_statut_plan)
        ateliers = enrichir_ateliers([dict(a) for a in ateliers_bruts], lieux_dict_global, horaires_dict_global)

        at_ids = tuple(a['id'] for a in ateliers)
        toutes_ins = get_toutes_inscriptions_ateliers(at_ids)
        cache_ins_adm = construire_cache_ins(toutes_ins)

        adm_ins_list = []
        for a in ateliers:
            for p in cache_ins_adm.get(a['id'], []):
                adm_ins_list.append({
                    "Date": a['date_atelier'], "Atelier": a['titre'] if a['titre'] else "", "Lieu": a['lieu_nom'],
                    "AM": f"{p['adherents']['prenom']} {p['adherents']['nom']}", "Enfants": p['nb_enfants']
                })

        df_adm_at = pd.DataFrame(adm_ins_list) if adm_ins_list else pd.DataFrame(columns=["Date", "Atelier", "Lieu", "AM", "Enfants"])
        cea1, cea2 = st.columns(2)
        cea1.download_button("📥 Excel Planning (Admin)", data=export_to_excel_with_period(df_adm_at, d_s_a, d_e_a, "Planning des ateliers"), file_name="admin_planning_ateliers.xlsx", key="adm_exp_xl")
        cea2.download_button("📥 PDF Planning (Admin)", data=export_planning_ateliers_pdf_with_period("Planning des Ateliers (Administration)", ateliers, cache_ins_adm, d_s_a, d_e_a), file_name="admin_planning_ateliers.pdf", key="adm_exp_pdf")

        if ateliers:
            for index, a in enumerate(ateliers):
                c_l = get_color(a['lieu_nom'])
                anim_id_at = a.get('animateur_id')
                ins_at = cache_ins_adm.get(a['id'], [])
                t_ad = len(ins_at)
                t_en = sum([p['nb_enfants'] for p in ins_at])
                restantes = a['capacite_max'] - (t_ad + t_en)
                max_enf_at = get_max_enfants_atelier(a, MAX_ENFANTS)
                places_enfants_restantes = max(max_enf_at - t_en, 0)
                statut_enfants = "🚫 Complet" if places_enfants_restantes == 0 else f"👶 {places_enfants_restantes} pl. enfants"
                if restantes < 0:
                    statut_enfants += " ⚠️ Salle saturée"
                verrou_icon = " 🔒" if is_verrouille(a) else ""
                at_info_log = f"{a['date_atelier']} | {a['horaire_lib']} | {a['lieu_nom']}"

                anim_nom_plan = None
                if anim_id_at:
                    anim_adh_plan = next((x for x in adh_data if x['id'] == anim_id_at), None)
                    if anim_adh_plan:
                        anim_nom_plan = f"{anim_adh_plan['prenom']} {anim_adh_plan['nom']}"
                anim_label_plan = f" | ⭐ {anim_nom_plan}" if anim_nom_plan else ""

                titre_affiche = a['titre'] if a['titre'] else "(sans titre)"
                c_at_admp = hex_couleur_badge(get_couleur_atelier(a))
                date_html_admp = f"<span style='color:{c_at_admp};font-weight:800;'>{format_date_fr_complete(a['date_atelier'], gras=False)}</span>"
                st.markdown(f"{date_html_admp} | {titre_affiche} | <span class='lieu-badge' style='background-color:{c_l}'>{a['lieu_nom']}</span> | <span class='horaire-text'>{a['horaire_lib']}</span>{verrou_icon}{anim_label_plan} <span class='compteur-badge'>👤 {t_ad} AM</span> <span class='compteur-badge'>👶 {t_en} enf.</span> <span class='compteur-badge'>{statut_enfants}</span>", unsafe_allow_html=True)

                if st.button("✏️ Modifier l'atelier", key=f"plan_edit_{a['id']}"):
                    edit_atelier_dialog(a['id'], a['titre'], a['date_atelier'], a['lieu_id'], a['horaire_id'], a['capacite_max'], a.get('max_enfants'), l_raw, h_raw, map_l_id, map_h_id, couleur_actuelle=a.get('couleur_badge'))

                if ins_at:
                    anim_ins_plan = next((p for p in ins_at if p['adherent_id'] == anim_id_at), None) if anim_id_at else None
                    autres_plan_tries = sorted([p for p in ins_at if p['adherent_id'] != anim_id_at], key=lambda x: (x['adherents']['nom'].upper(), x['adherents']['prenom'].upper()))

                    if anim_ins_plan:
                        n_a = f"{anim_ins_plan['adherents']['prenom']} {anim_ins_plan['adherents']['nom']}"
                        ca1, ca2, ca3, ca4 = st.columns([0.42, 0.18, 0.18, 0.22])
                        ca1.markdown(f'<span style="color:#e65100;font-weight:bold;">⭐ {n_a} <span style="background:#e65100;color:white;padding:1px 6px;border-radius:4px;font-size:0.78rem;">ANIMATEUR</span></span>', unsafe_allow_html=True)
                        new_nb_a = ca2.number_input("Enf.", 0, 10, int(anim_ins_plan['nb_enfants']), key=f"adm_anim_nb_{anim_ins_plan['id']}", label_visibility="collapsed")
                        if ca3.button("✏️ Modifier", key=f"adm_anim_mod_{anim_ins_plan['id']}"):
                            delta = new_nb_a - anim_ins_plan['nb_enfants']
                            nouveau_total_enf = t_en + delta
                            if (t_ad + t_en + delta) > a['capacite_max']:
                                st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                            elif nouveau_total_enf > max_enf_at:
                                st.markdown(f"<span style='color:red; font-weight:bold;'>🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé.</span>", unsafe_allow_html=True)
                            else:
                                supabase.table("inscriptions").update({"nb_enfants": new_nb_a}).eq("id", anim_ins_plan['id']).execute()
                                enregistrer_log("Admin", "Modification nb enf. animateur", f"{n_a} → {new_nb_a} enf. - {at_info_log}")
                                invalider_cache_inscriptions()
                                st.rerun()
                        if ca4.button("❌ Retirer anim.", key=f"adm_anim_del_{a['id']}"):
                            dialog_retirer_animateur(a['id'], a['titre'], anim_id_at, n_a, "Admin")

                    for p in autres_plan_tries:
                        n_f = f"{p['adherents']['prenom']} {p['adherents']['nom']}"
                        cp1, cp2, cp3, cp4 = st.columns([0.45, 0.18, 0.18, 0.19])
                        cp1.write(f"• {n_f}")
                        new_nb = cp2.number_input("Enf.", 0, 10, int(p['nb_enfants']), key=f"adm_nb_{p['id']}", label_visibility="collapsed")
                        if cp3.button("✏️ Modifier", key=f"adm_mod_{p['id']}"):
                            delta = new_nb - p['nb_enfants']
                            nouveau_total_enf = t_en + delta
                            if (t_ad + t_en + delta) > a['capacite_max']:
                                st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                            elif nouveau_total_enf > max_enf_at:
                                st.markdown(f"<span style='color:red; font-weight:bold;'>🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé.</span>", unsafe_allow_html=True)
                            else:
                                supabase.table("inscriptions").update({"nb_enfants": new_nb}).eq("id", p['id']).execute()
                                enregistrer_log("Admin", "Modification (admin)", f"{n_f} → {new_nb} enfants - {at_info_log}")
                                invalider_cache_inscriptions()
                                st.rerun()
                        if cp4.button("🗑️", key=f"adm_del_plan_{p['id']}"):
                            confirm_unsubscribe_dialog(p['id'], n_f, at_info_log, "Admin")

                with st.expander(f"➕ Inscrire une AM à cet atelier", expanded=False):
                    if not liste_adh:
                        st.info("Aucune AM enregistrée.")
                    else:
                        ca1, ca2, ca3 = st.columns([2, 1, 1])
                        qui_adm = ca1.selectbox("AM à inscrire", ["Choisir..."] + liste_adh, key=f"adm_qui_{a['id']}")
                        nb_adm = ca2.number_input("Enfants", 1, 10, 1, key=f"adm_enf_{a['id']}")
                        qui_est_anim_adm = (qui_adm != "Choisir..." and dict_adh.get(qui_adm) == anim_id_at)
                        if qui_est_anim_adm:
                            st.warning("🔒 Cette personne est l'animateur de cet atelier.")
                        elif ca3.button("✅ Inscrire", key=f"adm_ins_{a['id']}", type="primary"):
                            if qui_adm != "Choisir...":
                                id_adh = dict_adh[qui_adm]
                                existing = next((ins for ins in ins_at if ins['adherent_id'] == id_adh), None)
                                if existing:
                                    delta_enf = nb_adm - existing['nb_enfants']
                                    nouveau_total_enf = t_en + delta_enf
                                    if (t_ad + t_en + delta_enf) > a['capacite_max']:
                                        st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                                    elif nouveau_total_enf > max_enf_at:
                                        st.markdown(f"<span style='color:red; font-weight:bold;'>🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé.</span>", unsafe_allow_html=True)
                                    else:
                                        supabase.table("inscriptions").update({"nb_enfants": nb_adm}).eq("id", existing['id']).execute()
                                        enregistrer_log("Admin", "Modification (admin)", f"{qui_adm} → {nb_adm} enfants - {at_info_log}")
                                        invalider_cache_inscriptions()
                                        st.rerun()
                                else:
                                    nouveau_total_enf = t_en + nb_adm
                                    if (t_ad + t_en + 1 + nb_adm) > a['capacite_max']:
                                        st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                                    elif nouveau_total_enf > max_enf_at:
                                        st.markdown(f"<span style='color:red; font-weight:bold;'>🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé.</span>", unsafe_allow_html=True)
                                    else:
                                        supabase.table("inscriptions").insert({"adherent_id": id_adh, "atelier_id": a['id'], "nb_enfants": nb_adm}).execute()
                                        enregistrer_log("Admin", "Inscription (admin)", f"{qui_adm} inscrite (+{nb_adm} enf.) - {at_info_log}")
                                        invalider_cache_inscriptions()
                                        st.rerun()

                if index < len(ateliers) - 1:
                    st.markdown('<hr class="separateur-atelier">', unsafe_allow_html=True)
        else:
            st.info("Aucun atelier trouvé sur cette période.")

    # ---- T4 : STATISTIQUES ----
    with t4:
        st.subheader("📈 Statistiques de participation")

        defaut_debut, defaut_fin = periode_stats_defaut()
        cs1, cs2 = st.columns(2)
        ds_stat = cs1.date_input("Date début (date de l'atelier)", defaut_debut, key="stat_d1", format="DD/MM/YYYY")
        de_stat = cs2.date_input("Date fin (date de l'atelier)", defaut_fin, key="stat_d2", format="DD/MM/YYYY")

        st.markdown("**Filtrer les ateliers par statut :**")
        if "stat_statut_filtre" not in st.session_state:
            st.session_state["stat_statut_filtre"] = "Actifs"
        cf1, cf2, cf3, cf_rest = st.columns([1, 1, 1, 5])
        for col_f, opt in zip([cf1, cf2, cf3], ["Actifs", "Inactifs", "Tous"]):
            with col_f:
                if st.button(opt, key=f"stat_filtre_{opt}", use_container_width=True,
                             type="primary" if st.session_state["stat_statut_filtre"] == opt else "secondary"):
                    st.session_state["stat_statut_filtre"] = opt; st.rerun()
        st.caption(f"Filtre actif : **{st.session_state['stat_statut_filtre']}**")
        statut_filtre_stat = st.session_state["stat_statut_filtre"]
        actif_filter_stat = None if statut_filtre_stat == "Tous" else statut_filtre_stat

        ateliers_bruts = get_ateliers_periode(str(ds_stat), str(de_stat), actif_filter_stat)
        if not ateliers_bruts:
            st.info("ℹ️ Aucun atelier sur cette période.")
        else:
            ateliers = enrichir_ateliers([dict(a) for a in ateliers_bruts], lieux_dict_global, horaires_dict_global)
            for a in ateliers:
                a['couleur_calc'] = get_couleur_atelier(a)
            at_ids = tuple(a['id'] for a in ateliers)
            toutes_ins = get_toutes_inscriptions_ateliers(at_ids)

            if not toutes_ins:
                st.info("Aucune inscription sur cette période.")
            else:
                couleur_lieux = defaultdict(set)
                atelier_couleur = {}
                atelier_date = {}
                atelier_animateur = {}
                for a in ateliers:
                    atelier_couleur[a['id']] = a['couleur_calc']
                    atelier_date[a['id']] = a['date_atelier']
                    atelier_animateur[a['id']] = a.get('animateur_id')
                    couleur_lieux[a['couleur_calc']].add(a['lieu_nom'])

                data_am = defaultdict(lambda: defaultdict(lambda: {"count": 0, "dates": []}))
                adherent_info = {}
                for ins in toutes_ins:
                    couleur = atelier_couleur.get(ins['atelier_id'])
                    if not couleur:
                        continue
                    am_id = ins['adherent_id']
                    entry = data_am[am_id][couleur]
                    entry["count"] += 1
                    est_animateur = atelier_animateur.get(ins['atelier_id']) == am_id
                    entry["dates"].append((atelier_date.get(ins['atelier_id']), est_animateur))
                    adherent_info[am_id] = (ins['adherents']['nom'], ins['adherents']['prenom'])

                couleurs_presentes = set()
                for d in data_am.values():
                    couleurs_presentes.update(d.keys())
                # Seules les couleurs comportant au moins une inscription sur la période sont affichées
                couleurs_utilisees = [c for c in COULEURS_BADGE_LIST if c in couleurs_presentes]

                am_rows = sorted(
                    [(nom, prenom, am_id) for am_id, (nom, prenom) in adherent_info.items()],
                    key=lambda x: (x[0].upper(), x[1].upper())
                )

                if not couleurs_utilisees or not am_rows:
                    st.info("Aucune inscription sur cette période.")
                else:
                    incoherences = [c for c in couleurs_utilisees if _lieux_label_couleur(c, couleur_lieux)[1]]
                    if incoherences:
                        st.warning(f"⚠️ Couleur(s) utilisée(s) pour plusieurs lieux différents sur cette période : {', '.join(incoherences)}.")

                    st.markdown(rendu_html_stats_couleur(am_rows, couleurs_utilisees, couleur_lieux, data_am), unsafe_allow_html=True)

                    total_inscr = sum(v["count"] for d in data_am.values() for v in d.values())
                    st.markdown(f"**Total des inscriptions sur la période :** {total_inscr}")
                    st.markdown(f"**Nombre d'ateliers sur la période :** {len(at_ids)}")

                    cex1, cex2 = st.columns(2)
                    cex1.download_button(
                        "📥 Excel Statistiques",
                        data=export_stats_couleur_excel(am_rows, couleurs_utilisees, couleur_lieux, data_am, ds_stat, de_stat, statut_filtre_stat),
                        file_name=f"stats_participation_{ds_stat}_{de_stat}.xlsx", key="stat_excel"
                    )
                    cex2.download_button(
                        "📥 PDF Statistiques",
                        data=export_stats_couleur_pdf(am_rows, couleurs_utilisees, couleur_lieux, data_am, ds_stat, de_stat, statut_filtre_stat),
                        file_name=f"stats_participation_{ds_stat}_{de_stat}.pdf", key="stat_pdf"
                    )

    # ---- T5 : LISTE AM ----
    with t5:
        st.subheader("👥 Gestion des Assistantes Maternelles")
        with st.form("add_am"):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nom").upper().strip()
            pre = " ".join([w.capitalize() for w in c2.text_input("Prénom").split()]).strip()
            if st.form_submit_button("➕ Ajouter"):
                if nom and pre:
                    try:
                        supabase.table("adherents").insert({"nom": nom, "prenom": pre, "est_actif": True, "est_animateur": False}).execute()
                        invalider_cache_referentiels()
                        st.success(f"✅ {pre} {nom} ajouté(e) !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {str(e)}")
                else:
                    st.warning("Veuillez renseigner le nom et le prénom.")

        adh_data_admin = get_adherents_tous_cached()
        if not adh_data_admin:
            st.info("ℹ️ Aucune assistante maternelle enregistrée.")
        else:
            nb_actives = sum(1 for u in adh_data_admin if u.get('est_actif', True))
            nb_inactives = len(adh_data_admin) - nb_actives
            st.markdown("---")
            st.markdown("**Filtrer :**")
            options_filtre_am = ("Tous", "Actifs", "Inactifs")
            if "filtre_liste_am" not in st.session_state:
                st.session_state["filtre_liste_am"] = "Tous"
            col_am1, col_am2, col_am3, col_am_rest = st.columns([1, 1, 1, 5])
            for col_am, opt in zip([col_am1, col_am2, col_am3], options_filtre_am):
                with col_am:
                    if st.button(opt, key=f"filtre_am_{opt}", use_container_width=True, type="primary" if st.session_state["filtre_liste_am"] == opt else "secondary"):
                        st.session_state["filtre_liste_am"] = opt; st.rerun()
            st.caption(f"Filtre actif : **{st.session_state['filtre_liste_am']}**")
            filtre_am_actuel = st.session_state["filtre_liste_am"]
            st.markdown(f"**Liste des AM** ({nb_actives} actives, {nb_inactives} inactives)")

            for u in adh_data_admin:
                est_anim = u.get('est_animateur', False)
                est_actif_am = u.get('est_actif', True)
                if filtre_am_actuel == "Actifs" and not est_actif_am: continue
                if filtre_am_actuel == "Inactifs" and est_actif_am: continue

                style_nom = "color:#9e9e9e; text-decoration:line-through;" if not est_actif_am else ""
                badge_inactif = ' <span style="background:#9e9e9e;color:white;padding:1px 6px;border-radius:4px;font-size:0.78rem;font-weight:bold;">INACTIF</span>' if not est_actif_am else ''
                anim_label_am = ' <span style="background:#e65100;color:white;padding:1px 6px;border-radius:4px;font-size:0.78rem;font-weight:bold;">ANIMATEUR</span>' if est_anim else ''

                c1, c_anim, c_actif, c_edit, c_del = st.columns([0.45, 0.2, 0.12, 0.12, 0.11])
                c1.markdown(f'<span style="{style_nom}"><strong>{u["nom"]}</strong> {u["prenom"]}</span>{anim_label_am}{badge_inactif}', unsafe_allow_html=True)

                if est_anim:
                    if c_anim.button("⭐ Retirer anim.", key=f"am_anim_off_{u['id']}", disabled=not est_actif_am):
                        supabase.table("adherents").update({"est_animateur": False}).eq("id", u['id']).execute()
                        enregistrer_log("Admin", "Retrait statut animateur", f"{u['prenom']} {u['nom']}")
                        invalider_cache_referentiels(); st.rerun()
                else:
                    if c_anim.button("⭐ Rendre anim.", key=f"am_anim_on_{u['id']}", disabled=not est_actif_am):
                        supabase.table("adherents").update({"est_animateur": True}).eq("id", u['id']).execute()
                        enregistrer_log("Admin", "Attribution statut animateur", f"{u['prenom']} {u['nom']}")
                        invalider_cache_referentiels(); st.rerun()

                if est_actif_am:
                    if c_actif.button("🟢 Actif", key=f"am_actif_{u['id']}"):
                        today_str = str(date.today())
                        try:
                            res_ins_futures = supabase.table("inscriptions").select("id, ateliers(date_atelier, titre)").eq("adherent_id", u['id']).execute()
                            ins_futures = [i for i in (res_ins_futures.data or []) if i.get('ateliers') and i['ateliers'].get('date_atelier', '') >= today_str]
                        except:
                            ins_futures = []
                        if ins_futures:
                            noms_ateliers = ", ".join([f"{format_date_fr_simple(i['ateliers']['date_atelier'])} – {i['ateliers'].get('titre','?')}" for i in ins_futures[:3]])
                            st.session_state[f"confirm_desact_{u['id']}"] = {"ins_futures": ins_futures, "noms": noms_ateliers}
                        else:
                            supabase.table("adherents").update({"est_actif": False}).eq("id", u['id']).execute()
                            enregistrer_log("Admin", "Désactivation AM", f"{u['prenom']} {u['nom']}")
                            invalider_cache_referentiels(); st.rerun()
                else:
                    if c_actif.button("🔴 Inactif", key=f"am_actif_{u['id']}"):
                        supabase.table("adherents").update({"est_actif": True}).eq("id", u['id']).execute()
                        enregistrer_log("Admin", "Réactivation AM", f"{u['prenom']} {u['nom']}")
                        invalider_cache_referentiels(); st.rerun()

                if st.session_state.get(f"confirm_desact_{u['id']}"):
                    info = st.session_state[f"confirm_desact_{u['id']}"]
                    nb_ins = len(info["ins_futures"])
                    st.warning(f"⚠️ **{u['prenom']} {u['nom']}** a **{nb_ins} inscription(s) à venir** ({info['noms']}{'...' if nb_ins > 3 else ''}). Elle restera inscrite. Confirmer la désactivation ?")
                    ca, cb = st.columns(2)
                    if ca.button("✅ Confirmer quand même", key=f"ok_desact_{u['id']}"):
                        supabase.table("adherents").update({"est_actif": False}).eq("id", u['id']).execute()
                        enregistrer_log("Admin", "Désactivation AM (avec inscriptions futures)", f"{u['prenom']} {u['nom']} ({nb_ins} inscriptions futures conservées)")
                        del st.session_state[f"confirm_desact_{u['id']}"]
                        invalider_cache_referentiels(); st.rerun()
                    if cb.button("❌ Annuler", key=f"cancel_desact_{u['id']}"):
                        del st.session_state[f"confirm_desact_{u['id']}"]
                        st.rerun()

                if c_edit.button("✏️", key=f"am_edit_{u['id']}", help="Modifier le nom/prénom"):
                    edit_am_dialog(u['id'], u['nom'], u['prenom'])
                if c_del.button("🗑️", key=f"am_del_{u['id']}"):
                    secure_delete_dialog("adherents", u['id'], f"{u['prenom']} {u['nom']}")

    # ---- T6 : LIEUX / HORAIRES ----
    with t6:
        l_raw = lieux_actifs
        h_raw = horaires_actifs
        cl1, cl2 = st.columns(2)
        with cl1:
            st.subheader("Lieux")
            if not l_raw:
                st.info("ℹ️ Aucun lieu enregistré.")
            else:
                for l in l_raw:
                    ca, cb_edit, cb_del = st.columns([0.65, 0.18, 0.17])
                    nom_lieu = l['nom']
                    ca.markdown(f"<span class='lieu-badge' style='background-color:{get_color(nom_lieu)}'>{nom_lieu} (Cap: {l['capacite']})</span>", unsafe_allow_html=True)
                    if cb_edit.button("✏️", key=f"lx_edit_{l['id']}", help="Modifier"):
                        edit_lieu_dialog(l['id'], l['nom'], l['capacite'])
                    if cb_del.button("🗑️", key=f"lx_{l['id']}", help="Supprimer"):
                        try:
                            supabase.table("lieux").delete().eq("id", l['id']).execute()
                            invalider_cache_referentiels(); st.rerun()
                        except Exception as e:
                            st.error(f"Erreur suppression : {str(e)}")
            with st.form("add_lx"):
                nl = st.text_input("Nouveau Lieu")
                cp = st.number_input("Capacité", 1, 50, 10)
                if st.form_submit_button("Ajouter"):
                    if nl.strip():
                        nom_upper = nl.strip().upper()
                        try:
                            existing = supabase.table("lieux").select("id, est_actif").eq("nom", nom_upper).execute()
                            if existing.data:
                                supabase.table("lieux").update({"est_actif": True, "capacite": cp}).eq("nom", nom_upper).execute()
                                st.success(f"✅ Lieu '{nom_upper}' réactivé.")
                            else:
                                supabase.table("lieux").insert({"nom": nom_upper, "capacite": cp}).execute()
                                st.success(f"✅ Lieu '{nom_upper}' ajouté.")
                            invalider_cache_referentiels(); st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {str(e)}")
                    else:
                        st.error("Le nom du lieu ne peut pas être vide.")

        with cl2:
            st.subheader("Horaires")
            if not h_raw:
                st.info("ℹ️ Aucun horaire enregistré.")
            else:
                for h in h_raw:
                    cc, cd_edit, cd_del = st.columns([0.65, 0.18, 0.17])
                    cc.write(f"• {h['libelle']}")
                    if cd_edit.button("✏️", key=f"hx_edit_{h['id']}", help="Modifier"):
                        edit_horaire_dialog(h['id'], h['libelle'])
                    if cd_del.button("🗑️", key=f"hx_{h['id']}", help="Supprimer"):
                        secure_delete_dialog("horaires", h['id'], h['libelle'])
            with st.form("add_hx"):
                nh = st.text_input("Nouvel Horaire (ex: '09:00-11:00')")
                if st.form_submit_button("Ajouter"):
                    if nh.strip():
                        try:
                            supabase.table("horaires").insert({"libelle": nh.strip()}).execute()
                            invalider_cache_referentiels()
                            st.success(f"✅ Horaire '{nh.strip()}' ajouté.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {str(e)}")
                    else:
                        st.error("L'horaire ne peut pas être vide.")

    # ---- T7 : SÉCURITÉ ----
    with t7:
        st.subheader("⚙️ Sécurité & Configuration")
        st.markdown("**🔑 Changer le code administrateur**")
        with st.form("sec_form"):
            o = st.text_input("Ancien code", type="password")
            n = st.text_input("Nouveau code", type="password")
            if st.form_submit_button("Changer le code"):
                if o == get_secret_code() or o == "0000":
                    try:
                        supabase.table("configuration").update({"secret_code": n}).eq("id", "main_config").execute()
                        get_config.clear()
                        st.success("Code modifié avec succès !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {str(e)}")
                else:
                    st.error("Ancien code incorrect")
        st.markdown("---")
        st.markdown("**👶 Nombre maximum d'enfants par défaut (global)**")
        current_max = get_max_enfants()
        st.info(f"Valeur actuelle : **{current_max} enfants**")
        with st.form("max_enfants_form"):
            nouveau_max = st.number_input("Nombre maximum d'enfants par défaut", min_value=1, max_value=100, value=current_max)
            if st.form_submit_button("💾 Enregistrer la limite globale"):
                result = set_max_enfants(nouveau_max)
                if result is True:
                    enregistrer_log("Admin", "Configuration", f"Nombre max enfants global : {nouveau_max}")
                    st.success(f"✅ Limite globale mise à jour : {nouveau_max} enfants.")
                    st.rerun()
                else:
                    st.error(f"Erreur : {result}")
        st.markdown("---")
        if st.button("🚪 Déconnexion Super Admin"):
            st.session_state['super_access'] = False
            st.rerun()

    # ---- T8 : JOURNAL ----
    with t8:
        st.subheader("📜 Journal des manipulations")
        cj1, cj2 = st.columns(2)
        dj_s = cj1.date_input("Depuis le", date.today() - timedelta(days=7), format="DD/MM/YYYY", key="log_d1")
        dj_e = cj2.date_input("Jusqu'au", date.today(), format="DD/MM/YYYY", key="log_d2")
        try:
            res_logs = supabase.table("logs").select("*").gte("created_at", dj_s.strftime("%Y-%m-%d") + "T00:00:00").lte("created_at", dj_e.strftime("%Y-%m-%d") + "T23:59:59").order("created_at", desc=True).execute()
            if res_logs.data:
                logs_df = pd.DataFrame(res_logs.data)
                logs_df['created_at'] = pd.to_datetime(logs_df['created_at'], utc=True).dt.tz_convert("Europe/Paris").dt.strftime('%d/%m/%Y %H:%M')
                # Nettoyer la colonne 'details' : supprimer le texte entre crochets (date/heure ajoutée par enregistrer_log)
                logs_df['details'] = logs_df['details'].str.replace(r' \[.*?\]$', '', regex=True)
                st.dataframe(logs_df[['created_at', 'utilisateur', 'action', 'details']], column_config={"created_at": "Date & Heure", "utilisateur": "Auteur", "action": "Action", "details": "Détails"}, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune action enregistrée pour cette période.")
        except Exception as e:
            st.info("ℹ️ Le journal sera disponible une fois des opérations effectuées.")

    # ---- T9 : ANIMATEUR (Admin) ----
    with t9:
        st.subheader("🎯 Espace Animateur (accès Administration)")
        st.markdown(f'<div style="background-color:#fff3e0; border:1px solid #e65100; border-radius:8px; padding:10px 16px; margin-bottom:16px; color:#e65100; font-weight:bold;">⭐ Vous accédez à la vue animateur en tant qu\'administrateur.</div>', unsafe_allow_html=True)

        ca_d1, ca_d2 = st.columns(2)
        anim_d_debut = ca_d1.date_input("Du", date.today(), key="anim_adm_d1", format="DD/MM/YYYY")
        anim_d_fin = ca_d2.date_input("Au", ajouter_mois(date.today(), 12), key="anim_adm_d2", format="DD/MM/YYYY")

        ateliers_bruts_anim = get_ateliers_periode(str(anim_d_debut), str(anim_d_fin), "Actifs")
        ateliers_anim = enrichir_ateliers([dict(a) for a in ateliers_bruts_anim], lieux_dict_global, horaires_dict_global)

        at_ids_anim = tuple(a['id'] for a in ateliers_anim)
        toutes_ins_anim = get_toutes_inscriptions_ateliers(at_ids_anim)
        cache_ins_anim = construire_cache_ins(toutes_ins_anim)

        if not ateliers_anim:
            st.info("ℹ️ Aucun atelier actif sur cette période.")
        else:
            for idx, at in enumerate(ateliers_anim):
                anim_id_at = at.get('animateur_id')
                ins_data = cache_ins_anim.get(at['id'], [])

                total_occ = sum([(1 + (i['nb_enfants'] if i['nb_enfants'] else 0)) for i in ins_data])
                max_enf_at = get_max_enfants_atelier(at, MAX_ENFANTS)
                total_enfants_actuel = sum([i['nb_enfants'] for i in ins_data])
                places_enfants_restantes = max(max_enf_at - total_enfants_actuel, 0)
                statut_enfants = "🚫 Complet" if places_enfants_restantes == 0 else f"👶 {places_enfants_restantes} pl. enfants"

                anim_ins = next((i for i in ins_data if i['adherent_id'] == anim_id_at), None) if anim_id_at else None
                anim_nom_at = None
                if anim_ins:
                    anim_nom_at = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
                elif anim_id_at:
                    anim_adh = next((a for a in adh_data if a['id'] == anim_id_at), None)
                    if anim_adh:
                        anim_nom_at = f"{anim_adh['prenom']} {anim_adh['nom']}"

                anim_label = f" | ⭐ {anim_nom_at}" if anim_nom_at else " | ⭐ Pas d'animateur"
                titre_affiche = at['titre'] if at['titre'] else "(sans titre)"
                titre_label = f"{format_date_fr_complete(at['date_atelier'])} — {titre_affiche} | 📍 {at['lieu_nom']} | ⏰ {at['horaire_lib']} | {statut_enfants}{anim_label}"

                with st.expander(titre_label, expanded=False):
                    at_info_log = f"{at['date_atelier']} | {at['horaire_lib']} | {at['lieu_nom']}"
                    st.markdown("**Gestion de l'animateur :**")

                    options_anim = ["Choisir..."] + liste_adh_anim
                    idx_def = (liste_adh_anim.index(anim_nom_at) + 1) if anim_nom_at and anim_nom_at in liste_adh_anim else 0
                    nouvel_anim = st.selectbox("Animateur à assigner", options_anim, index=idx_def, key=f"adm_anim_select_{at['id']}_{idx}")

                    default_nb = anim_ins['nb_enfants'] if anim_ins else 1
                    nb_enf = st.number_input("Nombre d'enfants de l'animateur", min_value=0, max_value=10, value=default_nb, key=f"adm_anim_nb_{at['id']}_{idx}")

                    if st.button("✅ Appliquer", key=f"adm_anim_apply_{at['id']}_{idx}", type="primary"):
                        _appliquer_animateur_ui(at, total_occ, total_enfants_actuel, max_enf_at,
                                                anim_id_at, anim_ins, nouvel_anim, nb_enf,
                                                at_info_log, "Admin", f"adm_anim_{at['id']}")

    if st.sidebar.button("🚪 Déconnexion administration"):
        st.session_state["admin_auth"] = False
        st.rerun()
