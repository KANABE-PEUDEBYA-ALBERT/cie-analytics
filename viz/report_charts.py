"""
Graphiques du Générateur de rapport.

Reproduit côté serveur (Plotly, exportable en image) le contenu du Tableau
de bord HTML/Chart.js, à partir des mêmes données standardisées produites
par data/questionnaire.py (Agence, Satisfaction, Resolu, Apprecie_liste,
Motif_insatisfaction, Horodatage). Chaque graphique est renvoyé avec un
résumé de données chiffré (pas les lignes brutes) destiné au commentaire
Gemini — jamais les réponses individuelles.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from viz.charts import CHART_PALETTE, apply_readable_style

# Même orange que le reste de l'application (bandeaux PDF/Word/PPTX,
# pastilles KPI...) — un seul et même orange partout, pour la cohérence
# visuelle demandée : plus de couleurs différentes d'un graphique à l'autre.
ORANGE = "F28C28"

SAT_ORDER = ["😞 Très insatisfait", "🙁 Insatisfait", "😐 Neutre", "🙂 Satisfait", "😃 Très satisfait"]
SAT_COLORS = {
    "😞 Très insatisfait": "#DC2626", "🙁 Insatisfait": "#F97316",
    "😐 Neutre": "#9CA3AF", "🙂 Satisfait": "#84CC16", "😃 Très satisfait": "#16A34A",
}


def _split_multi(series: pd.Series) -> pd.Series:
    """Éclate une colonne à choix multiples séparés par ';' (ex: Apprecie_liste)."""
    items = series.dropna().astype(str).str.split(";").explode().str.strip()
    return items[items != ""]


def build_report_charts(df: pd.DataFrame) -> list[dict]:
    """Retourne une liste ordonnée de graphiques prêts pour le rapport :
    {"title": str, "fig": plotly figure, "data_summary": dict pour Gemini}.
    Ne construit que les graphiques dont les colonnes nécessaires sont
    présentes — jamais d'erreur sur un jeu de données incomplet."""
    charts: list[dict] = []
    n_total = len(df)
    if n_total == 0:
        return charts

    agences = sorted(df["Agence"].dropna().unique().tolist()) if "Agence" in df.columns else []

    # --- 1. Répartition de la satisfaction ---------------------------------
    if "Satisfaction" in df.columns:
        vc = df["Satisfaction"].dropna().value_counts()
        vc = vc.reindex([s for s in SAT_ORDER if s in vc.index])
        if len(vc):
            fig = go.Figure(go.Bar(
                x=vc.index.tolist(), y=vc.values.tolist(),
                marker_color=f"#{ORANGE}", text=vc.values.tolist(), textposition="outside",
            ))
            fig.update_layout(title="Comment évalueriez-vous votre passage en agence ?")
            apply_readable_style(fig)
            charts.append({
                "title": "Comment évalueriez-vous votre passage en agence ?",
                "fig": fig,
                "data_summary": {"type": "satisfaction_distribution", "effectifs": vc.to_dict(), "total": int(vc.sum()), "pourcentages_exacts": {k: round(100*v/vc.sum(), 2) for k, v in vc.to_dict().items()}},
            })

    # --- 2. Résolution -------------------------------------------------------
    if "Resolu" in df.columns:
        vc = df["Resolu"].dropna().value_counts()
        if len(vc):
            fig = go.Figure(go.Bar(
                x=vc.values.tolist(), y=vc.index.tolist(), orientation="h",
                marker_color=f"#{ORANGE}",
                text=vc.values.tolist(), textposition="outside",
            ))
            fig.update_layout(title="Votre requête ou préoccupation a-t-elle été résolue ?")
            apply_readable_style(fig)
            charts.append({
                "title": "Votre requête ou préoccupation a-t-elle été résolue ?",
                "fig": fig,
                "data_summary": {"type": "resolution", "effectifs": vc.to_dict(), "total": int(vc.sum()), "pourcentages_exacts": {k: round(100*v/vc.sum(), 2) for k, v in vc.to_dict().items()}},
            })

    # --- 3. Points les plus appréciés ----------------------------------------
    if "Apprecie_liste" in df.columns:
        items = _split_multi(df["Apprecie_liste"])
        if len(items):
            vc = items.value_counts()
            fig = go.Figure(go.Bar(
                x=vc.values.tolist(), y=vc.index.tolist(), orientation="h",
                marker_color=CHART_PALETTE[0], text=vc.values.tolist(), textposition="outside",
            ))
            fig.update_layout(title="Qu'avez-vous le plus apprécié ?", yaxis=dict(autorange="reversed"))
            apply_readable_style(fig)
            charts.append({
                "title": "Qu'avez-vous le plus apprécié ?",
                "fig": fig,
                "data_summary": {"type": "top_items", "citations": vc.to_dict(), "n_repondants": n_total, "pourcentages_exacts_sur_repondants": {k: round(100*v/n_total, 2) for k, v in vc.to_dict().items()}},
            })

    # --- 4. Motifs d'insatisfaction -------------------------------------------
    if "Motif_insatisfaction" in df.columns:
        # Un même répondant peut cocher PLUSIEURS motifs à la fois (valeurs
        # séparées par ";" dans la même cellule) — sans découpage, toute la
        # chaîne concaténée ("Manque de confort;Temps de traitement trop
        # long;...") était comptée comme UNE SEULE modalité géante au lieu de
        # créditer chacun des motifs cochés. `_split_multi` (déjà utilisée
        # pour "Apprécié" ci-dessus) répartit chaque motif dans sa propre
        # modalité : le nombre d'individus reste le même, mais un individu
        # ayant coché 5 motifs contribue bien 1 citation à CHACUN des 5,
        # comptés comme des modalités normales.
        motifs = _split_multi(df["Motif_insatisfaction"])
        if len(motifs):
            vc = motifs.value_counts()
            n_insatisfaits = df["Motif_insatisfaction"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().shape[0]
            fig = go.Figure(go.Bar(
                x=vc.values.tolist(), y=vc.index.tolist(), orientation="h",
                marker_color=f"#{ORANGE}", text=vc.values.tolist(), textposition="outside",
            ))
            fig.update_layout(title="Quel est le motif d'insatisfaction ?", yaxis=dict(autorange="reversed"))
            apply_readable_style(fig)
            charts.append({
                "title": "Quel est le motif d'insatisfaction ?",
                "fig": fig,
                "data_summary": {"type": "complaint_reasons", "citations": vc.to_dict(), "n_insatisfaits": n_insatisfaits, "pourcentages_exacts": {k: round(100*v/n_insatisfaits, 2) for k, v in vc.to_dict().items()}},
            })

    # --- 5 & 6. Évolution dans le temps ---------------------------------------
    if "Horodatage" in df.columns and df["Horodatage"].notna().any():
        dts = pd.to_datetime(df["Horodatage"], errors="coerce")
        month = dts.dt.to_period("M").dt.to_timestamp()
        counts = month.value_counts().sort_index()
        if len(counts):
            fig = go.Figure(go.Scatter(
                x=counts.index, y=counts.values, mode="lines+markers",
                line=dict(color=f"#{ORANGE}", width=3), marker=dict(size=8),
            ))
            fig.update_layout(title="Nombre de réponses par mois")
            apply_readable_style(fig)
            charts.append({
                "title": "Nombre de réponses par mois",
                "fig": fig,
                "data_summary": {"type": "volume_over_time", "par_mois": {str(k.date()): int(v) for k, v in counts.items()}},
            })

        if "Satisfaction" in df.columns:
            tmp = pd.DataFrame({"mois": month, "sat": df["Satisfaction"]})
            tmp["positif"] = tmp["sat"].isin(["🙂 Satisfait", "😃 Très satisfait"])
            grp = (tmp.dropna(subset=["mois"]).groupby("mois")["positif"].mean().sort_index() * 100).round(2)
            if len(grp):
                fig = go.Figure(go.Scatter(
                    x=grp.index, y=grp.values, mode="lines+markers", fill="tozeroy",
                    line=dict(color=f"#{ORANGE}", width=3), marker=dict(size=8),
                ))
                fig.update_layout(title="Taux de satisfaction par mois (%)", yaxis=dict(range=[0, 100]))
                apply_readable_style(fig)
                charts.append({
                    "title": "Taux de satisfaction par mois (%)",
                    "fig": fig,
                    "data_summary": {"type": "satisfaction_rate_over_time", "par_mois_pct": {str(k.date()): round(v, 1) for k, v in grp.items()}},
                })

    # --- 7, 8, 9. Comparaisons entre agences (seulement si plusieurs) --------
    if len(agences) > 1 and "Agence" in df.columns:
        n_by_ag = df["Agence"].value_counts().reindex(agences)
        fig = go.Figure(go.Bar(x=agences, y=n_by_ag.values.tolist(), marker_color=f"#{ORANGE}",
                                text=n_by_ag.values.tolist(), textposition="outside"))
        fig.update_layout(title="Nombre de répondants par agence")
        apply_readable_style(fig)
        charts.append({
            "title": "Nombre de répondants par agence",
            "fig": fig,
            "data_summary": {"type": "respondents_by_agency", "effectifs": n_by_ag.to_dict(), "pourcentages_exacts": {k: round(100*v/n_by_ag.sum(), 2) for k, v in n_by_ag.to_dict().items()}},
        })

        if "Satisfaction" in df.columns:
            sat_rate, insat_rate = {}, {}
            for ag in agences:
                sub = df.loc[df["Agence"] == ag, "Satisfaction"].dropna()
                if len(sub):
                    sat_rate[ag] = round(100 * sub.isin(["🙂 Satisfait", "😃 Très satisfait"]).mean(), 1)
                    insat_rate[ag] = round(100 * sub.isin(["🙁 Insatisfait", "😞 Très insatisfait"]).mean(), 1)
            fig = go.Figure()
            fig.add_bar(name="Satisfaction", x=agences, y=[sat_rate.get(a, 0) for a in agences], marker_color=CHART_PALETTE[1])
            fig.add_bar(name="Insatisfaction", x=agences, y=[insat_rate.get(a, 0) for a in agences], marker_color=CHART_PALETTE[5])
            fig.update_layout(title="Taux de satisfaction / insatisfaction par agence (%)", barmode="group", yaxis=dict(range=[0, 100]))
            apply_readable_style(fig)
            charts.append({
                "title": "Taux de satisfaction / insatisfaction par agence (%)",
                "fig": fig,
                "data_summary": {"type": "satisfaction_by_agency", "taux_satisfaction": sat_rate, "taux_insatisfaction": insat_rate},
            })

        if "Resolu" in df.columns:
            res_rate = {}
            for ag in agences:
                sub = df.loc[df["Agence"] == ag, "Resolu"].dropna()
                if len(sub):
                    res_rate[ag] = round(100 * (sub == "OUI").mean(), 1)
            if res_rate:
                fig = go.Figure(go.Scatter(
                    x=list(res_rate.keys()), y=list(res_rate.values()), mode="lines+markers",
                    line=dict(color=f"#{ORANGE}", width=3), marker=dict(size=9),
                ))
                fig.update_layout(title="Taux de résolution par agence (%)", yaxis=dict(range=[0, 100]))
                apply_readable_style(fig)
                charts.append({
                    "title": "Taux de résolution par agence (%)",
                    "fig": fig,
                    "data_summary": {"type": "resolution_by_agency", "taux_resolution": res_rate},
                })

    return charts


# ============================================================================
# Modèle de rapport officiel CIE — une page par agence, même habillage que le
# gabarit PowerPoint existant : pastilles KPI colorées, anneau de satisfaction
# (vert = positif / rouge = négatif), barres horizontales des points appréciés.
# ============================================================================

def build_custom_chart(df: pd.DataFrame, x_col: str, y_col: str | None, agg: str,
                        chart_type: str, title: str | None = None):
    """Graphique construit librement par l'utilisateur : n'importe quelle
    colonne des données en X, n'importe quelle colonne (ou aucune) en Y,
    n'importe quel type. Aucun catalogue imposé — l'utilisateur choisit tout.

    x_col : colonne dont chaque valeur devient une catégorie/point de l'axe X.
    y_col : colonne numérique à agréger par catégorie de x_col. Si None,
            l'agrégation est forcée à « Effectif » (nombre de lignes par
            catégorie de x_col), quelle que soit la valeur de `agg`.
    agg : "count" (effectif), "sum" (somme), "mean" (moyenne).
    chart_type : "bar", "line", "pie".
    """
    if x_col not in df.columns or df.empty:
        return None
    work = df[[x_col] + ([y_col] if y_col and y_col in df.columns else [])].dropna(subset=[x_col])
    if work.empty:
        return None

    if not y_col or agg == "count":
        grouped = work.groupby(x_col).size()
        agg_label = "Effectif"
    else:
        work = work.dropna(subset=[y_col])
        if agg == "sum":
            grouped = work.groupby(x_col)[y_col].sum()
            agg_label = "Somme"
        else:
            grouped = work.groupby(x_col)[y_col].mean()
            agg_label = "Moyenne"

    grouped = grouped.sort_values(ascending=False)
    if len(grouped) > 30:  # évite un graphique illisible sur une variable à trop de modalités
        grouped = grouped.head(30)

    labels = [str(v) for v in grouped.index.tolist()]
    values = [round(float(v), 2) for v in grouped.values.tolist()]
    auto_title = title or f"{agg_label} de {y_col} par {x_col}" if y_col and agg != "count" else (title or f"Effectif par {x_col}")

    if chart_type == "pie":
        fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.35))
    elif chart_type == "line":
        fig = go.Figure(go.Scatter(x=labels, y=values, mode="lines+markers"))
    else:
        fig = go.Figure(go.Bar(x=labels, y=values, marker_color=CHART_PALETTE[0]))
    fig.update_layout(title=auto_title, height=420, margin=dict(t=50, b=40))

    return {
        "title": auto_title,
        "fig": fig,
        "data_summary": {"x": x_col, "y": y_col, "agg": agg_label, "labels": labels, "values": values},
    }


