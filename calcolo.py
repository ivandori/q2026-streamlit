'''
=============================================================================
Q2026 - DEMO DIMENSIONAMENTO DI UNA LINEA ELETTRICA
CALCOLI E FUNZIONI DI SUPPORTO
Ultimo aggiornamento: 22/02/2026
AUTORE: Ivano Dorigatti
LICENZA: MIT License
=============================================================================
'''

import sqlite3
import math
import streamlit as st

def calcolo_temperatura_cavo(temp_ambiente, temp_massima, Ib, Iz):
    """
    Calcola la temperatura effettiva di funzionamento di un cavo elettrico.

    Parametri:
    - temp_ambiente (float): temperatura ambiente in °C
    - temp_massima (float): temperatura massima ammissibile del cavo in °C
    - Ib (float): corrente assorbita dal carico in A
    - Iz (float): corrente nominale ammessa dal cavo in A

    Ritorna:
    - temperatura di funzionamento in °C
    """
    if Iz == 0:
        raise ValueError("Iz non può essere zero.")
    incremento_temp = (temp_massima - temp_ambiente) * (Ib / Iz) ** 2
    temperatura_cavo = incremento_temp + temp_ambiente
    supera_limite = temperatura_cavo > temp_massima

    return temperatura_cavo, supera_limite


def calcolo_temperatura_cavo_preciso(
    temp_ambiente,
    temp_massima,
    Ib,
    Iz,
    materiale="Rame",
    toll=0.01,
    max_iter=50
):
    """
    Calcolo temperatura cavo con resistività variabile
    e soluzione iterativa dell'equazione termica.

    Ritorna:
    - temperatura_cavo
    - supera_limite (bool)
    """

    if Iz <= 0:
        raise ValueError("Iz deve essere > 0")

    # coefficiente temperatura resistività
    if materiale.lower() == "rame":
        alpha = 0.00393
    else:
        alpha = 0.00403  # alluminio

    # denominatore costante
    denom = Iz**2 * (1 + alpha * (temp_massima - 20))

    # stima iniziale (modello semplificato)
    T = temp_ambiente + (temp_massima - temp_ambiente) * (Ib / Iz) ** 2

    for _ in range(max_iter):
        numer = Ib**2 * (1 + alpha * (T - 20))
        T_new = temp_ambiente + \
            (temp_massima - temp_ambiente) * (numer / denom)

        if abs(T_new - T) < toll:
            break

        T = T_new

    supera_limite = T > temp_massima

    return T, supera_limite


def lista_iz_nominali(isolamento, formazione):
    '''
    Recupera la lista di Iz nominali per un dato isolamento e formazione.
    Ritorna un dizionario {sezione: iz_nominale}
    '''
    db_path = r'cavi_q2025.sqlite'

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Selezione colonna corretta in base alla formazione
        if formazione == "Unipolare 1x":
            colonna = "IZUNIPOLARE30"
        elif formazione == "Multipolare 2x":
            colonna = "IZBIPOLARE30"
        else:
            colonna = "IZTRIPOLARE30"

        query = f"""
            SELECT SEZ, {colonna}
            FROM "{isolamento}"
            ORDER BY SEZ ASC
        """

        cursor.execute(query)
        risultati = cursor.fetchall()

        if not risultati:
            raise ValueError(
                f"Nessun dato IZ trovato per {isolamento} - {formazione}"
            )

        # ritorna lista di tuple (sezione, iz)
        return {row[0]: row[1] for row in risultati}


