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
# 1. SIDEBAR INPUTS (Step 2: Edit Assumptions)
# ==========================================
with st.sidebar:
    st.header("Step 2: Edit Assumptions")
    
    # --- A. PERSONAL PROFILE ---
    with st.expander("👤 Personal Profile", expanded=True):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            current_age = st.number_input("Current Age", 20, 60, 30, step=1)
        with col_p2:
            gender = st.selectbox("Gender", ["Male", "Female"])
            
        death_age = st.number_input("Projection Age", 60, 100, 85, step=1, help="How long do you expect to live?")

    # --- B. TERM INSURANCE ---
    with st.expander("🔴 Term + Invest", expanded=True):
        base_prem_term = st.number_input("Term Premium ($/yr)", value=800, step=50)
        sa = st.number_input("Sum Assured ($)", value=300000, step=10000)
        term_age = st.number_input("Term Expires At Age", 60, 99, 70, step=1)
        cost_ci_term = st.number_input("Term Rider Cost ($/yr)", value=0, step=50)

    # --- C. WHOLE LIFE ---
    with st.expander("🔵 Whole Life", expanded=True):
        base_prem_wl = st.number_input("WL Premium ($/yr)", value=6000, step=100)
        pay_term = st.number_input("Payment Term (Yrs)", value=20, step=1)
        mult_factor = st.selectbox("Multiplier Factor", [1.0, 2.0, 3.0, 4.0, 5.0], index=2)
        mult_age = st.number_input("Multiplier Drop-off Age", 60, 85, 70, step=1)
        cost_ci_wl = st.number_input("WL Rider Cost ($/yr)", value=0, step=50)

    # --- D. MARKET ---
    with st.expander("📈 Market Assumptions", expanded=False):
        r_invest = st.number_input("Exp. Return (%)", 0.0, 15.0, 5.0, 0.5) / 100
        # NEW INPUT: Volatility for Act 3
        volatility = st.number_input("Market Volatility (%)", 0.0, 30.0, 12.0, 1.0, help="Standard Deviation. S&P500 is ~15%. Bonds are ~5%.") / 100
        r_disc = st.number_input("Risk-Free Rate (%)", 0.0, 8.0, 3.0, 0.1) / 100

    st.caption("💡 **Note:** Rider costs reduce your investible difference.")

# --- Derived Variables ---
prem_wl_total = base_prem_wl + cost_ci_wl
prem_term_total = base_prem_term + cost_ci_term
stop_age = current_age + pay_term
monthly_save = (prem_wl_total - prem_term_total) / 12
annual_save = prem_wl_total - prem_term_total

# ==========================================
# 2. MAIN BODY: CONTEXT (Step 1)
# ==========================================
st.markdown("### Step 1: Context & Architecture")

col1, col2 = st.columns([1, 1])

with col1:
    with st.expander("📚 Product Logic (Read Me)", expanded=True):
        st.markdown(f"""
        **🔴 Option A: Buy Term + Invest**
        * **Cost:** You pay **${prem_term_total:,.0f}/yr** for Insurance.
        * **Strategy:** Invest the savings (**${annual_save:,.0f}/yr**).
        * **Claims:** If you die, family gets **${sa:,.0f}** + Portfolio Value.
        
        **🔵 Option B: Whole Life**
        * **Cost:** Bundled product. You pay **${prem_wl_total:,.0f}/yr**.
        * **Claims:** Higher of ({mult_factor}x SA) OR (SA + Bonuses).
        """)

with col2:
    st.info(f"""
    **📋 Scenario Summary:**
    * **Life Plan:** Projecting from Age **{current_age}** to **{death_age}**.
    * **Save & Invest:** You have **${monthly_save:,.0f}/mth** extra to invest if you buy Term.
    * **Premiums Stop:** At Age **{stop_age}** (in {pay_term} years).
    * **Coverage:** WL is **{mult_factor}x** (Age {mult_age}); Term is **${sa:,.0f}** (Age {term_age}).
    """)

st.divider()

# ==========================================
# 3. THE 3-ACT NARRATIVE (Step 3)
# ==========================================
st.markdown("### Step 3: Analyze the Strategy")
act1, act2, act3 = st.tabs(["Act 1: The Deterministic Math", "Act 2: The Behavior", "Act 3: The Reality"])

# Instantiate Model
model = DeterministicModel(
    current_age, death_age, sa, prem_wl_total, prem_term_total, 0.0375, pay_term,
    multiplier_factor=mult_factor, multiplier_age=mult_age, term_expiry_age=term_age
)
df = model.calculate_simulation(r_invest, r_disc)

