# 🛡️ Singapore Insurance Strategy Dashboard
### Stochastic Actuarial Modeling: BTID vs. Whole Life Plans

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge.svg)](https://sg-insurance-model.streamlit.app/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **"At what level of human error does a 'mathematically superior' strategy fail?"**

This project is a high-fidelity actuarial simulation engine designed to solve the age-old "Buy Term, Invest the Difference" (BTID) vs. "Whole Life" (WL) debate. Unlike standard deterministic calculators, this dashboard incorporates **stochastic risk**, **Singapore-specific mortality data**, and **behavioral leakage**.

---

## 🚀 Quick Links
- **[Live Interactive Dashboard](https://sg-insurance-model.streamlit.app/)**

---

## 🧠 The Problem: Math vs. Reality
Most financial advice assumes investors are robots who reinvest every cent saved for 40 years. This model introduces the **"Discipline Coefficient"** to stress-test these assumptions against reality.

### Key Features:
* **Actuarial Rigor:** Uses the **S0408 Singapore Mortality Tables** to model age-specific death/TPD probabilities ($q_x$).
* **Behavioral Stress Testing:** Adjust "discipline" levels to visualize capital leakage and forced savings benefits.
* **Monte Carlo Simulations:** Evaluates sequence-of-returns risk and tail-end actuarial events.

---

## 🛠️ The Three-Act Simulation

### Act 1: The Deterministic Baseline
A standard financial projection comparing Surrender Values and Death Benefits. It calculates the **'Strategy Frontier'**—the exact age where BTID mathematically overtakes WL based on specified hurdle rates.

### Act 2: Behavioral Stress Testing
Introduces a "Discipline Coefficient." 
* **Insight:** If reinvestment discipline drops below ~60%, the "forced savings" nature of Whole Life often outperforms BTID despite lower theoretical IRRs.

### Act 3: Stochastic Reality
A Monte Carlo engine that models:
1. **Actuarial Risk:** Probabilistic death/TPD events triggered monthly.
2. **Market Volatility:** Simulating non-linear returns to show the range of BTID outcomes.

---

## 💻 Technical Implementation

### Tech Stack
* **Backend:** Python (Pandas, NumPy for vectorized cashflow projections).
* **Frontend:** Streamlit for reactive state management.
* **Visualization:** Plotly for interactive, zoomable financial time-series.

### Code Highlight: Modeling Discipline Leakage
The model accounts for "lifestyle creep" or missed investment months by calculating the realized accumulation after leakage:

```python
import numpy_financial as npf

def calculate_btid_accumulation(savings, discipline_rate, market_return, months):
    # realized_investment: Capital that actually reaches the brokerage
    realized_investment = savings * discipline_rate
    
    # Projecting the portfolio using the realized capital
    # Formula: FV = Pmt * (((1 + r)^n - 1) / r)
    portfolio_value = npf.fv(rate=market_return/12, nper=months, pmt=-realized_investment, pv=0)
    return portfolio_value
```