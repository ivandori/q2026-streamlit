'''
=============================================================================
Q2026 - DEMO DIMENSIONAMENTO DI UNA LINEA ELETTRICA
FUNZIONI MAIN PER STREAMLIT
Ultimo aggiornamento: 24/02/2026
AUTORE: Ivano Dorigatti
LICENZA: MIT License
=============================================================================
'''

import streamlit as st
import sqlite3

from calcolo import (
    calcola_ib, calcolo_temperatura_cavo_preciso, cerca_dispositivi, cerca_inom, cerca_curva, cerca_potint,
    cerca_classe, cerca_dmin, cerca_tipo_cavo, cerca_formazione, cerca_sezf,
    cerca_iz_nominale, cerca_posa, cerca_kposa, cerca_kcircuiti, cerca_ktambiente,
    calcoloicc, calcolocdt, calcolo_i2t, calcolok2s2, calcolo_temperatura_cavo,
    cerca_sezng, poli_validi_da_carico, formazioni_ammesse, seleziona_in_nominale,
    calcolo_sezione_cavo,sezione_derivata
)
from impaginazione import centered_title, subtitle, centered_header
from helper import init_state, invalidate, selectbox_safe, on_change_formazione, sync_selectbox

import streamlit as st

# Inizializzazione sicura contatore e selezione per evitare errori alla prima esecuzione
if "counter_select" not in st.session_state:
    st.session_state.counter_select = 0

if "my_select" not in st.session_state:
    st.session_state.my_select = None

# Callback
def incrementa_contatore():
    st.session_state.counter_select += 1


# =============================================================================
# 1. DEFAULT GLOBALI DELLO STATO (UNICA FONTE DI VERITÀ)
# =============================================================================
DEFAULT_STATE = {
    # -------------------------
    # PARAMETRI ELETTRICI BASE
    # -------------------------
    "v_nominale": 400,
    "cos_fi_carico": 0.9,
    "potenza_carico": 10.0,
    "cdt_in_ingresso": 0.0,
    "cdt_max": 4.0,

    # -------------------------
    # FASI / CONDUTTORI
    # -------------------------
    "n_fasi_ingresso": 3,
    "n_ingresso": True,
    "pe_ingresso": True,

    "n_fasi_carico": 3,
    "n_carico": True,
    "pe_carico": True,

    # -------------------------
    # CAVO
    # -------------------------
    "materiale_cavo": "Rame",
    "isolamento_cavo": "PVC",
    "tipo_cavo": "FS17",
    "formazione_cavo": "Unipolare 1x",
    "sezione_f": 4.0,
    "sezione_n": 4.0,
    "sezione_pe": 4.0,

    # -------------------------
    # LINEA
    # -------------------------
    "lunghezza_m": 10,
    "n_paralleli_f": 1,
    "n_paralleli_n": 1,
    "n_paralleli_pe": 1,

    # -------------------------
    # PROTEZIONI
    # -------------------------
    "n_poli_selection": "4_",
    "dispositivo_selection": "MTD",
    "inom_selection": 25.0,
    "curva_selection": "C",
    "potint_selection": 15.0,
    "classe_selection": "AC",
    "idiff_selection": 0.3,
    "in_insufficiente": False,      # flag per avviso

    # -------------------------
    # CONDIZIONI DI GUASTO IN INGRESSO
    # -------------------------
    "icc_3f_ingresso": 10.0,
    "icc_fn_ingresso": 6.0,
    "icc_fpe_ingresso": 4.0,
    "cos_fi_3f_ingresso": 0.5,
    "cos_fi_fn_ingresso": 0.7,
    "cos_fi_fpe_ingresso": 0.7,

    # -------------------------
    # POSA E TEMPERATURA
    # -------------------------
    "n_strati": 1,
    "n_circuiti": 1,
    "temperatura_ambiente": 30,
    "posa_cei": None,

    # -------------------------
    # CALCOLI
    # -------------------------
    "ib_carico": 0.0,
}

# =============================================================================
# 2. FUNZIONI DI INIZIALIZZAZIONE
# =============================================================================

def init_session_state():
    """Inizializza lo stato con i DEFAULT_STATE, senza sovrascrivere."""
    for key, value in DEFAULT_STATE.items():
        st.session_state.setdefault(key, value)

def init_cavo_state():
    """Inizializza tipo cavo, formazione e sezioni in base ai dati iniziali."""
    # --- Tipo cavo ---
    if st.session_state.tipo_cavo is None:
        tipi = cerca_tipo_cavo(
            st.session_state.materiale_cavo.upper(),
            st.session_state.isolamento_cavo.upper()
        )
        st.session_state.tipo_cavo = tipi[0] if tipi else None

    # --- Formazione ---
    if st.session_state.formazione_cavo is None and st.session_state.tipo_cavo:
        formazioni = cerca_formazione(st.session_state.tipo_cavo)
        st.session_state.formazione_cavo = formazioni[0] if formazioni else None

    # --- Sezioni ---
    if (
        st.session_state.sezione_f is None
        and st.session_state.tipo_cavo
        and st.session_state.formazione_cavo
    ):
        sezioni = cerca_sezf(
            st.session_state.tipo_cavo,
            st.session_state.formazione_cavo
        )
        if sezioni:
            st.session_state.sezione_f = max(sezioni[0], 2.5)
            st.session_state.sezione_n = max(sezioni[0], 2.5)
            st.session_state.sezione_pe = max(sezioni[0], 2.5)