def calcolo_sezione_cavo(
    materiale_cavo,
    isolamento_cavo,
    formazione_cavo,
    i_nominale_dispositivo,
    i2t_dispositivo,
    k_totale,
    ib,
    cosfi,
    v_nominale,
    lunghezza_m,
    n_paralleli,
    cdt_ingresso,
    cdt_max,
    nfasi_carico
):
    """
    Seleziona automaticamente la sezione minima che soddisfa:

    1) Ib ≤ Iz corretta
    2) I²t dispositivo ≤ k²S²
    3) ΔV% totale ≤ cdt_max
    """

    # Recupero tutte le Iz nominali
    iz_dict = dict(lista_iz_nominali(isolamento_cavo, formazione_cavo))

    # Ordine crescente per garantire la minima conforme
    for sezione in sorted(iz_dict.keys()):

        iz_nominale = iz_dict[sezione]
        iz_corretta = iz_nominale * k_totale

        # -----------------------------------------
        # 1) VERIFICA TERMICA
        # -----------------------------------------
        # Ib ≤ In
        if ib > i_nominale_dispositivo:
            continue

        # In ≤ Iz
        if i_nominale_dispositivo > iz_corretta:
            continue

        # -----------------------------------------
        # 2) VERIFICA ENERGIA PASSANTE
        # -----------------------------------------
        k2s2 = calcolok2s2(
            sezione,
            materiale_cavo,
            isolamento_cavo,
            formazione_cavo,
            n_paralleli
        )

        if k2s2 < i2t_dispositivo:
            continue

        # -----------------------------------------
        # 3) VERIFICA CADUTA DI TENSIONE
        # -----------------------------------------
        # Recupero R e X
        resistenza, reattanza = cerca_impedenza(
            isolamento_cavo,
            formazione_cavo,
            sezione
        )

        r = resistenza * (lunghezza_m / 1000) / n_paralleli
        x = reattanza * (lunghezza_m / 1000) / n_paralleli

        cdt_tot = calcolocdt(
            cdt_ingresso,
            r,
            x,
            cosfi,
            ib,
            v_nominale,
            nfasi_carico
        )

        if cdt_tot > cdt_max:
            continue

        # Se tutte le verifiche sono superate
        return sezione

    # Nessuna sezione valida trovata
    return None


def calcolo_i2t(curva, i_nominale, t_intervento=0.1):
    '''
    Calcola l'i2t di intervento per un dispositivo di protezione in base alla curva di intervento e alla corrente nominale.
    Parametri:
    - curva: stringa che rappresenta la curva di intervento (es. "B", "C", "D", "Z", "K", "MA")
    - i_nominale: corrente nominale del dispositivo in A
    - t_intervento: tempo di intervento in secondi (default 0.1s)
     Ritorna:
     - i2t: energia passante in A²s
     '''

    if curva == "B":
        i_intervento = 4 * i_nominale
    elif curva == "C":
        i_intervento = 7 * i_nominale
    elif curva == "D":
        i_intervento = 10 * i_nominale
    elif curva == "Z":
        i_intervento = 3 * i_nominale
    elif curva == "K":
        i_intervento = 12 * i_nominale
    elif curva == "MA":
        i_intervento = 13 * i_nominale
    else:
        i_intervento = 15 * i_nominale
        # 15 è un valore di sicurezza che copre curve più lente come "MA" o "K" e fornisce un margine per eventuali errori di stima.
    i_intervento_squared = i_intervento**2
    i2t = t_intervento * i_intervento_squared
    # Il calcolo dell'i2t è fondamentale per valutare se un cavo può sopportare l'energia passante durante un guasto senza subire danni permanenti.
    # L'i2t rappresenta l'energia che un dispositivo di protezione lascia passare durante un guasto. Viene calcolato come il prodotto del tempo di intervento (t_intervento) e il quadrato della corrente di intervento (i_intervento).
    return i2t


def valida_topologia(Fasi, Neutro, Ground):
    '''
    Valida la coerenza della topologia elettrica in base al numero di fasi e alla presenza di neutro e terra.
     Regole:
     - Fasi deve essere 1, 2 o 3
     - Se Fasi=1, Neutro deve essere presente
     - Almeno uno tra Neutro e Ground deve essere presente
    '''
    errori = []

    if Fasi not in (1, 2, 3):
        errori.append("Numero fasi non valido")

    if not Neutro and not Ground:
        errori.append("Nessun conduttore di ritorno disponibile")

    if Fasi == 1 and not Neutro:
        errori.append("Sistema monofase senza neutro non coerente")

    return errori


def calcoloicc(Fasi, IccFN, Icc3F, IccFG, CosFiccFN, CosFicc3F, cosFiccFG, V_nominale, Neutro, Ground, Fparalleli, Nparalleli, Gparalleli, lunghezza_m, isolamento, formazione, sezione_f, sezione_n, sezione_pe):
    '''
    Calcolo cortocircuito conforme CEI 64-8.
    '''
    errori = valida_topologia(Fasi, Neutro, Ground)
    if errori:
        return {"errore": errori}
    Icc3F_monte = Icc3F * 1000  # Converti da kA a A
    cosphi3F = CosFicc3F
    Z_km = cerca_impedenza(isolamento, formazione, sezione_f)
    R_fase_km = Z_km[0]
    X_fase_km = Z_km[1]
    if Neutro:
        IccFN_monte = IccFN * 1000  # Converti da kA a A
        cosphiFN = CosFiccFN
        Z_km = cerca_impedenza(isolamento, formazione, sezione_n)
        R_neutro_km = Z_km[0]
        X_neutro_km = Z_km[1]
    else:
        IccFN_monte = None
        cosphiFN = None
        R_neutro_km = None
        X_neutro_km = None
    if Ground:
        IccFG_monte = IccFG * 1000  # Converti da kA a A
        cosphiFG = cosFiccFG
        Z_km = cerca_impedenza(isolamento, formazione, sezione_pe)
        R_pe_km = Z_km[0]
        X_pe_km = Z_km[1]
    else:
        IccFG_monte = None
        cosphiFG = None
        R_pe_km = None
        X_pe_km = None

    Fparalleli = max(1, int(Fparalleli))
    Nparalleli = max(1, int(Nparalleli))
    Gparalleli = max(1, int(Gparalleli))

    return calcoloicc_industriale(
        V_nominale,
        Icc3F_monte,
        cosphi3F,
        IccFN_monte,
        cosphiFN,
        IccFG_monte,
        cosphiFG,
        lunghezza_m,
        R_fase_km, X_fase_km,
        R_neutro_km, X_neutro_km,
        R_pe_km, X_pe_km,
        Fparalleli,
        Nparalleli,
        Gparalleli
    )


