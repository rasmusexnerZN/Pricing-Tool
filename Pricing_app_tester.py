import streamlit as st
import pandas as pd
import plotly.express as px
import math

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Pricing Tool",
    page_icon="🚢",
    layout="wide",
)

# --- HELPER FUNCTION ---
def calculate_costs_over_time(total_vessels, contract_months, vessels_per_month,
                              pay_per_vessel_price, single_flat_monthly_fee):
    """Calculates monthly and cumulative costs over time for the two models."""
    
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
    costs_single_flat = [single_flat_monthly_fee] * contract_months

    # 4. Create DataFrame
    df = pd.DataFrame({
        'Month': range(1, contract_months + 1),
        'Onboarded Vessels': monthly_vessels,
        'Pay-Per-Vessel': costs_ppv,
        'Single Flat Fee': costs_single_flat,
    })
    
    # 5. Calculate Cumulative Costs
    df['Cumulative Pay-Per-Vessel'] = df['Pay-Per-Vessel'].cumsum()
    df['Cumulative Single Flat Fee'] = df['Single Flat Fee'].cumsum()
    
    return df, onboarding_duration

# --- UI & APP LOGIC ---

st.title("🚢 Pricing Model Simulator")
st.markdown(
    "A tool to compare **Pay-Per-Vessel** and **Single Flat Fee** models."
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
        single_flat_monthly_fee = st.number_input(
            f"Flat Monthly Fee ({currency})",
            min_value=0,
            value=35000,
            step=500,
            help="A single, fixed fee charged every month for the entire contract period."
        )

# --- MAIN PAGE FOR OUTPUTS ---
cost_df, onboarding_duration = calculate_costs_over_time(
    total_vessels, contract_months, vessels_per_month,
    pay_per_vessel_price, single_flat_monthly_fee
)

# --- Update Sidebar with Calculated Value ---
onboarding_duration_placeholder.metric(label="Calculated Onboarding Duration", value=f"{onboarding_duration} Months")

# --- Summary Metrics ---
st.header("📊 Financial Summary (Total Cost of Ownership)")
tco_ppv = cost_df['Pay-Per-Vessel'].sum()
single_flat_fee_tco = single_flat_monthly_fee * contract_months

cols = st.columns(2)
cols[0].metric(label="Pay-Per-Vessel TCO", value=f"{currency} {tco_ppv:,.0f}")
cols[1].metric(label="Single Flat Fee TCO", value=f"{currency} {single_flat_fee_tco:,.0f}")

st.markdown("---")

# --- DETAILED VISUALIZATIONS (SIDE-BY-SIDE) ---
st.header("📈 Detailed Analysis")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Price Per Vessel at Key Milestones")

    # --- Calculations for the new bar chart ---
    vessels_onethird = math.ceil(total_vessels / 3)
    vessels_twothirds = math.ceil(total_vessels * 2 / 3)

    price_ff_onethird = single_flat_monthly_fee / vessels_onethird if vessels_onethird > 0 else 0
    price_ff_twothirds = single_flat_monthly_fee / vessels_twothirds if vessels_twothirds > 0 else 0
    price_ff_full = single_flat_monthly_fee / total_vessels if total_vessels > 0 else 0

    bar_data = {
        'Scenario': [
            'Pay-Per-Vessel Rate', 
            f'Flat Fee ({vessels_onethird} Vessels)', 
            f'Flat Fee ({vessels_twothirds} Vessels)', 
            f'Flat Fee ({total_vessels} Vessels)'
        ],
        'Price Per Vessel': [
            pay_per_vessel_price, 
            price_ff_onethird, 
            price_ff_twothirds, 
            price_ff_full
        ],
        'Model': [
            'Pay-Per-Vessel', 
            'Single Flat Fee', 
            'Single Flat Fee', 
            'Single Flat Fee'
        ]
    }
    bar_df = pd.DataFrame(bar_data)

    fig_bar = px.bar(
        bar_df,
        x='Scenario',
        y='Price Per Vessel',
        color='Model',
        labels={'Price Per Vessel': f'Price/Vessel ({currency})'},
        text_auto='.0f'
    )
    st.plotly_chart(fig_bar, use_container_width=True)


with col2:
    st.subheader("Monthly Cost Over Time")
    
    plot_df_monthly = cost_df.melt(
        id_vars='Month', 
        value_vars=['Pay-Per-Vessel', 'Single Flat Fee'], 
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
    fig_monthly.update_traces(selector={"name": "Pay-Per-Vessel"}, line_shape='hv')
    st.plotly_chart(fig_monthly, use_container_width=True)

# --- CUMULATIVE TCO GRAPH ---
st.markdown("---")
st.header("🕰️ Cumulative Cost Over Time")

cumulative_cols = ['Cumulative Pay-Per-Vessel', 'Cumulative Single Flat Fee']
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