def init_posa_default():
    """Inizializza il primo valore valido per posa_cei."""
    if st.session_state.posa_cei is None:
        is_unipolare = 1 if st.session_state.formazione_cavo == "Unipolare 1x" else 0
        posa_options = cerca_posa(is_unipolare)
        if posa_options:
            st.session_state.posa_cei = posa_options[0]

def init_ib():
    """Calcola la corrente di carico Ib e la memorizza nello stato."""
    e_stellata = (
        st.session_state.v_nominale
        if st.session_state.n_fasi_carico == 1
        else st.session_state.v_nominale / (3 ** 0.5)
    )
    st.session_state.ib_carico = calcola_ib(
        e_stellata,
        st.session_state.n_fasi_carico,
        st.session_state.potenza_carico * 1000,
        st.session_state.cos_fi_carico
    )

def validate_session_state():
    """Corregge eventuali incongruenze nello stato."""
    # --- Fasi ingresso ---
    if st.session_state.n_fasi_ingresso == 1:
        st.session_state.n_ingresso = True

    # --- Fasi carico ---
    if st.session_state.n_fasi_carico == 1:
        st.session_state.n_carico = True
    if not st.session_state.n_ingresso:
        st.session_state.n_carico = False

    # --- PE ---
    if not st.session_state.pe_ingresso:
        st.session_state.pe_carico = False

    # --- Forzatura sezioni per cavi multipolari ---
    if st.session_state.formazione_cavo != "Unipolare 1x":
        if st.session_state.sezione_f is not None:
            st.session_state.sezione_n = st.session_state.sezione_f
            st.session_state.sezione_pe = st.session_state.sezione_f
        else:
            # Unipolare non monofase
            selectbox_safe("Sez. N", sez_f_opts, "sezione_n")
            if st.session_state.sezione_n is None:
                st.session_state.sezione_n = sez_f_opts[0]
            selectbox_safe("Sez. Pe", sez_f_opts, "sezione_pe")
            if st.session_state.sezione_pe is None:
                st.session_state.sezione_pe = sez_f_opts[0]    

    # --- Paralleli positivi ---
    for k in ("n_paralleli_f", "n_paralleli_n", "n_paralleli_pe"):
        if st.session_state.get(k, 1) < 1:
            st.session_state[k] = 1

    # --- Limiti cosφ e potenza ---
    if not (0 < st.session_state.cos_fi_carico <= 1):
        st.session_state.cos_fi_carico = 0.9
    if st.session_state.potenza_carico <= 0:
        st.session_state.potenza_carico = 0.01

# =============================================================================
# 3. SEQUENZA DI INIZIALIZZAZIONE (ESEGUITA AD OGNI RUN)
# =============================================================================
init_state()              # helper.py: chiavi minime di base
init_session_state()      # nostri DEFAULT_STATE
init_cavo_state()         # dipendenze DB
init_posa_default()       # default per posa_cei
init_ib()                # calcolo corrente carico
validate_session_state() # pulizia finale

# =============================================================================
# 4. CONFIGURAZIONE PAGINA E INTESTAZIONE
# =============================================================================
st.set_page_config(page_title="DIMENSIONAMENTO LINEA BT", layout="wide")
centered_title("DIMENSIONAMENTO LINEA BT")

# =============================================================================
# 5. UI – INPUT (CABINA / TRASFORMATORE)
# =============================================================================
with st.container():
    centered_header("INPUT")
    subtitle("Dati cabina o trasformatore")
    col_input1, col_input2 = st.columns([1, 1])

    # --- Condizioni di guasto in ingresso ---
    with col_input1:
        with st.container(border=True):
            st.markdown(":blue[Condizioni di guasto in ingresso]")
            col64, col65 = st.columns(2)
            with col64:
                st.number_input(
                    "Icc (kA) 3F", min_value=0.001,
                    key="icc_3f_ingresso", format="%.3f"
                )
                st.number_input(
                    "Icc (kA) F-N", min_value=0.001,
                    key="icc_fn_ingresso", format="%.3f"
                )
                st.number_input(
                    "Icc (kA) F-Pe", min_value=0.001,
                    key="icc_fpe_ingresso", format="%.3f"
                )
            with col65:
                st.number_input(
                    "Cosφ 3F", min_value=0.000, max_value=1.000,
                    key="cos_fi_3f_ingresso", format="%.3f"
                )
                st.number_input(
                    "Cosφ F-N", min_value=0.000, max_value=1.000,
                    key="cos_fi_fn_ingresso", format="%.3f"
                )
                st.number_input(
                    "Cosφ F-Pe", min_value=0.000, max_value=1.000,
                    key="cos_fi_fpe_ingresso", format="%.3f"
                )

    # --- Dati iniziali (tensione, fasi, CDT) ---
    with col_input2:
        with st.container(border=True):
            st.markdown(":blue[Dati iniziali]")
            v_nominale = st.number_input("V nominale (V)", key="v_nominale")
            e_stellata = v_nominale / (3 ** 0.5)

            n_fasi_ingresso = sync_selectbox(
                label="N° Fasi",
                key="n_fasi_ingresso",
                options=[1, 2, 3],
                help_text="Seleziona il numero di fasi"
            )

            n_ingresso_disabled = n_fasi_ingresso == 1
            if n_ingresso_disabled:
                e_stellata = v_nominale
                st.session_state.n_ingresso = True
                
            if n_fasi_ingresso == 2:
                st.warning("⚠️ Sistema bifase: la tensione stellata è uguale alla nominale")
                e_stellata = v_nominale
                st.session_state.n_ingresso = False
                n_ingresso_disabled =True

            col11, col12, col13 = st.columns([1.5, 1, 1.5])
            with col11:
                pass
            with col12:
                st.checkbox("N", key="n_ingresso", disabled=n_ingresso_disabled)
            with col13:
                st.checkbox("Pe", key="pe_ingresso")

            if n_fasi_ingresso and n_fasi_ingresso > 1:
                st.text(f"V fase (E): {round(e_stellata)}V")

            st.number_input(
                "C.D.T. % in ingresso", min_value=0.0, max_value=10.0,
                key="cdt_in_ingresso"
            )
            st.number_input(
                "C.D.T. % tot massima", min_value=0.001, max_value=10.0,
                key="cdt_max"
            )

