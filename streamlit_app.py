import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from supabase import create_client, Client
import hashlib
import io
from fpdf import FPDF

# ==========================================
# CONFIGURATION ET INITIALISATION
# ==========================================
st.set_page_config(page_title="Résa GDF", page_icon="🌿", layout="wide")

# --- GATEKEEPER : Code d'accès général ---
def check_access():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.markdown("""
            <div style="display: flex; align-items: center; justify-content: center; min-height: 60vh;">
                <div style="background-color: #cfe9ff; padding: 2rem; border-radius: 20px; text-align: center; border: 2px solid #1b5e20;">
                    <h2 style="color: #1b5e20;">🔐 Accès sécurisé</h2>
                    <p style="color: #1b5e20;">Veuillez saisir le code d'accès pour continuer.</p>
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
    <div style="display: flex; align-items: center; background-color: #e6f4ff; padding: 20px; border-radius: 15px; margin-bottom: 25px; border: 1px solid #a8cfe8;">
        <div style="font-size: 3.5rem; margin-right: 20px;">🎨</div>
        <div>
            <h1 style="color: #1b5e20; margin: 0;">Résa GDF</h1>
            <p style="margin: 0; color: #0a3d0a; font-weight: bold;">Ateliers d'éveil & Activités manuelles</p>
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
    html, body, [class*="st-"] { font-size: 1.05rem !important; background-color: #e6f4ff !important; color: #1b5e20 !important; }
    .stApp { background-color: #e6f4ff; }
    .lieu-badge { padding: 3px 10px; border-radius: 6px; color: white; font-weight: bold; font-size: 0.85rem; display: inline-block; margin: 2px 0; }
    .horaire-text { font-size: 0.9rem; color: #2e7d32; font-weight: 400; }
    .compteur-badge { font-size: 0.85rem; font-weight: 600; padding: 2px 8px; border-radius: 4px; background-color: #d4e6f1; color: #1b5e20; border: 1px solid #1b5e20; margin-left: 5px; }
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
    div[data-testid="column"] .stButton button {
        border-radius: 30px !important;
        border: 1px solid #a8e6cf !important;
        background-color: transparent !important;
        color: #1b5e20 !important;
        transition: all 0.2s;
    }
    div[data-testid="column"] .stButton button[kind="primary"] {
        background-color: #a8e6cf !important;
        color: #1b5e20 !important;
        border-color: #7ec8a3 !important;
        font-weight: bold;
    }
    div[data-testid="column"] .stButton button:hover {
        background-color: #d4f5e8 !important;
        border-color: #7ec8a3 !important;
    }
    .filtre-vert-menthe {
        display: inline-flex;
        gap: 8px;
        margin-bottom: 12px;
        flex-wrap: wrap;
    }
    .filtre-btn {
        border: 1.5px solid #80cbc4 !important;
        border-radius: 6px !important;
        padding: 3px 14px !important;
        background: transparent !important;
        color: #1b5e20 !important;
        font-size: 0.92rem !important;
        cursor: pointer !important;
        font-weight: 500;
    }
    .filtre-btn.actif {
        background-color: #b2dfdb !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS UTILITAIRES ---
def get_color(nom_lieu):
    colors = [
        "#2e7d32", "#1565c0", "#6a1b9a", "#c62828", "#e65100",
        "#00695c", "#4527a0", "#ad1457", "#558b2f", "#0277bd",
        "#4e342e", "#37474f", "#f9a825", "#0d47a1", "#1b5e20"
    ]
    hash_object = hashlib.md5(str(nom_lieu).upper().strip().encode())
    hue = int(hash_object.hexdigest()[:8], 16) % len(colors)
    return colors[hue]

def get_secret_code():
    try:
        res = supabase.table("configuration").select("secret_code").eq("id", "main_config").execute()
        return res.data[0]['secret_code'] if res.data else "1234"
    except:
        return "1234"

def get_max_enfants():
    try:
        res = supabase.table("configuration").select("max_enfants").eq("id", "main_config").execute()
        if res.data and res.data[0].get('max_enfants') is not None:
            return int(res.data[0]['max_enfants'])
    except:
        pass
    return 20

def set_max_enfants(valeur):
    try:
        supabase.table("configuration").update({"max_enfants": valeur}).eq("id", "main_config").execute()
        return True
    except Exception as e:
        return str(e)

def get_max_enfants_atelier(at):
    val = at.get('max_enfants')
    if val is not None:
        return int(val)
    return MAX_ENFANTS

def heure_paris_fr():
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
            "septembre", "octobre", "novembre", "décembre"]
    now = datetime.now(ZoneInfo("Europe/Paris"))
    return f"le {jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year} à {now.hour:02d}h{now.minute:02d}"

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
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    if isinstance(date_obj, str):
        try: date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        except: return date_obj
    res = f"{jours[date_obj.weekday()]} {date_obj.day} {mois[date_obj.month-1]} {date_obj.year}"
    return f"**{res}**" if gras else res

def format_date_fr_simple(date_str):
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    try:
        d = datetime.strptime(str(date_str), '%Y-%m-%d')
        return f"{jours[d.weekday()]} {d.day} {mois[d.month-1]} {d.year}"
    except:
        return str(date_str)

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
        jour = parts[1]
        mois_texte = parts[2].lower()
        annee = parts[3]
        mois_numerique = ["janvier", "février", "mars", "avril", "mai", "juin",
                          "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        if mois_texte in mois_numerique:
            m = mois_numerique.index(mois_texte) + 1
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

def is_verrouille(at):
    return bool(at.get("est_verrouille", False))

def trier_par_nom_puis_date(data):
    return sorted(data, key=lambda i: (
        i['adherents']['nom'].upper(),
        i['adherents']['prenom'].upper(),
        i['ateliers']['date_atelier']
    ))

# --- FONCTIONS ANIMATEUR ---
def get_animateur_atelier(at_id):
    try:
        res = supabase.table("ateliers").select("animateur_id").eq("id", at_id).execute()
        if res.data and res.data[0].get('animateur_id'):
            anim_id = res.data[0]['animateur_id']
            res_adh = supabase.table("adherents").select("id, nom, prenom").eq("id", anim_id).execute()
            if res_adh.data:
                return res_adh.data[0]
    except:
        pass
    return None

def get_inscription_animateur(at_id, animateur_id):
    try:
        res = supabase.table("inscriptions").select("*").eq("atelier_id", at_id).eq("adherent_id", animateur_id).execute()
        if res.data:
            return res.data[0]
    except:
        pass
    return None

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
                "adherent_id": nouvel_anim_id,
                "atelier_id": at_id,
                "nb_enfants": nb_enfants
            }).execute()
        enregistrer_log(auteur, "Attribution animateur", f"Animateur ID {nouvel_anim_id} assigné à atelier ID {at_id} ({nb_enfants} enf.)")
        return True
    except Exception as e:
        return str(e)

def retirer_animateur(at_id, anim_id, auteur="Admin"):
    try:
        supabase.table("inscriptions").delete().eq("atelier_id", at_id).eq("adherent_id", anim_id).execute()
        supabase.table("ateliers").update({"animateur_id": None}).eq("id", at_id).execute()
        enregistrer_log(auteur, "Retrait animateur", f"Animateur retiré de l'atelier ID {at_id}")
        return True
    except Exception as e:
        return str(e)

def afficher_liste_inscrits_avec_animateur(ins_data, animateur_id, mode="simple"):
    animateur_ins = None
    autres_ins = []
    for i in ins_data:
        if i['adherent_id'] == animateur_id:
            animateur_ins = i
        else:
            autres_ins.append(i)
    autres_tries = sorted(autres_ins, key=lambda x: (x['adherents']['nom'].upper(), x['adherents']['prenom'].upper()))

    if mode == "html":
        html = "<div class='container-inscrits'>"
        if animateur_ins:
            n = f"{animateur_ins['adherents']['prenom']} {animateur_ins['adherents']['nom']}"
            html += f'<span class="animateur-inscrit">⭐ {n} <span class="nb-enfants-focus">({animateur_ins["nb_enfants"]} enfants)</span> <span class="animateur-badge">ANIMATEUR</span></span>'
        for p in autres_tries:
            n = f"{p['adherents']['prenom']} {p['adherents']['nom']}"
            html += f'<span class="liste-inscrits">• {n} <span class="nb-enfants-focus">({p["nb_enfants"]} enfants)</span></span>'
        html += "</div>"
        return html
    else:
        return animateur_ins, autres_tries

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
    pdf.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=11)
    if not data_list:
        pdf.multi_cell(0, 10, txt="Aucune donnée à exporter.")
    else:
        for line in data_list:
            pdf.multi_cell(0, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

def export_stats_pdf(title, data_list, date_debut, date_fin):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(4)
    pdf.set_font("Arial", 'I', 11)
    periode_str = f"Période : du {format_date_fr_simple(str(date_debut))} au {format_date_fr_simple(str(date_fin))}"
    pdf.cell(0, 8, periode_str.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(8)
    pdf.set_font("Arial", size=11)
    if not data_list:
        pdf.multi_cell(0, 10, txt="Aucune donnée à exporter.")
    else:
        for line in data_list:
            pdf.multi_cell(0, 10, txt=line.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

def export_suivi_am_pdf(title, data_triee):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(6)
    if not data_triee:
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 10, txt="Aucune inscription trouvée.", ln=True)
        return pdf.output(dest='S').encode('latin-1')
    curr_am = ""
    for i in data_triee:
        nom_am = f"{i['adherents']['prenom']} {i['adherents']['nom']}"
        at = i['ateliers']
        date_fr = format_date_fr_simple(at['date_atelier'])
        titre_at = at.get('titre', '')
        lieu = at.get('lieu_nom', '?')
        horaire = at.get('horaire_lib', '?')
        nb_enf = i['nb_enfants']
        if nom_am != curr_am:
            pdf.ln(3)
            pdf.set_fill_color(27, 94, 32)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 9, f"  {nom_am}".encode('latin-1', 'replace').decode('latin-1'), ln=True, fill=True)
            pdf.set_text_color(0, 0, 0)
            curr_am = nom_am
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 6, f"  {date_fr}".encode('latin-1', 'replace').decode('latin-1'), ln=True)
        pdf.set_font("Arial", size=10)
        detail = f"     {titre_at}  |  {lieu}  |  {horaire}  |  {nb_enf} enfant(s)"
        pdf.cell(0, 6, detail.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    return pdf.output(dest='S').encode('latin-1')

def export_planning_ateliers_pdf(title, ateliers_data, get_inscrits_fn, animateurs_dict=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(6)
    if not ateliers_data:
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 10, txt="Aucun atelier trouvé sur cette période.", ln=True)
        return pdf.output(dest='S').encode('latin-1')
    for a in ateliers_data:
        ins_at = get_inscrits_fn(a['id'])
        t_ad = len(ins_at)
        t_en = sum([p['nb_enfants'] for p in ins_at])
        restantes = a['capacite_max'] - (t_ad + t_en)
        date_fr = format_date_fr_simple(a['date_atelier'])
        titre_at = a.get('titre', '')
        lieu = a.get('lieu_nom', '?')
        horaire = a.get('horaire_lib', '?')
        verrou = " [VERROUILLE]" if is_verrouille(a) else ""
        pdf.set_fill_color(212, 230, 241)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 11)
        entete = f"  {date_fr} | {titre_at} | {lieu}{verrou}"
        pdf.cell(0, 8, entete.encode('latin-1', 'replace').decode('latin-1'), ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        sous = f"     Horaire : {horaire}  |  AM : {t_ad}  |  Enfants : {t_en}  |  Places restantes : {restantes}"
        pdf.cell(0, 6, sous.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        anim_id = a.get('animateur_id')
        anim_ins = next((p for p in ins_at if p['adherent_id'] == anim_id), None) if anim_id else None
        autres = [p for p in ins_at if p['adherent_id'] != anim_id]
        autres_tries = sorted(autres, key=lambda x: (x['adherents']['nom'].upper(), x['adherents']['prenom'].upper()))
        if anim_ins:
            nom_p = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
            ligne = f"       ★ {nom_p}  ({anim_ins['nb_enfants']} enfant(s)) [ANIMATEUR]"
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 6, ligne.encode('latin-1', 'replace').decode('latin-1'), ln=True)
            pdf.set_font("Arial", size=10)
        for p in autres_tries:
            nom_p = f"{p['adherents']['prenom']} {p['adherents']['nom']}"
            ligne = f"       • {nom_p}  ({p['nb_enfants']} enfant(s))"
            pdf.cell(0, 6, ligne.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        pdf.ln(3)
    return pdf.output(dest='S').encode('latin-1')

def export_planning_ateliers_pdf_with_period(title, ateliers_data, get_inscrits_fn, date_debut, date_fin, animateurs_dict=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(2)
    pdf.set_font("Arial", 'I', 11)
    periode_str = f"Période : du {format_date_fr_simple(str(date_debut))} au {format_date_fr_simple(str(date_fin))}"
    pdf.cell(0, 8, periode_str.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
    pdf.ln(4)
    if not ateliers_data:
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 10, txt="Aucun atelier trouvé sur cette période.", ln=True)
        return pdf.output(dest='S').encode('latin-1')
    for a in ateliers_data:
        ins_at = get_inscrits_fn(a['id'])
        t_ad = len(ins_at)
        t_en = sum([p['nb_enfants'] for p in ins_at])
        restantes = a['capacite_max'] - (t_ad + t_en)
        date_fr = format_date_fr_simple(a['date_atelier'])
        titre_at = a.get('titre', '')
        lieu = a.get('lieu_nom', '?')
        horaire = a.get('horaire_lib', '?')
        verrou = " [VERROUILLE]" if is_verrouille(a) else ""
        pdf.set_fill_color(212, 230, 241)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 11)
        entete = f"  {date_fr} | {titre_at} | {lieu}{verrou}"
        pdf.cell(0, 8, entete.encode('latin-1', 'replace').decode('latin-1'), ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        sous = f"     Horaire : {horaire}  |  AM : {t_ad}  |  Enfants : {t_en}  |  Places restantes : {restantes}"
        pdf.cell(0, 6, sous.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        anim_id = a.get('animateur_id')
        anim_ins = next((p for p in ins_at if p['adherent_id'] == anim_id), None) if anim_id else None
        autres = [p for p in ins_at if p['adherent_id'] != anim_id]
        autres_tries = sorted(autres, key=lambda x: (x['adherents']['nom'].upper(), x['adherents']['prenom'].upper()))
        if anim_ins:
            nom_p = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
            ligne = f"       ★ {nom_p}  ({anim_ins['nb_enfants']} enfant(s)) [ANIMATEUR]"
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 6, ligne.encode('latin-1', 'replace').decode('latin-1'), ln=True)
            pdf.set_font("Arial", size=10)
        for p in autres_tries:
            nom_p = f"{p['adherents']['prenom']} {p['adherents']['nom']}"
            ligne = f"       • {nom_p}  ({p['nb_enfants']} enfant(s))"
            pdf.cell(0, 6, ligne.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        pdf.ln(3)
    return pdf.output(dest='S').encode('latin-1')

# --- WIDGET FILTRE VERT MENTHE ---
def filtre_vert_menthe(label_key, options=("Tous", "Actifs", "Inactifs"), default="Tous"):
    if label_key not in st.session_state:
        st.session_state[label_key] = default
    cols = st.columns(len(options) + 5)
    for i, opt in enumerate(options):
        actif = st.session_state[label_key] == opt
        with cols[i]:
            if st.button(opt, key=f"filtre_btn_{label_key}_{opt}", help=f"Filtrer : {opt}", use_container_width=False):
                st.session_state[label_key] = opt
                st.rerun()
    return st.session_state[label_key]

# --- DIALOGUES ---
@st.dialog("⚠️ Confirmation")
def secure_delete_dialog(table, item_id, label, current_code):
    st.write(f"Voulez-vous vraiment désactiver/supprimer : **{label}** ?")
    pw = st.text_input("Code secret admin", type="password")
    if st.button("Confirmer", type="primary"):
        if pw == current_code or pw == "0000":
            supabase.table(table).update({"est_actif": False}).eq("id", item_id).execute()
            st.success("Opération réussie"); st.rerun()
        else: st.error("Code incorrect")

@st.dialog("✏️ Modifier une AM")
def edit_am_dialog(am_id, nom_actuel, prenom_actuel):
    new_nom = st.text_input("Nom", value=nom_actuel).upper().strip()
    new_pre = st.text_input("Prénom", value=prenom_actuel).strip()
    if st.button("Enregistrer"):
        if new_nom and new_pre:
            supabase.table("adherents").update({"nom": new_nom, "prenom": new_pre}).eq("id", am_id).execute()
            st.success("Modifié !"); st.rerun()

@st.dialog("⚠️ Suppression Atelier")
def delete_atelier_dialog(at_id, titre, a_des_inscrits, current_code):
    st.warning(f"Voulez-vous supprimer l'atelier : **{titre}** ?")
    pw = st.text_input("Code secret admin", type="password")
    if st.button("Confirmer la suppression définitive"):
        if pw == current_code or pw == "0000":
            if a_des_inscrits: supabase.table("inscriptions").delete().eq("atelier_id", at_id).execute()
            supabase.table("ateliers").delete().eq("id", at_id).execute()
            st.rerun()

@st.dialog("⚠️ Confirmer la désinscription")
def confirm_unsubscribe_dialog(ins_id, nom_complet, atelier_info, user_admin="Utilisateur"):
    st.warning(f"Souhaitez-vous vraiment annuler la réservation de **{nom_complet}** ?")
    if st.button("Oui, désinscrire", type="primary"):
        enregistrer_log(user_admin, "Désinscription", f"Annulation pour {nom_complet} - {atelier_info}")
        supabase.table("inscriptions").delete().eq("id", ins_id).execute()
        st.rerun()

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
def edit_atelier_dialog(at_id, titre_actuel, date_actuelle, lieu_id_actuel, horaire_id_actuel, capacite_actuelle, max_enfants_actuel, lieux_list, horaires_list, map_lieu_id, map_horaire_id):
    if not lieux_list:
        st.error("Aucun lieu disponible. Veuillez d'abord créer des lieux dans l'onglet 'Lieux / Horaires'.")
        return
    if not horaires_list:
        st.error("Aucun horaire disponible. Veuillez d'abord créer des horaires dans l'onglet 'Lieux / Horaires'.")
        return
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
    
    # Champ pour la date
    date_actuelle_obj = datetime.strptime(date_actuelle, '%Y-%m-%d').date() if isinstance(date_actuelle, str) else date_actuelle
    nouvelle_date = st.date_input("Date de l'atelier", value=date_actuelle_obj, format="DD/MM/YYYY")

    nouveau_titre = st.text_input("Titre", value=titre_actuel)
    nouveau_lieu = st.selectbox("Lieu", options=lieux_options, index=lieux_options.index(lieu_actuel_nom) if lieu_actuel_nom in lieux_options else 0)
    nouvel_horaire = st.selectbox("Horaire", options=horaires_options, index=horaires_options.index(horaire_actuel_lib) if horaire_actuel_lib in horaires_options else 0)
    nouvelle_capacite = st.number_input("Capacité maximale (places totales)", min_value=1, value=int(capacite_actuelle))

    st.markdown("---")
    st.markdown("**👶 Limite d'enfants pour cet atelier**")
    val_max_enf = max_enfants_actuel if max_enfants_actuel is not None else MAX_ENFANTS
    nouvelle_limite_enfants = st.number_input(
        "Nombre maximum d'enfants acceptés sur cet atelier",
        min_value=0,
        max_value=200,
        value=int(val_max_enf),
        help=f"Valeur globale configurée : {MAX_ENFANTS}. Mettre 0 pour utiliser la valeur globale."
    )
    if nouvelle_limite_enfants == 0:
        st.caption(f"ℹ️ La limite globale ({MAX_ENFANTS} enfants) sera appliquée.")
    else:
        st.caption(f"ℹ️ Limite spécifique : {nouvelle_limite_enfants} enfants pour cet atelier.")

    if nouvelle_capacite < total_occupation:
        st.error(f"La capacité ne peut pas être inférieure au nombre actuel d'occupants ({total_occupation} places prises).")

    if nouvelle_limite_enfants > 0 and nouvelle_limite_enfants < nb_enfants_actuels:
        st.error(f"La limite d'enfants ne peut pas être inférieure au nombre d'enfants déjà inscrits ({nb_enfants_actuels}).")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Annuler", use_container_width=True):
            st.rerun()
    with col2:
        disable_save = (nouvelle_capacite < total_occupation) or (nouvelle_limite_enfants > 0 and nouvelle_limite_enfants < nb_enfants_actuels)
        if st.button("Enregistrer", type="primary", use_container_width=True, disabled=disable_save):
            nouveau_lieu_id = next(l['id'] for l in lieux_list if l['nom'] == nouveau_lieu)
            nouvel_horaire_id = next(h['id'] for h in horaires_list if h['libelle'] == nouvel_horaire)
            val_a_stocker = nouvelle_limite_enfants if nouvelle_limite_enfants > 0 else None
            supabase.table("ateliers").update({
                "date_atelier": nouvelle_date.strftime('%Y-%m-%d'),
                "titre": nouveau_titre,
                "lieu_id": nouveau_lieu_id,
                "horaire_id": nouvel_horaire_id,
                "capacite_max": nouvelle_capacite,
                "max_enfants": val_a_stocker
            }).eq("id", at_id).execute()
            enregistrer_log("Admin", "Modification atelier", f"Atelier ID {at_id} modifié : date={nouvelle_date}, titre={nouveau_titre}, lieu={nouveau_lieu}, horaire={nouvel_horaire}, capacité={nouvelle_capacite}, max_enfants={val_a_stocker}")
            st.success("Atelier modifié avec succès !")
            st.rerun()

@st.dialog("🎯 Attribuer / Changer l'animateur")
def dialog_attribuer_animateur(at_id, titre_at, ancien_anim_id, ancien_anim_nom, liste_adh_anim, dict_adh_anim, auteur="Animateur"):
    st.markdown(f"**Atelier :** {titre_at}")
    if ancien_anim_nom:
        st.info(f"Animateur actuel : **{ancien_anim_nom}**")
    else:
        st.info("Aucun animateur assigné.")
    options_anim = ["Choisir..."] + liste_adh_anim
    idx_def = 0
    if ancien_anim_nom and ancien_anim_nom in liste_adh_anim:
        idx_def = liste_adh_anim.index(ancien_anim_nom) + 1
    nouvel_anim = st.selectbox("Choisir l'animateur", options_anim, index=idx_def)
    nb_enf = st.number_input("Nombre d'enfants de l'animateur", min_value=0, max_value=10, value=1)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Annuler", use_container_width=True):
            st.rerun()
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
    st.warning(f"Voulez-vous retirer **{anim_nom}** de son rôle d'animateur pour l'atelier **{titre_at}** ?")
    st.write("Son inscription sera également supprimée.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Annuler", use_container_width=True):
            st.rerun()
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
                    st.success("Horaire modifié !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {str(e)}")

# --- INITIALISATION DES RÉFÉRENTIELS EN SESSION ---
if 'lieux_list' not in st.session_state:
    st.session_state.lieux_list = []
if 'horaires_list' not in st.session_state:
    st.session_state.horaires_list = []

def refresh_referentials():
    try:
        res_lieux = supabase.table("lieux").select("*").order("nom").execute()
        all_lieux = res_lieux.data or []
        st.session_state.lieux_list = [l for l in all_lieux if l.get("est_actif", True) is not False]
    except:
        st.session_state.lieux_list = []
    try:
        res_hor = supabase.table("horaires").select("*").execute()
        all_hor = res_hor.data or []
        st.session_state.horaires_list = [h for h in all_hor if h.get("est_actif", True) is not False]
    except:
        st.session_state.horaires_list = []

refresh_referentials()

# --- CHARGEMENT DES AUTRES DONNÉES GLOBALES ---
if 'at_list_gen' not in st.session_state: st.session_state['at_list_gen'] = []
if 'super_access' not in st.session_state: st.session_state['super_access'] = False

current_code = get_secret_code()
MAX_ENFANTS = get_max_enfants()

# --- Chargement sécurisé des adhérents ---
try:
    res_adh = supabase.table("adherents").select("*").eq("est_actif", True).order("nom").order("prenom").execute()
    adh_data = res_adh.data if res_adh.data else []
except:
    adh_data = []

dict_adh = {f"{a['prenom']} {a['nom']}": a['id'] for a in adh_data}
liste_adh = list(dict_adh.keys())

adh_animateurs = [a for a in adh_data if a.get('est_animateur', False)]
dict_adh_anim = {f"{a['prenom']} {a['nom']}": a['id'] for a in adh_animateurs}
liste_adh_anim = list(dict_adh_anim.keys())
set_id_animateurs = {a['id'] for a in adh_animateurs}

# --- SIDEBAR : Sélection utilisateur + Navigation ---
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
# SECTION 🎯 ANIMATEUR (affichage places enfants, gestion animateur)
# ==========================================
if menu == "🎯 Animateur":
    st.header(f"🎯 Espace Animateur — {user_connecte}")
    st.markdown(f'<div style="background-color:#fff3e0; border:1px solid #e65100; border-radius:8px; padding:10px 16px; margin-bottom:16px; color:#e65100; font-weight:bold;">⭐ Vous êtes connecté(e) en tant qu\'animateur.</div>', unsafe_allow_html=True)

    today_str = str(date.today())
    try:
        ateliers_bruts = supabase.table("ateliers").select("*").eq("est_actif", True).gte("date_atelier", today_str).order("date_atelier").execute().data or []
    except:
        ateliers_bruts = []

    lieux_dict = {l['id']: l['nom'] for l in st.session_state.lieux_list}
    horaires_dict = {h['id']: h['libelle'] for h in st.session_state.horaires_list}
    ateliers = []
    for at in ateliers_bruts:
        at['lieu_nom'] = lieux_dict.get(at['lieu_id'], '?')
        at['horaire_lib'] = horaires_dict.get(at['horaire_id'], '?')
        ateliers.append(at)

    if not ateliers:
        st.info("ℹ️ Aucun atelier à venir.")
    else:
        for at in ateliers:
            anim_id_at = at.get('animateur_id')
            try:
                res_ins = supabase.table("inscriptions").select("*, adherents(nom, prenom)").eq("atelier_id", at['id']).execute()
                ins_data = res_ins.data if res_ins.data else []
            except:
                ins_data = []

            # Calculs des places
            total_occ = sum([(1 + (i['nb_enfants'] if i['nb_enfants'] else 0)) for i in ins_data])
            restantes = at['capacite_max'] - total_occ
            max_enf_at = get_max_enfants_atelier(at)
            total_enfants_actuel = sum([i['nb_enfants'] for i in ins_data])
            places_enfants_restantes = max(max_enf_at - total_enfants_actuel, 0)

            # Déterminer l'affichage des places enfants
            if places_enfants_restantes == 0:
                statut_enfants = "🚫 Complet"
            else:
                statut_enfants = f"👶 {places_enfants_restantes} pl. enfants"

            # Récupérer l'inscription de l'animateur actuel (s'il existe)
            anim_ins = next((i for i in ins_data if i['adherent_id'] == anim_id_at), None) if anim_id_at else None
            anim_nom_at = None
            if anim_ins:
                anim_nom_at = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
            elif anim_id_at:
                anim_adh = next((a for a in adh_data if a['id'] == anim_id_at), None)
                if anim_adh:
                    anim_nom_at = f"{anim_adh['prenom']} {anim_adh['nom']}"

            # Titre sans les places totales, uniquement places enfants
            anim_label = f" | ⭐ {anim_nom_at}" if anim_nom_at else " | ⭐ Pas d'animateur"
            titre_label = f"{format_date_fr_complete(at['date_atelier'])} — {at['titre']} | 📍 {at['lieu_nom']} | ⏰ {at['horaire_lib']} | {statut_enfants}{anim_label}"

            with st.expander(titre_label, expanded=False):
                at_info_log = f"{at['date_atelier']} | {at['horaire_lib']} | {at['lieu_nom']}"

                st.markdown("**Gestion de l'animateur :**")
                
                # Sélection de l'animateur (tous les animateurs disponibles)
                options_anim = ["Choisir..."] + liste_adh_anim
                if anim_nom_at and anim_nom_at in liste_adh_anim:
                    idx_def = liste_adh_anim.index(anim_nom_at) + 1
                else:
                    idx_def = 0
                nouvel_anim = st.selectbox("Animateur à assigner", options_anim, index=idx_def, key=f"anim_select_{at['id']}")
                
                # Nombre d'enfants de l'animateur (valeur actuelle ou 1 par défaut)
                nb_enf_actuel = anim_ins['nb_enfants'] if anim_ins else 1
                nb_enf = st.number_input("Nombre d'enfants de l'animateur", min_value=0, max_value=10, value=int(nb_enf_actuel), key=f"anim_nb_enf_{at['id']}")
                
                if st.button("✅ Appliquer", key=f"anim_apply_{at['id']}", type="primary"):
                    if nouvel_anim == "Choisir...":
                        st.warning("Veuillez sélectionner un animateur.")
                    else:
                        nouvel_anim_id = dict_adh_anim[nouvel_anim]
                        ancien_anim_id = anim_id_at
                        
                        # Calculer l'impact sur les places
                        if ancien_anim_id and ancien_anim_id != nouvel_anim_id:
                            ancien_nb = anim_ins['nb_enfants'] if anim_ins else 1
                            nouvelle_occupation = total_occ - (1 + ancien_nb) + (1 + nb_enf)
                            nouveau_total_enfants = total_enfants_actuel - ancien_nb + nb_enf
                        elif ancien_anim_id == nouvel_anim_id:
                            delta = nb_enf - nb_enf_actuel
                            nouvelle_occupation = total_occ + delta
                            nouveau_total_enfants = total_enfants_actuel + delta
                        else:
                            nouvelle_occupation = total_occ + 1 + nb_enf
                            nouveau_total_enfants = total_enfants_actuel + nb_enf
                        
                        # Vérifications
                        if nouveau_total_enfants > max_enf_at:
                            st.error(f"🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé.")
                        elif nouvelle_occupation > at['capacite_max']:
                            st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                        else:
                            # Appliquer les modifications
                            if ancien_anim_id and ancien_anim_id != nouvel_anim_id:
                                supabase.table("inscriptions").delete().eq("atelier_id", at['id']).eq("adherent_id", ancien_anim_id).execute()
                            supabase.table("ateliers").update({"animateur_id": nouvel_anim_id}).eq("id", at['id']).execute()
                            existing_new = supabase.table("inscriptions").select("id").eq("atelier_id", at['id']).eq("adherent_id", nouvel_anim_id).execute()
                            if existing_new.data:
                                supabase.table("inscriptions").update({"nb_enfants": nb_enf}).eq("id", existing_new.data[0]['id']).execute()
                            else:
                                supabase.table("inscriptions").insert({"adherent_id": nouvel_anim_id, "atelier_id": at['id'], "nb_enfants": nb_enf}).execute()
                            enregistrer_log(user_connecte, "Modification animateur", f"Animateur {nouvel_anim} ({nb_enf} enfants) - {at_info_log}")
                            st.success("Modification effectuée !")
                            st.rerun()

# ==========================================
# SECTION 📝 INSCRIPTIONS (message erreur capacité en rouge gras)
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
            lieux_dict = {l['id']: l['nom'] for l in st.session_state.lieux_list}
            horaires_dict = {h['id']: h['libelle'] for h in st.session_state.horaires_list}
            ateliers = []
            for at in ateliers_bruts:
                at['lieu_nom'] = lieux_dict.get(at['lieu_id'], '?')
                at['horaire_lib'] = horaires_dict.get(at['horaire_id'], '?')
                ateliers.append(at)

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
                    max_enf_at = get_max_enfants_atelier(at)
                    capacite_max = at['capacite_max']
                    
                    # Calculs
                    total_occ = sum([(1 + (i['nb_enfants'] if i['nb_enfants'] else 0)) for i in ins_data])
                    nb_enfants_inscrits = sum([i['nb_enfants'] for i in ins_data])  # total enfants (inclut animateur)
                    places_enfants_restantes = max(max_enf_at - nb_enfants_inscrits, 0)
                    atelier_enfants_complet = (nb_enfants_inscrits >= max_enf_at)
                    places_totales_restantes = capacite_max - total_occ

                    # Déterminer le statut d'affichage (uniquement sur les places enfants)
                    if places_enfants_restantes == 0:
                        statut_enfants = "🚫 Complet"
                    else:
                        statut_enfants = f"👶 {places_enfants_restantes} pl. enfants"

                    at_info_log = f"{at['date_atelier']} | {at['horaire_lib']} | {at['lieu_nom']}"
                    titre_label = f"{format_date_fr_complete(at['date_atelier'])} — {at['titre']} | 📍 {at['lieu_nom']} | ⏰ {at['horaire_lib']} | {statut_enfants}"

                    with st.expander(titre_label):
                        if is_verrouille(at):
                            st.warning("🔒 Cet atelier est géré par l'administration. Les inscriptions et désinscriptions ne sont pas disponibles ici.")

                        if ins_data:
                            # Animateur (non modifiable)
                            anim_ins = next((i for i in ins_data if i['adherent_id'] == anim_id_at), None) if anim_id_at else None
                            autres_ins = [i for i in ins_data if i['adherent_id'] != anim_id_at]
                            autres_tries = sorted(autres_ins, key=lambda x: (x['adherents']['nom'].upper(), x['adherents']['prenom'].upper()))

                            if anim_ins:
                                n_a = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
                                if is_verrouille(at):
                                    st.markdown(f'<span style="color:#e65100;font-weight:bold;">⭐ {n_a} <b>({anim_ins["nb_enfants"]} enf.)</b> <span style="background:#e65100;color:white;padding:1px 6px;border-radius:4px;font-size:0.78rem;">ANIMATEUR</span></span>', unsafe_allow_html=True)
                                else:
                                    col_a1, col_a2 = st.columns([0.88, 0.12])
                                    col_a1.markdown(f'<span style="color:#e65100;font-weight:bold;">⭐ {n_a} <b>({anim_ins["nb_enfants"]} enf.)</b> <span style="background:#e65100;color:white;padding:1px 6px;border-radius:4px;font-size:0.78rem;">ANIMATEUR</span></span>', unsafe_allow_html=True)
                                    col_a2.write("🔒")

                            # Autres inscriptions : ligne avec nom, champ nombre, bouton Modifier, bouton Désinscrire
                            for p in autres_tries:
                                n_f = f"{p['adherents']['prenom']} {p['adherents']['nom']}"
                                if is_verrouille(at):
                                    st.write(f"• {n_f} **({p['nb_enfants']} enf.)**")
                                else:
                                    col_nom, col_nb, col_modif, col_del = st.columns([0.4, 0.2, 0.2, 0.2])
                                    col_nom.write(f"• {n_f}")
                                    new_nb = col_nb.number_input("", min_value=1, max_value=10, value=p['nb_enfants'], key=f"nb_{p['id']}", label_visibility="collapsed")
                                    if col_modif.button("✏️ Modifier", key=f"mod_{p['id']}"):
                                        # Vérifier les limites : enfants ET places totales
                                        delta = new_nb - p['nb_enfants']
                                        nouveau_total_enfants = nb_enfants_inscrits + delta
                                        nouveau_total_occupation = total_occ + delta  # car on change le nb enfants, l'adulte reste
                                        if nouveau_total_enfants > max_enf_at:
                                            st.error(f"🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé.")
                                        elif nouveau_total_occupation > capacite_max:
                                            st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                                        else:
                                            supabase.table("inscriptions").update({"nb_enfants": new_nb}).eq("id", p['id']).execute()
                                            enregistrer_log(user_principal, "Modification", f"{n_f} → {new_nb} enfants - {at_info_log}")
                                            st.rerun()
                                    if col_del.button("🗑️", key=f"del_{p['id']}"):
                                        confirm_unsubscribe_dialog(p['id'], n_f, at_info_log, user_principal)

                        # Formulaire d'inscription
                        if not is_verrouille(at):
                            st.markdown("---")
                            try:
                                idx_def = (liste_adh.index(user_principal) + 1)
                            except:
                                idx_def = 0
                            col_qui, col_nb_e, col_btn = st.columns([2, 1, 1])
                            qui = col_qui.selectbox("Qui ?", ["Choisir..."] + liste_adh, index=idx_def, key=f"q_{at['id']}")
                            nb_e = col_nb_e.number_input("Enfants", 1, 10, 1, key=f"e_{at['id']}")

                            qui_est_anim = (qui != "Choisir..." and dict_adh.get(qui) == anim_id_at)
                            if qui_est_anim:
                                st.warning("🔒 Cette personne est l'animateur de cet atelier. Son inscription est gérée automatiquement.")
                            elif atelier_enfants_complet and qui != "Choisir...":
                                st.warning(f"🚫 Le nombre maximum d'enfants ({max_enf_at}) est atteint pour cet atelier.")
                            elif col_btn.button("Valider", key=f"v_{at['id']}", type="primary"):
                                if qui != "Choisir...":
                                    id_adh = dict_adh[qui]
                                    existing = next((ins for ins in ins_data if ins['adherent_id'] == id_adh), None)
                                    if existing:
                                        delta_enf = nb_e - existing['nb_enfants']
                                        nouveau_total_enfants = nb_enfants_inscrits + delta_enf
                                        nouveau_total_occupation = total_occ + delta_enf
                                        if nouveau_total_enfants > max_enf_at:
                                            st.error(f"🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé.")
                                        elif nouveau_total_occupation > capacite_max:
                                            st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                                        else:
                                            supabase.table("inscriptions").update({"nb_enfants": nb_e}).eq("id", existing['id']).execute()
                                            enregistrer_log(user_principal, "Modification", f"{qui} change à {nb_e} enfants - {at_info_log}")
                                            st.rerun()
                                    else:
                                        nouveau_total_enfants = nb_enfants_inscrits + nb_e
                                        nouveau_total_occupation = total_occ + 1 + nb_e  # +1 pour l'adulte
                                        if nouveau_total_enfants > max_enf_at:
                                            st.error(f"🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé.")
                                        elif nouveau_total_occupation > capacite_max:
                                            st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                                        else:
                                            supabase.table("inscriptions").insert({"adherent_id": id_adh, "atelier_id": at['id'], "nb_enfants": nb_e}).execute()
                                            enregistrer_log(user_principal, "Inscription", f"{qui} s'inscrit (+{nb_e} enf.) - {at_info_log}")
                                            st.rerun()
# ==========================================
# SECTION 📊 SUIVI & RÉCAP (inchangée)
# ==========================================
elif menu == "📊 Suivi & Récap":
    st.header("🔎 Consultation")
    t1, t2 = st.tabs(["👤 Par Assistante Maternelle", "📅 Par Atelier"])
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
                    lieux_dict = {l['id']: l['nom'] for l in st.session_state.lieux_list}
                    horaires_dict = {h['id']: h['libelle'] for h in st.session_state.horaires_list}
                    for ins in inscriptions_brutes:
                        at = ins['ateliers']
                        at['lieu_nom'] = lieux_dict.get(at['lieu_id'], '?')
                        at['horaire_lib'] = horaires_dict.get(at['horaire_id'], '?')
                        ins['ateliers'] = at
                    data_triee = trier_par_nom_puis_date(inscriptions_brutes) if inscriptions_brutes else []
                except:
                    data_triee = []

            df_export = pd.DataFrame([{
                "Assistante Maternelle": f"{i['adherents']['prenom']} {i['adherents']['nom']}",
                "Date": i['ateliers']['date_atelier'],
                "Atelier": i['ateliers']['titre'],
                "Lieu": i['ateliers']['lieu_nom'],
                "Horaire": i['ateliers']['horaire_lib'],
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
                    st.write(f"{format_date_fr_complete(at['date_atelier'], gras=True)} — {at['titre']} <span class='lieu-badge' style='background-color:{c_l}'>{at['lieu_nom']}</span> <span class='horaire-text'>({at['horaire_lib']})</span> **({i['nb_enfants']} enf.)**", unsafe_allow_html=True)
            else:
                st.info("Aucune inscription trouvée pour les AM sélectionnées.")

    with t2:
        c_d1, c_d2 = st.columns(2)
        d_s = c_d1.date_input("Du", date.today(), key="pub_d1", format="DD/MM/YYYY")
        d_e = c_d2.date_input("Au", d_s + timedelta(days=30), key="pub_d2", format="DD/MM/YYYY")
        try:
            ateliers_bruts = supabase.table("ateliers").select("*").eq("est_actif", True).gte("date_atelier", str(d_s)).lte("date_atelier", str(d_e)).order("date_atelier").execute().data or []
        except:
            ateliers_bruts = []
        lieux_dict = {l['id']: l['nom'] for l in st.session_state.lieux_list}
        horaires_dict = {h['id']: h['libelle'] for h in st.session_state.horaires_list}
        ateliers = []
        for a in ateliers_bruts:
            a['lieu_nom'] = lieux_dict.get(a['lieu_id'], '?')
            a['horaire_lib'] = horaires_dict.get(a['horaire_id'], '?')
            ateliers.append(a)
        all_ins_data = []
        cache_ins = {}
        if ateliers:
            for a in ateliers:
                try:
                    ins_at = supabase.table("inscriptions").select("*, adherents(nom, prenom)").eq("atelier_id", a['id']).execute().data or []
                except:
                    ins_at = []
                cache_ins[a['id']] = ins_at
                for p in ins_at:
                    all_ins_data.append({
                        "Date": a['date_atelier'], "Atelier": a['titre'], "Lieu": a['lieu_nom'],
                        "Horaire": a['horaire_lib'],
                        "AM": f"{p['adherents']['prenom']} {p['adherents']['nom']}", "Enfants": p['nb_enfants']
                    })
        df_at_exp = pd.DataFrame(all_ins_data) if all_ins_data else pd.DataFrame(columns=["Date", "Atelier", "Lieu", "Horaire", "AM", "Enfants"])
        ce1, ce2 = st.columns(2)
        ce1.download_button("📥 Excel Planning", data=export_to_excel(df_at_exp), file_name="planning_ateliers.xlsx", key="exp_at_xl")
        ce2.download_button("📥 PDF Planning", data=export_planning_ateliers_pdf(
            "Planning des Ateliers", ateliers, lambda aid: cache_ins.get(aid, [])
        ), file_name="planning_ateliers.pdf", key="exp_at_pdf")
        if ateliers:
            for index, a in enumerate(ateliers):
                c_l = get_color(a['lieu_nom'])
                anim_id_at = a.get('animateur_id')
                ins_at = cache_ins.get(a['id'], [])
                t_ad = len(ins_at)
                t_en = sum([p['nb_enfants'] for p in ins_at])
                restantes = a['capacite_max'] - (t_ad + t_en)
                
                # --- Calcul des places enfants restantes ---
                max_enf_at = get_max_enfants_atelier(a)
                nb_enfants_inscrits = t_en
                places_enfants_restantes = max(max_enf_at - nb_enfants_inscrits, 0)
                if places_enfants_restantes == 0:
                    statut_enfants = "🚫 Complet"
                else:
                    statut_enfants = f"👶 {places_enfants_restantes} pl. enfants"
                
                # Optionnel : si la capacité totale est dépassée, ajouter un avertissement
                if restantes < 0:
                    statut_enfants += " ⚠️ Salle saturée"
                
                st.markdown(f"**{format_date_fr_complete(a['date_atelier'])}** | {a['titre']} | <span class='lieu-badge' style='background-color:{c_l}'>{a['lieu_nom']}</span> | <span class='horaire-text'>{a['horaire_lib']}</span> <span class='compteur-badge'>👤 {t_ad} AM</span> <span class='compteur-badge'>👶 {t_en} enf.</span> <span class='compteur-badge'>{statut_enfants}</span>", unsafe_allow_html=True)
                
                if ins_at:
                    anim_ins = next((p for p in ins_at if p['adherent_id'] == anim_id_at), None) if anim_id_at else None
                    autres = [p for p in ins_at if p['adherent_id'] != anim_id_at]
                    autres_tries = sorted(autres, key=lambda x: (x['adherents']['nom'], x['adherents']['prenom']))
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

# ==========================================
# SECTION 🔐 ADMINISTRATION (inchangée, sauf la partie max_enfants déjà intégrée)
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

    with t1:  # ATELIERS
        refresh_referentials()
        l_raw = st.session_state.lieux_list
        h_raw = st.session_state.horaires_list
        l_list = [l['nom'] for l in l_raw]
        h_list = [h['libelle'] for h in h_raw]
        map_l_cap = {l['nom']: l.get('capacite', 10) for l in l_raw}
        map_l_id = {l['nom']: l['id'] for l in l_raw}
        map_h_id = {h['libelle']: h['id'] for h in h_raw}

        if not l_raw:
            st.warning("⚠️ Aucun lieu n'est défini. Veuillez en créer dans l'onglet '📍 Lieux / Horaires'.")
        if not h_raw:
            st.warning("⚠️ Aucun horaire n'est défini. Veuillez en créer dans l'onglet '📍 Lieux / Horaires'.")

        if "admin_atelier_mode" not in st.session_state:
            st.session_state["admin_atelier_mode"] = "Générateur"

        st.markdown("**Mode**")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📦 Générateur", use_container_width=True,
                         type="primary" if st.session_state["admin_atelier_mode"] == "Générateur" else "secondary"):
                st.session_state["admin_atelier_mode"] = "Générateur"
                st.rerun()
        with col2:
            if st.button("📋 Répertoire", use_container_width=True,
                         type="primary" if st.session_state["admin_atelier_mode"] == "Répertoire" else "secondary"):
                st.session_state["admin_atelier_mode"] = "Répertoire"
                st.rerun()
        with col3:
            if st.button("⚡ Actions groupées", use_container_width=True,
                         type="primary" if st.session_state["admin_atelier_mode"] == "Actions groupées" else "secondary"):
                st.session_state["admin_atelier_mode"] = "Actions groupées"
                st.rerun()

        sub = st.session_state["admin_atelier_mode"]

        if sub == "Générateur":
            if not l_raw or not h_raw:
                st.error("⛔ Impossible de générer des ateliers : aucun lieu ou horaire n'est encore défini.")
                st.info("👉 Allez d'abord dans l'onglet **📍 Lieux / Horaires** pour créer au moins un lieu et un horaire.")
            else:
                col_lieu, col_horaire = st.columns(2)
                with col_lieu:
                    lieu_par_defaut = st.selectbox("Lieu par défaut pour les nouvelles lignes :", options=[""] + l_list)
                with col_horaire:
                    horaire_par_defaut = st.selectbox("Horaire par défaut pour les nouvelles lignes :", options=[""] + h_list)
                c1, c2 = st.columns(2)
                d1 = c1.date_input("Début", date.today(), format="DD/MM/YYYY", key="gen_d1")
                d2 = c2.date_input("Fin", date.today() + timedelta(days=7), format="DD/MM/YYYY", key="gen_d2")
                jours = st.multiselect("Jours", ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"], default=["Lundi", "Jeudi"])
                if st.button("📊 Générer les lignes"):
                    tmp, curr = [], d1
                    while curr <= d2:
                        js_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
                        if js_fr[curr.weekday()] in jours:
                            lieu_val = lieu_par_defaut if lieu_par_defaut else ""
                            horaire_val = horaire_par_defaut if horaire_par_defaut else ""
                            capa = map_l_cap.get(lieu_val, 10) if lieu_val else 10
                            tmp.append({
                                "Date": format_date_fr_complete(curr, False),
                                "Titre": "",
                                "Lieu": lieu_val,
                                "Horaire": horaire_val,
                                "Capacité": capa,
                                "Max Enfants": MAX_ENFANTS,
                                "Actif": False,
                                "Verrouillé": False
                            })
                        curr += timedelta(days=1)
                    st.session_state['at_list_gen'] = tmp
                    st.rerun()
                if st.session_state['at_list_gen']:
                    st.markdown("""
                    <style>
                    [data-testid="stDataFrame"] { background-color: #ffffff !important; color: #000000 !important; }
                    [data-testid="stDataFrame"] * { color: #000000 !important; background-color: #ffffff !important; }
                    [data-testid="stDataFrame"] table { background-color: #ffffff !important; }
                    [data-testid="stDataFrame"] th { background-color: #f0f0f0 !important; color: #000000 !important; }
                    [data-testid="stDataFrame"] td { color: #000000 !important; }
                    </style>
                    """, unsafe_allow_html=True)
                    df_ed = st.data_editor(
                        pd.DataFrame(st.session_state['at_list_gen']),
                        num_rows="dynamic",
                        column_config={
                            "Lieu": st.column_config.SelectboxColumn(options=l_list, required=False),
                            "Horaire": st.column_config.SelectboxColumn(options=h_list, required=False),
                            "Max Enfants": st.column_config.NumberColumn(
                                min_value=0, max_value=200,
                                help=f"0 = utiliser la valeur globale ({MAX_ENFANTS})"
                            ),
                            "Actif": st.column_config.CheckboxColumn(default=False),
                            "Verrouillé": st.column_config.CheckboxColumn(default=False)
                        },
                        use_container_width=True,
                        key="editor_ateliers"
                    )
                    if st.button("💾 Enregistrer"):
                        to_db = []
                        for _, r in df_ed.iterrows():
                            lieu_nom = r['Lieu']
                            horaire_lib = r['Horaire']
                            if not lieu_nom or not horaire_lib:
                                st.warning(f"Ligne ignorée : lieu ou horaire manquant pour la date {r['Date']}")
                                continue
                            if lieu_nom not in map_l_id:
                                st.error(f"Lieu '{lieu_nom}' introuvable. Annulation.")
                                st.stop()
                            if horaire_lib not in map_h_id:
                                st.error(f"Horaire '{horaire_lib}' introuvable. Annulation.")
                                st.stop()
                            date_iso = parse_date_fr_to_iso(r['Date'])
                            if not date_iso:
                                st.error(f"Format de date invalide : {r['Date']}")
                                st.stop()
                            max_enf_val = int(r.get('Max Enfants', MAX_ENFANTS))
                            to_db.append({
                                "date_atelier": date_iso,
                                "titre": r['Titre'],
                                "lieu_id": map_l_id[lieu_nom],
                                "horaire_id": map_h_id[horaire_lib],
                                "capacite_max": int(r['Capacité']),
                                "max_enfants": max_enf_val if max_enf_val > 0 else None,
                                "est_actif": bool(r['Actif']),
                                "est_verrouille": bool(r.get("Verrouillé", False))
                            })
                        if to_db:
                            try:
                                supabase.table("ateliers").insert(to_db).execute()
                                st.session_state['at_list_gen'] = []
                                st.success(f"{len(to_db)} ateliers enregistrés avec succès !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de l'enregistrement : {str(e)}")
                        else:
                            st.warning("Aucune ligne valide à enregistrer (lieu ou horaire manquant).")

        elif sub == "Répertoire":
            cf1, cf2, cf3 = st.columns(3)
            fs = cf1.date_input("Du", date.today()-timedelta(days=30), format="DD/MM/YYYY", key="rep_d1")
            fe = cf2.date_input("Au", fs+timedelta(days=60), format="DD/MM/YYYY", key="rep_d2")
            ft = cf3.selectbox("Statut Filtre", ["Tous", "Actifs", "Inactifs"])
            try:
                ateliers_bruts = supabase.table("ateliers").select("*").gte("date_atelier", str(fs)).lte("date_atelier", str(fe)).order("date_atelier").execute().data or []
            except:
                ateliers_bruts = []
            lieux_dict = {l['id']: l['nom'] for l in st.session_state.lieux_list}
            horaires_dict = {h['id']: h['libelle'] for h in st.session_state.horaires_list}
            
            # Préparer la liste des ateliers avec calcul des places enfants restantes
            rep = []
            for a in ateliers_bruts:
                a['lieu_nom'] = lieux_dict.get(a['lieu_id'], '?')
                a['horaire_lib'] = horaires_dict.get(a['horaire_id'], '?')
                # Récupérer les inscriptions pour calculer les places enfants
                try:
                    ins = supabase.table("inscriptions").select("nb_enfants").eq("atelier_id", a['id']).execute()
                    inscriptions = ins.data if ins.data else []
                except:
                    inscriptions = []
                nb_enfants_inscrits = sum([i['nb_enfants'] for i in inscriptions])
                max_enf_at = get_max_enfants_atelier(a)
                places_enfants_restantes = max(max_enf_at - nb_enfants_inscrits, 0)
                a['places_enfants_restantes'] = places_enfants_restantes
                a['nb_enfants_inscrits'] = nb_enfants_inscrits
                rep.append(a)
            
            if not rep:
                st.info("Aucun atelier trouvé sur cette période.")
            else:
                for a in rep:
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
                    
                    # Affichage des places enfants restantes
                    if a['places_enfants_restantes'] == 0:
                        statut_enfants = "🚫 Complet"
                    else:
                        statut_enfants = f"👶 {a['places_enfants_restantes']} pl. enfants"
                    
                    # Optionnel : vérifier si la capacité totale est dépassée (pour affichage)
                    total_occ = sum([1 + i['nb_enfants'] for i in inscriptions]) if 'inscriptions' in locals() else 0
                    capacite_depassee = total_occ > a['capacite_max']
                    if capacite_depassee:
                        statut_enfants += " ⚠️ Salle saturée"
                    
                    ca, cb, cc, cd, ce, cf_anim = st.columns([0.38, 0.1, 0.1, 0.1, 0.1, 0.22])
                    ca.write(f"**{format_date_fr_complete(a['date_atelier'])}** | {a['horaire_lib']} | {a['titre']} ({a['lieu_nom']}){verrou_icon}{anim_label_rep} | {statut_enfants}")
                    btn_l = "🔴 Désactiver" if a['est_actif'] else "🟢 Activer"
                    if cb.button(btn_l, key=f"at_stat_{a['id']}"):
                        supabase.table("ateliers").update({"est_actif": not a['est_actif']}).eq("id", a['id']).execute()
                        st.rerun()
                    btn_v = "🔓 Déverrouiller" if is_verrouille(a) else "🔒 Verrouiller"
                    if cc.button(btn_v, key=f"at_verr_{a['id']}"):
                        nouvel_etat = not is_verrouille(a)
                        supabase.table("ateliers").update({"est_verrouille": bool(nouvel_etat)}).eq("id", a['id']).execute()
                        etat_str = "verrouillé" if nouvel_etat else "déverrouillé"
                        enregistrer_log("Admin", "Verrouillage atelier", f"Atelier '{a['titre']}' du {a['date_atelier']} {etat_str}")
                        st.rerun()
                    if cd.button("✏️", key=f"at_edit_{a['id']}"):
                        edit_atelier_dialog(
                        a['id'], a['titre'], a['date_atelier'], a['lieu_id'], a['horaire_id'],
                        a['capacite_max'], a.get('max_enfants'),
                        l_raw, h_raw, map_l_id, map_h_id
                        )
                    if ce.button("🗑️", key=f"at_del_{a['id']}"):
                        try:
                            cnt = supabase.table("inscriptions").select("id", count="exact").eq("atelier_id", a['id']).execute().count or 0
                        except:
                            cnt = 0
                        delete_atelier_dialog(a['id'], a['titre'], cnt > 0, current_code)
                    if anim_nom_rep:
                        if cf_anim.button("⭐ Changer anim.", key=f"at_anim_chg_{a['id']}"):
                            dialog_attribuer_animateur(a['id'], a['titre'], anim_id_at, anim_nom_rep, liste_adh_anim, dict_adh_anim, auteur="Admin")
                    else:
                        if cf_anim.button("⭐ Assigner anim.", key=f"at_anim_set_{a['id']}"):
                            dialog_attribuer_animateur(a['id'], a['titre'], None, None, liste_adh_anim, dict_adh_anim, auteur="Admin")
                                
        elif sub == "Actions groupées":
            with st.form("bulk_form"):
                c1, c2 = st.columns(2)
                bs = c1.date_input("Début", format="DD/MM/YYYY", key="blk_d1")
                be = c2.date_input("Fin", format="DD/MM/YYYY", key="blk_d2")
                action = st.radio("Action :", ["Activer", "Désactiver"], horizontal=True)
                if st.form_submit_button("🚀 Appliquer"):
                    supabase.table("ateliers").update({"est_actif": (action=="Activer")}).gte("date_atelier", str(bs)).lte("date_atelier", str(be)).execute()
                    st.rerun()

    with t2:  # SUIVI AM (Admin)
        if not liste_adh:
            st.info("ℹ️ Aucune assistante maternelle enregistrée. Créez-en dans l'onglet 👥 Liste AM.")
        else:
            choix_adm = st.multiselect("Filtrer par AM (Admin) :", liste_adh, key="adm_filter_am")
            ids_adm = [dict_adh[n] for n in choix_adm] if choix_adm else list(dict_adh.values())
            data_adm_triee = []
            if ids_adm:
                try:
                    inscriptions_brutes = supabase.table("inscriptions").select("*, ateliers!inner(*), adherents(nom, prenom)").in_("adherent_id", ids_adm).eq("ateliers.est_actif", True).execute().data or []
                    lieux_dict = {l['id']: l['nom'] for l in st.session_state.lieux_list}
                    horaires_dict = {h['id']: h['libelle'] for h in st.session_state.horaires_list}
                    for ins in inscriptions_brutes:
                        at = ins['ateliers']
                        at['lieu_nom'] = lieux_dict.get(at['lieu_id'], '?')
                        at['horaire_lib'] = horaires_dict.get(at['horaire_id'], '?')
                        ins['ateliers'] = at
                    data_adm_triee = trier_par_nom_puis_date(inscriptions_brutes) if inscriptions_brutes else []
                except:
                    data_adm_triee = []

            df_adm = pd.DataFrame([{
                "AM": f"{i['adherents']['prenom']} {i['adherents']['nom']}",
                "Date": i['ateliers']['date_atelier'],
                "Atelier": i['ateliers']['titre'],
                "Lieu": i['ateliers']['lieu_nom'],
                "Horaire": i['ateliers']['horaire_lib'],
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
                    st.write(f"{format_date_fr_complete(at['date_atelier'], gras=True)} — {at['titre']} <span class='lieu-badge' style='background-color:{c_l}'>{at['lieu_nom']}</span> <span class='horaire-text'>({at['horaire_lib']})</span> **({i['nb_enfants']} enf.)**", unsafe_allow_html=True)
            else:
                st.info("Aucune inscription trouvée pour les AM sélectionnées.")

    with t3:  # PLANNING ATELIERS (Admin)
        st.subheader("📅 Planning des Ateliers")
        st.markdown("**Filtrer par statut :**")
        options_filtre_plan = ("Tous", "Actifs", "Inactifs")
        if "filtre_plan_admin" not in st.session_state:
            st.session_state["filtre_plan_admin"] = "Tous"
        col_f1, col_f2, col_f3, col_f_rest = st.columns([1, 1, 1, 5])
        for col_f, opt in zip([col_f1, col_f2, col_f3], options_filtre_plan):
            actif = st.session_state["filtre_plan_admin"] == opt
            with col_f:
                if st.button(opt, key=f"filtre_plan_{opt}", help=f"Filtrer : {opt}", use_container_width=True):
                    st.session_state["filtre_plan_admin"] = opt
                    st.rerun()
        st.markdown("""
        <style>
        [data-testid="column"]:nth-child(1) button, [data-testid="column"]:nth-child(2) button, [data-testid="column"]:nth-child(3) button {
            border: 1.5px solid #80cbc4 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        filtre_statut_plan = st.session_state["filtre_plan_admin"]
        c1_adm, c2_adm = st.columns(2)
        d_s_a = c1_adm.date_input("Du", date.today(), key="adm_plan_d1", format="DD/MM/YYYY")
        d_e_a = c2_adm.date_input("Au", d_s_a + timedelta(days=30), key="adm_plan_d2", format="DD/MM/YYYY")
        try:
            query = supabase.table("ateliers").select("*").gte("date_atelier", str(d_s_a)).lte("date_atelier", str(d_e_a))
            if filtre_statut_plan == "Actifs":
                query = query.eq("est_actif", True)
            elif filtre_statut_plan == "Inactifs":
                query = query.eq("est_actif", False)
            ateliers_bruts = query.order("date_atelier").execute().data or []
        except:
            ateliers_bruts = []
        lieux_dict = {l['id']: l['nom'] for l in st.session_state.lieux_list}
        horaires_dict = {h['id']: h['libelle'] for h in st.session_state.horaires_list}
        ateliers = []
        for a in ateliers_bruts:
            a['lieu_nom'] = lieux_dict.get(a['lieu_id'], '?')
            a['horaire_lib'] = horaires_dict.get(a['horaire_id'], '?')
            ateliers.append(a)
        cache_ins_adm = {}
        adm_ins_list = []
        if ateliers:
            for a in ateliers:
                try:
                    ins_at = supabase.table("inscriptions").select("*, adherents(nom, prenom)").eq("atelier_id", a['id']).execute().data or []
                except:
                    ins_at = []
                cache_ins_adm[a['id']] = ins_at
                for p in ins_at:
                    adm_ins_list.append({
                        "Date": a['date_atelier'], "Atelier": a['titre'], "Lieu": a['lieu_nom'],
                        "AM": f"{p['adherents']['prenom']} {p['adherents']['nom']}", "Enfants": p['nb_enfants']
                    })
        df_adm_at = pd.DataFrame(adm_ins_list) if adm_ins_list else pd.DataFrame(columns=["Date", "Atelier", "Lieu", "AM", "Enfants"])
        cea1, cea2 = st.columns(2)
        cea1.download_button("📥 Excel Planning (Admin)",
                             data=export_to_excel_with_period(df_adm_at, d_s_a, d_e_a, "Planning des ateliers"),
                             file_name="admin_planning_ateliers.xlsx", key="adm_exp_xl")
        cea2.download_button("📥 PDF Planning (Admin)",
                             data=export_planning_ateliers_pdf_with_period(
                                 "Planning des Ateliers (Administration)", ateliers,
                                 lambda aid: cache_ins_adm.get(aid, []),
                                 d_s_a, d_e_a
                             ),
                             file_name="admin_planning_ateliers.pdf", key="adm_exp_pdf")
        if ateliers:
            for index, a in enumerate(ateliers):
                c_l = get_color(a['lieu_nom'])
                anim_id_at = a.get('animateur_id')
                ins_at = cache_ins_adm.get(a['id'], [])
                t_ad = len(ins_at)
                t_en = sum([p['nb_enfants'] for p in ins_at])
                restantes = a['capacite_max'] - (t_ad + t_en)  # places totales restantes (peut être négatif)
                
                # --- Calcul des places enfants restantes ---
                max_enf_at = get_max_enfants_atelier(a)
                nb_enfants_inscrits = t_en  # total enfants déjà inscrits (inclut animateur)
                places_enfants_restantes = max(max_enf_at - nb_enfants_inscrits, 0)
                if places_enfants_restantes == 0:
                    statut_enfants = "🚫 Complet"
                else:
                    statut_enfants = f"👶 {places_enfants_restantes} pl. enfants"
                
                # Vérifier si la capacité totale est dépassée
                capacite_depassee = restantes < 0
                if capacite_depassee:
                    statut_enfants += " ⚠️ Salle saturée"
                
                verrou_icon = " 🔒" if is_verrouille(a) else ""
                at_info_log = f"{a['date_atelier']} | {a['horaire_lib']} | {a['lieu_nom']}"
                anim_nom_plan = None
                if anim_id_at:
                    anim_adh_plan = next((x for x in adh_data if x['id'] == anim_id_at), None)
                    if anim_adh_plan:
                        anim_nom_plan = f"{anim_adh_plan['prenom']} {anim_adh_plan['nom']}"
                anim_label_plan = f" | ⭐ {anim_nom_plan}" if anim_nom_plan else ""
                
                # Affichage sans le compteur de places totales
                st.markdown(f"**{format_date_fr_complete(a['date_atelier'])}** | {a['titre']} | <span class='lieu-badge' style='background-color:{c_l}'>{a['lieu_nom']}</span> | <span class='horaire-text'>{a['horaire_lib']}</span>{verrou_icon}{anim_label_plan} <span class='compteur-badge'>👤 {t_ad} AM</span> <span class='compteur-badge'>👶 {t_en} enf.</span> <span class='compteur-badge'>{statut_enfants}</span>", unsafe_allow_html=True)
                
                if ins_at:
                    anim_ins_plan = next((p for p in ins_at if p['adherent_id'] == anim_id_at), None) if anim_id_at else None
                    autres_plan = [p for p in ins_at if p['adherent_id'] != anim_id_at]
                    autres_plan_tries = sorted(autres_plan, key=lambda x: (x['adherents']['nom'].upper(), x['adherents']['prenom'].upper()))
                    if anim_ins_plan:
                        n_a = f"{anim_ins_plan['adherents']['prenom']} {anim_ins_plan['adherents']['nom']}"
                        ca1, ca2, ca3, ca4 = st.columns([0.42, 0.18, 0.18, 0.22])
                        ca1.markdown(f'<span style="color:#e65100;font-weight:bold;">⭐ {n_a} <span style="background:#e65100;color:white;padding:1px 6px;border-radius:4px;font-size:0.78rem;">ANIMATEUR</span></span>', unsafe_allow_html=True)
                        new_nb_a = ca2.number_input("Enf.", 0, 10, int(anim_ins_plan['nb_enfants']), key=f"adm_anim_nb_{anim_ins_plan['id']}", label_visibility="collapsed")
                        if ca3.button("✏️ Modifier", key=f"adm_anim_mod_{anim_ins_plan['id']}"):
                            # Vérifier la capacité totale après modification
                            delta = new_nb_a - anim_ins_plan['nb_enfants']
                            nouvelle_occupation = t_ad + t_en + delta
                            if nouvelle_occupation > a['capacite_max']:
                                st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                            else:
                                supabase.table("inscriptions").update({"nb_enfants": new_nb_a}).eq("id", anim_ins_plan['id']).execute()
                                enregistrer_log("Admin", "Modification nb enf. animateur", f"{n_a} → {new_nb_a} enf. - {at_info_log}")
                                st.rerun()
                        if ca4.button("❌ Retirer anim.", key=f"adm_anim_del_{a['id']}"):
                            dialog_retirer_animateur(a['id'], a['titre'], anim_id_at, n_a, "Admin")
                    for p in autres_plan_tries:
                        n_f = f"{p['adherents']['prenom']} {p['adherents']['nom']}"
                        cp1, cp2, cp3, cp4 = st.columns([0.45, 0.18, 0.18, 0.19])
                        cp1.write(f"• {n_f}")
                        new_nb = cp2.number_input("Enf.", 0, 10, int(p['nb_enfants']), key=f"adm_nb_{p['id']}", label_visibility="collapsed")
                        if cp3.button("✏️ Modifier", key=f"adm_mod_{p['id']}"):
                            # Vérifier la capacité totale après modification
                            delta = new_nb - p['nb_enfants']
                            nouvelle_occupation = t_ad + t_en + delta
                            if nouvelle_occupation > a['capacite_max']:
                                st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                            else:
                                supabase.table("inscriptions").update({"nb_enfants": new_nb}).eq("id", p['id']).execute()
                                enregistrer_log("Admin", "Modification (admin)", f"{n_f} → {new_nb} enfants - {at_info_log}")
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
                                    nouvelle_occupation = t_ad + t_en + delta_enf
                                    if nouvelle_occupation > a['capacite_max']:
                                        st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                                    else:
                                        supabase.table("inscriptions").update({"nb_enfants": nb_adm}).eq("id", existing['id']).execute()
                                        enregistrer_log("Admin", "Modification (admin)", f"{qui_adm} → {nb_adm} enfants - {at_info_log}")
                                        st.rerun()
                                else:
                                    nouvelle_occupation = t_ad + t_en + 1 + nb_adm  # +1 pour l'adulte
                                    if nouvelle_occupation > a['capacite_max']:
                                        st.markdown("<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée</span>", unsafe_allow_html=True)
                                    else:
                                        supabase.table("inscriptions").insert({"adherent_id": id_adh, "atelier_id": a['id'], "nb_enfants": nb_adm}).execute()
                                        enregistrer_log("Admin", "Inscription (admin)", f"{qui_adm} inscrite (+{nb_adm} enf.) - {at_info_log}")
                                        st.rerun()
                if index < len(ateliers) - 1:
                    st.markdown('<hr class="separateur-atelier">', unsafe_allow_html=True)
        else:
            st.info("Aucun atelier trouvé sur cette période.")
            
    with t4:  # STATISTIQUES
        st.subheader("📈 Statistiques de participation")
        cs1, cs2 = st.columns(2)
        ds_stat = cs1.date_input("Date début", date.today().replace(day=1), key="stat_d1", format="DD/MM/YYYY")
        de_stat = cs2.date_input("Date fin", date.today(), key="stat_d2", format="DD/MM/YYYY")
        try:
            ateliers_bruts = supabase.table("ateliers").select("*").gte("date_atelier", str(ds_stat)).lte("date_atelier", str(de_stat)).order("date_atelier").execute().data or []
        except:
            ateliers_bruts = []
        lieux_dict = {l['id']: l['nom'] for l in st.session_state.lieux_list}
        horaires_dict = {h['id']: h['libelle'] for h in st.session_state.horaires_list}
        ateliers = []
        for a in ateliers_bruts:
            a['lieu_nom'] = lieux_dict.get(a['lieu_id'], '?')
            a['horaire_lib'] = horaires_dict.get(a['horaire_id'], '?')
            ateliers.append(a)
        atelier_ids = [a['id'] for a in ateliers]
        filtered_ins = []
        if atelier_ids:
            try:
                inscriptions = supabase.table("inscriptions").select("*, adherents(nom, prenom)").in_("atelier_id", atelier_ids).execute().data or []
                filtered_ins = inscriptions
            except:
                filtered_ins = []
        nb_at_proposes = len(atelier_ids)
        if filtered_ins and liste_adh:
            stats_list = []
            for am_nom in liste_adh:
                am_id = dict_adh[am_nom]
                count = sum(1 for x in filtered_ins if x['adherent_id'] == am_id)
                stats_list.append({"Assistante Maternelle": am_nom, "Nombre d'ateliers": count})
            df_stats = pd.DataFrame(stats_list).sort_values("Nombre d'ateliers", ascending=False).reset_index(drop=True)
    
            # --- STYLE PERSONNALISÉ ---
            styled_df = df_stats.style.set_properties(**{'background-color': 'white', 'color': 'black'}).set_table_styles([
                {'selector': 'th', 'props': [('background-color', '#f0f0f0'), ('color', 'black'), ('font-weight', 'bold')]},
                {'selector': 'td:nth-child(2)', 'props': [('text-align', 'center')]},
                {'selector': 'th:nth-child(2)', 'props': [('text-align', 'center')]},
                {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]},
                {'selector': 'td, th', 'props': [('padding', '8px'), ('border', '1px solid #ddd')]}
            ]).hide(axis='index')
            html_table = styled_df.to_html()
            st.markdown(html_table, unsafe_allow_html=True)
    
            total_inscr = df_stats["Nombre d'ateliers"].sum()
            st.markdown(f"**Total des inscriptions sur la période :** {total_inscr}")
            st.markdown(f"**Nombre d'ateliers proposés sur la période :** {nb_at_proposes}")
            if ateliers:
                st.markdown("**Ateliers proposés :**")
                for at in ateliers:
                    date_fr = format_date_fr_simple(at['date_atelier'])
                    st.write(f"- {date_fr} : **{at['titre']}** ({at['lieu_nom']} - {at['horaire_lib']})")
            ce_s1, ce_s2 = st.columns(2)
            ce_s1.download_button(
                "📥 Excel Statistiques",
                data=export_to_excel_with_period(df_stats, ds_stat, de_stat, "Statistiques de participation"),
                file_name=f"stats_am_{ds_stat}_{de_stat}.xlsx"
            )
            pdf_stat_lines = []
            for _, r in df_stats.iterrows():
                pdf_stat_lines.append(f"{r['Assistante Maternelle']} : {r['Nombre d\'ateliers']} atelier(s)")
            pdf_stat_lines.append("")
            pdf_stat_lines.append(f"Total inscriptions sur la période : {total_inscr}")
            pdf_stat_lines.append(f"Ateliers proposés sur la période : {nb_at_proposes}")
            pdf_stat_lines.append("")
            pdf_stat_lines.append("Liste des ateliers proposés :")
            for at in ateliers:
                date_fr = format_date_fr_simple(at['date_atelier'])
                pdf_stat_lines.append(f"- {date_fr} : {at['titre']} ({at['lieu_nom']} - {at['horaire_lib']})")
            ce_s2.download_button(
                "📥 PDF Statistiques",
                data=export_stats_pdf("Statistiques de participation AM", pdf_stat_lines, ds_stat, de_stat),
                file_name=f"stats_am_{ds_stat}_{de_stat}.pdf"
            )
        else:
            if not liste_adh:
                st.info("ℹ️ Aucune assistante maternelle enregistrée.")
            elif not atelier_ids:
                st.info("ℹ️ Aucun atelier proposé sur cette période.")
            else:
                st.info("Aucune donnée pour cette période.")
            if ateliers:
                st.markdown("**Ateliers proposés sur la période :**")
                for at in ateliers:
                    date_fr = format_date_fr_simple(at['date_atelier'])
                    st.write(f"- {date_fr} : **{at['titre']}** ({at['lieu_nom']} - {at['horaire_lib']})")
                
    with t5:  # 👥 LISTE AM
        st.subheader("👥 Gestion des Assistantes Maternelles")
        with st.form("add_am"):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nom").upper().strip()
            pre = " ".join([w.capitalize() for w in c2.text_input("Prénom").split()]).strip()
            if st.form_submit_button("➕ Ajouter"):
                if nom and pre:
                    try:
                        supabase.table("adherents").insert({"nom": nom, "prenom": pre, "est_actif": True, "est_animateur": False}).execute()
                        st.success(f"✅ {pre} {nom} ajouté(e) avec succès !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'ajout : {str(e)}")
                else:
                    st.warning("Veuillez renseigner le nom et le prénom.")
        try:
            res_adh_admin = supabase.table("adherents").select("*").order("nom").order("prenom").execute()
            adh_data_admin = res_adh_admin.data if res_adh_admin.data else []
        except:
            adh_data_admin = []
        if not adh_data_admin:
            st.info("ℹ️ Aucune assistante maternelle enregistrée. Utilisez le formulaire ci-dessus pour en ajouter.")
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
                actif = st.session_state["filtre_liste_am"] == opt
                with col_am:
                    if st.button(opt, key=f"filtre_am_{opt}", use_container_width=True):
                        st.session_state["filtre_liste_am"] = opt
                        st.rerun()
            filtre_am_actuel = st.session_state["filtre_liste_am"]
            st.markdown(
                f"**Liste des AM** ({nb_actives} actives, {nb_inactives} inactives) — "
                f"⭐ statut animateur · 🟢/🔴 statut adhésion"
            )
            for u in adh_data_admin:
                est_anim = u.get('est_animateur', False)
                est_actif_am = u.get('est_actif', True)
                if filtre_am_actuel == "Actifs" and not est_actif_am:
                    continue
                if filtre_am_actuel == "Inactifs" and est_actif_am:
                    continue
                style_nom = "color:#9e9e9e; text-decoration:line-through;" if not est_actif_am else ""
                badge_inactif = ' <span style="background:#9e9e9e;color:white;padding:1px 6px;border-radius:4px;font-size:0.78rem;font-weight:bold;">INACTIF</span>' if not est_actif_am else ''
                anim_label_am = ' <span style="background:#e65100;color:white;padding:1px 6px;border-radius:4px;font-size:0.78rem;font-weight:bold;">ANIMATEUR</span>' if est_anim else ''
                c1, c_anim, c_actif, c_edit, c_del = st.columns([0.45, 0.2, 0.12, 0.12, 0.11])
                c1.markdown(
                    f'<span style="{style_nom}"><strong>{u["nom"]}</strong> {u["prenom"]}</span>{anim_label_am}{badge_inactif}',
                    unsafe_allow_html=True
                )
                if est_anim:
                    if c_anim.button("⭐ Retirer anim.", key=f"am_anim_off_{u['id']}", disabled=not est_actif_am):
                        supabase.table("adherents").update({"est_animateur": False}).eq("id", u['id']).execute()
                        enregistrer_log("Admin", "Retrait statut animateur", f"{u['prenom']} {u['nom']} n'est plus animateur")
                        st.rerun()
                else:
                    if c_anim.button("⭐ Rendre anim.", key=f"am_anim_on_{u['id']}", disabled=not est_actif_am):
                        supabase.table("adherents").update({"est_animateur": True}).eq("id", u['id']).execute()
                        enregistrer_log("Admin", "Attribution statut animateur", f"{u['prenom']} {u['nom']} devient animateur")
                        st.rerun()
                if est_actif_am:
                    if c_actif.button("🟢 Actif", key=f"am_actif_{u['id']}"):
                        today_str = str(date.today())
                        try:
                            res_ins_futures = supabase.table("inscriptions").select("id, ateliers(date_atelier, titre)").eq("adherent_id", u['id']).execute()
                            ins_futures = [
                                i for i in (res_ins_futures.data or [])
                                if i.get('ateliers') and i['ateliers'].get('date_atelier', '') >= today_str
                            ]
                        except:
                            ins_futures = []
                        if ins_futures:
                            noms_ateliers = ", ".join([
                                f"{format_date_fr_simple(i['ateliers']['date_atelier'])} – {i['ateliers'].get('titre','?')}"
                                for i in ins_futures[:3]
                            ])
                            st.session_state[f"confirm_desact_{u['id']}"] = {"ins_futures": ins_futures, "noms": noms_ateliers}
                        else:
                            supabase.table("adherents").update({"est_actif": False}).eq("id", u['id']).execute()
                            enregistrer_log("Admin", "Désactivation AM", f"{u['prenom']} {u['nom']} passée en statut inactif")
                            st.rerun()
                else:
                    if c_actif.button("🔴 Inactif", key=f"am_actif_{u['id']}"):
                        supabase.table("adherents").update({"est_actif": True}).eq("id", u['id']).execute()
                        enregistrer_log("Admin", "Réactivation AM", f"{u['prenom']} {u['nom']} passée en statut actif")
                        st.rerun()
                if st.session_state.get(f"confirm_desact_{u['id']}"):
                    info = st.session_state[f"confirm_desact_{u['id']}"]
                    nb_ins = len(info["ins_futures"])
                    st.warning(
                        f"⚠️ **{u['prenom']} {u['nom']}** a **{nb_ins} inscription(s) à venir** "
                        f"({info['noms']}{'...' if nb_ins > 3 else ''}). "
                        f"Elle restera inscrite à ces ateliers. Confirmer la désactivation ?"
                    )
                    ca, cb = st.columns(2)
                    if ca.button("✅ Confirmer quand même", key=f"ok_desact_{u['id']}"):
                        supabase.table("adherents").update({"est_actif": False}).eq("id", u['id']).execute()
                        enregistrer_log("Admin", "Désactivation AM (avec inscriptions futures)", f"{u['prenom']} {u['nom']} désactivée ({nb_ins} inscriptions futures conservées)")
                        del st.session_state[f"confirm_desact_{u['id']}"]
                        st.rerun()
                    if cb.button("❌ Annuler", key=f"cancel_desact_{u['id']}"):
                        del st.session_state[f"confirm_desact_{u['id']}"]
                        st.rerun()
                if c_edit.button("✏️", key=f"am_edit_{u['id']}", help="Modifier le nom/prénom"):
                    edit_am_dialog(u['id'], u['nom'], u['prenom'])
                if c_del.button("🗑️", key=f"am_del_{u['id']}"):
                    secure_delete_dialog("adherents", u['id'], f"{u['prenom']} {u['nom']}", current_code)

    with t6:  # 📍 LIEUX / HORAIRES
        refresh_referentials()
        l_raw = st.session_state.lieux_list
        h_raw = st.session_state.horaires_list
        cl1, cl2 = st.columns(2)
        with cl1:
            st.subheader("Lieux")
            if not l_raw:
                st.info("ℹ️ Aucun lieu enregistré. Utilisez le formulaire ci-dessous pour en ajouter.")
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
                            st.rerun()
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
                            refresh_referentials()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {str(e)}")
                    else:
                        st.error("Le nom du lieu ne peut pas être vide.")
        with cl2:
            st.subheader("Horaires")
            if not h_raw:
                st.info("ℹ️ Aucun horaire enregistré. Utilisez le formulaire ci-dessous pour en ajouter.")
            else:
                for h in h_raw:
                    cc, cd_edit, cd_del = st.columns([0.65, 0.18, 0.17])
                    cc.write(f"• {h['libelle']}")
                    if cd_edit.button("✏️", key=f"hx_edit_{h['id']}", help="Modifier"):
                        edit_horaire_dialog(h['id'], h['libelle'])
                    if cd_del.button("🗑️", key=f"hx_{h['id']}", help="Supprimer"):
                        secure_delete_dialog("horaires", h['id'], h['libelle'], current_code)
            with st.form("add_hx"):
                nh = st.text_input("Nouvel Horaire (ex: '09:00-11:00')")
                if st.form_submit_button("Ajouter"):
                    if nh.strip():
                        try:
                            supabase.table("horaires").insert({"libelle": nh.strip()}).execute()
                            refresh_referentials()
                            st.success(f"✅ Horaire '{nh.strip()}' ajouté.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {str(e)}")
                    else:
                        st.error("L'horaire ne peut pas être vide.")

    with t7:  # ⚙️ SÉCURITÉ
        st.subheader("⚙️ Sécurité & Configuration")
        st.markdown("**🔑 Changer le code administrateur**")
        with st.form("sec_form"):
            o, n = st.text_input("Ancien code", type="password"), st.text_input("Nouveau code", type="password")
            if st.form_submit_button("Changer le code"):
                if o == current_code or o == "0000":
                    try:
                        supabase.table("configuration").update({"secret_code": n}).eq("id", "main_config").execute()
                        st.success("Code modifié avec succès !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {str(e)}")
                else:
                    st.error("Ancien code incorrect")
        st.markdown("---")
        st.markdown("**👶 Nombre maximum d'enfants par défaut (global)**")
        current_max = get_max_enfants()
        st.info(f"Valeur actuelle : **{current_max} enfants** — utilisée pour les ateliers sans limite spécifique.")
        with st.form("max_enfants_form"):
            nouveau_max = st.number_input(
                "Nombre maximum d'enfants par défaut",
                min_value=1, max_value=100, value=current_max,
                help="Valeur appliquée aux ateliers dont le champ 'Max Enfants' est vide ou à 0."
            )
            if st.form_submit_button("💾 Enregistrer la limite globale"):
                result = set_max_enfants(nouveau_max)
                if result is True:
                    enregistrer_log("Admin", "Configuration", f"Nombre max enfants global modifié : {nouveau_max}")
                    st.success(f"✅ Limite globale mise à jour : {nouveau_max} enfants.")
                    st.rerun()
                else:
                    st.error(f"Erreur : {result}")
        st.markdown("---")
        if st.button("🚪 Déconnexion Super Admin"):
            st.session_state['super_access'] = False
            st.rerun()

    with t8:  # 📜 JOURNAL DES ACTIONS
        st.subheader("📜 Journal des manipulations")
        cj1, cj2 = st.columns(2)
        dj_s = cj1.date_input("Depuis le", date.today() - timedelta(days=7), format="DD/MM/YYYY", key="log_d1")
        dj_e = cj2.date_input("Jusqu'au", date.today(), format="DD/MM/YYYY", key="log_d2")
        start_date = dj_s.strftime("%Y-%m-%d") + "T00:00:00"
        end_date = dj_e.strftime("%Y-%m-%d") + "T23:59:59"
        try:
            res_logs = supabase.table("logs").select("*").gte("created_at", start_date).lte("created_at", end_date).order("created_at", desc=True).execute()
            if res_logs.data:
                logs_df = pd.DataFrame(res_logs.data)
                logs_df['created_at'] = pd.to_datetime(logs_df['created_at'], utc=True).dt.tz_convert("Europe/Paris").dt.strftime('%d/%m/%Y %H:%M')
                st.dataframe(
                    logs_df[['created_at', 'utilisateur', 'action', 'details']],
                    column_config={
                        "created_at": "Date & Heure",
                        "utilisateur": "Auteur",
                        "action": "Action",
                        "details": "Détails"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Aucune action enregistrée pour cette période.")
        except Exception as e:
            st.info("ℹ️ Le journal des actions sera disponible une fois que des opérations auront été effectuées.")

    with t9:  # 🎯 ANIMATEUR (Admin)
        st.subheader("🎯 Espace Animateur (accès Administration)")
        st.markdown(f'<div style="background-color:#fff3e0; border:1px solid #e65100; border-radius:8px; padding:10px 16px; margin-bottom:16px; color:#e65100; font-weight:bold;">⭐ Vous accédez à la vue animateur en tant qu\'administrateur.</div>', unsafe_allow_html=True)

        ca_d1, ca_d2 = st.columns(2)
        anim_d_debut = ca_d1.date_input("Du", date.today(), key="anim_adm_d1", format="DD/MM/YYYY")
        anim_d_fin = ca_d2.date_input("Au", date.today() + timedelta(days=30), key="anim_adm_d2", format="DD/MM/YYYY")

        try:
            ateliers_bruts_anim = (
                supabase.table("ateliers").select("*")
                .eq("est_actif", True)
                .gte("date_atelier", str(anim_d_debut))
                .lte("date_atelier", str(anim_d_fin))
                .order("date_atelier")
                .execute().data or []
            )
        except:
            ateliers_bruts_anim = []

        lieux_dict_anim = {l['id']: l['nom'] for l in st.session_state.lieux_list}
        horaires_dict_anim = {h['id']: h['libelle'] for h in st.session_state.horaires_list}
        ateliers_anim = []
        for at in ateliers_bruts_anim:
            at['lieu_nom'] = lieux_dict_anim.get(at['lieu_id'], '?')
            at['horaire_lib'] = horaires_dict_anim.get(at['horaire_id'], '?')
            ateliers_anim.append(at)

        if not ateliers_anim:
            st.info("ℹ️ Aucun atelier actif sur cette période.")
        else:
            for idx, at in enumerate(ateliers_anim):
                anim_id_at = at.get('animateur_id')
                try:
                    res_ins = supabase.table("inscriptions").select("*, adherents(nom, prenom)").eq("atelier_id", at['id']).execute()
                    ins_data = res_ins.data if res_ins.data else []
                except:
                    ins_data = []

                # Calculs des places
                total_occ = sum([(1 + (i['nb_enfants'] if i['nb_enfants'] else 0)) for i in ins_data])
                restantes = at['capacite_max'] - total_occ
                max_enf_at = get_max_enfants_atelier(at)
                total_enfants_actuel = sum([i['nb_enfants'] for i in ins_data])
                places_enfants_restantes = max(max_enf_at - total_enfants_actuel, 0)

                if places_enfants_restantes == 0:
                    statut_enfants = "🚫 Complet"
                else:
                    statut_enfants = f"👶 {places_enfants_restantes} pl. enfants"

                # Récupérer l'animateur actuel
                anim_ins = next((i for i in ins_data if i['adherent_id'] == anim_id_at), None) if anim_id_at else None
                anim_nom_at = None
                if anim_ins:
                    anim_nom_at = f"{anim_ins['adherents']['prenom']} {anim_ins['adherents']['nom']}"
                elif anim_id_at:
                    anim_adh = next((a for a in adh_data if a['id'] == anim_id_at), None)
                    if anim_adh:
                        anim_nom_at = f"{anim_adh['prenom']} {anim_adh['nom']}"

                anim_label = f" | ⭐ {anim_nom_at}" if anim_nom_at else " | ⭐ Pas d'animateur"
                titre_label = f"{format_date_fr_complete(at['date_atelier'])} — {at['titre']} | 📍 {at['lieu_nom']} | ⏰ {at['horaire_lib']} | {statut_enfants}{anim_label}"

                # Clé pour la session state du nombre d'enfants
                nb_key = f"adm_anim_nb_{at['id']}_{idx}"
                if nb_key not in st.session_state:
                    st.session_state[nb_key] = anim_ins['nb_enfants'] if anim_ins else 1

                with st.expander(titre_label, expanded=False):
                    at_info_log = f"{at['date_atelier']} | {at['horaire_lib']} | {at['lieu_nom']}"
                    st.markdown("**Gestion de l'animateur :**")

                    # Sélection de l'animateur
                    options_anim = ["Choisir..."] + liste_adh_anim
                    if anim_nom_at and anim_nom_at in liste_adh_anim:
                        idx_def = liste_adh_anim.index(anim_nom_at) + 1
                    else:
                        idx_def = 0
                    nouvel_anim = st.selectbox("Animateur à assigner", options_anim, index=idx_def, key=f"adm_anim_select_{at['id']}_{idx}")

                    # Nombre d'enfants avec valeur stockée
                    nb_enf = st.number_input("Nombre d'enfants de l'animateur", min_value=0, max_value=10, value=st.session_state[nb_key], key=nb_key)

                    if st.button("✅ Appliquer", key=f"adm_anim_apply_{at['id']}_{idx}", type="primary"):
                        if nouvel_anim == "Choisir...":
                            st.warning("Veuillez sélectionner un animateur.")
                        else:
                            nouvel_anim_id = dict_adh_anim[nouvel_anim]
                            ancien_anim_id = anim_id_at
                            ancien_nb = anim_ins['nb_enfants'] if anim_ins else 1

                            # Calcul des nouveaux totaux selon le cas
                            if ancien_anim_id and ancien_anim_id != nouvel_anim_id:
                                # Changement d'animateur
                                nouvelle_occupation = total_occ - (1 + ancien_nb) + (1 + nb_enf)
                                nouveau_total_enfants = total_enfants_actuel - ancien_nb + nb_enf
                            elif ancien_anim_id == nouvel_anim_id:
                                # Même animateur
                                delta = nb_enf - ancien_nb
                                nouvelle_occupation = total_occ + delta
                                nouveau_total_enfants = total_enfants_actuel + delta
                            else:
                                # Pas d'animateur actuel
                                nouvelle_occupation = total_occ + 1 + nb_enf
                                nouveau_total_enfants = total_enfants_actuel + nb_enf

                            # Calcul de la valeur maximale autorisée pour nb_enf
                            if ancien_anim_id and ancien_anim_id != nouvel_anim_id:
                                marge_enf = max_enf_at - (total_enfants_actuel - ancien_nb)
                                marge_capa = at['capacite_max'] - (total_occ - (1 + ancien_nb))
                            elif ancien_anim_id == nouvel_anim_id:
                                marge_enf = max_enf_at - total_enfants_actuel + ancien_nb
                                marge_capa = at['capacite_max'] - total_occ + ancien_nb
                            else:
                                marge_enf = max_enf_at - total_enfants_actuel
                                marge_capa = at['capacite_max'] - total_occ - 1

                            max_autorise = min(marge_enf, marge_capa, 10)  # plafonner à 10
                            if max_autorise < 0:
                                max_autorise = 0

                            # Vérifications
                            erreur = False
                            if nouveau_total_enfants > max_enf_at:
                                st.error(f"🚫 Le nombre maximum d'enfants ({max_enf_at}) serait dépassé. Valeur maximale possible : {max_autorise}")
                                erreur = True
                            elif nouvelle_occupation > at['capacite_max']:
                                st.markdown(f"<span style='color:red; font-weight:bold;'>❌ Trop de monde : capacité de la salle dépassée. Valeur maximale possible : {max_autorise}</span>", unsafe_allow_html=True)
                                erreur = True

                            if erreur:
                                # Mettre à jour la session state avec la valeur max autorisée et relancer
                                st.session_state[nb_key] = max_autorise
                                st.rerun()
                            else:
                                # Appliquer les modifications
                                if ancien_anim_id and ancien_anim_id != nouvel_anim_id:
                                    supabase.table("inscriptions").delete().eq("atelier_id", at['id']).eq("adherent_id", ancien_anim_id).execute()
                                supabase.table("ateliers").update({"animateur_id": nouvel_anim_id}).eq("id", at['id']).execute()
                                existing_new = supabase.table("inscriptions").select("id").eq("atelier_id", at['id']).eq("adherent_id", nouvel_anim_id).execute()
                                if existing_new.data:
                                    supabase.table("inscriptions").update({"nb_enfants": nb_enf}).eq("id", existing_new.data[0]['id']).execute()
                                else:
                                    supabase.table("inscriptions").insert({"adherent_id": nouvel_anim_id, "atelier_id": at['id'], "nb_enfants": nb_enf}).execute()
                                enregistrer_log("Admin", "Modification animateur", f"Animateur {nouvel_anim} ({nb_enf} enfants) - {at_info_log}")
                                st.success("Modification effectuée !")
                                # Mettre à jour la session state avec la nouvelle valeur validée
                                st.session_state[nb_key] = nb_enf
                                st.rerun()
                                
    if st.sidebar.button("🚪 Déconnexion administration"):
        st.session_state["admin_auth"] = False
        st.rerun()