def compute_agency_kpis(df_agence: pd.DataFrame, demandes_enregistrees: int | None = None) -> dict:
    """KPI d'une agence. Les 5 premiers reprennent les formules du gabarit
    PPTX d'origine ; les suivants sont des indicateurs complémentaires,
    proposables au choix dans le Générateur de rapport :
    Taux de Réponse = répondants / demandes-réclamations enregistrées (si connu)
    Taux de Satisfaction = (Très satisfait + Satisfait) / répondants
    Taux d'insatisfaction = (Très insatisfait + Insatisfait) / répondants
    Taux de résolution = Résolu / répondants"""
    n = len(df_agence)
    kpis = {
        "nbre_repondant": n, "taux_reponse": None, "taux_satisfaction": None,
        "taux_insatisfaction": None, "taux_resolution": None,
        "taux_neutre": None, "score_moyen": None, "duree_moyenne_min": None,
        "taux_commentaires": None, "n_telephones": None,
    }
    # Aucune saisie manuelle possible désormais (interface retirée) — si le
    # fichier importé contient LUI-MÊME une colonne avec ce nombre, on
    # l'utilise automatiquement ; sinon le taux reste à None (affiché
    # "N/A"), comme demandé explicitement plutôt que d'inventer une valeur.
    if not demandes_enregistrees:
        _demandes_col_candidates = [
            "Demandes_Enregistrees", "Demandes_enregistrees", "Nbre_Demandes",
            "Nombre_Demandes", "Demandes_Reclamations", "Demandes_Recla",
        ]
        _demandes_col = next((c for c in _demandes_col_candidates if c in df_agence.columns), None)
        if _demandes_col:
            _vals = pd.to_numeric(df_agence[_demandes_col], errors="coerce").dropna()
            if len(_vals):
                demandes_enregistrees = _vals.sum()
    if demandes_enregistrees:
        kpis["taux_reponse"] = round(100 * n / demandes_enregistrees, 2)
    if "Satisfaction" in df_agence.columns and n:
        sat = df_agence["Satisfaction"].dropna()
        if len(sat):
            pos = sat.isin(["🙂 Satisfait", "😃 Très satisfait"]).sum()
            neg = sat.isin(["🙁 Insatisfait", "😞 Très insatisfait"]).sum()
            neutre = sat.isin(["😐 Neutre"]).sum()
            kpis["taux_satisfaction"] = round(100 * pos / len(sat), 2)
            kpis["taux_insatisfaction"] = round(100 * neg / len(sat), 2)
            kpis["taux_neutre"] = round(100 * neutre / len(sat), 2)
    if "Score_satisfaction" in df_agence.columns and n:
        scores = df_agence["Score_satisfaction"].dropna()
        if len(scores):
            kpis["score_moyen"] = round(float(scores.mean()), 2)
    if "Resolu" in df_agence.columns and n:
        res = df_agence["Resolu"].dropna()
        if len(res):
            kpis["taux_resolution"] = round(100 * (res == "OUI").sum() / len(res), 2)
    if "Duree_reponse_min" in df_agence.columns:
        durees = df_agence["Duree_reponse_min"].dropna()
        durees = durees[durees < 24 * 60]
        if len(durees):
            kpis["duree_moyenne_min"] = round(float(durees.mean()), 1)
    if "A_commente" in df_agence.columns and n:
        kpis["taux_commentaires"] = round(100 * df_agence["A_commente"].mean(), 2)
    if "A_laisse_telephone" in df_agence.columns:
        kpis["n_telephones"] = int(df_agence["A_laisse_telephone"].sum())
    return kpis