# =============================================================================
# 6. UI – CARICO
# =============================================================================
with st.container():
    centered_header("CARICO")
    colA, colB = st.columns([1, 1])

    with colA:
        with st.container(border=True):
            st.markdown(":blue[Carico]")
            col11, col12, col13 = st.columns([1.5, 1, 1.5])

            with col11:
                max_fasi = st.session_state.n_fasi_ingresso + 1
                min_fasi = 1 if st.session_state.n_ingresso else 2
                sync_selectbox(
                    label="N° Fasi",
                    key="n_fasi_carico",
                    options=list(range(min_fasi, max_fasi))
                )

            with col12:
                st.text("N")
                n_disabled = False
                if st.session_state.n_fasi_carico == 2 or (not st.session_state.n_ingresso and st.session_state.n_fasi_carico > 1):
                    st.session_state.n_carico = False
                    n_disabled = True
                elif st.session_state.n_fasi_carico == 1:
                    st.session_state.n_carico = True
                    n_disabled = True
                st.checkbox("N", key="n_carico", disabled=n_disabled)

            with col13:
                st.text("Pe")
                pe_disabled = not st.session_state.pe_ingresso
                if pe_disabled:
                    st.session_state.pe_carico = False
                st.checkbox("Pe", key="pe_carico", disabled=pe_disabled)

            col1, col2 = st.columns([1.5, 1])
            with col1:
                st.number_input("Pot.(kW)", min_value=0.01, key="potenza_carico")
            with col2:
                st.number_input("Cosφ", min_value=0.001, max_value=1.0, key="cos_fi_carico")

            # Ricalcolo Ib dopo modifica potenza/cosφ/fasi
            init_ib()

    with colB:
        with st.container(border=True):
            st.markdown(":blue[Corrente]")
            st.metric(":blue[$I_b$ carico (A) ]", f"{st.session_state.ib_carico:.2f}")
            if st.button("CALCOLA LA CORRENTE NOMINALE", key="calcola_la_in", type="primary", use_container_width=True):
                ib = st.session_state.ib_carico
                available_nominal_currents = cerca_inom(
                    st.session_state.n_poli_selection,
                    st.session_state.dispositivo_selection
                )
                in_options = available_nominal_currents
                in_sel, in_insufficiente = seleziona_in_nominale(
                    ib, in_options)
                st.session_state.inom_selection = in_sel
                st.session_state.in_insufficiente = in_insufficiente

                if st.session_state.in_insufficiente:
                    st.warning(
                        f"⚠️ Corrente nominale insufficiente: "
                        f"Ib = {st.session_state.ib_carico:.2f} A > "
                        f"In max = {st.session_state.inom_selection} A"
                    )
                else:
                    st.success(
                        f"Nuovo valore di I nominale: {st.session_state.inom_selection:.2f} A")