def calcoloicc_industriale(
    V_nominale,              # V concatenata (es. 400)
    Icc3F_monte,             # A
    cosphi3F,
    IccFN_monte,             # A (può essere None)
    cosphiFN,
    IccFG_monte,             # A (può essere None)
    cosphiFG,
    lunghezza_m,
    R_fase_km, X_fase_km,
    R_neutro_km, X_neutro_km,
    R_pe_km, X_pe_km,
    n_paralleli_fase=1,
    n_paralleli_neutro=1,
    n_paralleli_pe=1,
    fattore_tensione_min=0.95
):
    """
    Calcolo cortocircuito conforme CEI 64-8.

    Restituisce:
    - Icc3F_valle_max (cortocircuito trifase a valle)    
    - Icc3F_min (cortocircuito trifase a valle con fattore di tensione minimo)
    - cosphi3F_out (fattore di potenza a valle del cortocircuito trifase)
    - IccFN_min (cortocircuito fase-neutro a valle con fattore di tensione minimo, se IccFN_monte fornito)
    - cosphiFN_out (fattore di potenza a valle del cortocircuito fase-neutro, se IccFN_monte fornito)
    - IccFG_min (cortocircuito fase-terra a valle con fattore di tensione minimo, se IccFG_monte fornito)
    - cosphiFG_out (cortocircuito fase-terra a valle con fattore di tensione minimo, se IccFG_monte fornito)
    - Zs_loop (impedenza anello di guasto FG)
    - Rf, Xf (resistenza e reattanza fase)
    - Rn, Xn (resistenza e reattanza neutro, se presente)
    """

    # ----------------------------------------------------------
    # PROTEZIONI INPUT
    # ----------------------------------------------------------
    if Icc3F_monte is None or Icc3F_monte <= 0:
        return None

    V_fase = V_nominale / math.sqrt(3)

    cosphi3F = max(-1.0, min(1.0, cosphi3F))
    cosphiFN = max(-1.0, min(1.0, cosphiFN))
    cosphiFG = max(-1.0, min(1.0, cosphiFG))

    sinphi3F = math.sqrt(1 - cosphi3F**2)
    sinphiFN = math.sqrt(1 - cosphiFN**2)
    sinphiFG = math.sqrt(1 - cosphiFG**2)

    n_paralleli_fase = max(1, n_paralleli_fase)
    n_paralleli_neutro = max(1, n_paralleli_neutro)
    n_paralleli_pe = max(1, n_paralleli_pe)

    L_km = lunghezza_m / 1000.0

    # ----------------------------------------------------------
    # IMPEDENZA SORGENTE TRIFASE
    # ----------------------------------------------------------
    Zs_3F = V_nominale / (math.sqrt(3) * Icc3F_monte)
    Rs_3F = Zs_3F * cosphi3F
    Xs_3F = Zs_3F * sinphi3F

    # ----------------------------------------------------------
    # IMPEDENZA LINEA
    # ----------------------------------------------------------
    Rf = (R_fase_km * L_km) / n_paralleli_fase
    Xf = (X_fase_km * L_km) / n_paralleli_fase

    Rn = (R_neutro_km * L_km) / n_paralleli_neutro
    Xn = (X_neutro_km * L_km) / n_paralleli_neutro

    Rpe = (R_pe_km * L_km) / n_paralleli_pe
    Xpe = (X_pe_km * L_km) / n_paralleli_pe

    # ==========================================================
    # TRIFASE
    # ==========================================================
    R_tot_3F = Rs_3F + Rf
    X_tot_3F = Xs_3F + Xf
    Z_tot_3F = math.sqrt(R_tot_3F**2 + X_tot_3F**2)

    cosphi3F_out = R_tot_3F / Z_tot_3F if Z_tot_3F > 0 else 0
    Icc3F_valle_max = V_nominale / \
        (math.sqrt(3) * Z_tot_3F * 1000)  # Converti a kA
    Icc3F_min = (fattore_tensione_min * V_nominale) / \
        (math.sqrt(3) * Z_tot_3F * 1000)  # Converti a kA

    # ==========================================================
    # FASE-NEUTRO
    # ==========================================================
    IccFN_min = None

    if IccFN_monte is not None and IccFN_monte > 0:

        Zs_FN = V_fase / IccFN_monte
        Rs_FN = Zs_FN * cosphiFN
        Xs_FN = Zs_FN * sinphiFN

        R_tot_FN = Rs_FN + Rf + Rn
        X_tot_FN = Xs_FN + Xf + Xn
        Z_tot_FN = math.sqrt(R_tot_FN**2 + X_tot_FN**2)

        cosphiFN_out = R_tot_FN / Z_tot_FN if Z_tot_FN > 0 else 0
        IccFN_min = (fattore_tensione_min * V_fase) / \
            (Z_tot_FN * 1000)  # Converti a kA

    # ==========================================================
    # FASE-TERRA
    # ==========================================================
    IccFG_min = None
    Zs_loop = None

    if IccFG_monte is not None and IccFG_monte > 0:

        Zs_FG = V_fase / IccFG_monte
        Rs_FG = Zs_FG * cosphiFG
        Xs_FG = Zs_FG * sinphiFG

        R_tot_FG = Rs_FG + Rf + Rpe
        X_tot_FG = Xs_FG + Xf + Xpe

    else:
        # fallback TN simmetrico (se IccFG non fornita)
        R_tot_FG = Rs_3F + Rf + Rpe
        X_tot_FG = Xs_3F + Xf + Xpe

    Zs_loop = math.sqrt(R_tot_FG**2 + X_tot_FG**2)
    cosphiFG_out = R_tot_FG / Zs_loop if Zs_loop > 0 else 0
    IccFG_min = (fattore_tensione_min * V_fase) / \
        (Zs_loop * 1000)  # Converti a kA

    return Icc3F_valle_max, Icc3F_min, cosphi3F_out, IccFN_min, cosphiFN_out, IccFG_min, cosphiFG_out, Rf, Xf, Rn, Xn