def satisfaction_distribution_data(df_agence: pd.DataFrame) -> tuple[list[str], list[int], list[str]] | None:
    """Données brutes de la répartition de satisfaction : (labels, effectifs,
    couleurs hex sans #). Réutilisées à la fois par le graphique Plotly
    (PDF/Word/HTML) et par le graphique PowerPoint natif (mêmes chiffres,
    jamais recalculés deux fois différemment)."""
    if "Satisfaction" not in df_agence.columns:
        return None
    vc = df_agence["Satisfaction"].dropna().value_counts()
    vc = vc.reindex([s for s in SAT_ORDER if s in vc.index])
    if not len(vc):
        return None
    labels = vc.index.tolist()
    values = vc.values.tolist()
    colors = [SAT_COLORS.get(k, CHART_PALETTE[0]).lstrip("#") for k in labels]
    return labels, values, colors


def top_appreciated_data(df_agence: pd.DataFrame, top_n: int = 5) -> tuple[list[str], list[float]] | None:
    """Données brutes du top des points appréciés : (labels, % des répondants)."""
    if "Apprecie_liste" not in df_agence.columns:
        return None
    items = _split_multi(df_agence["Apprecie_liste"])
    if not len(items):
        return None
    n_total = len(df_agence)
    vc = items.value_counts().head(top_n)
    pct = (vc / n_total * 100).round(1)
    return pct.index.tolist(), pct.values.tolist()