# =============================================================================
# 7. UI – DISPOSITIVO DI PROTEZIONE
# =============================================================================
with st.container():
    centered_header("DISPOSITIVO PROTEZIONE")
    col1, col2, col3, col4 = st.columns([1.12, 1.11, 1, 1.11])
    
    i2t_val=0
    # --- Interruttore (poli e tipo) ---
    with col1:
        with st.container(border=True):
            st.markdown(":blue[Interruttore]")
            poli_opts, poli_def = poli_validi_da_carico(
                st.session_state.n_fasi_carico,
                st.session_state.n_carico
            )
            if st.session_state.n_poli_selection not in poli_opts:
                st.session_state.n_poli_selection = poli_def
            disabled = len(poli_opts) == 1
            st.selectbox("N° poli", poli_opts, key="n_poli_selection", disabled=disabled)

            sync_selectbox(
                "Tipo di int.", "dispositivo_selection",
                cerca_dispositivi(st.session_state.n_poli_selection)
            )

    # --- Corrente nominale ---
    with col2:
        with st.container(border=True):
            st.markdown(":blue[Corrente]")
            st.selectbox(
                "I nominale (A)",
                cerca_inom(
                    st.session_state.n_poli_selection,
                    st.session_state.dispositivo_selection
                ),
                key="inom_selection",
                help="Seleziona il valore di corrente nominale"
            )

    # --- Magnetotermico (curva, I²t, potere interr.) ---
    if st.session_state.dispositivo_selection in ["MTD", "MT_"]:
        with col3:
            curva_opts = cerca_curva(
                st.session_state.n_poli_selection,
                st.session_state.dispositivo_selection,
                st.session_state.inom_selection
            )
            if curva_opts:
                with st.container(border=True):
                    st.markdown(":blue[Magnetotermico]")
                    sync_selectbox("Curva", "curva_selection", curva_opts)
                    if st.session_state.curva_selection:
                        i2t_val = calcolo_i2t(
                            st.session_state.curva_selection,
                            st.session_state.inom_selection
                        )
                        if i2t_val >= 1e8:
                            st.metric("$I^2t$ (A²s)", f"{i2t_val:.3e}",
                                    help="Valore stimato basato sulla curva di intervento selezionata (consultare i dati del costruttore per valori precisi).")
                        else:
                            st.metric("$I^2t$ (A²s)", f"{i2t_val:.0f}",
                        help="Valore stimato basato sulla curva di intervento selezionata (consultare i dati del costruttore per valori precisi).")
                    sync_selectbox(
                        "Potere di int.", "potint_selection",
                        cerca_potint(
                            st.session_state.n_poli_selection,
                            st.session_state.dispositivo_selection,
                            st.session_state.inom_selection,
                            st.session_state.curva_selection,
                            st.session_state.n_fasi_carico
                        )
                    )

    # --- Differenziale (classe, Idiff) ---
    if st.session_state.dispositivo_selection in ["MTD", "DIF"]:
        with col4:
            classe_opts = cerca_classe(
                st.session_state.n_poli_selection,
                st.session_state.dispositivo_selection,
                st.session_state.inom_selection
            )
            if classe_opts:
                with st.container(border=True):
                    st.markdown(":blue[Differenziale]")
                    sync_selectbox("Classe", "classe_selection", classe_opts)
                    sync_selectbox(
                        "Idiff", "idiff_selection",
                        cerca_dmin(
                            st.session_state.n_poli_selection,
                            st.session_state.dispositivo_selection,
                            st.session_state.inom_selection,
                            st.session_state.classe_selection
                        )
                    )