# --- ACT 1: DETERMINISTIC ---
with act1:
    st.caption("Assumes you are a 'Robot' who invests 100% of the savings perfectly with no withdrawals.")
    view_mode = st.radio("Graph View Mode", ["Nominal Value (Cash)", "Present Value (Today's $)"], index=1, horizontal=True)

    graph_tab1, graph_tab2 = st.tabs(["📊 Financial Analysis", "🏁 The 'Winning' Frontier"])

    with graph_tab1:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("1. Liquidity (Wealth)")
            y_btid = "BTID_PV" if "Present" in view_mode else "BTID_Nominal"
            y_wl = "WL_PV" if "Present" in view_mode else "WL_Nominal"
            
            fig1 = px.line(df, x="Age", y=[y_btid, y_wl], 
                           labels={"value": f"Wealth ({view_mode})", "variable": "Strategy"},
                           color_discrete_map={y_btid: "#2ca02c", y_wl: "#1f77b4"}) 
            fig1.add_vline(x=stop_age, line_dash="dash", line_color="red", annotation_text="Stop Pay")
            fig1.update_layout(legend_title_text='')
            st.plotly_chart(fig1, use_container_width=True)

        with col_right:
            st.subheader("2. Legacy & Critical Illness")
            st.caption("Also represents Max CI Payout during Multiplier years.")
            if "Present" in view_mode: st.info("Note: Nominal terms used for clarity.")
            
            y_btid_d = "BTID_Death"
            y_wl_d = "WL_Death"

            fig2 = px.line(df, x="Age", y=[y_btid_d, y_wl_d], 
                           labels={"value": "Payout ($)", "variable": "Strategy"},
                           color_discrete_map={y_btid_d: "#98df8a", y_wl_d: "#aec7e8"}) 
            
            fig2.add_vline(x=term_age, line_dash="dot", line_color="gray", annotation_text=f"Term Exp ({term_age})", annotation_position="top left")
            fig2.add_shape(type="line", x0=mult_age, y0=0, x1=mult_age, y1=1, xref="x", yref="paper", line=dict(color="orange", width=1, dash="dot"))
            fig2.add_annotation(x=mult_age, y=0.9, text=f"Mult. Drops ({mult_age})", showarrow=False, font=dict(color="orange"), xanchor="left", bgcolor="rgba(255, 255, 255, 0.7)")

            if death_age > term_age:
                val = df[df['Age'] == death_age][y_btid_d].iloc[0]
                fig2.add_annotation(x=term_age + (death_age - term_age)/2, y=val, text="🚀 'Unshackled' Growth", showarrow=True, arrowhead=1, ax=40, ay=-40, font=dict(size=10, color="green"))

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
        fig3.add_trace(go.Scatter(x=df_markers['Market Return (%)'], y=df_markers['WL_Catchup_Age'], mode='markers', marker=dict(color=fig3.data[0].line.color, size=8), showlegend=False))
        fig3.add_hline(y=death_age, line_dash="dash", line_color="red", annotation_text="Your Death Age")
        fig3.update_yaxes(range=[current_age, 100], title="Age WL Finally Overtakes")
        st.plotly_chart(fig3, use_container_width=True)


# --- ACT 2: BEHAVIOR & PROBABILITY ---
with act2:
    st.header("Act 2: The Human Factor")
    st.markdown("Act 1 assumes a perfect world. Act 2 looks at **Discipline** and **Risk Probability**.")
    
    # 1. DISCIPLINE
    st.subheader("1. The Discipline Stress Test")
    col_d1, col_d2 = st.columns([3, 1])
    
    with col_d1:
        discipline = st.slider("💰 Discipline Ratio: % of savings actually invested", 
                               min_value=0, max_value=100, value=100, step=10)
        
        human_savings_annual = annual_save * (discipline / 100)
        fake_wl_prem_for_human = prem_term_total + human_savings_annual
        
        model_human = DeterministicModel(
            current_age, death_age, sa, fake_wl_prem_for_human, prem_term_total, 0.0375, pay_term,
            multiplier_factor=mult_factor, multiplier_age=mult_age, term_expiry_age=term_age
        )
        df_human = model_human.calculate_simulation(r_invest, r_disc)
        
        fig_beh = go.Figure()
        fig_beh.add_trace(go.Scatter(x=df['Age'], y=df['BTID_Nominal'], name='Robot (100%)', line=dict(dash='dash', color='green')))
        fig_beh.add_trace(go.Scatter(x=df_human['Age'], y=df_human['BTID_Nominal'], name=f'You ({discipline}%)', fill='tonexty', line=dict(color='#d62728')))
        fig_beh.add_trace(go.Scatter(x=df['Age'], y=df['WL_Nominal'], name='Whole Life (Forced)', line=dict(color='blue')))
        fig_beh.update_layout(title="Wealth: Robot vs. Human", height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_beh, use_container_width=True)

    with col_d2:
        gap_65 = df[df['Age'] == 65]['BTID_Nominal'].iloc[0] - df_human[df_human['Age'] == 65]['BTID_Nominal'].iloc[0]
        st.metric("Wealth Lost (Age 65)", f"${gap_65:,.0f}", delta_color="inverse")
        
        wl_65 = df[df['Age'] == 65]['WL_Nominal'].iloc[0]
        human_65 = df_human[df_human['Age'] == 65]['BTID_Nominal'].iloc[0]
        if wl_65 > human_65:
            st.error("🚨 **Danger:** Whole Life WINS due to forced savings.")
        else:
            st.success("✅ **Safe:** Buy Term still wins.")

    st.divider()

    # 2. PROBABILITY
    st.subheader("2. Risk Reality & ROI")
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        st.markdown("**Probability of Claim (During Coverage)**")
        real_prob = DeterministicModel.calculate_cumulative_risk(current_age, term_age, gender)
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = real_prob,
            number = {'suffix': "%", 'valueformat': ".1f"}, 
            title = {'text': f"Chance of CI (Age {current_age}-{term_age})"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "orange"},
                'steps': [
                    {'range': [0, 15], 'color': "#d4edda"}, 
                    {'range': [15, 30], 'color': "#fff3cd"},
                    {'range': [30, 100], 'color': "#f8d7da"}],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 25}}
        ))
        fig_gauge.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.caption(f"Based on S0408DTPD {gender} Tables (loaded 1.3x for Critical Illness).")

    with col_p2:
        st.markdown("**The 'Break-Even' Metric**")
        total_term_cost = prem_term_total * (term_age - current_age)
        leverage = sa / total_term_cost if total_term_cost > 0 else 0
        
        m1, m2 = st.columns(2)
        m1.metric("Total Term Cost", f"${total_term_cost:,.0f}")
        m2.metric("Payout Leverage", f"{leverage:.1f}x")
        
        st.info(f"You pay **\${total_term_cost:,.0f}** over {term_age - current_age} years for **\${sa:,.0f}** coverage.")