def donut_satisfaction_fig(df_agence: pd.DataFrame):
    """Anneau de satisfaction, palette sémantique vert->rouge (comme le
    gabarit PPTX) — seule exception à la règle « une couleur » du dashboard,
    car ce graphique doit rester lisible en tant qu'image isolée sur la page."""
    data = satisfaction_distribution_data(df_agence)
    if data is None:
        return None
    labels, values, colors = data
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=[f"#{c}" for c in colors]),
        textinfo="percent", textfont=dict(size=22, color="white"),
    ))
    fig.update_layout(showlegend=True, margin=dict(t=10, b=10, l=10, r=10),
                       legend=dict(orientation="h", y=-0.15, font=dict(size=17)))
    apply_readable_style(fig)
    return fig


def bar_top_appreciated_fig(df_agence: pd.DataFrame, top_n: int = 5):
    """Barres horizontales des points les plus appréciés, en % des répondants."""
    data = top_appreciated_data(df_agence, top_n)
    if data is None:
        return None
    labels, pct = data
    fig = go.Figure(go.Bar(
        x=pct, y=labels, orientation="h",
        marker_color=CHART_PALETTE[0], text=[f"{v}%" for v in pct], textposition="outside",
        textfont=dict(size=17),
    ))
    fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(ticksuffix="%", range=[0, 100]))
    apply_readable_style(fig)
    return fig