# =============================================================================
# 8. UI – CONDUTTORE E POSA
# =============================================================================
with st.container():
    centered_header("CONDUTTORE")
    col_left, col_right = st.columns([1, 1])

    # --- SCELTA DEL CAVO ---
    with col_left:
        with st.container(border=True):
            st.markdown(":blue[SCELTA DEL CAVO]")
            st.selectbox("Materiale", ["Rame", "Alluminio"], key="materiale_cavo")

            # Carica isolamenti dal DB
            db_path = r'cavi_q2025.sqlite'
            with sqlite3.connect(db_path) as conn:
                iso_opts = [
                    r[0] for r in conn.execute(
                        "SELECT DISTINCT ISOLAMENTO FROM CAVI WHERE MATERIALE = ?",
                        (st.session_state.materiale_cavo.upper(),)
                    )
                ]
            st.selectbox("Isolamento", iso_opts, key="isolamento_cavo")

            # Tipo cavo
            tipo_opts = cerca_tipo_cavo(
                st.session_state.materiale_cavo.upper(),
                st.session_state.isolamento_cavo.upper()
            )
            if not tipo_opts:
                st.error("Nessun tipo cavo trovato.")
            idx = 0
            if st.session_state.tipo_cavo in tipo_opts:
                idx = tipo_opts.index(st.session_state.tipo_cavo)
            st.selectbox("Tipo cavo", tipo_opts, index=idx, key="tipo_cavo")

            # Formazione (filtra per compatibilità poli/PE)
            tutte_formazioni = cerca_formazione(st.session_state.tipo_cavo)
            formazioni_valide = formazioni_ammesse(
                tutte_formazioni,
                st.session_state.n_poli_selection,
                st.session_state.pe_carico
            )
            if not formazioni_valide:
                st.error("⚠️ Nessuna formazione compatibile.")
                st.stop()
            if st.session_state.formazione_cavo not in formazioni_valide:
                st.session_state.formazione_cavo = formazioni_valide[0]
            formazione=st.selectbox("Formazione", formazioni_valide, key="formazione_cavo")

            # Pulsante calcolo automatico sezione (placeholder)
 
    # --- SEZIONI DEI CAVI ---
    with col_right:
        with st.container(border=True):
            st.markdown(":blue[SEZIONI DEI CAVI]")
           
            if st.session_state.formazione_cavo is None:
                st.error("Selezionare una formazione valida.")
                st.stop()

            sez_f_opts = cerca_sezf(
                st.session_state.tipo_cavo,
                st.session_state.formazione_cavo
            )
            if not sez_f_opts:
                st.error("Nessuna sezione disponibile.")
                st.stop()

            # Sezione fase
            def aggiorna_sezioni_derivate():

                # ---- Protezione inizializzazione ----
                if "counter_select" not in st.session_state:
                    st.session_state.counter_select = 0

                st.session_state.counter_select += 1

                sez_f = st.session_state.sezione_f
                
                formazione = st.session_state.formazione_cavo


                # Funzione di clamp sicura
                def clamp(val):
                    if val not in sez_f_opts:
                        return sez_f
                    return val

                # ==============================
                # MULTIPOLARE
                # ==============================
                if formazione != "Unipolare 1x":

                    sez_n = cerca_sezng(st.session_state.tipo_cavo, sez_f)
                    st.session_state.sezione_n = clamp(sez_n if sez_n else sez_f)

                    sez_pe = cerca_sezng(st.session_state.tipo_cavo, sez_f)
                    st.session_state.sezione_pe = clamp(sez_pe if sez_pe else sez_f)

                    return

                # ==============================
                # UNIPOLARE
                # ==============================

                # ----- NEUTRO -----
                if st.session_state.n_carico:
                    if st.session_state.n_fasi_carico == 1:
                        st.session_state.sezione_n = sez_f
                    else:
                        if st.session_state.get("mezza_sezione_n", False):
                            val = sezione_derivata(
                                sez_f,
                                sez_f_opts,
                                st.session_state.materiale_cavo
                            )
                            st.session_state.sezione_n = clamp(val)
                        else:
                            val = st.session_state.get("sezione_n", sez_f)
                            st.session_state.sezione_n = clamp(min(val, sez_f))

                # ----- PE -----
                if st.session_state.pe_carico:
                    if st.session_state.get("mezza_sezione_pe", False):
                        val = sezione_derivata(
                            sez_f,
                            sez_f_opts,
                            st.session_state.materiale_cavo
                        )
                        st.session_state.sezione_pe = clamp(val)
                    else:
                        val = st.session_state.get("sezione_pe", sez_f)
                        st.session_state.sezione_pe = clamp(min(val, sez_f))
            
            # --- Gestione forzatura automatica ---
            if st.session_state.get("sezione_auto_pending"):

                nuova_sez = st.session_state.sezione_auto_pending

                if nuova_sez in sez_f_opts:
                    st.session_state.sezione_f = nuova_sez
                    st.success(f"Sezione calcolata: **{nuova_sez} mm²**")

                    if st.session_state.get("forza_sezioni_derivate"):
                        aggiorna_sezioni_derivate()

                # pulizia flag
                del st.session_state["sezione_auto_pending"]
                st.session_state.forza_sezioni_derivate = False

            sync_selectbox(
                "Sez. F",
                "sezione_f",
                sez_f_opts,
                on_change=aggiorna_sezioni_derivate
            )

            # debug contatore
            #st.text(f"{st.session_state.counter_select}) Sezione fase: {st.session_state.sezione_f} mm²")

            formazione = st.session_state.formazione_cavo
            is_unipolare = formazione == "Unipolare 1x"        

            if not is_unipolare:

                # Niente checkbox
                if st.session_state.n_carico:
                    sync_selectbox(
                        "Sez. N",
                        "sezione_n",
                        sez_f_opts,
                        disabled=True
                    )
                if st.session_state.pe_carico:
                    sync_selectbox(
                        "Sez. Pe",
                        "sezione_pe",
                        sez_f_opts,
                        disabled=True
                    )
            else:
                if st.session_state.n_carico:
                    st.checkbox(
                        "Mezza sezione neutro",
                        key="mezza_sezione_n",
                        on_change=aggiorna_sezioni_derivate
                    )
                    sync_selectbox(
                        "Sez. N",
                        "sezione_n",
                        sez_f_opts,
                        on_change=aggiorna_sezioni_derivate
                    )
                if st.session_state.pe_carico:
                    st.checkbox(
                        "Mezza sezione PE",
                        key="mezza_sezione_pe",
                        on_change=aggiorna_sezioni_derivate
                    )                    
                    sync_selectbox(
                        "Sez. Pe",
                        "sezione_pe",
                        sez_f_opts,
                        on_change=aggiorna_sezioni_derivate
                    )

            # Numero paralleli
            st.number_input("N° Paralleli", min_value=1, max_value=10, key="n_paralleli_f")
            k_paralleli = st.session_state.n_paralleli_f ** 0.8
            # debug coefficiente paralleli
            #st.text(f"K paralleli: {k_paralleli:.3f}")
                    

# --- POSA E COEFFICIENTI ---
with st.container(border=True):
    st.markdown(":blue[Posa]")
    is_unipolare = 1 if st.session_state.formazione_cavo == "Unipolare 1x" else 0
    posa_opts = cerca_posa(is_unipolare)
    if not posa_opts:
        st.error("Nessuna opzione di posa disponibile")
        st.stop()
    if st.session_state.posa_cei not in posa_opts:
        st.session_state.posa_cei = posa_opts[0]
    idx_posa = posa_opts.index(st.session_state.posa_cei)
    st.selectbox("Posa (CEI)", posa_opts, index=idx_posa, key="posa_cei",help=st.session_state.get("posa_cei"))

    sigla_posa = st.session_state.posa_cei.split()[0]
    k_posa = cerca_kposa(sigla_posa)

    col_s, col_c = st.columns(2)
    with col_s:
        st.number_input("N° Strati", min_value=1, max_value=3, value=1, key="n_strati")
    with col_c:
        with sqlite3.connect(db_path) as conn:
            max_circ = conn.execute(
                "SELECT MAX(NCIRCUITI) FROM KCIRCUITO WHERE NSTRATI = ?",
                (st.session_state.n_strati,)
            ).fetchone()[0] or 15
        st.number_input("N° Circuiti", min_value=1, max_value=max_circ, value=1, key="n_circuiti")

    k_circuiti = cerca_kcircuiti(st.session_state.n_strati, st.session_state.n_circuiti)
    t_amb = st.slider("Temperatura Ambiente (°C)", 10, 60, 30, 5, key="temperatura_ambiente")
    k_ambiente = cerca_ktambiente(st.session_state.isolamento_cavo, t_amb)

    if k_ambiente is None:
        st.error(
            f"Coefficiente kt non disponibile per "
            f"{st.session_state.isolamento_cavo} a {t_amb}°C"
        )
        st.stop()
    
    k_totale = k_posa * k_circuiti * k_ambiente * k_paralleli

    # Corrente di portata nominale e corretta
    iz_nom = cerca_iz_nominale(
        st.session_state.isolamento_cavo,
        st.session_state.formazione_cavo,
        st.session_state.sezione_f
    )
    iz_corretta = iz_nom * k_totale

    # Lunghezza
    st.number_input(":red[**Lunghezza (m)**]", 1, key="lunghezza_m")

