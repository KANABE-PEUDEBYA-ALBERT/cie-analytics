"""
Page — Générateur de rapport.

Reste un document téléchargeable (PDF / Word / PowerPoint) — jamais une
page HTML. La logique elle-même vit dans viz/report_ui.py, partagée avec
le second point d'accès situé en bas de la page 📊 Tableau de bord (même
moteur appelé deux fois, pas deux versions séparées qui risqueraient de
diverger).
"""
from __future__ import annotations

from config.theme import set_page_title
from data.state import require_dataframe_or_stop
from viz.report_ui import render_report_generator

set_page_title("🗞️ Générateur de rapport", "Export PDF, Word et PowerPoint")

df_full = require_dataframe_or_stop()
render_report_generator(df_full, key_prefix="report", show_title=False)
