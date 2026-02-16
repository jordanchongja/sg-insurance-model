import numpy as np
import pandas as pd
import streamlit as st

class DeterministicModel:
    def __init__(self, current_age, death_age, sa, prem_wl, prem_term, wl_par_return, payment_term, 
                 multiplier_factor=1.0, multiplier_age=70, term_expiry_age=70):
        self.current_age = int(current_age)
        self.death_age = int(death_age)
        self.sa = float(sa)
        self.prem_wl = float(prem_wl)
        self.prem_term = float(prem_term)
        self.wl_par_return = float(wl_par_return)
        self.payment_term = int(payment_term)
        self.multiplier_factor = float(multiplier_factor)
        self.multiplier_age = int(multiplier_age)
        self.term_expiry_age = int(term_expiry_age)

    # ... [Keep calculate_simulation (Act 1) and get_crossover_age (Frontier) here] ...
    # (Pasting essential Act 1 logic for completeness)
    def calculate_simulation(self, investment_return, discount_rate):
        duration = self.death_age - self.current_age + 1
        plot_ages = [self.current_age + i for i in range(duration + 1)]
        
        btid_fund_accum = [0]
        wl_sv_accum = [0]
        fund = 0
        wl_sv = 0
        prev_wl_sv = 0
        total_wl_paid = 0
        
        for t in range(1, duration + 1):
            age = self.current_age + t
            # BTID
            cf = 0
            if t <= self.payment_term: cf = self.prem_wl - self.prem_term
            elif age < self.term_expiry_age: cf = -self.prem_term
            fund = (fund + cf) * (1 + investment_return)
            if fund < 0: fund = 0
            btid_fund_accum.append(fund)
            
            # WL
            if t <= self.payment_term: total_wl_paid += self.prem_wl
            if t <= 2: wl_sv = 0
            elif t <= self.payment_term: 
                progress = (t - 2) / (self.payment_term - 2)
                wl_sv = total_wl_paid * progress * 0.85
            else: 
                wl_sv = prev_wl_sv * (1 + self.wl_par_return)
            prev_wl_sv = wl_sv
            wl_sv_accum.append(wl_sv)
            
        btid_death = []
        wl_death = []
        for i, age in enumerate(plot_ages):
            term_val = self.sa if age < self.term_expiry_age else 0
            btid_death.append(term_val + btid_fund_accum[i])
            mult = self.multiplier_factor if age < self.multiplier_age else 1.0
            wl_val = max(self.sa * mult, self.sa + wl_sv_accum[i])
            wl_death.append(wl_val)
            
        disc = (1 + discount_rate) ** -np.arange(len(plot_ages))
        return pd.DataFrame({
            "Age": plot_ages,
            "BTID_Nominal": btid_fund_accum, "WL_Nominal": wl_sv_accum,
            "BTID_Death": btid_death, "WL_Death": wl_death,
            "BTID_PV": np.array(btid_fund_accum) * disc, "WL_PV": np.array(wl_sv_accum) * disc
        })

    def get_crossover_age(self, investment_return):
        temp_model = DeterministicModel(
            self.current_age, 100, self.sa, self.prem_wl, self.prem_term, 
            self.wl_par_return, self.payment_term,
            self.multiplier_factor, self.multiplier_age, self.term_expiry_age
        )
        df = temp_model.calculate_simulation(investment_return, 0.0)
        subset = df[df['Age'] > (self.current_age + 5)]
        wins = subset[subset['WL_Nominal'] > subset['BTID_Nominal']]
        if wins.empty: return 100
        return wins['Age'].iloc[0]

    @staticmethod
    def calculate_cumulative_risk(current_age, target_age, gender):
        try:
            df_death = pd.read_csv("death_rates.csv") 
            df_ci = pd.read_csv("ci_rates.csv")       
            latest_year = df_death['year'].max()
            df_death = df_death[(df_death['year'] == latest_year) & (df_death['sex'] == gender)]
            ci_col = "S0408DTPD Male" if gender == "Male" else "S0408DTPD Female"
            cumulative_survival_prob = 1.0
            for age in range(current_age, target_age):
                try:
                    raw_dtpd = df_ci.loc[df_ci['Age Last'] == age, ci_col].values[0]
                    q_dtpd = raw_dtpd / 1000.0 
                    q_risk = q_dtpd * 1.3
                except:
                    q_risk = 0.05 
                cumulative_survival_prob *= (1 - q_risk)
            return (1 - cumulative_survival_prob) * 100
        except:
            return 0.0

    @st.cache_data
    def load_actuarial_tables():
        df_death = pd.read_csv("death_rates.csv")
        df_ci = pd.read_csv("ci_rates.csv")
        return df_death, df_ci

    def run_stochastic_simulation(self, n_sims, gender, r_inv, r_disc, enable_multi_pay=False, max_ci_claims=2):
        """
        Simulates lives with:
        1. Mortality Loading (Sick people die faster).
        2. Maximum Age Cap (Everyone dies at 100).
        3. Corrected Single vs Multi Pay logic.
        """
        try:
            df_death = pd.read_csv("death_rates.csv")
            df_ci = pd.read_csv("ci_rates.csv")
            latest_year = df_death['year'].max()
            death_rates = df_death[(df_death['year'] == latest_year) & (df_death['sex'] == gender)].set_index('age_x')['qx'].to_dict()
            
            ci_col = "S0408DTPD Male" if gender == "Male" else "S0408DTPD Female"
            ci_rates = (df_ci.set_index('Age Last')[ci_col] / 1000.0 * 1.3).to_dict()
        except:
            return pd.DataFrame() 

        results = []
        max_simulation_age = 100  # The hard stop
        
        limit_wl_claims = max_ci_claims if enable_multi_pay else 1
        limit_term_claims = 1 
        
        for _ in range(n_sims):
            age = self.current_age
            alive = True
            
            # State Tracking
            wl_claims_count = 0
            term_claims_count = 0
            health_ci_count = 0  # NEW: Tracks physical health separate from policy claims
            
            # Funds
            btid_fund = 0.0
            wl_cash_received = 0.0
            
            # Status Flags
            wl_active = True
            term_active = True
            
            event_log = []
            
            while alive and age <= max_simulation_age:
                year_idx = age - self.current_age + 1
                
                # --- 1. MORTALITY & HEALTH DYNAMICS ---
                base_q_d = death_rates.get(age, 0.05)
                base_q_ci = ci_rates.get(age, 0.05)
                
                # Mortality Loading: Healthier people live longer
                if health_ci_count == 0:
                    q_d = base_q_d
                elif health_ci_count == 1:
                    q_d = min(0.99, base_q_d * 2.5) 
                else:
                    q_d = min(0.99, base_q_d * 5.0) 
                
                # Grim Reaper at 100
                if age == max_simulation_age:
                    is_death = True
                    is_ci = False
                else:
                    roll = np.random.random()
                    is_death = roll < q_d
                    is_ci = False
                    if not is_death:
                        is_ci = roll < (q_d + base_q_ci)

                if is_ci: health_ci_count += 1

                # --- 2. CALCULATE POLICY VALUES ---
                mult = self.multiplier_factor if age < self.multiplier_age else 1.0
                total_paid = min(year_idx, self.payment_term) * self.prem_wl
                
                if year_idx <= 2: wl_sv_current = 0
                elif year_idx <= self.payment_term: wl_sv_current = total_paid * 0.85 * ((year_idx)/(self.payment_term))
                else: wl_sv_current = (self.prem_wl * self.payment_term) * 0.85 * ((1 + self.wl_par_return) ** (year_idx - self.payment_term))

                # --- 3. EVENT HANDLING & LOGGING ---
                payout_this_turn = False # Only log if money moves
                
                if is_death:
                    alive = False
                    
                    # WL Death Payout
                    if wl_active and wl_claims_count < limit_wl_claims:
                        if wl_claims_count == 0:
                            payout = max(self.sa * mult, self.sa + wl_sv_current)
                        else:
                            payout = self.sa * mult # Multi-Pay Death
                        
                        wl_cash_received += payout
                        wl_active = False
                        payout_this_turn = True
                    
                    # Term Death Payout
                    if term_active and term_claims_count < limit_term_claims and age < self.term_expiry_age:
                        btid_fund += self.sa
                        term_active = False
                        payout_this_turn = True

                    # LOGGING FIX: Only log "Death" if a claim was paid
                    if payout_this_turn:
                        event_log.append("Death")
                    
                    break 
                    
                elif is_ci:
                    # WL CI Payout
                    if wl_active and wl_claims_count < limit_wl_claims:
                        if wl_claims_count == 0:
                            payout = max(self.sa * mult, self.sa + wl_sv_current)
                        else:
                            payout = self.sa * mult
                            
                        wl_cash_received += payout
                        wl_claims_count += 1
                        payout_this_turn = True
                        
                        # SINGLE PAY TERMINATION
                        if not enable_multi_pay:
                            wl_active = False 
                    
                    # Term CI Payout
                    if term_active and term_claims_count < limit_term_claims and age < self.term_expiry_age:
                        btid_fund += self.sa
                        term_claims_count += 1
                        term_active = False 
                        payout_this_turn = True

                    # LOGGING FIX: Only log "CI" if a claim was paid
                    if payout_this_turn:
                        event_log.append("CI")

                # --- 4. CASHFLOW ---
                if wl_cash_received > 0: wl_cash_received *= (1 + r_inv)
                
                budget = self.prem_wl if year_idx <= self.payment_term else 0
                term_premium_due = self.prem_term if (age < self.term_expiry_age and term_active) else 0
                
                net_savings = budget - term_premium_due
                btid_fund = (btid_fund + net_savings) * (1 + r_inv)
                if btid_fund < 0: btid_fund = 0
                
                age += 1
            
            # --- FINAL CALCULATION ---
            years_passed = age - self.current_age
            pv_factor = (1 + r_disc) ** -years_passed
            event_str = " -> ".join(event_log) if event_log else "Survive"
            
            results.append({
                "Event Chain": event_str,
                "Final Age": age,
                "Diff": (btid_fund * pv_factor) - (wl_cash_received * pv_factor)
            })
            
        return pd.DataFrame(results)