# Calcolo sezione automatica

if st.button("CALCOLA LA SEZIONE", key="calcola_la_sezione", type="primary", use_container_width=True):
    # DIDATTICA: Questa funzione dovrebbe essere implementata
    #st.warning(
    #   "Funzione 'calcola_sezione_ottimale' da implementare")
    
    sezione_calcolata = calcolo_sezione_cavo(st.session_state.materiale_cavo, st.session_state.isolamento_cavo, st.session_state.formazione_cavo,
                                            st.session_state.inom_selection, i2t_val, k_totale,    st.session_state.ib_carico,    st.session_state.cos_fi_carico,    st.session_state.v_nominale,    st.session_state.lunghezza_m,    st.session_state.n_paralleli_f,    st.session_state.cdt_in_ingresso,   st.session_state.cdt_max, st.session_state.n_fasi_carico)
    
        
    if sezione_calcolata:
        st.session_state.sezione_auto_pending = sezione_calcolata
        st.session_state.forza_sezioni_derivate = True
        st.rerun()
    else:
        st.warning("Nessuna sezione valida trovata. Verifica i parametri di input.")

    
# =============================================================================
# 9. CALCOLO K²S² e CORRENTI DI CORTO
# =============================================================================

# forzare un valore di default se ancora None (doppia sicurezza):
if st.session_state.sezione_n is None:
    st.session_state.sezione_n = st.session_state.sezione_f
if st.session_state.sezione_pe is None:
    st.session_state.sezione_pe = st.session_state.sezione_f
    
k2s2f = calcolok2s2(
    st.session_state.sezione_f,
    st.session_state.materiale_cavo,
    st.session_state.isolamento_cavo,
    st.session_state.formazione_cavo,
    st.session_state.n_paralleli_f
)
k2s2n = calcolok2s2(
    st.session_state.sezione_n,
    st.session_state.materiale_cavo,
    st.session_state.isolamento_cavo,
    st.session_state.formazione_cavo,
    st.session_state.n_paralleli_f #st.session_state.n_paralleli_n
)
k2s2pe = calcolok2s2(
    st.session_state.sezione_pe,
    st.session_state.materiale_cavo,
    st.session_state.isolamento_cavo,
    st.session_state.formazione_cavo,
    st.session_state.n_paralleli_f #st.session_state.n_paralleli_pe
)

# --- CORRENTI DI CORTO ---
if st.session_state.sezione_f is None:
    st.warning("Selezionare una sezione valida per il cavo")
    st.stop()

e_stellata = (
    st.session_state.v_nominale
    if st.session_state.n_fasi_carico == 1
    else st.session_state.v_nominale / (3 ** 0.5)
)

IccFNmax=st.session_state.icc_fn_ingresso
CosFiccFNMax=st.session_state.cos_fi_fn_ingresso
Icc3Fmax=st.session_state.icc_3f_ingresso
CosFicc3FMax=st.session_state.cos_fi_3f_ingresso
IccFGmax=st.session_state.icc_fpe_ingresso
CosFiccFGMax=st.session_state.cos_fi_fpe_ingresso
  
l_out_cc = calcoloicc(
    st.session_state.n_fasi_carico, 
    IccFNmax, 
    Icc3Fmax, 
    IccFGmax, 
    CosFiccFNMax, 
    CosFicc3FMax, 
    CosFiccFGMax,
    st.session_state.v_nominale,
    st.session_state.n_carico,
    st.session_state.pe_carico,
    st.session_state.n_paralleli_f,
    st.session_state.n_paralleli_n,
    st.session_state.n_paralleli_pe,
    st.session_state.lunghezza_m,
    st.session_state.isolamento_cavo,
    st.session_state.formazione_cavo,
    st.session_state.sezione_f,
    st.session_state.sezione_n,
    st.session_state.sezione_pe
)

if l_out_cc is not None:
    Icc3Fout, Icc3Fmin, CosFicc3Fmin, IccFNmin, CosFiccFNmin, IccFGmin, CosFiccFGmin, ResF, ReaF, ResN, ReaN = l_out_cc
else:
    # Gestisci il caso in cui l_out_cc è None
    # Assegna valori di default o gestisci l'errore
    print("Attenzione: l_out_cc è None")
    Icc3Fout = Icc3Fmin = CosFicc3Fmin = IccFNmin = CosFiccFNmin = IccFGmin = CosFiccFGmin = ResF = ReaF = ResN = ReaN = None

Idiff_min= IccFGmin*1000 if IccFGmin is not None else None


