import numpy as np
import pandas as pd

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
        
        # NEW VARIABLES
        self.multiplier_factor = float(multiplier_factor)
        self.multiplier_age = int(multiplier_age)
        self.term_expiry_age = int(term_expiry_age) # NEW

    def calculate_simulation(self, investment_return, discount_rate):
        duration = self.death_age - self.current_age + 1
        
        # --- LOGIC LOOP ---
        btid_fund_accum = []
        wl_sv_accum = []
        btid_death_accum = []
        wl_death_accum = []
        
        fund_balance = 0.0
        total_wl_premiums_paid = 0.0
        wl_prev_sv = 0.0 
        
        for t in range(duration):
            year_idx = t + 1 
            age_at_end_of_year = self.current_age + year_idx 
            
            # --- BTID LOGIC ---
            if year_idx <= self.payment_term:
                cashflow = self.prem_wl - self.prem_term
            else:
                # Term premiums stop when coverage ends (Using NEW term_expiry_age)
                if (self.current_age + t) < self.term_expiry_age: 
                    cashflow = -self.prem_term
                else:
                    cashflow = 0

            fund_balance = (fund_balance * (1 + investment_return)) + cashflow
            if fund_balance < 0: fund_balance = 0
            btid_fund_accum.append(fund_balance)
            
            # Death Benefit (Using NEW term_expiry_age)
            term_cover = self.sa if (self.current_age + t) < self.term_expiry_age else 0
            btid_death_accum.append(term_cover + fund_balance)

            # --- WHOLE LIFE LOGIC ---
            if year_idx <= self.payment_term:
                total_wl_premiums_paid += self.prem_wl

            # Surrender Value
            if year_idx <= 2:
                wl_sv = 0
            elif year_idx <= self.payment_term:
                target_ratio = 0.85
                progress = (year_idx - 2) / (self.payment_term - 2)
                wl_sv = total_wl_premiums_paid * progress * target_ratio
            else:
                wl_sv = wl_prev_sv * (1 + self.wl_par_return)
            
            wl_prev_sv = wl_sv
            wl_sv_accum.append(wl_sv)

            # Death Benefit (Multiplier Logic)
            current_mult = self.multiplier_factor if (self.current_age + t) < self.multiplier_age else 1.0
            wl_death_accum.append(max(self.sa * current_mult, self.sa + wl_sv))

        # --- DATA CONSTRUCTION ---
        plot_ages = [self.current_age] + [self.current_age + i for i in range(1, duration + 1)]
        
        # Prepend Start Values
        final_btid_fund = [0] + btid_fund_accum
        final_wl_sv = [0] + wl_sv_accum
        
        final_btid_death = [self.sa] + btid_death_accum
        final_wl_death = [self.sa * self.multiplier_factor] + wl_death_accum 

        # Discounting
        disc_factors = (1 + discount_rate) ** -np.arange(len(plot_ages))

        return pd.DataFrame({
            "Age": plot_ages,
            "BTID_Nominal": final_btid_fund,
            "WL_Nominal": final_wl_sv,
            "BTID_Death": final_btid_death,
            "WL_Death": final_wl_death,
            "BTID_PV": np.array(final_btid_fund) * disc_factors,
            "WL_PV": np.array(final_wl_sv) * disc_factors
        })

    def get_crossover_age(self, investment_return):
        # Pass new arg to temp model
        long_model = DeterministicModel(
            self.current_age, 100, self.sa, self.prem_wl, self.prem_term, 
            self.wl_par_return, self.payment_term,
            self.multiplier_factor, self.multiplier_age, self.term_expiry_age
        )
        df = long_model.calculate_simulation(investment_return, 0.0)
        
        start_check_age = self.current_age + 5
        valid_zone = df[df['Age'] > start_check_age]
        
        wl_wins = valid_zone[valid_zone['WL_Nominal'] > valid_zone['BTID_Nominal']]
        
        if wl_wins.empty: return 100
        return wl_wins['Age'].iloc[0]