import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Payment Analytics Dashboard",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130 0%, #262b3d 100%);
        border: 1px solid #2d3250;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 10px;
    }
    .metric-label { color: #8892b0; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { color: #ccd6f6; font-size: 28px; font-weight: 700; margin-top: 4px; }
    .metric-sub   { color: #64ffda; font-size: 13px; margin-top: 2px; }
    .section-header {
        color: #ccd6f6; font-size: 18px; font-weight: 600;
        border-left: 3px solid #64ffda; padding-left: 10px;
        margin: 24px 0 12px 0;
    }
    .insight-box {
        background: #1a1f35; border: 1px solid #2d3250;
        border-left: 4px solid #f6c90e;
        border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
    }
    .insight-text { color: #a8b2d8; font-size: 14px; line-height: 1.6; }
    .alert-box {
        background: #1f1a2e; border: 1px solid #2d3250;
        border-left: 4px solid #ff6b6b;
        border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
    }
    .good-box {
        background: #1a2f1f; border: 1px solid #2d3250;
        border-left: 4px solid #64ffda;
        border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;
    }
    div[data-testid="stSidebarContent"] { background-color: #0d1117; }
    .stSelectbox label, .stMultiSelect label { color: #8892b0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Data Loading ─────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    frames = []

    # ── 1. BridgerPay ──────────────────────────────────────────────────────
    bp = pd.read_csv("data/BridgerPay.csv")
    # Keep unique merchant order IDs (retry logic – keep first occurrence)
    bp = bp.drop_duplicates(subset=["merchantOrderId"], keep="first")
    bp["psp"]        = bp["pspName"]
    bp["mid"]        = bp["midAlias"]
    bp["country"]    = bp["country"]
    bp["amount_usd"] = bp["amount"].astype(float)
    bp["method"]     = bp["paymentMethod"]
    bp["is_success"] = bp["status"].str.lower() == "approved"
    bp["status_raw"] = bp["status"]
    bp["source"]     = "BridgerPay"
    frames.append(bp[["source","psp","mid","country","amount_usd","method","is_success","status_raw"]])

    # ── 2. Coinsbuy ────────────────────────────────────────────────────────
    cb = pd.read_excel("data/Coinsbuy.xlsx")
    cb["psp"]        = "Coinsbuy"
    cb["mid"]        = "Coinsbuy-Crypto-MID"
    cb["country"]    = "N/A"
    cb["amount_usd"] = cb["Source amount"].astype(float)  # USD-equivalent
    cb["method"]     = "Crypto"
    cb["is_success"] = cb["Status"].str.lower() == "confirmed"
    cb["status_raw"] = cb["Status"]
    cb["source"]     = "Coinsbuy"
    frames.append(cb[["source","psp","mid","country","amount_usd","method","is_success","status_raw"]])

    # ── 3. Confirmo ────────────────────────────────────────────────────────
    cf = pd.read_csv("data/Confirmo.csv", sep=",", skiprows=1)
    cf["psp"]        = "Confirmo"
    cf["mid"]        = "Confirmo-Crypto-MID"
    cf["country"]    = "N/A"
    cf["amount_usd"] = pd.to_numeric(cf["MerchantAmount"], errors="coerce")
    cf["method"]     = "Crypto"
    cf["is_success"] = cf["Status"].str.upper() == "PAID"
    cf["status_raw"] = cf["Status"]
    cf["source"]     = "Confirmo"
    frames.append(cf[["source","psp","mid","country","amount_usd","method","is_success","status_raw"]])

    # ── 4. PayProcc ────────────────────────────────────────────────────────
    pp = pd.read_csv("data/PayProcc.csv")
    # USD amount: if Currency==USD use Amount, else use Applied Amount (USD)
    pp["amount_usd"] = pp.apply(
        lambda r: r["Amount"] if r["Currency"] == "USD" else r["Applied Amount"], axis=1
    )
    pp["amount_usd"] = pd.to_numeric(pp["amount_usd"], errors="coerce")
    # Unique merchant order IDs
    pp = pp.drop_duplicates(subset=["Merchant Order ID"], keep="first")
    pp["psp"]        = "PayProcc"
    pp["mid"]        = pp["MID"]
    pp["country"]    = pp["Payer Country"]
    pp["method"]     = pp["Payment Method"]
    pp["is_success"] = pp["Status"].str.lower() == "success"
    pp["status_raw"] = pp["Status"]
    pp["source"]     = "PayProcc"
    frames.append(pp[["source","psp","mid","country","amount_usd","method","is_success","status_raw"]])

    # ── 5. Zen Pay ─────────────────────────────────────────────────────────
    zp = pd.read_csv("data/Zen_Pay.csv")
    # Only Apple Pay and Google Pay
    zp = zp[zp["payment_channel"].isin(["Apple Pay", "Google Pay"])]
    zp["psp"]        = "Zen Pay"
    zp["mid"]        = "Zen-Pay-MID-1"
    zp["country"]    = zp["customer_country"]
    zp["amount_usd"] = pd.to_numeric(zp["transaction_amount"], errors="coerce")
    zp["method"]     = zp["payment_channel"]
    zp["is_success"] = zp["transaction_state"].str.upper() == "ACCEPTED"
    zp["status_raw"] = zp["transaction_state"]
    zp["source"]     = "Zen Pay"
    frames.append(zp[["source","psp","mid","country","amount_usd","method","is_success","status_raw"]])

    df = pd.concat(frames, ignore_index=True)
    df["amount_usd"] = pd.to_numeric(df["amount_usd"], errors="coerce")
    df["country"] = df["country"].fillna("Unknown")
    return df

df_all = load_data()

# ── Sidebar Filters ───────────────────────────────────────────────────────────
st.sidebar.markdown("## 🔍 Filters")

all_sources   = sorted(df_all["source"].unique())
all_psps      = sorted(df_all["psp"].unique())
all_mids      = sorted(df_all["mid"].unique())
all_countries = sorted([c for c in df_all["country"].unique() if c not in ("N/A","Unknown")])
all_methods   = sorted(df_all["method"].unique())

sel_sources = st.sidebar.multiselect("PSP Source", all_sources, default=all_sources)
sel_psps    = st.sidebar.multiselect("PSP Name",   all_psps,   default=all_psps)
sel_mids    = st.sidebar.multiselect("MID",        all_mids,   default=all_mids)
sel_countries = st.sidebar.multiselect("Country",  all_countries, default=[])
sel_methods = st.sidebar.multiselect("Method",     all_methods, default=all_methods)

df = df_all.copy()
if sel_sources:   df = df[df["source"].isin(sel_sources)]
if sel_psps:      df = df[df["psp"].isin(sel_psps)]
if sel_mids:      df = df[df["mid"].isin(sel_mids)]
if sel_countries: df = df[df["country"].isin(sel_countries)]
if sel_methods:   df = df[df["method"].isin(sel_methods)]

# ── Colour palette ────────────────────────────────────────────────────────────
COLORS = ["#64ffda","#7b68ee","#f6c90e","#ff6b6b","#a8e063","#ff9f43","#4ecdc4","#c56cf0","#fd79a8","#00b894"]
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892b0", size=12),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#2d3250"),
    xaxis=dict(gridcolor="#1e2130", zerolinecolor="#2d3250"),
    yaxis=dict(gridcolor="#1e2130", zerolinecolor="#2d3250"),
)

def styled_fig(fig):
    fig.update_layout(**CHART_LAYOUT)
    return fig

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='color:#ccd6f6;font-size:2rem;font-weight:700;margin-bottom:4px;'>
💳 Payment Analytics Dashboard
</h1>
<p style='color:#8892b0;font-size:14px;margin-bottom:24px;'>
FundedNext · Multi-PSP · All Transactions
</p>
""", unsafe_allow_html=True)

# ── KPI Row ───────────────────────────────────────────────────────────────────
total       = len(df)
success     = df["is_success"].sum()
approval    = success / total * 100 if total else 0
total_vol   = df[df["is_success"]]["amount_usd"].sum()
avg_ticket  = df[df["is_success"]]["amount_usd"].mean()

c1,c2,c3,c4,c5 = st.columns(5)
with c1:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Total Attempts</div>
        <div class='metric-value'>{total:,}</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Successful</div>
        <div class='metric-value'>{success:,}</div>
    </div>""", unsafe_allow_html=True)
with c3:
    ar_color = "#64ffda" if approval >= 70 else ("#f6c90e" if approval >= 50 else "#ff6b6b")
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Approval Rate</div>
        <div class='metric-value' style='color:{ar_color}'>{approval:.1f}%</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Total Volume (USD)</div>
        <div class='metric-value'>${total_vol:,.0f}</div>
    </div>""", unsafe_allow_html=True)
with c5:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Avg Ticket (USD)</div>
        <div class='metric-value'>${avg_ticket:,.2f}</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🌍 Country Analysis", "🏦 PSP & MID Analysis", "💡 Insights"])

# ── TAB 1: OVERVIEW ───────────────────────────────────────────────────────────
with tab1:

    # PSP-wise attempts + approval
    st.markdown("<div class='section-header'>Attempts & Approval by PSP</div>", unsafe_allow_html=True)
    psp_df = df.groupby("psp").agg(
        attempts=("is_success","count"),
        successes=("is_success","sum"),
        volume=("amount_usd", lambda x: x[df.loc[x.index,"is_success"]].sum())
    ).reset_index()
    psp_df["approval_rate"] = psp_df["successes"] / psp_df["attempts"] * 100

    fig_psp = make_subplots(specs=[[{"secondary_y": True}]])
    fig_psp.add_trace(go.Bar(
        x=psp_df["psp"], y=psp_df["attempts"],
        name="Attempts", marker_color="#7b68ee", opacity=0.85
    ), secondary_y=False)
    fig_psp.add_trace(go.Bar(
        x=psp_df["psp"], y=psp_df["successes"],
        name="Successful", marker_color="#64ffda", opacity=0.85
    ), secondary_y=False)
    fig_psp.add_trace(go.Scatter(
        x=psp_df["psp"], y=psp_df["approval_rate"],
        mode="lines+markers+text", name="Approval %",
        line=dict(color="#f6c90e", width=2),
        marker=dict(size=9),
        text=[f"{v:.1f}%" for v in psp_df["approval_rate"]],
        textposition="top center", textfont=dict(color="#f6c90e", size=11)
    ), secondary_y=True)
    fig_psp.update_yaxes(title_text="Transactions", secondary_y=False, gridcolor="#1e2130", color="#8892b0")
    fig_psp.update_yaxes(title_text="Approval Rate (%)", secondary_y=True, range=[0,110], color="#f6c90e")
    fig_psp.update_layout(barmode="group", **CHART_LAYOUT, height=380, title="PSP Performance")
    st.plotly_chart(fig_psp, use_container_width=True)

    # Method breakdown
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='section-header'>Method-wise Attempts</div>", unsafe_allow_html=True)
        meth_df = df.groupby("method").agg(
            attempts=("is_success","count"),
            successes=("is_success","sum")
        ).reset_index()
        meth_df["approval_rate"] = meth_df["successes"] / meth_df["attempts"] * 100
        meth_df = meth_df.sort_values("attempts", ascending=False)
        fig_meth = px.bar(
            meth_df, x="attempts", y="method", orientation="h",
            color="approval_rate", color_continuous_scale=["#ff6b6b","#f6c90e","#64ffda"],
            labels={"attempts":"Attempts","method":"Method","approval_rate":"Approval %"},
            text="attempts", title="Method Breakdown"
        )
        fig_meth.update_traces(textposition="outside")
        fig_meth = styled_fig(fig_meth)
        fig_meth.update_layout(height=320)
        st.plotly_chart(fig_meth, use_container_width=True)

    with col_b:
        st.markdown("<div class='section-header'>Volume Share by PSP</div>", unsafe_allow_html=True)
        vol_df = df[df["is_success"]].groupby("psp")["amount_usd"].sum().reset_index()
        vol_df.columns = ["psp","volume"]
        fig_pie = px.pie(
            vol_df, values="volume", names="psp",
            color_discrete_sequence=COLORS, hole=0.45, title="Successful Volume by PSP"
        )
        fig_pie = styled_fig(fig_pie)
        fig_pie.update_traces(textfont_color="white", textfont_size=11)
        fig_pie.update_layout(height=320)
        st.plotly_chart(fig_pie, use_container_width=True)

    # Status distribution per PSP
    st.markdown("<div class='section-header'>Transaction Status Distribution</div>", unsafe_allow_html=True)
    status_df = df.groupby(["source","is_success"]).size().reset_index(name="count")
    status_df["status_label"] = status_df["is_success"].map({True:"Success", False:"Failed/Other"})
    fig_status = px.bar(
        status_df, x="source", y="count", color="status_label",
        color_discrete_map={"Success":"#64ffda","Failed/Other":"#ff6b6b"},
        barmode="stack", title="Transaction Status by PSP Source"
    )
    fig_status = styled_fig(fig_status)
    fig_status.update_layout(height=340)
    st.plotly_chart(fig_status, use_container_width=True)


# ── TAB 2: COUNTRY ANALYSIS ───────────────────────────────────────────────────
with tab2:
    st.markdown("<div class='section-header'>Country-wise Performance</div>", unsafe_allow_html=True)

    country_df = df[df["country"].isin(all_countries)].groupby("country").agg(
        attempts=("is_success","count"),
        successes=("is_success","sum"),
        volume=("amount_usd", lambda x: x[df.loc[x.index,"is_success"]].sum())
    ).reset_index()
    country_df["approval_rate"] = country_df["successes"] / country_df["attempts"] * 100
    country_df = country_df.sort_values("attempts", ascending=False)

    top_n = st.slider("Show top N countries", 5, 30, 15)
    top_countries = country_df.head(top_n)

    col1, col2 = st.columns(2)
    with col1:
        fig_c1 = px.bar(
            top_countries, x="country", y="attempts",
            color="approval_rate",
            color_continuous_scale=["#ff6b6b","#f6c90e","#64ffda"],
            title=f"Top {top_n} Countries by Attempts",
            labels={"attempts":"Attempts","approval_rate":"Approval %"}
        )
        fig_c1 = styled_fig(fig_c1)
        fig_c1.update_layout(height=380)
        st.plotly_chart(fig_c1, use_container_width=True)

    with col2:
        fig_c2 = px.scatter(
            top_countries, x="attempts", y="approval_rate",
            size="volume", color="country",
            color_discrete_sequence=COLORS,
            hover_name="country", title="Attempts vs Approval Rate (bubble = volume)",
            labels={"attempts":"Attempts","approval_rate":"Approval Rate (%)","volume":"Volume USD"}
        )
        fig_c2 = styled_fig(fig_c2)
        fig_c2.add_hline(y=70, line_dash="dash", line_color="#f6c90e", annotation_text="70% benchmark")
        fig_c2.update_layout(height=380)
        st.plotly_chart(fig_c2, use_container_width=True)

    # Map
    st.markdown("<div class='section-header'>Global Approval Rate Map</div>", unsafe_allow_html=True)
    fig_map = px.choropleth(
        country_df, locations="country", locationmode="ISO-3166-1-alpha-2",
        color="approval_rate",
        color_continuous_scale=["#ff6b6b","#f6c90e","#64ffda"],
        range_color=[0,100],
        hover_data={"attempts":True,"successes":True,"volume":":.0f"},
        title="Approval Rate by Country (%)"
    )
    fig_map.update_layout(**CHART_LAYOUT, height=420, geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False))
    st.plotly_chart(fig_map, use_container_width=True)

    # Country table
    st.markdown("<div class='section-header'>Country Summary Table</div>", unsafe_allow_html=True)
    display_df = country_df.copy()
    display_df["approval_rate"] = display_df["approval_rate"].round(1).astype(str) + "%"
    display_df["volume"] = display_df["volume"].round(0).map("${:,.0f}".format)
    display_df.columns = ["Country","Attempts","Successes","Volume (USD)","Approval Rate"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ── TAB 3: PSP & MID ANALYSIS ─────────────────────────────────────────────────
with tab3:
    st.markdown("<div class='section-header'>PSP-wise Approval Rate</div>", unsafe_allow_html=True)

    psp_perf = df.groupby("psp").agg(
        attempts=("is_success","count"),
        successes=("is_success","sum"),
        volume=("amount_usd", lambda x: x[df.loc[x.index,"is_success"]].sum())
    ).reset_index()
    psp_perf["approval_rate"] = psp_perf["successes"] / psp_perf["attempts"] * 100
    psp_perf["fail_rate"] = 100 - psp_perf["approval_rate"]

    col1, col2 = st.columns(2)
    with col1:
        fig_psp2 = go.Figure(go.Bar(
            x=psp_perf["psp"], y=psp_perf["approval_rate"],
            marker=dict(color=psp_perf["approval_rate"],
                        colorscale=[[0,"#ff6b6b"],[0.5,"#f6c90e"],[1,"#64ffda"]],
                        showscale=True),
            text=[f"{v:.1f}%" for v in psp_perf["approval_rate"]],
            textposition="outside"
        ))
        fig_psp2.update_layout(title="Approval Rate by PSP", **CHART_LAYOUT, height=360,
                               yaxis=dict(range=[0,110], gridcolor="#1e2130", color="#8892b0"),
                               xaxis=dict(gridcolor="#1e2130", color="#8892b0"))
        st.plotly_chart(fig_psp2, use_container_width=True)

    with col2:
        fig_vol2 = px.bar(
            psp_perf, x="psp", y="volume", color="psp",
            color_discrete_sequence=COLORS,
            title="Successful Volume by PSP (USD)",
            labels={"volume":"Volume USD","psp":"PSP"}
        )
        fig_vol2 = styled_fig(fig_vol2)
        fig_vol2.update_layout(height=360, showlegend=False)
        st.plotly_chart(fig_vol2, use_container_width=True)

    # MID-wise analysis
    st.markdown("<div class='section-header'>MID-wise Approval Rate</div>", unsafe_allow_html=True)

    mid_df = df.groupby(["psp","mid"]).agg(
        attempts=("is_success","count"),
        successes=("is_success","sum"),
        volume=("amount_usd", lambda x: x[df.loc[x.index,"is_success"]].sum())
    ).reset_index()
    mid_df["approval_rate"] = mid_df["successes"] / mid_df["attempts"] * 100
    mid_df = mid_df.sort_values("approval_rate", ascending=False)

    fig_mid = px.bar(
        mid_df, x="mid", y="approval_rate",
        color="psp", color_discrete_sequence=COLORS,
        title="Approval Rate by MID",
        text=mid_df["approval_rate"].round(1).astype(str) + "%",
        labels={"approval_rate":"Approval Rate (%)","mid":"MID","psp":"PSP"}
    )
    fig_mid.update_traces(textposition="outside")
    fig_mid = styled_fig(fig_mid)
    fig_mid.update_layout(height=420, xaxis_tickangle=-35,
                          yaxis=dict(range=[0,115]))
    st.plotly_chart(fig_mid, use_container_width=True)

    # MID detail table
    st.markdown("<div class='section-header'>MID Summary Table</div>", unsafe_allow_html=True)
    mid_display = mid_df.copy()
    mid_display["approval_rate"] = mid_display["approval_rate"].round(1).astype(str) + "%"
    mid_display["volume"] = mid_display["volume"].round(0).map("${:,.0f}".format)
    mid_display.columns = ["PSP","MID","Attempts","Successes","Volume (USD)","Approval Rate"]
    st.dataframe(mid_display, use_container_width=True, hide_index=True)

    # BridgerPay specific: MID x Country heatmap
    st.markdown("<div class='section-header'>BridgerPay: MID × Country Heatmap (Approval %)</div>", unsafe_allow_html=True)
    bp_sub = df[(df["source"]=="BridgerPay") & (df["country"].isin(all_countries))]
    if len(bp_sub) > 0:
        heat_df = bp_sub.groupby(["mid","country"]).agg(
            attempts=("is_success","count"),
            successes=("is_success","sum")
        ).reset_index()
        heat_df = heat_df[heat_df["attempts"] >= 5]
        heat_df["approval_rate"] = heat_df["successes"] / heat_df["attempts"] * 100
        top_mids_bp = heat_df.groupby("mid")["attempts"].sum().nlargest(10).index
        top_ctry_bp = heat_df.groupby("country")["attempts"].sum().nlargest(15).index
        heat_df = heat_df[heat_df["mid"].isin(top_mids_bp) & heat_df["country"].isin(top_ctry_bp)]
        pivot = heat_df.pivot_table(index="mid", columns="country", values="approval_rate", aggfunc="mean")
        fig_heat = px.imshow(
            pivot, color_continuous_scale=["#ff6b6b","#f6c90e","#64ffda"],
            range_color=[0,100], aspect="auto",
            title="Approval Rate (%) — BridgerPay MID × Country"
        )
        fig_heat.update_layout(**CHART_LAYOUT, height=400)
        st.plotly_chart(fig_heat, use_container_width=True)


# ── TAB 4: INSIGHTS ───────────────────────────────────────────────────────────
with tab4:
    st.markdown("<div class='section-header'>🔍 Automated Insights</div>", unsafe_allow_html=True)

    # Compute insights dynamically
    psp_ar = df.groupby("psp").agg(attempts=("is_success","count"), successes=("is_success","sum")).reset_index()
    psp_ar["ar"] = psp_ar["successes"] / psp_ar["attempts"] * 100

    best_psp = psp_ar.loc[psp_ar["ar"].idxmax()]
    worst_psp = psp_ar.loc[psp_ar["ar"].idxmin()]

    country_ar = df[df["country"].isin(all_countries)].groupby("country").agg(
        attempts=("is_success","count"), successes=("is_success","sum")
    ).reset_index()
    country_ar["ar"] = country_ar["successes"] / country_ar["attempts"] * 100
    country_ar = country_ar[country_ar["attempts"] >= 20]

    if len(country_ar) > 0:
        best_country  = country_ar.loc[country_ar["ar"].idxmax()]
        worst_country = country_ar.loc[country_ar["ar"].idxmin()]
        high_vol_low_ar = country_ar[(country_ar["attempts"] > country_ar["attempts"].quantile(0.6)) &
                                      (country_ar["ar"] < 50)]
    else:
        best_country = worst_country = high_vol_low_ar = None

    mid_ar = df.groupby("mid").agg(attempts=("is_success","count"), successes=("is_success","sum")).reset_index()
    mid_ar["ar"] = mid_ar["successes"] / mid_ar["attempts"] * 100
    mid_ar = mid_ar[mid_ar["attempts"] >= 10]

    crypto_df = df[df["method"]=="Crypto"]
    crypto_ar = crypto_df["is_success"].mean() * 100 if len(crypto_df) else 0
    card_df = df[df["method"]=="credit_card"]
    card_ar  = card_df["is_success"].mean() * 100 if len(card_df) else 0

    # Overall health
    st.markdown("#### 🏥 Overall Health")
    col_i1, col_i2 = st.columns(2)

    with col_i1:
        box_class = "good-box" if approval >= 60 else "alert-box"
        st.markdown(f"""<div class='{box_class}'>
            <b style='color:#ccd6f6;'>Overall Approval Rate: {approval:.1f}%</b>
            <div class='insight-text'>
            Across {total:,} total attempts, {success:,} were successful generating 
            ${total_vol:,.0f} in volume. {"Healthy rate above 60%." if approval>=60 else "⚠️ Below 60% — needs attention."}
            </div></div>""", unsafe_allow_html=True)

        st.markdown(f"""<div class='insight-box'>
            <b style='color:#ccd6f6;'>🏆 Best Performing PSP: {best_psp['psp']}</b>
            <div class='insight-text'>
            {best_psp['psp']} leads with a <b>{best_psp['ar']:.1f}%</b> approval rate 
            across {int(best_psp['attempts']):,} attempts.
            </div></div>""", unsafe_allow_html=True)

        st.markdown(f"""<div class='alert-box'>
            <b style='color:#ccd6f6;'>⚠️ Lowest Performing PSP: {worst_psp['psp']}</b>
            <div class='insight-text'>
            {worst_psp['psp']} has only a <b>{worst_psp['ar']:.1f}%</b> approval rate. 
            Investigate failure reasons and consider routing optimisation or escalation with the PSP.
            </div></div>""", unsafe_allow_html=True)

    with col_i2:
        if best_country is not None:
            st.markdown(f"""<div class='good-box'>
                <b style='color:#ccd6f6;'>🌟 Best Country: {best_country['country']}</b>
                <div class='insight-text'>
                {best_country['country']} achieves <b>{best_country['ar']:.1f}%</b> approval 
                on {int(best_country['attempts']):,} attempts. Consider increasing routing volume here.
                </div></div>""", unsafe_allow_html=True)

            st.markdown(f"""<div class='alert-box'>
                <b style='color:#ccd6f6;'>🚨 Weakest Country: {worst_country['country']}</b>
                <div class='insight-text'>
                {worst_country['country']} approval is only <b>{worst_country['ar']:.1f}%</b>. 
                Check if specific PSPs or MIDs serve this country poorly. 
                May need a localised payment method.
                </div></div>""", unsafe_allow_html=True)

        if len(high_vol_low_ar) > 0:
            countries_str = ", ".join(high_vol_low_ar["country"].tolist()[:5])
            st.markdown(f"""<div class='alert-box'>
                <b style='color:#ccd6f6;'>📉 High Volume, Low Approval Countries</b>
                <div class='insight-text'>
                <b>{countries_str}</b> have high transaction volumes but below 50% approval. 
                These markets represent significant revenue leakage — prioritise routing improvement.
                </div></div>""", unsafe_allow_html=True)

    st.markdown("#### 💡 Strategic Recommendations")

    insights = [
        ("🔁 BridgerPay Retry Impact",
         f"BridgerPay had {df_all[df_all['source']=='BridgerPay'].shape[0]:,} raw attempts but only "
         f"{df[df['source']=='BridgerPay'].shape[0]:,} unique orders after deduplication. "
         f"The retry mechanism is active — monitor retry rates to ensure they don't inflate cost without improving approval."),

        ("🪙 Crypto PSPs — No Country Data",
         "Coinsbuy and Confirmo lack country-level data. Consider requesting country attribution from these providers "
         "to enable proper geographic performance analysis and compliance monitoring."),

        ("📲 Wallet Payments (Zen Pay)",
         f"Apple Pay & Google Pay via Zen Pay show a combined approval rate of "
         f"{df[df['source']=='Zen Pay']['is_success'].mean()*100:.1f}%. "
         "Wallet payments typically have higher approval due to tokenisation — "
         "consider expanding wallet options across more PSPs."),

        ("💱 PayProcc Multi-currency Risk",
         "PayProcc processes transactions in 10+ currencies, with USD conversion via Applied Amount. "
         "FX rate fluctuations between transaction initiation and processing can cause value discrepancy. "
         "Ensure real-time FX rates are applied and review KES, PKR, PHP volumes for rate exposure."),

        ("🏦 MID Diversification",
         f"BridgerPay alone has {df_all[df_all['source']=='BridgerPay']['mid'].nunique()} MIDs active. "
         "A single MID shutdown can significantly disrupt flow. Ensure each country/volume segment has "
         "at least 2 active MIDs for redundancy."),

        ("🌍 Localisation Opportunity",
         "Markets like Nigeria (NG), Kenya (KE), Pakistan (PK) appear prominently. "
         "These markets often perform better with local payment rails (M-Pesa, bank transfers) "
         "rather than card-based PSPs — evaluate adding a local payment method PSP."),

        ("📊 Approval Rate Benchmark",
         f"Industry benchmark for online payments is typically 70–85%. "
         f"Current overall rate is {approval:.1f}%. "
         f"{'Above 70% — maintain and optimise.' if approval>=70 else 'Below 70% — immediate PSP routing review recommended.'}"),

        ("⚡ Pending / Waiting Transactions",
         "PayProcc has 'waiting' status transactions and BridgerPay has 'pending'/'in_process' entries. "
         "These require follow-up — stale pending transactions should be resolved within 24–48 hours "
         "to avoid customer disputes and settlement delays."),
    ]

    for i, (title, text) in enumerate(insights):
        box_class = "alert-box" if any(w in title for w in ["Risk","⚠️","📉","🚨"]) else "insight-box"
        st.markdown(f"""<div class='{box_class}'>
            <b style='color:#ccd6f6;'>{title}</b>
            <div class='insight-text'>{text}</div>
        </div>""", unsafe_allow_html=True)

    # Method approval comparison
    st.markdown("#### 📊 Method Approval Rate Comparison")
    meth_ar = df.groupby("method").agg(
        attempts=("is_success","count"), successes=("is_success","sum")
    ).reset_index()
    meth_ar["ar"] = meth_ar["successes"] / meth_ar["attempts"] * 100
    fig_m = px.bar(
        meth_ar.sort_values("ar", ascending=False), x="method", y="ar",
        color="ar", color_continuous_scale=["#ff6b6b","#f6c90e","#64ffda"],
        text=meth_ar.sort_values("ar",ascending=False)["ar"].round(1).astype(str)+"%",
        title="Approval Rate by Payment Method",
        labels={"ar":"Approval Rate (%)","method":"Method"}
    )
    fig_m.update_traces(textposition="outside")
    fig_m = styled_fig(fig_m)
    fig_m.add_hline(y=70, line_dash="dash", line_color="#f6c90e", annotation_text="70% industry benchmark")
    fig_m.update_layout(height=360, yaxis=dict(range=[0,115]))
    st.plotly_chart(fig_m, use_container_width=True)

st.markdown("---")
st.markdown("<p style='color:#4a5568;text-align:center;font-size:12px;'>FundedNext Payment Analytics · Built with Streamlit & Plotly</p>", unsafe_allow_html=True)