# --- CADUTA DI TENSIONE ---
cdt_uscita = calcolocdt(st.session_state.cdt_in_ingresso,
                        ResF,
                        ReaF,
                        st.session_state.cos_fi_carico,
                        st.session_state.ib_carico,
                        st.session_state.v_nominale, st.session_state.n_fasi_carico
                        )

# --- TEMPERATURA CAVO ---
temp_max = 70 if st.session_state.isolamento_cavo == "PVC" else 90

temp_cavo, supera_temp = calcolo_temperatura_cavo_preciso(
    st.session_state.temperatura_ambiente,
    temp_max,
    st.session_state.ib_carico,
    iz_corretta,
    materiale=st.session_state.materiale_cavo,
)


# =============================================================================
# 10. UI – OUTPUT (METRICHE)
# =============================================================================
# risultati calcolo sezioni e k2s2
with st.container(border=True):
    st.markdown(":blue[CALCOLO]")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(":blue[$I_z$ nominale (A)]", iz_nom)
        st.metric(":blue[$k^2s^2$F (A²s)]", f"{k2s2f:.0f}")
    with col2:
        st.metric(":blue[$K$ totale]", f"{k_totale:.3f}")
        if st.session_state.n_carico:st.metric(":blue[$k^2s^2$N (A²s)]", f"{k2s2n:.0f}")
    
        
    with col3:
        st.metric(":blue[$I_z$ corretta (A)]", f"{iz_corretta:.1f}")
        
        if st.session_state.pe_carico:st.metric(":blue[$k^2s^2$Pe (A²s)]", f"{k2s2pe:.0f}")   

    with col4:
        with st.expander("Mostra dettagli dei coefficienti K"):
            st.write(f"**K posa:** {k_posa}")
            st.write(f"**K circuiti:** {k_circuiti}")
            st.write(f"**K ambiente:** {k_ambiente}")
            st.write(f"**K paralleli:** {k_paralleli}")            
            st.markdown(
                f"**K totale =** {k_posa} × {k_circuiti} × {k_ambiente} × {k_paralleli} = "
                f"**{k_totale:.3f}**"
            )

        
centered_header("OUTPUT")
with st.container(border=True):
    col_cdt, col_temp = st.columns(2)
    with col_cdt:
        if cdt_uscita < 100:
            st.metric(":blue[Caduta di tensione in uscita (%)]", f"{cdt_uscita:.2f}%")
        else:
            st.error(f"⚠️ Caduta di tensione in uscita ({cdt_uscita:.2f}%) > 100%")
    with col_temp:
        if supera_temp:
            st.error(f"⚠️ Temperatura esterna cavo ({temp_cavo:.0f}°C) > temperatura massima ammissibile ({temp_max}°C)")
        else:
            st.metric(":blue[Temperatura esterna cavo (°C)]", f"{temp_cavo:.0f} < {temp_max}°C", help="temperatura stimata a scopo informativo sulla base della corrente di carico, sezione e condizioni di posa (non è una stima precisa, consultare i dati del costruttore per informazioni dettagliate).")

    st.markdown(
        "<h3 style='text-align: center; color: green;'>Condizioni di guasto (min ⚠️)</h3>",
        unsafe_allow_html=True, help="Consultare le curve di intervento $$I^2t-Icc$$ del dispositivo fornite dal costruttore per verificare la protezione contro i cortocircuiti, considerando le condizioni di guasto minime indicate.\n⚠️ in presenza di parallelli il minimo non sta a fine linea!"

    )
    col_cc1, col_cc2 = st.columns(2)
    with col_cc1:
        if st.session_state.n_fasi_carico > 1 and Icc3Fmin is not None:
            st.metric(":blue[$I_{cc}$ trifase / Fase-Fase (kA)]", f"{float(Icc3Fmin):.3f}")
        if st.session_state.n_carico and IccFNmin is not None:
            st.metric(":blue[$I_{cc}$ Fase-Neutro (kA)]", f"{float(IccFNmin):.3f}")
        if st.session_state.pe_carico and IccFGmin is not None:
            st.metric(":blue[$I_{cc}$ Fase-Prot.esterna (kA)]", f"{float(IccFGmin):.3f}")
    with col_cc2:
        if st.session_state.n_fasi_carico > 1 and CosFicc3Fmin is not None:
            st.metric(":blue[$Cosφ$ trifase / Fase-Fase]", f"{float(CosFicc3Fmin):.3f}")
        if st.session_state.n_carico and CosFiccFNmin is not None:
            st.metric(":blue[$Cosφ$ Fase-Neutro]", f"{float(CosFiccFNmin):.3f}")
        if st.session_state.pe_carico and CosFiccFGmin is not None:
            st.metric(":blue[$Cosφ$ Fase-Prot.esterna]", f"{float(CosFiccFGmin):.3f}")
    if "classe_opts" in st.session_state and st.session_state.pe_carico:
        st.markdown(
                "<h3 style='text-align: left; color: green;'>Protezione dai contatti indiretti (TN)</h3>",
                unsafe_allow_html=True
            )
        col_idiff1, col_idiff2 = st.columns(2)
        with col_idiff1:
            if Idiff_min is not None:
                st.metric(":blue[Idiff min (A)]", f"{float(Idiff_min):.3f} A")
        with col_idiff2:
            st.metric(":blue[Idiff differenziale scelto]", f"{st.session_state.idiff_selection} A")
        