def cerca_impedenza(isolamento, formazione, sez):
    '''Restituisce una tupla (resistenza, reattanza) in Ω/km per il dato isolamento, formazione e sezione.
    Se non trovato, restituisce (0, 0) e mostra un warning.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        if formazione == "Unipolare 1x":
            query = f"SELECT RCCTMAX, XUNIPOLARE FROM {isolamento} WHERE SEZ = ?"
        else:
            query = f"SELECT RCCTMAX, XMULTIPOLARE FROM {isolamento} WHERE SEZ = ?"

        cursor.execute(query, (sez,))
        risultato = cursor.fetchone()
        if risultato is None:
            if sez > 0:
                st.warning(
                    f"Attenzione: {isolamento} e {formazione} e {sez} non è presente nel database. Impostazione valori predefiniti.")
                print(
                    f"Attenzione: {isolamento} e {formazione} e {sez} non è presente nel database. Impostazione valori predefiniti.")

            return (0, 0)  # Default values for RCCTMAX and reactance
        # Restituisce una tupla (RCCTMAX, XUNIPOLARE o XMULTIPOLARE)
        return risultato


def calcolocdt(cdtingresso,         # caduta percentuale a monte
               r,                   # resistenza linea (Ω)
               x,                   # reattanza linea (Ω)
               cosfi,               # fattore di potenza
               ib,                  # corrente di impiego (A)
               tensione_nominale,   # V concatenata (es. 400)
               n_fasi):             # numero di fasi (1, 2 o 3)
    """
    Calcolo caduta di tensione conforme CEI 64-8.

    Parametri:
    - cdtingresso : caduta percentuale a monte
    - r : resistenza totale della linea in Ω
    - x : reattanza totale della linea in Ω
    - cosfi : fattore di potenza del carico
    - ib : corrente di impiego in A
    - tensione_nominale : tensione nominale del sistema in V (concatenata)
    - n_fasi : numero di fasi del sistema (1, 2 o 3)

    Ritorna:
    - Caduta totale percentuale
    """

    if tensione_nominale <= 0:
        return cdtingresso

    # Clamp cosφ
    cosfi = max(0.0, min(1.0, cosfi))
    senfi = math.sqrt(1 - cosfi**2)

    # ---- Calcolo ΔV ----
    if n_fasi == 3:
        # Trifase
        delta_v = math.sqrt(3) * ib * (r * cosfi + x * senfi)
    else:
        # Monofase (1F o 2F)
        delta_v = 2 * ib * (r * cosfi + x * senfi)

    # ---- Percentuale rispetto a V concatenata ----
    cdt_percent = (delta_v / tensione_nominale) * 100

    return cdtingresso + cdt_percent


def calcolok2s2(sez, materiale, isolamento, formazione, np=1):
    """
    Verifica energia passante secondo CEI 64-8:
    I²t ≤ n · k² · S²
    dove:
    - I²t è l'energia passante del dispositivo di protezione (calcolata in base alla curva e alla corrente nominale)
    - n è il numero di conduttori in parallelo
    - k è un coefficiente che dipende da materiale, isolamento e formazione del cavo (cercato nel database)
    - S è la sezione del cavo in mm²
    """
    if np < 1:
        np = 1

    k = cerca_k(materiale, isolamento, formazione)

    return np * (k**2) * (sez**2)


def cerca_iz_nominale(isolamento, formazione, sez):
    '''Restituisce il valore di Iz nominale per un dato isolamento, formazione e sezione.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        if formazione == "Unipolare 1x":
            query = f"SELECT IZUNIPOLARE30 FROM {isolamento} WHERE SEZ = ?"
        elif formazione == "Multipolare 2x":
            query = f"SELECT IZBIPOLARE30 FROM {isolamento} WHERE SEZ = ?"
        else:
            query = f"SELECT IZTRIPOLARE30 FROM {isolamento} WHERE SEZ = ?"

        cursor.execute(query, (sez,))
        risultato = cursor.fetchone()
        if risultato is None:
            raise ValueError(
                f"{isolamento} e {formazione} e {sez} non è presente nel database")
        return risultato[0]


