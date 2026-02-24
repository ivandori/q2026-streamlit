'''
=============================================================================
Q2026 - DEMO DIMENSIONAMENTO DI UNA LINEA ELETTRICA
FUNZIONI IMPAGINAZIONE PER STREAMLIT
Ultimo aggiornamento: 22/02/2026
AUTORE: Ivano Dorigatti
LICENZA: MIT License
=============================================================================
'''

import streamlit as st

def titolo_verde(text):
    st.markdown(f"<h1 style='color: green;'>{text}</h1>", unsafe_allow_html=True)
    
def sfondo_giallo():
    st.markdown(f"""
        <div style="background-color:yellow;">
        """, unsafe_allow_html=True)

def chiudi_div():
    st.markdown("</div>", unsafe_allow_html=True)

# Funzione per creare una cornice
def create_frame(title, col):
    with col:
        st.markdown(f"""
            <div style="border: 2px solid yellow; padding: 10px; border-radius: 10px;">
                <h3 style='text-align: center;'>{title}</h3>
                <hr style='border:1px solid white;'>
        """, unsafe_allow_html=True)

def close_frame(col):
    with col:
        st.markdown("</div>", unsafe_allow_html=True)

def create_subframe(title, col):
    with col:
        st.markdown(f"""
            <div style="border: 2px solid yellow; padding: 10px; border-radius: 10px;">
            <h4 style='text-align: center;'>{title}</h4>
        """, unsafe_allow_html=True)

# Funzione per aggiungere CSS personalizzato
def add_css(css: str):
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Definisci una funzione per centrare l'header
def centered_title(text):
    st.markdown(
        f"<h2 style='text-align: center;color:green;'>{text}</h2>", unsafe_allow_html=True)

def subtitle(text):
    st.markdown(
        f"<h3 style='text-align: center;color:gray;'>{text}</h3>", unsafe_allow_html=True)

def centered_header(text):
    st.markdown(
        f"<h3 style='text-align: center;color:rgb(250,25,250);'>{text}</h3>", unsafe_allow_html=True)
