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
                              pay_per_vessel_price, single_flat_fee_tco,
                              scheduled_fee_tiers):
    """Calculates monthly and cumulative costs over time for all three models."""
    
    # 1. Calculate the Onboarding Duration 
    if vessels_per_month > 0:
        onboarding_duration = math.ceil(total_vessels / vessels_per_month)
    else:
        onboarding_duration = 0

    # 2. Generate the monthly vessel count with remainder logic
    monthly_vessels = []
    current_vessels = 0
    for month in range(1, contract_months + 1):
        if current_vessels < total_vessels:
            remaining_to_onboard = total_vessels - current_vessels
            vessels_to_add = min(vessels_per_month, remaining_to_onboard)
            current_vessels += vessels_to_add
        monthly_vessels.append(current_vessels)

    # 3. Calculate monthly costs for each model
    costs_ppv = [pay_per_vessel_price * v for v in monthly_vessels]
    effective_monthly_single_flat = single_flat_fee_tco / contract_months if contract_months > 0 else 0
    costs_single_flat = [effective_monthly_single_flat] * contract_months
    costs_scheduled_flat = [get_fee_for_month(m, scheduled_fee_tiers) for m in range(1, contract_months + 1)]

    # 4. Create DataFrame
    df = pd.DataFrame({
        'Month': range(1, contract_months + 1),
        'Onboarded Vessels': monthly_vessels,
        'Pay-Per-Vessel': costs_ppv,
        'Scheduled Flat Fee': costs_scheduled_flat,
        'Single Flat Fee': costs_single_flat,
    })
    
    # 5. Calculate Cumulative Costs
    df['Cumulative Pay-Per-Vessel'] = df['Pay-Per-Vessel'].cumsum()
    df['Cumulative Scheduled Flat Fee'] = df['Scheduled Flat Fee'].cumsum()
    df['Cumulative Single Flat Fee'] = df['Single Flat Fee'].cumsum()
    
    return df, onboarding_duration

# --- UI & APP LOGIC ---

st.title("🚢 Pricing Model Simulator")
st.markdown(
    "A tool to compare **Pay-Per-Vessel**, **Scheduled Flat Fee**, and **Single Flat Fee** models."
)

# --- SIDEBAR FOR INPUTS ---
with st.sidebar:
    st.header("⚙️ Configuration")

    tab1, tab2 = st.tabs(["📄 Contract Setup", "💰 Pricing Inputs"])

    with tab1:
        st.subheader("Client & Contract")
        currency = st.selectbox("Currency", ["USD", "EUR", "DKK"])
        total_vessels = st.number_input("Total Number of Vessels", min_value=1, value=50, step=1)
        contract_months = st.number_input("Contract Period (Months)", min_value=1, value=48, step=1)
        
        st.markdown("---")
        st.subheader("Onboarding Plan")
        vessels_per_month = st.number_input("Vessels Onboarded Per Month", min_value=1, value=5, step=1, help="The number of vessels to add each month until the total is reached.")
        
        onboarding_duration_placeholder = st.empty()

    with tab2:
        st.subheader("Model Configuration")

        st.markdown("**Model 1: Pay-Per-Vessel**")
        pay_per_vessel_price = st.number_input(
            f"Price Per Vessel Per Month ({currency})", 
            min_value=0, 
            value=1000, 
            step=50
        )
        st.markdown("---")
        
        with st.expander("**Model 2: Scheduled Flat Fee**", expanded=True):
            st.write("Define multiple periods with custom start months and fees.")

            def add_scheduled_period():
                if st.session_state.num_scheduled_periods < 5:
                    st.session_state.num_scheduled_periods += 1
            def remove_scheduled_period():
                if st.session_state.num_scheduled_periods > 1:
                    st.session_state.num_scheduled_periods -= 1

            b_col1, b_col2 = st.columns(2)
            b_col1.button("Add Period", on_click=add_scheduled_period, use_container_width=True, key="add_ramp")
            b_col2.button("Remove Last Period", on_click=remove_scheduled_period, use_container_width=True, key="remove_ramp")

            scheduled_fee_tiers = {}
            last_month = 1
            
            default_scheduled_values = [
                {'month': 1, 'fee': 15000},
                {'month': 6, 'fee': 35000},
                {'month': 12, 'fee': 45000}
            ]

            for i in range(st.session_state.num_scheduled_periods):
                st.markdown(f"**Period {i + 1}**")
                cols = st.columns(2)
                
                default_month = default_scheduled_values[i]['month'] if i < len(default_scheduled_values) else last_month + 6
                default_fee = default_scheduled_values[i]['fee'] if i < len(default_scheduled_values) else 50000

                if i == 0:
                    start_month = 1
                    cols[0].metric("Start Month", "1")
                    fee = cols[1].number_input("Monthly Fee", value=default_fee, step=500, key=f'ramp_fee_{i}')
                else:
                    start_month = cols[0].number_input("Start Month", min_value=last_month + 1, max_value=contract_months, value=default_month, key=f'ramp_month_{i}')
                    fee = cols[1].number_input("Monthly Fee", value=default_fee, step=500, key=f'ramp_fee_{i}')
                
                scheduled_fee_tiers[start_month] = fee
                last_month = start_month
        st.markdown("---")
        
        st.markdown("**Model 3: Single Flat Fee**")
        single_flat_fee_tco = st.number_input(
            f"Total Cost of Ownership ({currency})",
            min_value=0,
            value=3500000,
            step=10000,
            help="The total price for the entire fleet for the whole contract period."
        )

