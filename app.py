"""Dashboard EHPM 2021 (Streamlit). Ejecutar:  streamlit run app.py
Requiere ehpm2021_escala_original.csv en la misma carpeta (se genera con preparar_datos.py)."""
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="EHPM 2021 · Pobreza e ingresos", layout="wide")

CONDS = ["Pobreza extrema", "Pobreza relativa", "No pobre"]
COLORS = {"Pobreza extrema": "#B3261E", "Pobreza relativa": "#E08A00", "No pobre": "#8AA1B1"}
TAMS = ["1–2", "3–4", "5–6", "7 o más"]


@st.cache_data
def load():
    d = pd.read_csv("ehpm2021_escala_original.csv")
    d["Área"] = d["area"].map({0: "Rural", 1: "Urbano"})
    d["Condición"] = d["pobreza"].astype(int).map(dict(zip([1, 2, 3], CONDS)))
    d["Miembros"] = pd.cut(d["r021a"], [0, 2, 4, 6, 99], labels=TAMS)
    d["pobre"] = d["pobreza"] < 3
    d["Con ayudas"] = d["totayuda"] > 0
    d["con_ing"] = d["ingre"] > 0
    return d


df = load()

# ---------- Filtros globales (Zoom and filter) ----------
st.sidebar.header("Filtros")
areas = st.sidebar.multiselect("Área", ["Rural", "Urbano"], default=["Rural", "Urbano"])
conds = st.sidebar.multiselect("Condición", CONDS, default=CONDS)
tams = st.sidebar.multiselect("Miembros del hogar", TAMS, default=TAMS)
ayud = st.sidebar.multiselect("Ayudas", ["Con ayudas", "Sin ayudas"], default=["Con ayudas", "Sin ayudas"])


def subset(skip=None):
    m = pd.Series(True, index=df.index)
    if skip != "tam":
        m &= df["Miembros"].isin(tams)
    if skip != "cond":
        m &= df["Condición"].isin(conds)
    m &= df["Área"].isin(areas)
    m &= df["Con ayudas"].map({True: "Con ayudas", False: "Sin ayudas"}).isin(ayud)
    return df[m]


f = subset()
st.title("Pobreza e ingresos en los hogares salvadoreños")
st.caption("EHPM 2021 · registros de personas con indicadores de hogar. Las tasas son por persona, no por hogar.")
if f.empty:
    st.warning("Los filtros no dejan registros. Amplíe la selección.")
    st.stop()

# ---------- 1. Diagnóstico (Overview first) ----------
st.subheader("1 · Diagnóstico")
k = st.columns(5)
k[0].metric("Personas en el filtro", f"{len(f):,}", f"{len(f)/len(df):.1%} del total", delta_color="off")
k[1].metric("Tasa de pobreza", f"{f.pobre.mean():.1%}", f"{(f.pobre.mean()-df.pobre.mean())*100:+.1f} pts vs total", delta_color="inverse")
k[2].metric("Mediana ingreso per cápita", f"${f.ingpe.median():,.0f}", f"{f.ingpe.median()-df.ingpe.median():+,.0f} vs total")
k[3].metric("Reciben ayudas", f"{f['Con ayudas'].mean():.1%}", f"{(f['Con ayudas'].mean()-df['Con ayudas'].mean())*100:+.1f} pts", delta_color="off")
k[4].metric("Sin ingreso individual", f"{1-f.con_ing.mean():.1%}", f"{(df.con_ing.mean()-f.con_ing.mean())*100:+.1f} pts vs total", delta_color="inverse")

# ---------- 2. Patrones ----------
st.subheader("2 · Patrones")
c1, c2 = st.columns(2)
a = subset("tam").groupby("Miembros", observed=False).agg(tasa=("pobre", "mean"), n=("pobre", "size")).reset_index()
fa = px.bar(a, y="Miembros", x="tasa", orientation="h", text=a["tasa"].map("{:.1%}".format),
            hover_data={"n": ":,", "tasa": ":.1%"}, title="Tasa de pobreza por tamaño del hogar")
fa.add_vline(x=df.pobre.mean(), line_dash="dot", annotation_text="Total")
fa.update_traces(marker_color="#1D4F73", textposition="outside")
fa.update_xaxes(range=[0, 1], tickformat=".0%", title=None)
fa.update_yaxes(title=None, categoryorder="array", categoryarray=TAMS[::-1])
c1.plotly_chart(fa, use_container_width=True)

fb = px.histogram(f.assign(ing=f.ingpe.clip(upper=500)), x="ing", color="Condición", nbins=20,
                  color_discrete_map=COLORS, category_orders={"Condición": CONDS},
                  title="Distribución del ingreso per cápita mensual (US$, tope 500)")
fb.update_layout(bargap=0.05, legend_title=None)
fb.update_xaxes(title=None); fb.update_yaxes(title="Personas")
c2.plotly_chart(fb, use_container_width=True)

# ---------- 3. Anomalías ----------
st.subheader("3 · Anomalías")
an = f[f.gmvi >= 1e5]
st.error(f"**{len(an):,}** registros ({len(an)/len(f):.2%}) con gasto en vivienda (gmvi) ≥ 100,000 (valor centinela). "
         f"Media con centinelas: {f.gmvi.mean():,.0f} · sin centinelas: {f[f.gmvi < 1e5].gmvi.mean():,.1f} · "
         f"mediana: {f.gmvi.median():,.1f}. Se reportan medianas.")

# ---------- 4. Causa raíz ----------
st.subheader("4 · Causa raíz")
g = subset("cond").groupby("Condición").agg(ing=("con_ing", "mean"), ay=("Con ayudas", "mean")).reindex(CONDS).reset_index()
c3, c4 = st.columns(2)
for col, var, ttl in [(c3, "ing", "Personas con ingreso individual (ingre > 0)"), (c4, "ay", "Personas con ayudas (totayuda > 0)")]:
    fc = px.bar(g, y="Condición", x=var, orientation="h", color="Condición", color_discrete_map=COLORS,
                text=g[var].map("{:.1%}".format), title=ttl)
    fc.update_traces(textposition="outside")
    fc.update_xaxes(range=[0, 1], tickformat=".0%", title=None)
    fc.update_yaxes(title=None, categoryorder="array", categoryarray=CONDS[::-1])
    fc.update_layout(showlegend=False)
    col.plotly_chart(fc, use_container_width=True)

# ---------- 5. Recomendación ----------
st.subheader("5 · Recomendación")
ext = f[f["Condición"] == "Pobreza extrema"]["Con ayudas"].mean()
npo = f[f["Condición"] == "No pobre"]["Con ayudas"].mean()
st.success(f"**Focalizar las ayudas hacia los hogares más vulnerables.** En el filtro actual, "
           f"{ext:.1%} de las personas en pobreza extrema recibe ayudas frente a {npo:.1%} de las no pobres. "
           f"Priorizar hogares de 5 o más miembros y personas sin ingreso individual ({1-f.con_ing.mean():.1%} del filtro), "
           f"donde la tasa de pobreza es {f.pobre.mean():.1%}. Depurar gmvi antes de modelar.")

# ---------- Detalles bajo demanda ----------
st.subheader("Inspección de registros")
solo = st.checkbox("Solo valores atípicos de gmvi (≥ 100,000)")
orden = st.selectbox("Ordenar por", ["gmvi", "ingpe", "ingfa", "ingre", "totayuda", "r021a"])
t = (an if solo else f).sort_values(orden, ascending=False).head(12)
st.dataframe(t[["Área", "Condición", "r021a", "ingpe", "ingfa", "ingre", "totayuda", "gmvi"]], use_container_width=True)
