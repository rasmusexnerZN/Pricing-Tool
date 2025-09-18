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
if 'num_ramp_periods' not in st.session_state:
    st.session_state.num_ramp_periods = 2

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
                              ramp_fee_tiers):
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
    costs_ramped_flat = [get_fee_for_month(m, ramp_fee_tiers) for m in range(1, contract_months + 1)]

    # 5. Create DataFrame
    df = pd.DataFrame({
        'Month': range(1, contract_months + 1),
        'Onboarded Vessels': monthly_vessels,
        'Pay-Per-Vessel': costs_ppv,
        'Single Flat Fee': costs_single_flat,
        'Ramped Flat Fee': costs_ramped_flat,
    })
    
    # 6. Calculate Cumulative Costs
    df['Cumulative Pay-Per-Vessel'] = df['Pay-Per-Vessel'].cumsum()
    df['Cumulative Single Flat Fee'] = df['Single Flat Fee'].cumsum()
    df['Cumulative Ramped Flat Fee'] = df['Ramped Flat Fee'].cumsum()
    
    return df, single_flat_fee_tco, onboarding_duration

# --- UI & APP LOGIC ---

st.title("🚢 Pricing Model Simulator")
st.markdown(
    "A tool to compare **Pay-Per-Vessel**, **Single Flat Fee**, and **Ramped Flat Fee** models."
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
        
        st.markdown("**Model 2: Single Flat Fee**")
        flat_fee_discount = st.slider(
            "Discount for Flat Fee (%)", 
            min_value=0, 
            max_value=100, 
            value=20,
            help="The discount applied to the total potential Pay-Per-Vessel cost to calculate this fee."
        )
        st.markdown("---")

        with st.expander("**Model 3: Ramped Flat Fee**", expanded=True):
            st.write("Define multiple periods with custom start months and fees.")

            def add_ramp_period():
                if st.session_state.num_ramp_periods < 5:
                    st.session_state.num_ramp_periods += 1
            def remove_ramp_period():
                if st.session_state.num_ramp_periods > 1:
                    st.session_state.num_ramp_periods -= 1

            b_col1, b_col2 = st.columns(2)
            b_col1.button("Add Period", on_click=add_ramp_period, use_container_width=True, key="add_ramp")
            b_col2.button("Remove Last Period", on_click=remove_ramp_period, use_container_width=True, key="remove_ramp")

            ramp_fee_tiers = {}
            last_month = 1
            
            default_ramp_values = [
                {'month': 1, 'fee': 14500},
                {'month': 6, 'fee': 35000},
                {'month': 12, 'fee': 45000}
            ]

            for i in range(st.session_state.num_ramp_periods):
                st.markdown(f"**Period {i + 1}**")
                cols = st.columns(2)
                
                default_month = default_ramp_values[i]['month'] if i < len(default_ramp_values) else last_month + 6
                default_fee = default_ramp_values[i]['fee'] if i < len(default_ramp_values) else 50000

                if i == 0:
                    start_month = 1
                    cols[0].metric("Start Month", "1")
                    fee = cols[1].number_input("Monthly Fee", value=default_fee, step=500, key=f'ramp_fee_{i}')
                else:
                    start_month = cols[0].number_input("Start Month", min_value=last_month + 1, max_value=contract_months, value=default_month, key=f'ramp_month_{i}')
                    fee = cols[1].number_input("Monthly Fee", value=default_fee, step=500, key=f'ramp_fee_{i}')
                
                ramp_fee_tiers[start_month] = fee
                last_month = start_month

# --- MAIN PAGE FOR OUTPUTS ---
cost_df, single_flat_fee_tco, onboarding_duration = calculate_costs_over_time(
    total_vessels, contract_months, vessels_per_month,
    pay_per_vessel_price, flat_fee_discount,
    ramp_fee_tiers
)

# --- Update Sidebar with Calculated Value ---
onboarding_duration_placeholder.metric(label="Calculated Onboarding Duration", value=f"{onboarding_duration} Months")

# --- Summary Metrics with Highlighting ---
st.header("📊 Financial Summary (Total Cost of Ownership)")
tco_ppv = cost_df['Pay-Per-Vessel'].sum()
tco_ramped = cost_df['Ramped Flat Fee'].sum()
tco_list = {
    "Pay-Per-Vessel TCO": tco_ppv,
    "Single Flat Fee TCO": single_flat_fee_tco,
    "Ramped Flat Fee TCO": tco_ramped
}
min_tco_label = min(tco_list, key=tco_list.get)
max_tco_value = max(tco_list.values())

cols = st.columns(3)
metric_labels_ordered = ["Pay-Per-Vessel TCO", "Ramped Flat Fee TCO", "Single Flat Fee TCO"]

for i, label in enumerate(metric_labels_ordered):
    value = tco_list[label]
    delta_val = None
    if label == min_tco_label and value < max_tco_value:
        savings = max_tco_value - value
        delta_val = -savings
    
    cols[i].metric(
        label=label, 
        value=f"{currency} {value:,.0f}", 
        delta=f"{delta_val:,.0f}" if delta_val is not None else None
    )

st.markdown("---")

# --- DETAILED VISUALIZATIONS (SIDE-BY-SIDE) ---
st.header("📈 Detailed Analysis")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Price Per Vessel")
    st.markdown("Shows the effective monthly price per vessel at different fleet sizes.")
    vessels_range = range(1, total_vessels + 1) if total_vessels > 0 else range(1,2)
    avg_monthly_ramped_fee = tco_ramped / contract_months if contract_months > 0 else 0

    price_per_vessel_data = {
        'Number of Vessels': vessels_range,
        'Pay-Per-Vessel': [pay_per_vessel_price] * len(vessels_range),
        'Single Flat Fee': [(single_flat_fee_tco / contract_months) / v if v > 0 else 0 for v in vessels_range],
        'Ramped Flat Fee': [avg_monthly_ramped_fee / v if v > 0 else 0 for v in vessels_range]
    }
    ppv_df = pd.DataFrame(price_per_vessel_data)

    fig_ppv = px.line(
        ppv_df.melt(id_vars='Number of Vessels', var_name='Pricing Model', value_name='Price'),
        x='Number of Vessels',
        y='Price',
        color='Pricing Model',
        labels={'Price': f'Price/Vessel ({currency})'},
    )
    fig_ppv.update_yaxes(range=[0, 5000])
    st.plotly_chart(fig_ppv, use_container_width=True)

with col2:
    st.subheader("Monthly Cost Over Time")
    st.markdown("Shows the expected monthly cash flow based on the onboarding plan.")
    
    plot_df_monthly = cost_df.melt(
        id_vars='Month', 
        value_vars=['Pay-Per-Vessel', 'Single Flat Fee', 'Ramped Flat Fee'], 
        var_name='Pricing Model', 
        value_name='Monthly Cost'
    )
    
    fig_monthly = px.line(
        plot_df_monthly,
        x='Month',
        y='Monthly Cost',
        color='Pricing Model',
        labels={'Monthly Cost': f'Monthly Cost ({currency})'},
    )
    fig_monthly.update_traces(selector={"name": "Ramped Flat Fee"}, line_shape='hv')
    fig_monthly.update_traces(selector={"name": "Pay-Per-Vessel"}, line_shape='hv')
    st.plotly_chart(fig_monthly, use_container_width=True)

# --- NEW CUMULATIVE TCO GRAPH ---
st.markdown("---")
st.header("🕰️ Cumulative Cost Over Time")
st.markdown("This graph shows the total investment accumulating over the contract period, making it easy to see break-even points.")

cumulative_cols = ['Cumulative Pay-Per-Vessel', 'Cumulative Single Flat Fee', 'Cumulative Ramped Flat Fee']
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
    labels={'Cumulative TCO': f'Cumulative TCO ({currency})'},
    title='<b>Cumulative TCO Comparison</b>'
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