# Catalogue des graphiques supplémentaires proposables au choix dans le
# rapport officiel, en plus de l'anneau et des barres appréciés d'origine —
# réutilise telles quelles les figures déjà produites par
# `build_report_charts` (mêmes titres, même rendu), simplement recalculées
# sur la seule sous-base de l'agence concernée.
EXTRA_CHART_TITLES = [
    "Comment évalueriez-vous votre passage en agence ?",
    "Votre requête ou préoccupation a-t-elle été résolue ?",
    "Qu'avez-vous le plus apprécié ?",
    "Quel est le motif d'insatisfaction ?",
    "Nombre de réponses par mois",
    "Taux de satisfaction par mois (%)",
]


# Correspondance entre l'identifiant d'un graphique dans le Tableau de bord
# (JS, attribut data-slot) et le titre du même graphique tel que produit par
# build_report_charts() côté Python — nécessaire pour appliquer le type
# réellement choisi à l'écran (barres/camembert/anneau/courbe) au rapport.
CHART_ID_TO_TITLE = {
    "sat-dist": "Comment évalueriez-vous votre passage en agence ?",
    "res-dist": "Votre requête ou préoccupation a-t-elle été résolue ?",
    "apprecie": "Qu'avez-vous le plus apprécié ?",
    "motif": "Quel est le motif d'insatisfaction ?",
}


