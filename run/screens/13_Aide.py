"""Page — Aide."""
from __future__ import annotations
from config.theme import set_page_title

import streamlit as st

from auth.auth_utils import current_role

set_page_title("Aide", "Présentation de l'application")

st.markdown(
    """
    <style>
    .st-key-aide_box_fait, .st-key-aide_box_organisation {
        background:#FFFFFF; border:1px solid #E5E1DC; border-radius:14px;
        padding:20px 24px 24px; margin-bottom:22px;
        box-shadow: 0 12px 30px rgba(0,0,0,.16), 0 4px 9px rgba(0,0,0,.09);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(key="aide_box_fait"):
    st.markdown("### Ce que fait l'application")
    st.markdown(
        "CIE Analytics centralise et analyse les questionnaires de satisfaction "
        "collectés en agence après chaque visite client. Elle fusionne "
        "automatiquement les fichiers de plusieurs agences, calcule les "
        "indicateurs de satisfaction et de performance, et produit des rapports "
        "PDF, Word et PowerPoint prêts à diffuser."
    )

with st.container(key="aide_box_organisation"):
    st.markdown("### Organisation de l'application")
    menu_admin = "\nAdministration : gestion des comptes utilisateurs (réservé aux administrateurs)." if current_role() == "administrateur" else ""
    st.markdown(
        f"""
    Accueil : vue d'ensemble et statut des données chargées.

    Préparation : import et fusion des fichiers de questionnaires.

    Tableau de bord : indicateurs et graphiques de satisfaction, globaux et par agence.

    Générateur de rapport : export PDF, Word et PowerPoint par agence ou combiné.

    Assistant : questions en langage naturel sur les données chargées.{menu_admin}
    """
    )