def cerca_k(materiale, isolamento, formazione):
    '''Restituisce il coefficiente k per un dato materiale, isolamento e formazione.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        if formazione == "Unipolare 1x":
            query = f"SELECT KUNIPOLARE FROM '648' WHERE MATERIALE = ? AND ISOLANTE = ?"
        else:
            query = f"SELECT KMULTIPOLARE FROM '648' WHERE MATERIALE = ? AND ISOLANTE = ?"

        cursor.execute(query, (materiale.upper(), isolamento.upper()))
        risultato = cursor.fetchone()
        if risultato is None:
            raise ValueError(
                f"{formazione} e {isolamento} e {materiale} non è presente nel database")
        return risultato[0]


def cerca_sezf(tipo_cavo, formazione_cavo):
    '''Restituisce la lista di sezioni disponibili per un dato tipo di cavo e formazione.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        try:
            if formazione_cavo == "Unipolare 1x":
                query = f'SELECT SEZ FROM "{tipo_cavo}" WHERE UNIPOLARE = 1'
            elif formazione_cavo == "Multipolare 2x":
                query = f'SELECT SEZ FROM "{tipo_cavo}" WHERE MULTIPOLARE2 = 2'
            elif formazione_cavo == "Multipolare 3x":
                query = f'SELECT SEZ FROM "{tipo_cavo}" WHERE MULTIPOLARE3 = 3'
            elif formazione_cavo == "Multipolare 4x":
                query = f'SELECT SEZ FROM "{tipo_cavo}" WHERE MULTIPOLARE4 = 4'
            elif formazione_cavo == "Multipolare 5G":
                query = f'SELECT SEZ FROM "{tipo_cavo}" WHERE MULTIPOLARE5 = 5'
            else:
                raise ValueError(
                    f"Formazione cavo '{formazione_cavo}' non riconosciuta")

            # st.write(f"Eseguendo query: {query}")
            cursor.execute(query)
            risultati = cursor.fetchall()
            return [row[0] for row in risultati]

        except sqlite3.OperationalError as e:
            st.error(f"Errore nel database: {e}")
            return []


