import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from model import DeterministicModel

st.set_page_config(layout="wide", page_title="Model Debugger")

st.title("🕵️‍♂️ The Logic Debugger")
st.markdown("""
**Goal:** Inspect ONE specific scenario to see why the Frontier Graph calculates a specific 'Crossover Age'.
This allows you to see the exact moment 'Buy Term' overtakes 'Whole Life' for a given return rate.
""")

# --- 1. FIXED INPUTS (Standardize so we don't get lost) ---
with st.sidebar:
    st.header("1. Fixed Profile")
    st.info("These matches your screenshots to keep things consistent.")
    current_age = 30
    death_age = 85
    prem_wl = 6000
    prem_term = 800
    sa = 300000
    pay_term = 20
    wl_par = 0.0375 # 3.75% Fixed WL Growth
    
    st.write(f"**WL Premium:** ${prem_wl}")
    st.write(f"**Term Premium:** ${prem_term}")
    st.write(f"**WL Par Return:** {wl_par*100}%")

# --- 2. THE VARIABLE (This is what the Frontier Graph iterates over) ---
st.subheader("2. The Variable")
test_return = st.slider("👇 If the Market Return is exactly...", 1.0, 10.0, 4.0, 0.1, format="%.1f%%") / 100

# --- 3. RUN THE SIMULATION ---
model = DeterministicModel(current_age, death_age, sa, prem_wl, prem_term, wl_par, pay_term)
df = model.calculate_simulation(test_return, 0.0) # 0% discount rate to see raw cash

# --- 4. FIND THE CROSSOVER (The "Brain" of the Frontier Graph) ---
# Filter: Only look after Age 35 (ignore early noise)
start_check_age = current_age + 5
valid_zone = df[df['Age'] > start_check_age]
winning_rows = valid_zone[valid_zone['WL_Nominal'] > valid_zone['BTID_Nominal']]

if not winning_rows.empty:
    crossover_age = winning_rows['Age'].iloc[0]
    status = "✅ BTID WINS"
    status_color = "green"
    msg = f"At {test_return*100:.1f}% return, BTID overtakes Whole Life at **Age {crossover_age}**."
else:
    crossover_age = 100
    status = "❌ WL WINS"
    status_color = "red"
    msg = f"At {test_return*100:.1f}% return, BTID **NEVER** catches up."

# --- 5. VISUALIZE THE RESULT ---
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(f"### Result: :{status_color}[{status}]")
    st.write(msg)
    
    # Plot
    fig = px.line(df, x="Age", y=["BTID_Nominal", "WL_Nominal"], 
                  color_discrete_map={"BTID_Nominal": "green", "WL_Nominal": "blue"},
                  title=f"Scenario: {test_return*100:.1f}% Market Return")
    
    # Highlight the Crossover
    if crossover_age < 100:
        fig.add_vline(x=crossover_age, line_dash="dash", line_color="red", 
                      annotation_text=f"Crossover ({crossover_age})")
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### 🔍 The Data Under the Hood")
    st.markdown("This is the exact data table the algorithm scans.")
    
    # Show data around the crossover point
    if crossover_age < 100:
        radius = 3
        # Find index of crossover
        idx = df[df['Age'] == crossover_age].index[0]
        start = max(0, idx - radius)
        end = min(len(df), idx + radius + 1)
        
        subset = df.iloc[start:end][['Age', 'BTID_Nominal', 'WL_Nominal']].copy()
        subset['Diff'] = subset['BTID_Nominal'] - subset['WL_Nominal']
        
        # Format for readability
        st.dataframe(subset.style.format("{:,.0f}").apply(
            lambda x: ['background: #d4edda' if (x.name == idx) else '' for i in x], axis=1
        ))
    else:
        st.write("No crossover found. Showing end of simulation:")
        st.dataframe(df.tail(5)[['Age', 'BTID_Nominal', 'WL_Nominal']])