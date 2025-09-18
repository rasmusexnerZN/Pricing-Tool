import streamlit as st
import pandas as pd
import plotly.express as px
import math

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Maritime Pricing Simulator",
    page_icon="🚢",
    layout="wide",
)

# --- INITIALIZE SESSION STATE ---
# Default to 3 periods for the Scheduled Fee model
if 'num_scheduled_periods' not in st.session_state:
    st.session_state.num_scheduled_periods = 3

# --- HELPER FUNCTIONS ---

def get_fee_for_month(month, tiers_dict):
    """Gets the correct fee for a given month from a dictionary of tiers."""
    fee = 0
    # Sort tiers by month (key) in descending order to find the correct bracket
    for tier_month, tier_fee in sorted(tiers_dict.items(), reverse=True):
        if month >= tier_month:
            fee = tier_fee
            break
    return fee

def calculate_costs_over_time(total_vessels, contract_months, vessels_per_month,
                              pay_per_vessel_price, flat_fee_discount,
                              scheduled_fee_tiers):
    """Calculates monthly and cumulative costs over time for all three models."""
    
    # 1. Calculate the Onboarding Duration 
    if vessels_per_month > 0:
        onboarding_duration = math.ceil(total_vessels / vessels_per_month)
    else:
        onboarding_duration = 0

    # 2. Calculate the Single Flat Fee TCO
    base_tco = pay_per_vessel_price * total_vessels * contract_months
    discount_multiplier = 1 - (flat_fee_discount / 100)
    single_flat_fee_tco = base_tco * discount_multiplier

    # 3. Generate the monthly vessel count with remainder logic
    monthly_vessels = []
    current_vessels = 0
    for month in range(1, contract_months + 1):
        if current_vessels < total_vessels:
            remaining_to_onboard = total_vessels - current_vessels
            vessels_to_add = min(vessels_per_month, remaining_to_onboard)
            current_vessels += vessels_to_add
        monthly_vessels.append(current_vessels)

    # 4. Calculate monthly costs for each model
    costs_ppv = [pay_per_vessel_price * v for v in monthly_vessels]
    effective_monthly_single_flat = single_flat_fee_tco / contract_months if contract_months > 0 else 0
    costs_single_flat = [effective_monthly_single_flat] * contract_months
    costs_scheduled_flat = [get_fee_for_month(m, scheduled_fee_tiers) for m in range(1, contract_months + 1)]

    # 5. Create DataFrame
    df = pd.DataFrame({
        'Month': range(1, contract_months + 1),
        'Onboarded Vessels': monthly_vessels,
        'Pay-Per-Vessel': costs_ppv,
        'Single Flat Fee': costs_single_flat,
        'Scheduled Flat Fee': costs_scheduled_flat,
    })
    
    # 6. Calculate Cumulative Costs
    df['Cumulative Pay-Per-Vessel'] = df['Pay-Per-Vessel'].cumsum()
    df['Cumulative Single Flat Fee'] = df['Single Flat Fee'].cumsum()
    df['Cumulative Scheduled Flat Fee'] = df['Scheduled Flat Fee'].cumsum()
    
    return df,