# --- ACT 3: THE REALITY (STOCHASTIC LIFE EVENTS) ---
with act3:
    st.header("Act 3: Life Event Simulation (Monte Carlo)")
    st.markdown("""
    This simulation runs **1,000 distinct lifetimes**.
    It models your **Health** (getting sick multiple times) separate from your **Policy** (payout rules).
    """)
    
    col_mc1, col_mc2 = st.columns([1, 2])
    with col_mc1:
        # Multi-Pay Toggle
        enable_multi = st.checkbox("Enable Multi-Pay Mode?", value=False, 
                                  help="If checked, Whole Life allows multiple CI claims.")
        
        # NEW: Max Claims Input (Conditional)
        max_claims = 1
        if enable_multi:
            max_claims = st.number_input("Max Allowed CI Claims", min_value=2, max_value=5, value=2, step=1,
                                        help="Most Multi-Pay plans cap major claims at 2 or 3.")
    
    if st.button("🚀 Run 1,000 Lifetimes"):
        with st.spinner("Simulating lives..."):
            # Pass max_ci_claims to the model
            sim_results = model.run_stochastic_simulation(1000, gender, r_invest, r_disc, 
                                                          enable_multi_pay=enable_multi, 
                                                          max_ci_claims=max_claims)
            
            if not sim_results.empty:
                # 1. METRICS
                wins_btid = len(sim_results[sim_results['Diff'] > 0])
                win_rate = (wins_btid / 1000) * 100
                avg_diff = sim_results['Diff'].mean()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("BTID Win Rate", f"{win_rate:.1f}%")
                c2.metric("Avg. Net Benefit", f"${avg_diff:,.0f}")
                c3.metric("Simulated Lives", "1,000")
                
                # 2. HISTOGRAM
                fig_hist = px.histogram(
                    sim_results, 
                    x="Diff", 
                    nbins=50,
                    title="Distribution of Outcomes (Right = BTID Wins)",
                    labels={"Diff": "Net Present Value Difference ($)"},
                    color_discrete_sequence=['#2ca02c']
                )
                fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Breakeven")
                
                # Annotations for Clusters
                neg_out = sim_results[sim_results['Diff'] < 0]['Diff']
                pos_out = sim_results[sim_results['Diff'] > 0]['Diff']
                if not neg_out.empty:
                    fig_hist.add_annotation(x=neg_out.median(), y=10, text="Early/Multi Claim\n(WL Wins)", 
                                           showarrow=True, arrowhead=1, ax=0, ay=-40, font=dict(color="red"))
                if not pos_out.empty:
                    fig_hist.add_annotation(x=pos_out.median(), y=10, text="Long Life\n(Inv Wins)", 
                                           showarrow=True, arrowhead=1, ax=0, ay=-40, font=dict(color="green"))

                st.plotly_chart(fig_hist, use_container_width=True)
                
                # 3. MULTI-CLAIM ANALYSIS
                if enable_multi:
                    multi_claims = sim_results[sim_results['Event Chain'].str.count("CI") > 1]
                    if not multi_claims.empty:
                        count = len(multi_claims)
                        st.warning(f"⚠️ **Multi-Claim Reality:** In {count} simulations ({count/10}%), the user claimed CI {max_claims} times. WL creates significant value here.")
                        st.dataframe(multi_claims[['Event Chain', 'Final Age', 'Diff']].head(5))
                
                with st.expander("View Raw Simulation Data"):
                    st.dataframe(sim_results)
            else:
                st.error("Simulation failed. Check CSV files.")