def apply_chart_type(fig, chart_type: str):
    """Reconstruit `fig` avec le type choisi dans le Tableau de bord
    ('barre-v', 'barre-h', 'camembert', 'anneau', 'courbe') — à partir des
    mêmes catégories/valeurs déjà calculées, jamais recalculées autrement.
    Renvoie `fig` inchangée si le type est déjà celui demandé ou non reconnu."""
    if not fig.data:
        return fig
    trace = fig.data[0]
    ttype = trace.type
    orientation = getattr(trace, "orientation", None)

    # Extraction générique des catégories/valeurs, quel que soit le type de
    # départ (barre verticale, horizontale, camembert...).
    if ttype == "pie":
        categories, values = list(trace.labels), list(trace.values)
    elif ttype == "bar" and orientation == "h":
        categories, values = list(trace.y), list(trace.x)
    elif ttype == "bar":
        categories, values = list(trace.x), list(trace.y)
    elif ttype == "scatter":
        categories, values = list(trace.x), list(trace.y)
    else:
        return fig

    title = fig.layout.title.text if fig.layout.title else ""
    new_fig = None
    if chart_type == "barre-v":
        new_fig = go.Figure(go.Bar(x=categories, y=values, marker_color=f"#{ORANGE}",
                                    text=values, textposition="outside"))
    elif chart_type == "barre-h":
        new_fig = go.Figure(go.Bar(x=values, y=categories, orientation="h", marker_color=f"#{ORANGE}",
                                    text=values, textposition="outside"))
        new_fig.update_layout(yaxis=dict(autorange="reversed"))
    elif chart_type in ("camembert", "anneau"):
        new_fig = go.Figure(go.Pie(labels=categories, values=values, hole=0.5 if chart_type == "anneau" else 0,
                                    textinfo="percent"))
    elif chart_type == "courbe":
        new_fig = go.Figure(go.Scatter(x=categories, y=values, mode="lines+markers",
                                        line=dict(color=f"#{ORANGE}", width=3), marker=dict(size=8)))
    else:
        return fig

    new_fig.update_layout(title=title)
    apply_readable_style(new_fig)
    return new_fig