# --- MAIN PAGE FOR OUTPUTS ---
cost_df, onboarding_duration = calculate_costs_over_time(
    total_vessels, contract_months, vessels_per_month,
    pay_per_vessel_price, single_flat_fee_tco,
    scheduled_fee_tiers
)

# --- Update Sidebar with Calculated Value ---
onboarding_duration_placeholder.metric(label="Calculated Onboarding Duration", value=f"{onboarding_duration} Months")

# --- Summary Metrics (Delta Removed) ---
st.header("📊 Financial Summary (Total Cost of Ownership)")
tco_ppv = cost_df['Pay-Per-Vessel'].sum()
tco_scheduled = cost_df['Scheduled Flat Fee'].sum()
tco_list = {
    "Pay-Per-Vessel TCO": tco_ppv,
    "Scheduled Flat Fee TCO": tco_scheduled,
    "Single Flat Fee TCO": single_flat_fee_tco
}

cols = st.columns(3)
metric_labels_ordered = ["Pay-Per-Vessel TCO", "Scheduled Flat Fee TCO", "Single Flat Fee TCO"]

for i, label in enumerate(metric_labels_ordered):
    value = tco_list[label]
    cols[i].metric(label=label, value=f"{currency} {value:,.0f}")

st.markdown("---")

# --- DETAILED VISUALIZATIONS (SIDE-BY-SIDE) ---
st.header("📈 Detailed Analysis")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Price Per Vessel")
    vessels_range = range(1, total_vessels + 1) if total_vessels > 0 else range(1,2)
    avg_monthly_scheduled_fee = tco_scheduled / contract_months if contract_months > 0 else 0

    price_per_vessel_data = {
        'Number of Vessels': vessels_range,
        'Pay-Per-Vessel': [pay_per_vessel_price] * len(vessels_range),
        'Scheduled Flat Fee': [avg_monthly_scheduled_fee / v if v > 0 else 0 for v in vessels_range],
        'Single Flat Fee': [(single_flat_fee_tco / contract_months) / v if v > 0 else 0 for v in vessels_range]
    }
    ppv_df = pd.DataFrame(price_per_vessel_data)

    fig_ppv = px.line(
        ppv_df.melt(id_vars='Number of Vessels', var_name='Pricing Model', value_name='Price'),
        x='Number of Vessels',
        y='Price',
        color='Pricing Model',
        labels={'Price': f'Price/Vessel ({currency})'}
    )
    fig_ppv.update_yaxes(range=[0, 5000])
    st.plotly_chart(fig_ppv, use_container_width=True)

with col2:
    st.subheader("Monthly Cost Over Time")
    
    plot_df_monthly = cost_df.melt(
        id_vars='Month', 
        value_vars=['Pay-Per-Vessel', 'Scheduled Flat Fee', 'Single Flat Fee'], 
        var_name='Pricing Model', 
        value_name='Monthly Cost'
    )
    
    fig_monthly = px.line(
        plot_df_monthly,
        x='Month',
        y='Monthly Cost',
        color='Pricing Model',
        labels={'Monthly Cost': f'Monthly Cost ({currency})'}
    )
    fig_monthly.update_traces(selector={"name": "Scheduled Flat Fee"}, line_shape='hv')
    fig_monthly.update_traces(selector={"name": "Pay-Per-Vessel"}, line_shape='hv')
    st.plotly_chart(fig_monthly, use_container_width=True)

# --- NEW CUMULATIVE TCO GRAPH ---
st.markdown("---")
st.header("🕰️ Cumulative Cost Over Time")

cumulative_cols = ['Cumulative Pay-Per-Vessel', 'Cumulative Scheduled Flat Fee', 'Cumulative Single Flat Fee']
plot_df_cumulative = cost_df.melt(
    id_vars='Month',
    value_vars=cumulative_cols,
    var_name='Pricing Model',
    value_name='Cumulative TCO'
)
# Clean up names for the legend by removing 'Cumulative'
plot_df_cumulative['Pricing Model'] = plot_df_cumulative['Pricing Model'].str.replace('Cumulative ', '')

fig_cumulative = px.line(
    plot_df_cumulative,
    x='Month',
    y='Cumulative TCO',
    color='Pricing Model',
    labels={'Cumulative TCO': f'Cumulative TCO ({currency})'}
)
st.plotly_chart(fig_cumulative, use_container_width=True)


# --- DATA TABLE ---
st.markdown("---")
st.header("🔢 Detailed Data Breakdown")
with st.expander("Click to view the month-by-month data"):
    display_df = cost_df.copy()
    for col in display_df.columns:
        if col not in ['Month', 'Onboarded Vessels']:
            display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}")
    st.dataframe(display_df)