def cerca_sezng(tipo_cavo, sezione_f):
    '''Restituisce la sezione nominale equivalente (SEZNG) per un dato tipo di cavo e sezione fase.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        try:
            query = f'SELECT SEZNG FROM "{tipo_cavo}" WHERE SEZ = ?'

            cursor.execute(query, (sezione_f,))
            risultati = cursor.fetchall()
            return [row[0] for row in risultati][0]

        except sqlite3.OperationalError as e:
            st.error(f"Errore nel database: {e}")
            return None


def cerca_formazione(tipo_cavo):
    '''Restituisce la formazione del cavo per un dato tipo di cavo.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        try:
            query = "SELECT FORMAZIONE FROM CAVI WHERE SIGLA = ?"
            cursor.execute(query, (tipo_cavo,))
            risultati = cursor.fetchall()
            if not risultati:
                st.warning(
                    "Dati del cavo non disponibili, ripristino il precedente!")
                return None
        except sqlite3.Error as e:
            st.error(f"Errore nel database: {e}")
            return None
    return [cavo.strip() for cavo in risultati[0][0].split(',')]


def cerca_tipo_cavo(materiale, isolamento):
    '''Restituisce la lista dei tipi di cavo per un dato materiale e isolamento.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT SIGLA FROM CAVI WHERE MATERIALE = ? AND ISOLAMENTO = ?"
        cursor.execute(query, (materiale, isolamento,))
        risultati = cursor.fetchall()
    lista_cavi = [row[0] for row in risultati]
    return lista_cavi


def cerca_ktambiente(isolante, temperatura, strict=False):
    """
    Restituisce il coefficiente KTAMBIENTE.

    Parametri:
    - isolante: stringa (es. 'EPRA')
    - temperatura: numero (es. 30)
    - strict: se True solleva eccezione se non trovato

    Ritorna:
    - float oppure None
    """

    if isolante is None or temperatura is None:
        return None

    # Normalizzazione input
    isolante = str(isolante).strip().upper()
    temperatura = float(temperatura)

    db_path = r'cavi_q2025.sqlite'

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        query = """
        SELECT KTAMBIENTE
        FROM KTAMBIENTE
        WHERE UPPER(TRIM(ISOLANTE)) = ?
        AND TEMPERATURA = ?
        """

        cursor.execute(query, (isolante, temperatura))
        risultato = cursor.fetchone()

    if risultato is None:
        if strict:
            raise ValueError(
                f"KTAMBIENTE non trovato per {isolante} a {temperatura}°C"
            )
        return None

    return float(risultato[0])


def cerca_kcircuiti(n_strati, n_circuiti):
    '''Restituisce il coefficiente K per un dato numero di strati e circuiti.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT K FROM KCIRCUITO WHERE NSTRATI = ? AND NCIRCUITI = ?"
        cursor.execute(query, (n_strati, n_circuiti,))
        risultato = cursor.fetchone()
        if risultato is None:
            raise ValueError(f"K non trovato per {n_strati} strati e {n_circuiti} circuiti")
        return risultato[0] if risultato and risultato[0] is not None else None


def cerca_kposa(sigla):
    '''Restituisce il coefficiente K per un dato tipo di posa.  
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT K FROM KPOSA WHERE SIGLA = ?"
        cursor.execute(query, (sigla,))
        risultato = cursor.fetchone()
        if risultato is None:
            raise ValueError(f"{sigla} non è presente nel database")
        return risultato[0]


def cerca_posa(unipolari):
    '''Restituisce la lista delle posa per un dato tipo di cavo unipolare.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'cavi_q2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT NUMERO, LETTERA, DESCRIZIONE FROM POSA_CAVI WHERE UNIPOLARI = ?"
        cursor.execute(query, (unipolari,))
        risultati = cursor.fetchall()
    if not risultati:
        raise ValueError(f"Nessuna posa trovata per il tipo di cavo unipolare '{unipolari}'")
    lista_posa = [f"{row[0]}{row[1]} - {row[2]}" for row in risultati]
    return lista_posa


def cerca_dispositivi(dat_poli_valore):
    '''Restituisce la lista dei dispositivi per un dato tipo di poli.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'dispositivi_2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT DISTINCT DAT_DISP FROM POLI_DISP_IN WHERE DAT_POLI = ?"
        cursor.execute(query, (dat_poli_valore,))
        risultati = cursor.fetchall()
    if not risultati:
        raise ValueError(f"Nessun dispositivo trovato per il tipo di poli '{dat_poli_valore}'")
    lista_dat_disp = sorted(row[0] for row in risultati)
    return lista_dat_disp


def cerca_inom(dat_poli_valore, dat_disp_valore):
    '''Restituisce la lista dei valori di DAT_TARMAX per un dato tipo di poli e dispositivo.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'dispositivi_2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT DISTINCT DAT_TARMAX FROM POLI_DISP_IN WHERE DAT_POLI = ? AND DAT_DISP = ?"
        cursor.execute(query, (dat_poli_valore, dat_disp_valore))
        risultati = cursor.fetchall()
    if not risultati:
        raise ValueError(f"Nessun valore di DAT_TARMAX trovato per il tipo di poli '{dat_poli_valore}' e dispositivo '{dat_disp_valore}'")
    lista_dat_inom = sorted(float(row[0]) for row in risultati)
    return lista_dat_inom