def build_agency_full_charts(df_agence: pd.DataFrame, chart_type_override: dict | None = None) -> list[dict]:
    """Liste ORDONNÉE et SANS RESTRICTION des graphiques d'une agence — ce
    que l'on voit dans le Tableau de bord, appliqué à cette agence :
    1. Satisfaction — barre verticale
    2. Satisfaction — anneau (vue complémentaire, même donnée que 1)
    3. Résolution — barre horizontale
    4. Points appréciés — barre horizontale
    5+ le reste (motifs d'insatisfaction, évolutions dans le temps...),
       dans leur ordre naturel, sans qu'aucune case à cocher ne les filtre.

    `chart_type_override` : état `chartTypeOverride` reçu EN DIRECT du
    Tableau de bord (via le pont Streamlit Components — voir
    dashboard_live_state dans run/screens/11_Tableau_de_Bord.py). Si un
    graphique a été basculé en camembert/anneau/barres/courbe à l'écran, le
    rapport applique EXACTEMENT le même type — plus de reconstruction
    générique qui ne correspond pas à ce qui est configuré."""
    chart_type_override = chart_type_override or {}
    standard = build_report_charts(df_agence)
    by_title = {c["title"]: c for c in standard}

    def _apply(chart_id: str, entry: dict) -> dict:
        override = chart_type_override.get(chart_id)
        if override:
            entry = {**entry, "fig": apply_chart_type(entry["fig"], override)}
        return entry

    ordered: list[dict] = []
    sat_title = "Comment évalueriez-vous votre passage en agence ?"
    res_title = "Votre requête ou préoccupation a-t-elle été résolue ?"
    top_title = "Qu'avez-vous le plus apprécié ?"

    if sat_title in by_title:
        ordered.append(_apply("sat-dist", by_title[sat_title]))  # 1. barre verticale (ou le type choisi)
    # L'ancienne « vue en anneau » de la satisfaction, toujours ajoutée en
    # doublon juste après, est retirée — pure répétition de la même donnée
    # que le graphique 1 ci-dessus (demande explicite). Si l'anneau est
    # voulu, il suffit de basculer le type du graphique 1 lui-même dans le
    # Tableau de bord (chart_type_override s'applique déjà à "sat-dist").
    if res_title in by_title:
        ordered.append(_apply("res-dist", by_title[res_title]))  # 2. barre horizontale (ou le type choisi)
    if top_title in by_title:
        ordered.append(_apply("apprecie", by_title[top_title]))  # 3. barre horizontale (ou le type choisi)

    # Graphiques d'évolution dans le temps explicitement exclus du rapport
    # (demande explicite) — jamais inclus, même s'ils existent dans le
    # catalogue standard utilisé ailleurs (Tableau de bord, modèle libre).
    EXCLUDED_TITLES = {"Nombre de réponses par mois", "Taux de satisfaction par mois (%)"}

    used_titles = {sat_title, res_title, top_title} | EXCLUDED_TITLES
    for c in standard:
        if c["title"] not in used_titles:
            chart_id = next((cid for cid, t in CHART_ID_TO_TITLE.items() if t == c["title"]), None)
            ordered.append(_apply(chart_id, c) if chart_id else c)  # 5+ le reste, sans restriction
    return ordered


def build_agency_report_pages(df: pd.DataFrame, demandes_par_agence: dict | None = None,
                               include_donut: bool = True, include_bar: bool = True,
                               extra_chart_titles: list[str] | None = None,
                               custom_chart_specs: list[dict] | None = None,
                               include_verbatims: bool = False,
                               chart_type_override: dict | None = None,
                               dashboard_verbatim_summary: dict | None = None) -> list[dict]:
    """Une entrée par agence, dans l'ordre alphabétique : KPI + TOUS les
    graphiques (voir `build_agency_full_charts` — aucune restriction, exactement
    ce que montre le Tableau de bord pour cette agence) + verbatims (si
    demandé) + bornes de dates pour la période.

    `chart_type_override` : reçu en direct du Tableau de bord (voir
    `dashboard_live_state` dans 11_Tableau_de_Bord.py) — applique les mêmes
    types de graphique (camembert/anneau/barres/courbe) que ceux réellement
    configurés à l'écran, pour toutes les agences de ce rapport.

    `dashboard_verbatim_summary` : résumé des verbatims (4 points max par
    côté) déjà généré dans le Tableau de bord, reçu via le même pont. Utilisé
    TEL QUEL, jamais recalculé indépendamment — le rapport doit être « le
    Tableau de bord, dans un fichier », pas une seconde version qui pourrait
    diverger (l'ancien code retriait les 5 commentaires les plus longs par
    agence, un contenu totalement différent du résumé affiché à l'écran)."""
    demandes_par_agence = demandes_par_agence or {}
    pages = []
    if "Agence" not in df.columns:
        return pages
    for agence in sorted(df["Agence"].dropna().unique().tolist()):
        sub = df[df["Agence"] == agence]
        kpis = compute_agency_kpis(sub, demandes_par_agence.get(agence))
        periode = None
        if "Horodatage" in sub.columns and sub["Horodatage"].notna().any():
            dts = pd.to_datetime(sub["Horodatage"], errors="coerce").dropna()
            if len(dts):
                periode = (dts.min(), dts.max())

        verbatims = None
        if include_verbatims and dashboard_verbatim_summary:
            verbatims = {
                "positifs": dashboard_verbatim_summary.get("positifs") or [],
                "negatifs": dashboard_verbatim_summary.get("negatifs") or [],
            }

        pages.append({
            "agence": agence,
            "kpis": kpis,
            "periode": periode,
            "all_charts": build_agency_full_charts(sub, chart_type_override=chart_type_override),
            "verbatims": verbatims,
        })
    return pages
