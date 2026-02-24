# Roadmap di Miglioramento -- Progetto Dimensionamento Linea BT

------------------------------------------------------------------------

# 🔴 PRIORITÀ 1 --- Correttezza tecnica e affidabilità calcoli (CRITICO)

## 1.1 Validazione formale input numerici

-   Centralizzare clamp e validazioni (V \> 0, cosφ ∈ \[0,1\], Icc \> 0,
    lunghezza \> 0).
-   Evitare propagazione di `None` nei calcoli.
-   Bloccare il calcolo se `k_totale ≤ 0`.

**Obiettivo:** eliminare risultati fisicamente impossibili.

------------------------------------------------------------------------

## 1.2 Revisione completa calcolo cortocircuito

-   Separare chiaramente:
    -   Impedenza sorgente
    -   Impedenza linea
    -   Loop di guasto
-   Restituire struttura dati esplicita (dict con chiavi nominative).
-   Verificare coerenza unità (kA vs A).

**Rischio attuale:** errore concettuale nei min/max e cosφ di valle.

------------------------------------------------------------------------

## 1.3 Allineamento automatico verifiche CEI 64-8

Automatizzare controlli normativi:

-   ✔ Ib ≤ In ≤ Iz\
-   ✔ I²t ≤ n·k²S²\
-   ✔ ΔV% ≤ limite\
-   ✔ Protezione contro contatti indiretti (Zs ≤ U0 / Ia)

Mostrare esito: - ✅ Conforme\
- ❌ Non conforme (con motivazione tecnica)

------------------------------------------------------------------------

## 1.4 Refactoring calcolo sezione cavo

Separare in funzioni dedicate: - verifica_termica() - verifica_i2t() -
verifica_cdt()

Restituire report tecnico con motivo di scarto per ogni sezione.

------------------------------------------------------------------------

# 🟠 PRIORITÀ 2 --- Coerenza architetturale e manutenibilità

## 2.1 Unificazione gestione stato

-   Un'unica fonte di verità
-   Eliminare duplicazioni
-   Creare funzione normalize_state()

------------------------------------------------------------------------

## 2.2 Eliminare logica business nella UI

Architettura ideale:

UI → Service layer → Motore calcolo → DB

------------------------------------------------------------------------

## 2.3 Eliminare codice legacy

-   Rimuovere funzioni `_old`
-   Eliminare codice commentato
-   Rimuovere debug residuale

------------------------------------------------------------------------

# 🟡 PRIORITÀ 3 --- Robustezza ingegneristica

## 3.1 Logging tecnico strutturato

-   Log parametri
-   Log risultati
-   Export JSON progetto

------------------------------------------------------------------------

## 3.2 Relazione tecnica automatica

Generare automaticamente: - Sintesi parametri - Verifiche normative -
Esito finale

------------------------------------------------------------------------

## 3.3 Modalità calcolo inverso

-   Dato dispositivo → suggerisci sezione
-   Dato cavo → suggerisci In

------------------------------------------------------------------------

# 🟢 PRIORITÀ 4 --- Miglioramenti UX

## 4.1 Evidenziazione errori real-time

-   Rosso → non conforme
-   Giallo → borderline
-   Verde → conforme

------------------------------------------------------------------------

## 4.2 Estensione sistemi elettrici

-   Sistema TT
-   Sistema IT
-   Linee derivate multiple
-   Coordinamento selettivo

------------------------------------------------------------------------

## 4.3 Cronologia modifiche progetto

Salvataggio versioni progetto in sessione.

------------------------------------------------------------------------

## 4.4 Ottimizzazione performance DB

-   Cache query frequenti
-   Ridurre connessioni ripetute

------------------------------------------------------------------------

# 🔵 PRIORITÀ 5 --- Evoluzione professionale

## 5.1 Database parametrico aggiornabile

Separare: - Tabelle normative - Tabelle costruttore - Tabelle
personalizzate

------------------------------------------------------------------------

## 5.2 Multi-linea e progettazione quadro completo

Passare da dimensionamento linea singola a progettazione quadro
completo.

------------------------------------------------------------------------

## 5.3 Validazione normativa estesa

Integrare: - Sez. 43 (protezione sovracorrenti) - Sez. 41 (contatti
indiretti) - Sez. 52 (portata cavi) - Sez. 53 (dispositivi)

------------------------------------------------------------------------

# 📌 Sintesi Strategica

1.  Consolidare motore di calcolo\
2.  Separare UI da logica elettrica\
3.  Generare report tecnico automatico\
4.  Estendere a quadro multi-linea\
5.  Evolvere verso tool professionale certificabile