def cerca_curva(dat_poli_valore, dat_disp_valore, dat_inom_valore):
    '''Restituisce la lista dei valori di DAT_CURVA per un dato tipo di poli, dispositivo e valore di DAT_TARMAX.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'dispositivi_2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT DISTINCT DAT_CURVA FROM POLI_MT_CURVA WHERE DAT_POLI = ? AND DAT_DISP = ? AND DAT_TARMAX = ?"
        cursor.execute(
            query, (dat_poli_valore, dat_disp_valore, dat_inom_valore))
        risultati = cursor.fetchall()
    if not risultati:
        raise ValueError(f"Nessun valore di DAT_CURVA trovato per il tipo di poli '{dat_poli_valore}', dispositivo '{dat_disp_valore}' e valore di DAT_TARMAX '{dat_inom_valore}'")
    lista_dat_curva = sorted(row[0] for row in risultati)
    return lista_dat_curva


def cerca_potint(dat_poli_valore, dat_disp_valore, dat_inom_valore, dat_curva_valore, n_fasi_valore):
    '''Restituisce la lista dei valori di DAT_PI220 o DAT_PI380 (a seconda del numero di fasi) per un dato tipo di poli, dispositivo, valore di DAT_TARMAX e curva.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'dispositivi_2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        if n_fasi_valore == 1:
            query = "SELECT DISTINCT DAT_PI220 FROM POLI_MT_CURVA WHERE DAT_POLI = ? AND DAT_DISP = ? AND DAT_TARMAX = ? AND DAT_CURVA = ?"
        else:
            query = "SELECT DISTINCT DAT_PI380 FROM POLI_MT_CURVA WHERE DAT_POLI = ? AND DAT_DISP = ? AND DAT_TARMAX = ? AND DAT_CURVA = ?"
        cursor.execute(query, (dat_poli_valore, dat_disp_valore,
                       dat_inom_valore, dat_curva_valore))
        risultati = cursor.fetchall()
    if not risultati:
        raise ValueError(f"Nessun valore di potenza d'intervento trovato per il tipo di poli '{dat_poli_valore}', dispositivo '{dat_disp_valore}', valore di DAT_TARMAX '{dat_inom_valore}', curva '{dat_curva_valore}' e numero di fasi '{n_fasi_valore}'")
    lista_dat_inom = sorted(row[0] for row in risultati)
    return lista_dat_inom


