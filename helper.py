'''
=============================================================================
Q2026 - DEMO DIMENSIONAMENTO DI UNA LINEA ELETTRICA
FUNZIONI HELPER PER GESTIONE SICURA DELLO STATO
Ultimo aggiornamento: 22/02/2026
AUTORE: Ivano Dorigatti
LICENZA: MIT License
=============================================================================
'''

import streamlit as st

# ========================================================
# FUNZIONI HELPER PER GESTIONE SICURA DELLO STATO
# ========================================================
# Queste funzioni centralizzano la logica di gestione
# dello stato per prevenire errori comuni in Streamlit.
# ========================================================

def selectbox_safe(label, options, state_key):
    """
    Versione robusta di st.selectbox che gestisce automaticamente lo stato.
    
    Parametri:
    - label: Testo da visualizzare sopra il selectbox
    - options: Lista di opzioni disponibili
    - state_key: Chiave dello stato Streamlit dove salvare il valore
    
    Ritorna:
    - Valore selezionato dall'utente
    """
    # Ottieni il valore corrente dallo stato
    current = st.session_state.get(state_key)
    
    # DIDATTICA: Il pattern "if current in options" previene errori
    # quando il valore corrente non è più nelle opzioni disponibili
    index = options.index(current) if current in options else None

    # Crea il widget con gestione automatica dello stato
    value = st.selectbox(label, options, index=index)
    
    # Salva immediatamente il valore nello stato per persistenza
    st.session_state[state_key] = value
    
    return value

def invalidate(*keys):
    """
    Resetta a None le chiavi specificate dello stato.
    Utile quando una selezione rende altre selezioni obsolete.
    """
    for k in keys:
        st.session_state[k] = None

def init_state():
    """
    Inizializza TUTTI gli stati necessari per l'applicazione.
    Da chiamare all'inizio dell'app o quando si resetta il contesto.
    """
    defaults = {
        "materiale": None,
        "isolamento": None,
        "tipo_cavo": None,
        "formazione": None,
        "sezione_f": None,
        "sezione_n": None,
        "sezione_pe": None,
        "k_paralleli": 1,
        "iz_nominale": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def on_change_formazione():
    """
    Callback chiamato quando l'utente cambia la formazione del cavo.
    Invalida le sezioni N e PE perché potrebbero non essere più valide.
    """
    invalidate("sezione_n", "sezione_pe")

def gestione_neutro_pe(formazione, sezione_f, sezione_f_options):
    """
    Gestisce le sezioni di neutro e PE in base al contesto.
    
    Regole di business:
    - Per cavi unipolari: l'utente può scegliere sezioni indipendenti
    - Per cavi multipolari: le sezioni sono predeterminate
    - Se cambia la sezione fase, si propone un reset delle sezioni correlate
    """
    # Se non è un cavo unipolare, invalida le sezioni N e PE
    if formazione != "Unipolare 1x" or sezione_f is None:
        invalidate("sezione_n", "sezione_pe")
        return None, None

    # DIDATTICA: Le sezioni ammesse per N e PE dipendono dalla sezione F
    # e dalle normative (qui esempio semplificato)
    def sezioni_ammesse(sezione_f):
        """Restituisce le sezioni disponibili per N e PE in base alla sezione F"""
        # Regola semplificata: N e PE possono essere >= 50% della sezione F
        min_sezione = max(1.5, sezione_f / 2)
        return [s for s in sezione_f_options if float(s) >= min_sezione]

    sezioni = sezioni_ammesse(sezione_f)

    # Widget per sezione neutro
    sezione_n = selectbox_safe(
        "Sezione Neutro (mm²)",
        sezioni,
        "sezione_n"
    )

    # Widget per sezione protezione
    sezione_pe = selectbox_safe(
        "Sezione Protezione (mm²)",
        sezioni,
        "sezione_pe"
    )
    
    return sezione_n, sezione_pe

def stato_pronto():
    """
    Verifica se tutti i dati obbligatori sono stati inseriti.
    Restituisce True se l'app è pronta per i calcoli.
    """
    required = [
        "materiale_cavo",
        "isolamento_cavo",
        "tipo_cavo",
        "formazione_cavo",
        "sezione_f",
    ]
    
    # Controlla che nessun campo obbligatorio sia None
    return all(st.session_state.get(k) is not None for k in required)
   
def sync_selectbox(
    label,
    key,
    options,
    help_text=None,
    on_change=None,
    disabled=False
):
    """
    Selectbox sincronizzata con session_state.

    - Mantiene il valore coerente con le opzioni disponibili
    - Se il valore corrente non è valido → clamp al primo valore
    - Supporta disabled
    - Non genera stati inconsistenti
    """

    # ---- Nessuna opzione disponibile ----
    if not options:
        if help_text:
            st.warning(help_text)
        st.session_state[key] = None
        return None

    current = st.session_state.get(key)

    # ---- Clamp sicuro ----
    if current not in options:
        current = options[0]
        st.session_state[key] = current

    index = options.index(current)

    return st.selectbox(
        label=label,
        options=options,
        index=index,
        key=key,
        on_change=on_change,
        disabled=disabled
    )
    