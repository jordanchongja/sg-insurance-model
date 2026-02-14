import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from model import DeterministicModel

# --- PAGE CONFIG ---
st.set_page_config(page_title="SG Insurance Model", layout="wide")

# Tip for Light Mode
st.sidebar.info("💡 **Tip:** If graphs are dark, go to Settings (top right) > Theme > 'Light'.")

st.title("🛡️ Life Insurance Decision Model")

# ==========================================
# 1. LAYOUT SETUP
# ==========================================
context_container = st.container()

# ==========================================
# 2. MAIN BODY INPUTS (Step 2: Edit Assumptions)
# ==========================================
st.markdown("### Step 2: Edit Assumptions")

with st.container(border=True):
    # ROW 1: CORE PROFILE & MARKET
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**👤 Personal Profile**")
        current_age = st.number_input("Current Age", 20, 60, 30)
        death_age = st.number_input("Projection Age", 60, 100, 85, help="How long do you expect to live?")
        
    with col2:
        st.markdown("**🔴 Term Insurance + Invest the Rest**")
        base_prem_term = st.number_input("Term Premium ($/yr)", value=800, step=50)
        sa = st.number_input("Sum Assured ($)", value=300000, step=10000)
        term_age = st.number_input("Term Expires At Age", 60, 99, 70)

    with col3:
        st.markdown("**🔵 Whole Life Insurance**")
        base_prem_wl = st.number_input("WL Premium ($/yr)", value=6000, step=100)
        pay_term = st.number_input("Payment Term (Yrs)", value=20, help="How many years do you pay premiums?")

    with col4:
        st.markdown("**📈 Market Assumptions**")
        r_invest = st.number_input("Exp. Return (%)", 0.0, 15.0, 5.0, 0.5, help="Annual return on your investments.") / 100
        r_disc = st.number_input("Risk-Free Rate (%)", 0.0, 8.0, 3.0, 0.1, help="Used for Present Value calculations.") / 100

    st.divider()
    
    # ROW 2: RIDERS & MULTIPLIERS
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.markdown("**🔵 WL Multiplier**")
        mult_factor = st.selectbox("Multiplier Factor", [1.0, 2.0, 3.0, 4.0, 5.0], index=2) 
        mult_age = st.number_input("Multiplier Drop-off Age", 60, 85, 70)
        
    with c2:
        st.markdown("**🛡️ Rider Costs (Add-ons)**")
        cost_ci_wl = st.number_input("WL Rider Cost ($/yr)", value=0)
        cost_ci_term = st.number_input("Term Rider Cost ($/yr)", value=0)

    with c3:
        st.info("💡 **Cost of Insurance Drag:** Adding riders increases premiums. This reduces your 'Investible Difference,' meaning that money never gets the chance to grow.")

# --- Derived Variables ---
prem_wl_total = base_prem_wl + cost_ci_wl
prem_term_total = base_prem_term + cost_ci_term
stop_age = current_age + pay_term
monthly_save = (prem_wl_total - prem_term_total) / 12
annual_save = prem_wl_total - prem_term_total