# =============================================================================
# 11. UI – VERIFICHE
# =============================================================================
centered_header("VERIFICHE")
with st.container(border=True):

    # Ib ≤ In
    if st.session_state.ib_carico <= st.session_state.inom_selection:
        st.success(f"🙂 $I_b$ carico (${st.session_state.ib_carico:.1f}A$) $\\leq I_n$ dispositivo(${st.session_state.inom_selection:.1f}A$)", icon="✅")
    else:
        st.error(f"😟 $I_b$ carico (${st.session_state.ib_carico:.1f}A$) $\\gt I_n$ dispositivo(${st.session_state.inom_selection:.1f}A$)", icon="❌")

    # In ≤ Iz
    if st.session_state.inom_selection <= iz_corretta:
        st.success(f"🙂 $I_n$ dispositivo (${st.session_state.inom_selection:.1f}A$) $\\leq I_z$ (${iz_corretta:.1f}A$)", icon="✅")
    else:
        st.error(f"😟 $I_n$ dispositivo (${st.session_state.inom_selection:.1f}A$) > $I_z$ (${iz_corretta:.1f}A$)", icon="❌")

    if st.session_state.dispositivo_selection in ["MTD", "MT_"]:
        # Potere di interruzione
        if st.session_state.get('potint_selection') is not None:
            icc_max = max(Icc3Fmax, IccFNmax, IccFGmax)
            if st.session_state.potint_selection > icc_max:
                st.success(f"🙂 $P_i$ dispositivo (${st.session_state.potint_selection:.1f}kA$) > $I_{{cc}}$ conduttore (${icc_max:.1f}kA$)", icon="✅")
            else:
                st.error(f"😟 $P_i$ dispositivo (${st.session_state.potint_selection:.1f}kA$) $\\leq I_{{cc}}$ conduttore (${icc_max:.1f}kA$)", icon="❌")

        # I²t ≤ K²S²
        if st.session_state.curva_selection:
            i2t_disp = calcolo_i2t(st.session_state.curva_selection, st.session_state.inom_selection)
            k2s2_max = max(k2s2f, k2s2n, k2s2pe)
            if i2t_disp <= k2s2_max:
                st.success(f"🙂 $I_{{cc}}^2 \\cdot t_c$ dispositivo (${i2t_disp:.0f}A²s$) $\\leq K^2 \\cdot S^2$ conduttore(${k2s2_max:.0f}A²s$)", icon="✅")
            else:
                st.error(f"😟 $I_{{cc}}^2 \\cdot t_c$ dispositivo (${i2t_disp:.0f}A²s$) > $K^2 \\cdot S^2$ conduttore (${k2s2_max:.0f}A²s$)", icon="❌")

    # Caduta di tensione
    if cdt_uscita <= st.session_state.cdt_max:
        st.success(f"🙂 $cdt_{{\\mathrm{{out}}}}$ (${cdt_uscita:.2f}\\%$) $\\le cdt_{{\\mathrm{{max}}}}$ (${st.session_state.cdt_max:.2f}\\%$)", icon="✅")
    else:
        st.error(f"😟 $cdt_{{\\mathrm{{out}}}}$ (${cdt_uscita:.2f}\\%$) > $cdt_{{\\mathrm{{max}}}}$ (${st.session_state.cdt_max:.2f}\\%$)", icon="❌")
        
    # Verifica protezione differenziale (se presente)
    if st.session_state.dispositivo_selection in ["MTD", "DIF"]:  
        if st.session_state.pe_carico and st.session_state.get("idiff_selection") is not None and Idiff_min is not None:
            if isinstance(st.session_state.idiff_selection, (int, float)):
                valore_idiff = float(st.session_state.idiff_selection) if st.session_state.idiff_selection is not None else 0
                try:
                    valore_idiff_float = float(valore_idiff)
                    idiff_min_float = float(Idiff_min)
                    if valore_idiff_float <= idiff_min_float:
                        st.success(f"🙂 $I_{{diff}}$ differenziale (${st.session_state.idiff_selection}A$) $\\leq I_{{diff}}$ minimo (${Idiff_min:.3f}A$)", icon="✅")
                    else:
                        st.error(f"😟 $I_{{diff}}$ differenziale (${st.session_state.idiff_selection}A$) > $I_{{diff}}$ minimo (${Idiff_min:.3f}A$)", icon="❌")
                except (TypeError, ValueError):
                    st.error("Errore nel confronto Idiff: valori non numerici")

# =============================================================================
# 12. UI – FORMULE E DOCUMENTAZIONE
# =============================================================================
centered_header("FORMULE E DOCUMENTAZIONE")
with st.container(border=True):
    st.markdown(":blue[Algoritmi di calcolo utilizzati]")
    st.latex(r"I_{b} \leq I_{n} \leq I_{z}")
    st.latex(r"P_i > I_{cc}")
    st.latex(r"I_{\mathrm{cc}}^2 \cdot t_c \le k^2 \cdot S^2")
    st.latex(r"cdt\%_{\mathrm{out}} \le cdt\%_{\mathrm{max}}")
    st.latex(r"I_{a} \leq   \frac{U_0}{Z_{s}} = I_{cc\,\mathrm{F-Pe }\, min}")

    pdf_path = "verifica.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    st.download_button("DOCUMENTAZIONE...", pdf_bytes, pdf_path, "application/pdf")