def cerca_classe(dat_poli_valore, dat_disp_valore,  dat_inom_valore):
    '''Restituisce la lista dei valori di DAT_CLASSE per un dato tipo di poli, dispositivo e valore di DAT_TARMAX.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'dispositivi_2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT DISTINCT DAT_CLASSE FROM POLI_DIF_CLASSE WHERE DAT_POLI = ? AND DAT_DISP = ?  AND DAT_TARMAX = ?"
        cursor.execute(
            query, (dat_poli_valore, dat_disp_valore, dat_inom_valore))
        risultati = cursor.fetchall()
    if not risultati:
        raise ValueError(f"Nessuna classe trovata per il tipo di poli '{dat_poli_valore}', dispositivo '{dat_disp_valore}' e valore di DAT_TARMAX '{dat_inom_valore}'")
    lista_dat_classe = sorted(row[0] for row in risultati)
    return lista_dat_classe


def cerca_dmin(dat_poli_valore, dat_disp_valore,  dat_inom_valore, dat_classe_valore):
    '''Restituisce la lista dei valori di DAT_DMIN per un dato tipo di poli, dispositivo, valore di DAT_TARMAX e classe.
    Se non trovato, solleva un'eccezione.
    '''
    db_path = r'dispositivi_2025.sqlite'
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT DISTINCT DAT_DMIN FROM POLI_DIF_CLASSE WHERE DAT_POLI = ? AND DAT_DISP = ?  AND DAT_TARMAX = ? AND DAT_CLASSE = ?"
        cursor.execute(query, (dat_poli_valore, dat_disp_valore,
                       dat_inom_valore, dat_classe_valore))
        risultati = cursor.fetchall()
    if not risultati:
        raise ValueError(f"Nessun valore di DAT_DMIN trovato per il tipo di poli '{dat_poli_valore}', dispositivo '{dat_disp_valore}', valore di DAT_TARMAX '{dat_inom_valore}' e classe '{dat_classe_valore}'")
    lista_dat_dmin = sorted(row[0] for row in risultati)
    return [float(x) for x in lista_dat_dmin]


def calcola_ib(e_stellata: float, fasi: int, potenza: float, cosfi: float) -> float:
    '''Calcola la corrente di impiego (Ib) in base alla potenza, tensione, numero di fasi e fattore di potenza.
    Parametri:
    - e_stellata: tensione stellata (V)
    - fasi: numero di fasi (1, 2 o 3)
    - potenza: potenza del carico (W)
    - cosfi: fattore di potenza del carico (0 < cosfi ≤ 1)
    Ritorna:
    - Ib: corrente di impiego in A
    ''' 
    e_stellata = float(e_stellata)
    fasi = int(fasi)
    potenza = float(potenza)
    cosfi = float(cosfi)

    if fasi == 3:
        return potenza / (3 * e_stellata * cosfi)
    elif fasi == 2:
        return potenza / (math.sqrt(3) * e_stellata * cosfi)
    elif fasi == 1:
        return potenza / (e_stellata * cosfi)
    else:
        raise ValueError("Numero di fasi non valido. Deve essere 1, 2 o 3.")


def poli_validi_da_carico(n_fasi, n_carico):
    '''Restituisce la lista dei tipi di poli validi in base al numero di fasi e alla presenza di carico.
    - n_fasi: numero di fasi (1, 2 o 3)
    - n_carico: booleano, True se c'è un carico collegato, False altrimenti
    Ritorna:
    - lista_poli: lista dei tipi di poli validi (es. ["1N", "2_"])
    - poli_selezionato: il tipo di poli da selezionare di default (es. "1N"), o None se non c'è un default
    '''
    if n_fasi == 1 and n_carico:
        return ["1N", "2_"], "1N"

    if n_fasi == 2 and not n_carico:
        return ["2_"], "2_"

    if n_fasi == 2 and n_carico:
        return ["3_"], "3_"

    if n_fasi == 3 and not n_carico:
        return ["3_"], "3_"

    if n_fasi == 3 and n_carico:
        return ["3N", "4_"], "3N"

    return [], None


def formazioni_ammesse(
        formazione_options,
        poli,
        pe_carico):
    """
    Restituisce la lista delle formazioni di cavo AMMESSE,
    filtrate su quelle realmente disponibili per il tipo di cavo.
    """

    if not formazione_options:
        return []

    ammesse = []

    # Unipolare sempre ammesso SOLO se presente nel DB
    if "Unipolare 1x" in formazione_options:
        ammesse.append("Unipolare 1x")

    # Regole per multipolari
    if poli in ("3N", "4_"):
        richieste = ["Multipolare 5G"] if pe_carico else ["Multipolare 4x"]

    elif poli == "3_":
        richieste = ["Multipolare 4x"] if pe_carico else ["Multipolare 3x"]

    elif poli in ("2_", "1N"):
        richieste = ["Multipolare 3x"] if pe_carico else ["Multipolare 2x"]

    else:
        richieste = []

    # Intersezione con le opzioni DB
    for f in richieste:
        if f in formazione_options:
            ammesse.append(f)

    return ammesse


def seleziona_in_nominale(ib, in_options):
    """
    Seleziona la In corretta in base a Ib.
    Ritorna:
        - In selezionata
        - flag insufficiente (True/False)
    """

    if not in_options:
        return None, False

    in_options = sorted(in_options)

    # Prima In >= Ib
    for in_val in in_options:
        if in_val >= ib:
            return in_val, False

    # Nessuna In sufficiente → prendo la massima
    return in_options[-1], True


def sezione_derivata(sez_f, sezioni, materiale):
    """
    Calcola la sezione N/PE in funzione della sezione F
    applicando la regola rame/alluminio e
    restituisce la minima sezione disponibile >= target.
    """

    if not sezioni:
        return None

    sez_f = float(sez_f)

    # Soglie normative
    if materiale == "Rame":
        soglia = 16.0
    elif materiale == "Alluminio":
        soglia = 25.0
    else:
        soglia = 16.0  # fallback prudenziale

    # Regola normativa
    if sez_f <= soglia:
        target = sez_f
    else:
        target = sez_f / 2.0

    # Lista già ordinata crescente
    for s in sezioni:
        if float(s) >= target:
            return s

    # Se nessuna >= target, ritorna l'ultima (la più grande disponibile)
    return sezioni[-1]
