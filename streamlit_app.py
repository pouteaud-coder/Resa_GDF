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
    <div style="display: flex; align-items: center; background-color: #cfe9ff; padding: 20px; border-radius: 15px; margin-bottom: 25px; border: 2px solid #1b5e20;">
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

# --- STYLE CSS (identique à l'original) ---
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
    .nb-enfants-focus { color: #0a3d0a; font-weight: 600; }
    .stButton button { border-radius: 8px !important; background-color: #1b5e20 !important; color: white !important; border: none !important; }
    .stButton button:hover { background-color: #0a3d0a !important; }
    .badge-verrouille { background-color: #1b5e20; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-left: 6px; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { color: #1b5e20 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #d4e6f1; border-radius: 8px; padding: 8px 16px; color: #1b5e20; }
    .stTabs [aria-selected="true"] { background-color: #1b5e20 !important; color: white !important; }
    .stAlert { background-color: #cfe9ff; border-left-color: #1b5e20; color: #1b5e20; }
    .stSuccess { background-color: #d0e8d0; color: #0a3d0a; }
    .stError { background-color: #ffdddd; color: #c62828; }
    input, textarea, select { background-color: #ffffff !important; color: #1b5e20 !important; border-color: #1b5e20 !important; }
    .css-1d391kg, .css-1lcbmhc { background-color: #cfe9ff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS UTILITAIRES (adaptées) ---
def get_color(nom_lieu):
    colors = ["#2e7d32", "#1b5e20", "#0a3d0a", "#1565c0", "#1976d2", "#0d47a1"]
    hash_object = hashlib.md5(str(nom_lieu).upper().strip().encode())
    hue = int(hash_object.hexdigest()[:6], 16) % len(colors)
    return colors[hue]

def get_secret_code():
    try:
        res = supabase.table("configuration").select("secret_code").eq("id", "main_config").execute()
        return res.data[0]['secret_code'] if res.data else "1234"
    except:
        return "1234"

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
    # La colonne s'appelle est_verrouille (boolean)
    return bool(at.get("est_verrouille", False))

def trier_par_nom_puis_date(data):
    return sorted(data, key=lambda i: (
        i['adherents']['nom'].upper(),
        i['adherents']['prenom'].upper(),
        i['ateliers']['date']  # colonne 'date' au lieu de 'date_atelier'
    ))

# --- FONCTIONS D'EXPORT (adaptées) ---
def export_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Export')
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
        date_fr = format_date_fr_simple(at['date'])  # 'date'
        titre_at = at.get('titre', '')
        lieu = at.get('lieu', '')      # directement le texte
        horaire = at.get('horaire', '')# directement le texte
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

def export_planning_ateliers_pdf(title, ateliers_data, get_inscrits_fn):
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
        date_fr = format_date_fr_simple(a['date'])
        titre_at = a.get('titre', '')
        lieu = a.get('lieu', '')
        horaire = a.get('horaire', '')
        verrou = " [VERROUILLE]" if is_verrouille(a) else ""
        pdf.set_fill_color(212, 230, 241)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", 'B', 11)
        entete = f"  {date_fr} | {titre_at} | {lieu}{verrou}"
        pdf.cell(0, 8, entete.encode('latin-1', 'replace').decode('latin-1'), ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        sous = f"     Horaire : {horaire}  |  AM : {t_ad}  |  Enfants : {t_en}  |  Places restantes : {restantes}"
        pdf.cell(0, 6, sous.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        ins_tries = sorted(ins_at, key=lambda x: (x['adherents']['nom'].upper(), x['adherents']['prenom'].upper()))
        for p in ins_tries:
            nom_p = f"{p['adherents']['prenom']} {p['adherents']['nom']}"
            ligne = f"       • {nom_p}  ({p['nb_enfants']} enfant(s))"
            pdf.cell(0, 6, ligne.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        pdf.ln(3)
    return pdf.output(dest='S').encode('latin-1')

# --- DIALOGUES (inchangés, mais la fonction edit_atelier_dialog sera modifiée plus loin) ---
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
            if a_des_inscrits:
                supabase.table("inscriptions").delete().eq("atelier_id", at_id).execute()
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
def edit_atelier_dialog(at_id, titre_actuel, lieu_actuel, horaire_actuel, capacite_actuelle, lieux_list, horaires_list):
    """Dialogue adapté : on modifie directement les champs texte lieu et horaire"""
    inscriptions = supabase.table("inscriptions").select("nb_enfants").eq("atelier_id", at_id).execute()
    total_occupation = sum([1 + ins['nb_enfants'] for ins in inscriptions.data]) if inscriptions.data else 0

    nouveau_titre = st.text_input("Titre", value=titre_actuel)
    # Sélecteurs basés sur les listes de valeurs existantes (noms de lieux et créneaux)
    nouveau_lieu = st.selectbox("Lieu", options=lieux_list, index=lieux_list.index(lieu_actuel) if lieu_actuel in lieux_list else 0)
    nouvel_horaire = st.selectbox("Horaire", options=horaires_list, index=horaires_list.index(horaire_actuel) if horaire_actuel in horaires_list else 0)
    nouvelle_capacite = st.number_input("Capacité maximale (places totales)", min_value=1, value=int(capacite_actuelle))

    if nouvelle_capacite < total_occupation:
        st.error(f"La capacité ne peut pas être inférieure au nombre actuel d'occupants ({total_occupation} places prises).")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Annuler", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Enregistrer", type="primary", use_container_width=True, disabled=(nouvelle_capacite < total_occupation)):
            supabase.table("ateliers").update({
                "titre": nouveau_titre,
                "lieu": nouveau_lieu,
                "horaire": nouvel_horaire,
                "capacite_max": nouvelle_capacite
            }).eq("id", at_id).execute()
            enregistrer_log("Admin", "Modification atelier", f"Atelier ID {at_id} modifié : titre={nouveau_titre}, lieu={nouveau_lieu}, horaire={nouvel_horaire}, capacité={nouvelle_capacite}")
            st.success("Atelier modifié avec succès !")
            st.rerun()

# --- CHARGEMENT DES DONNÉES GLOBALES ---
if 'at_list_gen' not in st.session_state: st.session_state['at_list_gen'] = []
if 'super_access' not in st.session_state: st.session_state['super_access'] = False

current_code = get_secret_code()
res_adh = supabase.table("adherents").select("*").eq("est_actif", True).order("nom").order("prenom").execute()
dict_adh = {f"{a['prenom']} {a['nom']}": a['id'] for a in res_adh.data}
liste_adh = list(dict_adh.keys())

# --- NAVIGATION ---
menu = st.sidebar.radio("Navigation", ["📝 Inscriptions", "📊 Suivi & Récap", "🔐 Administration"])

# ==========================================
# SECTION 📝 INSCRIPTIONS
# ==========================================
if menu == "📝 Inscriptions":
    st.header("📍 Inscriptions")
    user_principal = st.selectbox("👤 Vous êtes :", ["Choisir..."] + liste_adh)

    if user_principal != "Choisir...":
        today_str = str(date.today())
        # Plus de jointure avec lieux/horaires : les infos sont dans ateliers directement
        res_at = supabase.table("ateliers").select("*").eq("est_actif", True).gte("date", today_str).order("date").execute()

        for at in res_at.data:
            res_ins = supabase.table("inscriptions").select("*, adherents(nom, prenom)").eq("atelier_id", at['id']).execute()
            total_occ = sum([(1 + (i['nb_enfants'] if i['nb_enfants'] else 0)) for i in res_ins.data])
            restantes = at['capacite_max'] - total_occ
            statut_p = f"✅ {restantes} pl. libres" if restantes > 0 else "🚨 COMPLET"
            at_info_log = f"{at['date']} | {at['horaire']} | {at['lieu']}"

            verrou_badge = " 🔒 <span class='badge-verrouille'>Inscription uniquement par l'admin</span>" if is_verrouille(at) else ""
            titre_label = f"{format_date_fr_complete(at['date'])} — {at['titre']} | 📍 {at['lieu']} | ⏰ {at['horaire']} | {statut_p}"

            with st.expander(titre_label):
                if is_verrouille(at):
                    st.warning("🔒 Cet atelier est géré par l'administration. Les inscriptions et désinscriptions ne sont pas disponibles ici.")

                if res_ins.data:
                    for i in res_ins.data:
                        n_f = f"{i['adherents']['prenom']} {i['adherents']['nom']}"
                        if is_verrouille(at):
                            st.write(f"• {n_f} **({i['nb_enfants']} enf.)**")
                        else:
                            c_nom, c_poub = st.columns([0.88, 0.12])
                            c_nom.write(f"• {n_f} **({i['nb_enfants']} enf.)**")
                            if c_poub.button("🗑️", key=f"del_{i['id']}"):
                                confirm_unsubscribe_dialog(i['id'], n_f, at_info_log, user_principal)

                if not is_verrouille(at):
                    st.markdown("---")
                    try: idx_def = (liste_adh.index(user_principal) + 1)
                    except: idx_def = 0
                    c1, c2, c3 = st.columns([2, 1, 1])
                    qui = c1.selectbox("Qui ?", ["Choisir..."] + liste_adh, index=idx_def, key=f"q_{at['id']}")
                    nb_e = c2.number_input("Enfants", 1, 10, 1, key=f"e_{at['id']}")

                    if c3.button("Valider", key=f"v_{at['id']}", type="primary"):
                        if qui != "Choisir...":
                            id_adh = dict_adh[qui]
                            existing = next((ins for ins in res_ins.data if ins['adherent_id'] == id_adh), None)
                            if existing:
                                if restantes - (nb_e - existing['nb_enfants']) < 0:
                                    st.error("Manque de places")
                                else:
                                    supabase.table("inscriptions").update({"nb_enfants": nb_e}).eq("id", existing['id']).execute()
                                    enregistrer_log(user_principal, "Modification", f"{qui} change à {nb_e} enfants - {at_info_log}")
                                    st.rerun()
                            else:
                                if restantes - (1 + nb_e) < 0:
                                    st.error("Manque de places")
                                else:
                                    supabase.table("inscriptions").insert({"adherent_id": id_adh, "atelier_id": at['id'], "nb_enfants": nb_e}).execute()
                                    enregistrer_log(user_principal, "Inscription", f"{qui} s'inscrit (+{nb_e} enf.) - {at_info_log}")
                                    st.rerun()

# ==========================================
# SECTION 📊 SUIVI & RÉCAP
# ==========================================
elif menu == "📊 Suivi & Récap":
    st.header("🔎 Consultation")
    t1, t2 = st.tabs(["👤 Par Assistante Maternelle", "📅 Par Atelier"])

    with t1:
        choix = st.multiselect("Filtrer par assistante maternelle :", liste_adh, key="pub_filter_am")
        ids = [dict_adh[n] for n in choix] if choix else list(dict_adh.values())
        # Requête sans jointure lieux/horaires (les colonnes sont dans ateliers)
        data = supabase.table("inscriptions").select("*, ateliers(*), adherents(nom, prenom)").in_("adherent_id", ids).eq("ateliers.est_actif", True).execute()

        data_triee = trier_par_nom_puis_date(data.data) if data.data else []

        if data.data:
            df_export = pd.DataFrame([{
                "Assistante Maternelle": f"{i['adherents']['prenom']} {i['adherents']['nom']}",
                "Date": i['ateliers']['date'],
                "Atelier": i['ateliers']['titre'],
                "Lieu": i['ateliers']['lieu'],
                "Horaire": i['ateliers']['horaire'],
                "Nb Enfants": i['nb_enfants']
            } for i in data_triee])
        else:
            df_export = pd.DataFrame(columns=["Assistante Maternelle", "Date", "Atelier", "Lieu", "Horaire", "Nb Enfants"])

        c_e1, c_e2 = st.columns(2)
        c_e1.download_button("📥 Excel", data=export_to_excel(df_export), file_name="suivi_am.xlsx")
        c_e2.download_button("📥 PDF", data=export_suivi_am_pdf("Suivi par Assistante Maternelle", data_triee), file_name="suivi_am.pdf")

        if data.data:
            curr_u = ""
            for i in data_triee:
                nom_u = f"{i['adherents']['prenom']} {i['adherents']['nom']}"
                if nom_u != curr_u:
                    st.markdown(f'<div style="color:#1b5e20; border-bottom:2px solid #1b5e20; padding-top:15px; margin-bottom:8px; font-weight:bold; font-size:1.2rem;">{nom_u}</div>', unsafe_allow_html=True)
                    curr_u = nom_u
                at = i['ateliers']
                c_l = get_color(at['lieu'])
                st.write(f"{format_date_fr_complete(at['date'], gras=True)} — {at['titre']} <span class='lieu-badge' style='background-color:{c_l}'>{at['lieu']}</span> <span class='horaire-text'>({at['horaire']})</span> **({i['nb_enfants']} enf.)**", unsafe_allow_html=True)
        else:
            st.info("Aucune inscription trouvée pour les AM sélectionnées.")

    with t2:
        c_d1, c_d2 = st.columns(2)
        d_s = c_d1.date_input("Du", date.today(), key="pub_d1", format="DD/MM/YYYY")
        d_e = c_d2.date_input("Au", d_s + timedelta(days=30), key="pub_d2", format="DD/MM/YYYY")
        ats_raw = supabase.table("ateliers").select("*").eq("est_actif", True).gte("date", str(d_s)).lte("date", str(d_e)).order("date").execute()

        all_ins_data = []
        cache_ins = {}
        if ats_raw.data:
            for a in ats_raw.data:
                ins_at = supabase.table("inscriptions").select("*, adherents(nom, prenom)").eq("atelier_id", a['id']).execute()
                cache_ins[a['id']] = ins_at.data
                for p in ins_at.data:
                    all_ins_data.append({
                        "Date": a['date'],
                        "Atelier": a['titre'],
                        "Lieu": a['lieu'],
                        "Horaire": a['horaire'],
                        "AM": f"{p['adherents']['prenom']} {p['adherents']['nom']}",
                        "Enfants": p['nb_enfants']
                    })

        if all_ins_data:
            df_at_exp = pd.DataFrame(all_ins_data)
        else:
            df_at_exp = pd.DataFrame(columns=["Date", "Atelier", "Lieu", "Horaire", "AM", "Enfants"])

        ce1, ce2 = st.columns(2)
        ce1.download_button("📥 Excel Planning", data=export_to_excel(df_at_exp), file_name="planning_ateliers.xlsx", key="exp_at_xl")
        ce2.download_button("📥 PDF Planning", data=export_planning_ateliers_pdf(
            "Planning des Ateliers", ats_raw.data if ats_raw.data else [], lambda aid: cache_ins.get(aid, [])
        ), file_name="planning_ateliers.pdf", key="exp_at_pdf")

        if ats_raw.data:
            for index, a in enumerate(ats_raw.data):
                c_l = get_color(a['lieu'])
                ins_at = cache_ins.get(a['id'], [])
                t_ad, t_en = len(ins_at), sum([p['nb_enfants'] for p in ins_at])
                restantes = a['capacite_max'] - (t_ad + t_en)
                cl_c = "alerte-complet" if restantes <= 0 else ""
                st.markdown(f"**{format_date_fr_complete(a['date'])}** | {a['titre']} | <span class='lieu-badge' style='background-color:{c_l}'>{a['lieu']}</span> | <span class='horaire-text'>{a['horaire']}</span> <span class='compteur-badge'>👤 {t_ad} AM</span> <span class='compteur-badge'>👶 {t_en} enf.</span> <span class='compteur-badge {cl_c}'>🏁 {restantes} pl.</span>", unsafe_allow_html=True)
                if ins_at:
                    ins_s = sorted(ins_at, key=lambda x: (x['adherents']['nom'], x['adherents']['prenom']))
                    html = "<div class='container-inscrits'>"
                    for p in ins_s:
                        html += f'<span class="liste-inscrits">• {p["adherents"]["prenom"]} {p["adherents"]["nom"]} <span class="nb-enfants-focus">({p["nb_enfants"]} enfants)</span></span>'
                    st.markdown(html + "</div>", unsafe_allow_html=True)
                if index < len(ats_raw.data) - 1:
                    st.markdown('<hr class="separateur-atelier">', unsafe_allow_html=True)
        else:
            st.info("Aucun atelier trouvé sur cette période.")

# ==========================================
# SECTION 🔐 ADMINISTRATION
# ==========================================
elif menu == "🔐 Administration":
    c_login1, c_login2 = st.columns([0.7, 0.3])
    pw = c_login1.text_input("Code secret admin", type="password")
    if c_login2.button("🔑 Code Super Admin"):
        super_admin_dialog()

    if pw == current_code or st.session_state['super_access']:
        t1, t2, t3, t4, t5, t6, t7, t8 = st.tabs([
            "🏗️ Ateliers", "📊 Suivi AM", "📅 Planning Ateliers",
            "📈 Statistiques de participation", "👥 Liste AM",
            "📍 Lieux / Horaires", "⚙️ Sécurité", "📜 Journal des actions"
        ])

        with t1:  # ATELIERS
            # Chargement des lieux et horaires depuis leurs tables (pour les listes déroulantes)
            l_raw = supabase.table("lieux").select("*").eq("est_actif", True).order("nom").execute().data
            h_raw = supabase.table("horaires").select("*").eq("est_actif", True).execute().data
            l_list = [l['nom'] for l in l_raw]
            h_list = [h['creneau'] for h in h_raw]  # colonne 'creneau'
            map_l_cap = {l['nom']: l['capacite'] for l in l_raw}  # colonne 'capacite'
            # Pas de map_l_id ni map_h_id car on stocke le texte directement

            sub = st.radio("Mode", ["Générateur", "Répertoire", "Actions groupées"], horizontal=True)

            if sub == "Générateur":
                col_lieu, col_horaire = st.columns(2)
                with col_lieu:
                    lieu_par_defaut = st.selectbox("Lieu par défaut pour les nouvelles lignes :",
                                                   options=[""] + l_list,
                                                   help="Choisissez un lieu qui sera prérempli dans chaque ligne générée.")
                with col_horaire:
                    horaire_par_defaut = st.selectbox("Horaire par défaut pour les nouvelles lignes :",
                                                      options=[""] + h_list,
                                                      help="Choisissez un horaire qui sera prérempli dans chaque ligne générée.")

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
                                "Actif": False,
                                "Verrouillé": False
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
                            "Actif": st.column_config.CheckboxColumn(default=False),
                            "Verrouillé": st.column_config.CheckboxColumn(default=False, help="Si coché, seul l'admin peut gérer les inscriptions")
                        },
                        use_container_width=True,
                        key="editor_ateliers"
                    )
                    if st.button("💾 Enregistrer"):
                        to_db = []
                        for _, r in df_ed.iterrows():
                            lieu_nom = r['Lieu']
                            horaire_val = r['Horaire']
                            if not lieu_nom or not horaire_val:
                                st.warning(f"Ligne ignorée : lieu ou horaire manquant pour la date {r['Date']}")
                                continue
                            # Vérification que le lieu et l'horaire existent dans les référentiels (optionnel)
                            if lieu_nom not in l_list:
                                st.error(f"Lieu '{lieu_nom}' introuvable dans la table lieux. Annulation.")
                                st.stop()
                            if horaire_val not in h_list:
                                st.error(f"Horaire '{horaire_val}' introuvable dans la table horaires. Annulation.")
                                st.stop()
                            date_iso = parse_date_fr_to_iso(r['Date'])
                            if not date_iso:
                                st.error(f"Format de date invalide : {r['Date']}")
                                st.stop()
                            to_db.append({
                                "date": date_iso,
                                "titre": r['Titre'],
                                "lieu": lieu_nom,
                                "horaire": horaire_val,
                                "capacite_max": int(r['Capacité']),
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
                            st.warning("Aucune ligne valide à enregistrer.")

            elif sub == "Répertoire":
                cf1, cf2, cf3 = st.columns(3)
                fs = cf1.date_input("Du", date.today() - timedelta(days=30), format="DD/MM/YYYY", key="rep_d1")
                fe = cf2.date_input("Au", fs + timedelta(days=60), format="DD/MM/YYYY", key="rep_d2")
                ft = cf3.selectbox("Statut Filtre", ["Tous", "Actifs", "Inactifs"])
                rep = supabase.table("ateliers").select("*").gte("date", str(fs)).lte("date", str(fe)).order("date").execute().data
                for a in rep:
                    if ft == "Actifs" and not a['est_actif']: continue
                    if ft == "Inactifs" and a['est_actif']: continue
                    verrou_icon = " 🔒" if is_verrouille(a) else ""
                    ca, cb, cc, cd, ce = st.columns([0.5, 0.12, 0.12, 0.12, 0.14])
                    ca.write(f"**{format_date_fr_complete(a['date'])}** | {a['horaire']} | {a['titre']} ({a['lieu']}){verrou_icon}")
                    btn_l = "🔴 Désactiver" if a['est_actif'] else "🟢 Activer"
                    if cb.button(btn_l, key=f"at_stat_{a['id']}"):
                        supabase.table("ateliers").update({"est_actif": not a['est_actif']}).eq("id", a['id']).execute()
                        st.rerun()
                    btn_v = "🔓 Déverrouiller" if is_verrouille(a) else "🔒 Verrouiller"
                    if cc.button(btn_v, key=f"at_verr_{a['id']}"):
                        nouvel_etat = not is_verrouille(a)
                        supabase.table("ateliers").update({"est_verrouille": bool(nouvel_etat)}).eq("id", a['id']).execute()
                        etat_str = "verrouillé" if nouvel_etat else "déverrouillé"
                        enregistrer_log("Admin", "Verrouillage atelier", f"Atelier '{a['titre']}' du {a['date']} {etat_str}")
                        st.rerun()
                    if cd.button("✏️", key=f"at_edit_{a['id']}"):
                        edit_atelier_dialog(a['id'], a['titre'], a['lieu'], a['horaire'], a['capacite_max'], l_list, h_list)
                    if ce.button("🗑️", key=f"at_del_{a['id']}"):
                        cnt = supabase.table("inscriptions").select("id", count="exact").eq("atelier_id", a['id']).execute().count
                        delete_atelier_dialog(a['id'], a['titre'], (cnt if cnt else 0) > 0, current_code)

            elif sub == "Actions groupées":
                with st.form("bulk_form"):
                    c1, c2 = st.columns(2)
                    bs = c1.date_input("Début", format="DD/MM/YYYY", key="blk_d1")
                    be = c2.date_input("Fin", format="DD/MM/YYYY", key="blk_d2")
                    action = st.radio("Action :", ["Activer", "Désactiver"], horizontal=True)
                    if st.form_submit_button("🚀 Appliquer"):
                        supabase.table("ateliers").update({"est_actif": (action == "Activer")}).gte("date", str(bs)).lte("date", str(be)).execute()
                        st.rerun()

        with t2:  # SUIVI AM (Admin)
            choix_adm = st.multiselect("Filtrer par AM (Admin) :", liste_adh, key="adm_filter_am")
            ids_adm = [dict_adh[n] for n in choix_adm] if choix_adm else list(dict_adh.values())
            data_adm = supabase.table("inscriptions").select("*, ateliers(*), adherents(nom, prenom)").in_("adherent_id", ids_adm).eq("ateliers.est_actif", True).execute()

            data_adm_triee = trier_par_nom_puis_date(data_adm.data) if data_adm.data else []

            if data_adm.data:
                df_adm = pd.DataFrame([{
                    "AM": f"{i['adherents']['prenom']} {i['adherents']['nom']}",
                    "Date": i['ateliers']['date'],
                    "Atelier": i['ateliers']['titre'],
                    "Lieu": i['ateliers']['lieu'],
                    "Horaire": i['ateliers']['horaire'],
                    "Enfants": i['nb_enfants']
                } for i in data_adm_triee])
            else:
                df_adm = pd.DataFrame(columns=["AM", "Date", "Atelier", "Lieu", "Horaire", "Enfants"])

            c_e3, c_e4 = st.columns(2)
            c_e3.download_button("📥 Excel (Admin)", data=export_to_excel(df_adm), file_name="admin_suivi_am.xlsx")
            c_e4.download_button("📥 PDF (Admin)", data=export_suivi_am_pdf("Suivi AM (Administration)", data_adm_triee), file_name="admin_suivi_am.pdf")

            if data_adm.data:
                curr = ""
                for i in data_adm_triee:
                    nom = f"{i['adherents']['prenom']} {i['adherents']['nom']}"
                    if nom != curr:
                        st.markdown(f'<div style="color:#1b5e20; border-bottom:2px solid #1b5e20; padding-top:15px; margin-bottom:8px; font-weight:bold; font-size:1.2rem;">{nom}</div>', unsafe_allow_html=True)
                        curr = nom
                    at = i['ateliers']
                    c_l = get_color(at['lieu'])
                    st.write(f"{format_date_fr_complete(at['date'], gras=True)} — {at['titre']} <span class='lieu-badge' style='background-color:{c_l}'>{at['lieu']}</span> <span class='horaire-text'>({at['horaire']})</span> **({i['nb_enfants']} enf.)**", unsafe_allow_html=True)
            else:
                st.info("Aucune inscription trouvée pour les AM sélectionnées.")

        with t3:  # PLANNING ATELIERS (Admin)
            st.subheader("📅 Planning des Ateliers")
            filtre_statut = st.radio("Filtrer par statut :", ["Tous", "Actifs", "Inactifs"], horizontal=True, key="admin_plan_filtre")
            c1_adm, c2_adm = st.columns(2)
            d_s_a = c1_adm.date_input("Du", date.today(), key="adm_plan_d1", format="DD/MM/YYYY")
            d_e_a = c2_adm.date_input("Au", d_s_a + timedelta(days=30), key="adm_plan_d2", format="DD/MM/YYYY")
            query = supabase.table("ateliers").select("*").gte("date", str(d_s_a)).lte("date", str(d_e_a))
            if filtre_statut == "Actifs":
                query = query.eq("est_actif", True)
            elif filtre_statut == "Inactifs":
                query = query.eq("est_actif", False)
            ats_adm = query.order("date").execute()
            cache_ins_adm = {}
            adm_ins_list = []
            if ats_adm.data:
                for a in ats_adm.data:
                    ins_at = supabase.table("inscriptions").select("*, adherents(nom, prenom)").eq("atelier_id", a['id']).execute()
                    cache_ins_adm[a['id']] = ins_at.data
                    for p in ins_at.data:
                        adm_ins_list.append({
                            "Date": a['date'],
                            "Atelier": a['titre'],
                            "Lieu": a['lieu'],
                            "AM": f"{p['adherents']['prenom']} {p['adherents']['nom']}",
                            "Enfants": p['nb_enfants']
                        })
            if adm_ins_list:
                df_adm_at = pd.DataFrame(adm_ins_list)
            else:
                df_adm_at = pd.DataFrame(columns=["Date", "Atelier", "Lieu", "AM", "Enfants"])
            cea1, cea2 = st.columns(2)
            cea1.download_button("📥 Excel Planning (Admin)", data=export_to_excel(df_adm_at), file_name="admin_planning_ateliers.xlsx", key="adm_exp_xl")
            cea2.download_button("📥 PDF Planning (Admin)", data=export_planning_ateliers_pdf(
                "Planning des Ateliers (Administration)", ats_adm.data if ats_adm.data else [], lambda aid: cache_ins_adm.get(aid, [])
            ), file_name="admin_planning_ateliers.pdf", key="adm_exp_pdf")
            if ats_adm.data:
                for index, a in enumerate(ats_adm.data):
                    c_l = get_color(a['lieu'])
                    ins_at = cache_ins_adm.get(a['id'], [])
                    t_ad, t_en = len(ins_at), sum([p['nb_enfants'] for p in ins_at])
                    restantes = a['capacite_max'] - (t_ad + t_en)
                    cl_c = "alerte-complet" if restantes <= 0 else ""
                    verrou_icon = " 🔒" if is_verrouille(a) else ""
                    at_info_log = f"{a['date']} | {a['horaire']} | {a['lieu']}"
                    st.markdown(f"**{format_date_fr_complete(a['date'])}** | {a['titre']} | <span class='lieu-badge' style='background-color:{c_l}'>{a['lieu']}</span> | <span class='horaire-text'>{a['horaire']}</span>{verrou_icon} <span class='compteur-badge'>👤 {t_ad} AM</span> <span class='compteur-badge'>👶 {t_en} enf.</span> <span class='compteur-badge {cl_c}'>🏁 {restantes} pl.</span>", unsafe_allow_html=True)
                    if ins_at:
                        ins_s = sorted(ins_at, key=lambda x: (x['adherents']['nom'], x['adherents']['prenom']))
                        for p in ins_s:
                            n_f = f"{p['adherents']['prenom']} {p['adherents']['nom']}"
                            cp1, cp2, cp3, cp4 = st.columns([0.45, 0.2, 0.2, 0.15])
                            cp1.write(f"• {n_f}")
                            new_nb = cp2.number_input("Enf.", 1, 10, int(p['nb_enfants']), key=f"adm_nb_{p['id']}", label_visibility="collapsed")
                            if cp3.button("✏️ Modifier", key=f"adm_mod_{p['id']}"):
                                supabase.table("inscriptions").update({"nb_enfants": new_nb}).eq("id", p['id']).execute()
                                enregistrer_log("Admin", "Modification (admin)", f"{n_f} → {new_nb} enfants - {at_info_log}")
                                st.rerun()
                            if cp4.button("🗑️", key=f"adm_del_plan_{p['id']}"):
                                confirm_unsubscribe_dialog(p['id'], n_f, at_info_log, "Admin")
                    with st.expander(f"➕ Inscrire une AM à cet atelier", expanded=False):
                        ca1, ca2, ca3 = st.columns([2, 1, 1])
                        qui_adm = ca1.selectbox("AM à inscrire", ["Choisir..."] + liste_adh, key=f"adm_qui_{a['id']}")
                        nb_adm = ca2.number_input("Enfants", 1, 10, 1, key=f"adm_enf_{a['id']}")
                        if ca3.button("✅ Inscrire", key=f"adm_ins_{a['id']}", type="primary"):
                            if qui_adm != "Choisir...":
                                id_adh = dict_adh[qui_adm]
                                existing = next((ins for ins in ins_at if ins['adherent_id'] == id_adh), None)
                                if existing:
                                    if restantes - (nb_adm - existing['nb_enfants']) < 0:
                                        st.error("Manque de places")
                                    else:
                                        supabase.table("inscriptions").update({"nb_enfants": nb_adm}).eq("id", existing['id']).execute()
                                        enregistrer_log("Admin", "Modification (admin)", f"{qui_adm} → {nb_adm} enfants - {at_info_log}")
                                        st.rerun()
                                else:
                                    if restantes - (1 + nb_adm) < 0:
                                        st.error("Manque de places")
                                    else:
                                        supabase.table("inscriptions").insert({"adherent_id": id_adh, "atelier_id": a['id'], "nb_enfants": nb_adm}).execute()
                                        enregistrer_log("Admin", "Inscription (admin)", f"{qui_adm} inscrite (+{nb_adm} enf.) - {at_info_log}")
                                        st.rerun()
                    if index < len(ats_adm.data) - 1:
                        st.markdown('<hr class="separateur-atelier">', unsafe_allow_html=True)
            else:
                st.info("Aucun atelier trouvé sur cette période.")

        with t4:  # STATS
            st.subheader("📈 Statistiques de participation")
            cs1, cs2 = st.columns(2)
            ds_stat = cs1.date_input("Date début", date.today().replace(day=1), key="stat_d1", format="DD/MM/YYYY")
            de_stat = cs2.date_input("Date fin", date.today(), key="stat_d2", format="DD/MM/YYYY")
            ins_stat = supabase.table("inscriptions").select("*, adherents(nom, prenom), ateliers!inner(date)").gte("ateliers.date", str(ds_stat)).lte("ateliers.date", str(de_stat)).execute()
            ats_count = supabase.table("ateliers").select("id", count="exact").gte("date", str(ds_stat)).lte("date", str(de_stat)).execute()
            ateliers_periode = supabase.table("ateliers").select("date, titre, lieu, horaire").gte("date", str(ds_stat)).lte("date", str(de_stat)).order("date").execute()
            if ins_stat.data:
                stats_list = []
                for am_nom in liste_adh:
                    am_id = dict_adh[am_nom]
                    count = sum(1 for x in ins_stat.data if x['adherent_id'] == am_id)
                    stats_list.append({"Assistante Maternelle": am_nom, "Nombre d'ateliers": count})
                df_stats = pd.DataFrame(stats_list).sort_values("Nombre d'ateliers", ascending=False)
                st.table(df_stats)
                total_inscr = df_stats["Nombre d'ateliers"].sum()
                nb_at_proposes = ats_count.count if ats_count.count else 0
                st.markdown(f"**Total des inscriptions sur la période :** {total_inscr}")
                st.markdown(f"**Nombre d'ateliers proposés sur la période :** {nb_at_proposes}")
                if ateliers_periode.data:
                    st.markdown("**Ateliers proposés :**")
                    for at in ateliers_periode.data:
                        date_fr = format_date_fr_simple(at['date'])
                        st.write(f"- {date_fr} : **{at['titre']}** ({at['lieu']} - {at['horaire']})")
                else:
                    st.info("Aucun atelier proposé sur cette période.")
                ce_s1, ce_s2 = st.columns(2)
                ce_s1.download_button("📥 Excel Statistiques", data=export_to_excel(df_stats), file_name=f"stats_am_{ds_stat}_{de_stat}.xlsx")
                pdf_stat_lines = []
                for _, r in df_stats.iterrows():
                    pdf_stat_lines.append(f"{r['Assistante Maternelle']} : {r['Nombre d\'ateliers']} atelier(s)")
                pdf_stat_lines.append("")
                pdf_stat_lines.append(f"Total inscriptions sur la période : {total_inscr}")
                pdf_stat_lines.append(f"Ateliers proposés sur la période : {nb_at_proposes}")
                pdf_stat_lines.append("")
                pdf_stat_lines.append("Liste des ateliers proposés :")
                for at in ateliers_periode.data:
                    date_fr = format_date_fr_simple(at['date'])
                    pdf_stat_lines.append(f"- {date_fr} : {at['titre']} ({at['lieu']} - {at['horaire']})")
                ce_s2.download_button("📥 PDF Statistiques", data=export_to_pdf("Statistiques de participation AM", pdf_stat_lines), file_name=f"stats_am_{ds_stat}_{de_stat}.pdf")
            else:
                st.info("Aucune donnée pour cette période.")
                if ateliers_periode.data:
                    st.markdown("**Ateliers proposés sur la période :**")
                    for at in ateliers_periode.data:
                        date_fr = format_date_fr_simple(at['date'])
                        st.write(f"- {date_fr} : **{at['titre']}** ({at['lieu']} - {at['horaire']})")

        with t5:  # 👥 LISTE AM
            with st.form("add_am"):
                c1, c2 = st.columns(2)
                nom = c1.text_input("Nom").upper().strip()
                pre = " ".join([w.capitalize() for w in c2.text_input("Prénom").split()]).strip()
                if st.form_submit_button("➕ Ajouter"):
                    if nom and pre:
                        supabase.table("adherents").insert({"nom": nom, "prenom": pre, "est_actif": True}).execute()
                        st.rerun()
            for u in res_adh.data:
                c1, c_edit, c_del = st.columns([0.7, 0.15, 0.15])
                c1.write(f"**{u['nom']}** {u['prenom']}")
                if c_edit.button("✏️ Modifier", key=f"am_edit_{u['id']}"):
                    edit_am_dialog(u['id'], u['nom'], u['prenom'])
                if c_del.button("🗑️", key=f"am_del_{u['id']}"):
                    secure_delete_dialog("adherents", u['id'], f"{u['prenom']} {u['nom']}", current_code)

        with t6:  # 📍 LIEUX / HORAIRES
            cl1, cl2 = st.columns(2)
            with cl1:
                st.subheader("Lieux")
                for l in l_raw:
                    ca, cb = st.columns([0.8, 0.2])
                    ca.markdown(f"<span class='lieu-badge' style='background-color:{get_color(l['nom'])}'>{l['nom']} (Cap: {l['capacite']})</span>", unsafe_allow_html=True)
                    if cb.button("🗑️", key=f"lx_{l['id']}"):
                        secure_delete_dialog("lieux", l['id'], l['nom'], current_code)
                with st.form("add_lx"):
                    nl = st.text_input("Nouveau Lieu")
                    cp = st.number_input("Capacité", 1, 50, 10)
                    if st.form_submit_button("Ajouter"):
                        supabase.table("lieux").insert({"nom": nl, "capacite": cp, "est_actif": True}).execute()
                        st.rerun()
            with cl2:
                st.subheader("Horaires")
                for h in h_raw:
                    cc, cd = st.columns([0.8, 0.2])
                    cc.write(f"• {h['creneau']}")
                    if cd.button("🗑️", key=f"hx_{h['id']}"):
                        secure_delete_dialog("horaires", h['id'], h['creneau'], current_code)
                with st.form("add_hx"):
                    nh = st.text_input("Nouvel Horaire")
                    if st.form_submit_button("Ajouter"):
                        supabase.table("horaires").insert({"creneau": nh, "est_actif": True}).execute()
                        st.rerun()

        with t7:  # ⚙️ SÉCURITÉ
            with st.form("sec_form"):
                o = st.text_input("Ancien code", type="password")
                n = st.text_input("Nouveau code", type="password")
                if st.form_submit_button("Changer le code"):
                    if o == current_code or o == "0000":
                        supabase.table("configuration").update({"secret_code": n}).eq("id", "main_config").execute()
                        st.rerun()
                    else:
                        st.error("Ancien code incorrect")
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
                st.error(f"Erreur lors du chargement du journal : {e}")

    else:
        st.info("Saisissez le code secret pour accéder aux fonctions d'administration.")