# ==========================================
# 3. FILL THE TOP CONTAINER (Step 1)
# ==========================================
with context_container:
    st.markdown("### Step 1: Context of Insurance Products and Assumptions")
    
    with st.expander("📚 Introduction to Insurance Product Comparison", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🔴 Option A: Term Insurance + Invest the Rest")
            st.markdown(f"""
            * **Strategy:** Buy Term (expires Age {term_age}) and invest savings (**${annual_save:,.0f}/yr**).
            * **Investments:** You control the risk. High volatility, no guarantees.
            * **Claims:** If you die, family gets **${sa:,.0f}** (Insurance) + **Portfolio Value**.
            """)
        with c2:
            st.subheader("🔵 Option B: Whole Life Insurance")
            st.markdown(f"""
            * **Strategy:** Bundled product. You pay **${prem_wl_total:,.0f}/yr** to the insurer.
            * **Investments:** Insurer manages the fund. Returns are "Smoothed."
            * **Claims:** Family gets **Higher of** ({mult_factor}x SA) OR (SA + Bonuses).
            """)

    st.markdown("##### 📋 Assumptions for your Life and Insurance Products")
    profile_data = {
        "Scenario Variable": ["**1. Lifespan**", "**2. When do Premiums End**", "**3. Investment Power**", "**4. Legacy Goal**"],
        "Your Input Details": [
            f"Start at **Age {current_age}** → End at **Age {death_age}**",
            f"Premiums STOP at **Age {stop_age}**.",
            f"You have **${monthly_save:,.0f}/month** extra to invest if you choose Term.",
            f"WL: **{mult_factor}x** until Age {mult_age}. Term: **${sa:,.0f}** until Age {term_age}."
        ],
        "Impact on Model": [
            "Defines the simulation duration.",
            "**Crucial:** WL user pays $0. Term user pays premiums from fund if active.",
            "This is the 'fuel' for the Buy Term strategy.",
            "The baseline for the death benefit comparison."
        ]
    }
    st.table(pd.DataFrame(profile_data).set_index("Scenario Variable"))
    st.divider()

# ==========================================
# 4. THE 3-ACT NARRATIVE (Step 3)
# ==========================================
st.markdown("### Step 3: Analyze the Strategy")
act1, act2, act3 = st.tabs(["Act 1: The Deterministic Math", "Act 2: The Behavior", "Act 3: The Reality"])

with act1:
    st.caption("Assumes you are a 'Robot' who invests 100% of the savings perfectly with no withdrawals.")
    view_mode = st.radio("Graph View Mode", ["Nominal Value (Cash)", "Present Value (Today's $)"], index=1, horizontal=True)

    # Instantiate Model
    model = DeterministicModel(
        current_age, death_age, sa, prem_wl_total, prem_term_total, 0.0375, pay_term,
        multiplier_factor=mult_factor, multiplier_age=mult_age, term_expiry_age=term_age
    )
    df = model.calculate_simulation(r_invest, r_disc)

    graph_tab1, graph_tab2 = st.tabs(["📊 Financial Analysis", "🏁 The 'Winning' Frontier"])

    with graph_tab1:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("1. Liquidity (If you live)")
            y_btid = "BTID_PV" if "Present" in view_mode else "BTID_Nominal"
            y_wl = "WL_PV" if "Present" in view_mode else "WL_Nominal"
            
            fig1 = px.line(df, x="Age", y=[y_btid, y_wl], 
                           labels={"value": f"Wealth ({view_mode})", "variable": "Strategy"},
                           color_discrete_map={y_btid: "#2ca02c", y_wl: "#1f77b4"}) 
            fig1.add_vline(x=stop_age, line_dash="dash", line_color="red", annotation_text="Stop Pay")
            fig1.update_layout(legend_title_text='')
            st.plotly_chart(fig1, use_container_width=True)

        with col_right:
            st.subheader("2. Legacy (If you die)")
            if "Present" in view_mode: st.info("Note: Death Benefit shown in Nominal terms for clarity.")
            
            y_btid_d = "BTID_Death"
            y_wl_d = "WL_Death"

            fig2 = px.line(df, x="Age", y=[y_btid_d, y_wl_d], 
                           labels={"value": "Payout ($)", "variable": "Strategy"},
                           color_discrete_map={y_btid_d: "#98df8a", y_wl_d: "#aec7e8"}) 
            
            # Dynamic Lines & Overlap Fix
            fig2.add_vline(x=term_age, line_dash="dot", line_color="gray", 
                           annotation_text=f"Term Exp ({term_age})", annotation_position="top left")
            
            fig2.add_shape(type="line", x0=mult_age, y0=0, x1=mult_age, y1=1, xref="x", yref="paper",
                           line=dict(color="orange", width=1, dash="dot"))
            
            fig2.add_annotation(x=mult_age, y=0.9, text=f"Mult. Drops ({mult_age})", showarrow=False,
                                font=dict(color="orange"), xanchor="left", bgcolor="rgba(255, 255, 255, 0.7)")

            # UN-SHACKLED GROWTH ANNOTATION
            if death_age > term_age:
                fig2.add_annotation(
                    x=term_age + (death_age - term_age)/2,
                    y=df[df['Age'] == death_age][y_btid_d].iloc[0],
                    text="🚀 'Unshackled' Exponential Growth<br>(Pure Investments, No Stagnant Insurance)",
                    showarrow=True, arrowhead=1, ax=40, ay=-40, font=dict(size=10, color="green")
                )

            fig2.update_layout(legend_title_text='')
            st.plotly_chart(fig2, use_container_width=True)

    with graph_tab2:
        st.subheader("Strategy Frontier: How long does BTID stay ahead?")
        returns = np.arange(0.0, 0.101, 0.001) 
        crossover_ages = []
        
        my_bar = st.progress(0, text="Simulating scenarios...")
        for i, r in enumerate(returns):
            crossover_ages.append(model.get_crossover_age(r))
            if i % 10 == 0: my_bar.progress((i + 1) / len(returns))
        my_bar.empty()
        
        df_cross = pd.DataFrame({"Market Return (%)": returns * 100, "WL_Catchup_Age": crossover_ages})
        df_plot = df_cross[df_cross['WL_Catchup_Age'] < 100].copy()
        df_markers = df_plot[df_plot['Market Return (%)'].round(1) % 0.5 == 0]
        
        fig3 = px.line(df_plot, x="Market Return (%)", y="WL_Catchup_Age")
        fig3.add_trace(go.Scatter(x=df_markers['Market Return (%)'], y=df_markers['WL_Catchup_Age'],
                                  mode='markers', marker=dict(color=fig3.data[0].line.color, size=8), showlegend=False))
        
        fig3.add_hline(y=death_age, line_dash="dash", line_color="red", annotation_text="Your Death Age")
        fig3.update_yaxes(range=[30, 90], title="Age WL Finally Overtakes")
        st.plotly_chart(fig3, use_container_width=True)

with act2:
    st.header("Act 2: The Human Factor")
    st.warning("🚧 This module is under construction.")

with act3:
    st.header("Act 3: Structural Stress Tests")
    st.warning("🚧 This module is under construction.")