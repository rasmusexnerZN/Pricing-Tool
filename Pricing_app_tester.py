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

# --- MODIFICATION: Added 'enable_scheduled_fee' parameter ---
def calculate_costs_over_time(total_vessels, contract_months, vessels_per_month,
                              pay_per_vessel_price, single_flat_monthly_fee,
                              scheduled_fee_tiers, enable_scheduled_fee):
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
    costs_single_flat = [single_flat_monthly_fee] * contract_months
    
    # --- MODIFICATION: Calculate scheduled costs only if enabled ---
    if enable_scheduled_fee:
        costs_scheduled_flat = [get_fee_for_month(m, scheduled_fee_tiers) for m in range(1, contract_months + 1)]
    else:
        costs_scheduled_flat = [0] * contract_months


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
            # --- MODIFICATION: Added toggle switch ---
            enable_scheduled_fee = st.toggle("Enable this model", value=True)
            
            # --- MODIFICATION: All inputs are now conditional on the toggle ---
            if enable_scheduled_fee:
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
            else:
                # If disabled, ensure an empty dictionary is passed
                scheduled_fee_tiers = {}

        st.markdown("---")
        
        st.markdown("**Model 3: Single Flat Fee**")
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
    pay_per_vessel_price, single_flat_monthly_fee,
    scheduled_fee_tiers, enable_scheduled_fee # --- MODIFICATION: Pass toggle state
)

# --- Update Sidebar with Calculated Value ---
onboarding_duration_placeholder.metric(label="Calculated Onboarding Duration", value=f"{onboarding_duration} Months")

# --- Define Color Palette ---
color_map = {
    'Pay-Per-Vessel': '#003143',
    'Scheduled Flat Fee': '#186e80',
    'Single Flat Fee': '#4fb18c'
}

# --- CALCULATIONS FOR CHARTS ---
tco_ppv = cost_df['Pay-Per-Vessel'].sum()
tco_scheduled = cost_df['Scheduled Flat Fee'].sum()
single_flat_fee_tco = single_flat_monthly_fee * contract_months
tco_list = {
    "Pay-Per-Vessel TCO": tco_ppv,
    "Scheduled Flat Fee TCO": tco_scheduled,
    "Single Flat Fee TCO": single_flat_fee_tco
}

# --- MODIFICATION: Create a dynamic list of models to plot ---
models_to_plot = ['Pay-Per-Vessel', 'Single Flat Fee']
if enable_scheduled_fee:
    models_to_plot.append('Scheduled Flat Fee')


# --- DETAILED VISUALIZATIONS (SIDE-BY-SIDE) ---
st.header("📈 Detailed Cost of Ownership Analysis")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Effective Cost of Ownership per Vessel")
    
    total_vessel_months = cost_df['Onboarded Vessels'].sum()

    if total_vessel_months > 0:
        avg_price_ppv = pay_per_vessel_price
        avg_price_scheduled = tco_scheduled / total_vessel_months if enable_scheduled_fee else 0
        avg_price_single_flat = single_flat_fee_tco / total_vessel_months
    else:
        avg_price_ppv = pay_per_vessel_price
        avg_price_scheduled = 0
        avg_price_single_flat = 0

    bar_data = {
        'Pricing Model': [
            'Pay-Per-Vessel',
            'Scheduled Flat Fee',
            'Single Flat Fee'
        ],
        'Average Price Per Vessel': [
            avg_price_ppv,
            avg_price_scheduled,
            avg_price_single_flat
        ]
    }
    bar_df = pd.DataFrame(bar_data)
    
    # --- MODIFICATION: Filter DataFrame before plotting ---
    bar_df_filtered = bar_df[bar_df['Pricing Model'].isin(models_to_plot)]

    fig_bar = px.bar(
        bar_df_filtered, # Use filtered data
        x='Pricing Model',
        y='Average Price Per Vessel',
        color='Pricing Model',
        labels={'Average Price Per Vessel': f'Avg. Price/Vessel ({currency})'},
        text_auto=True,
        color_discrete_map=color_map,
        category_orders={"Pricing Model": ["Pay-Per-Vessel", "Scheduled Flat Fee", "Single Flat Fee"]} # Keep consistent order
    )
    fig_bar.update_traces(texttemplate='%{value:,.0f}', textfont_size=16)
    fig_bar.update_yaxes(tickformat=',')
    fig_bar.update_xaxes(title_text="", tickfont_size=14)
    fig_bar.update_layout(legend=dict(font=dict(size=14)))

    # --- MODIFICATION: Make annotations conditional ---
    if enable_scheduled_fee and avg_price_ppv > 0 and avg_price_scheduled < avg_price_ppv:
        saving_scheduled_vs_ppv = ((avg_price_ppv - avg_price_scheduled) / avg_price_ppv) * 100
        fig_bar.add_annotation(
            x='Scheduled Flat Fee', y=avg_price_scheduled,
            text=f"<b>{saving_scheduled_vs_ppv:.1f}% saving</b><br>vs. Pay-Per-Vessel",
            showarrow=False, yshift=25,
            font=dict(color="#186e80", size=14)
        )

    if enable_scheduled_fee and avg_price_scheduled > 0 and avg_price_single_flat < avg_price_scheduled:
        saving_single_vs_scheduled = ((avg_price_scheduled - avg_price_single_flat) / avg_price_scheduled) * 100
        fig_bar.add_annotation(
            x='Single Flat Fee', y=avg_price_single_flat,
            text=f"<b>{saving_single_vs_scheduled:.1f}% saving</b><br>vs. Scheduled",
            showarrow=False, yshift=25,
            font=dict(color="#4fb18c", size=14)
        )
        
    st.plotly_chart(fig_bar, use_container_width=True)


with col2:
    st.subheader("Monthly Cost of Ownership")
    
    plot_df_monthly = cost_df.melt(
        id_vars='Month', 
        value_vars=models_to_plot, # --- MODIFICATION: Use dynamic list
        var_name='Pricing Model', 
        value_name='Monthly Cost'
    )
    
    fig_monthly = px.line(
        plot_df_monthly,
        x='Month',
        y='Monthly Cost',
        color='Pricing Model',
        labels={'Monthly Cost': f'Monthly Cost ({currency})'},
        color_discrete_map=color_map
    )
    # Only apply hv shape if the model is active
    if 'Scheduled Flat Fee' in models_to_plot:
        fig_monthly.update_traces(selector={"name": "Scheduled Flat Fee"}, line_shape='hv')
    fig_monthly.update_traces(selector={"name": "Pay-Per-Vessel"}, line_shape='hv')
    fig_monthly.update_yaxes(tickformat=',')
    fig_monthly.update_layout(legend=dict(font=dict(size=14)))
    st.plotly_chart(fig_monthly, use_container_width=True)

# --- CUMULATIVE TCO SECTION ---
st.markdown("---")
st.header("🕰️ Cumulative Cost of Ownership")
col3, col4 = st.columns(2)

with col3:
    st.subheader("Cumulative Cost of Ownership")
    # --- MODIFICATION: Dynamically select cumulative columns ---
    cumulative_cols_to_plot = [f'Cumulative {model}' for model in models_to_plot]

    plot_df_cumulative = cost_df.melt(
        id_vars='Month',
        value_vars=cumulative_cols_to_plot,
        var_name='Pricing Model',
        value_name='Cumulative TCO'
    )
    plot_df_cumulative['Pricing Model'] = plot_df_cumulative['Pricing Model'].str.replace('Cumulative ', '')

    fig_cumulative = px.line(
        plot_df_cumulative,
        x='Month',
        y='Cumulative TCO',
        color='Pricing Model',
        labels={'Cumulative TCO': f'Cumulative TCO ({currency})'},
        color_discrete_map=color_map
    )
    fig_cumulative.update_yaxes(tickformat=',')
    fig_cumulative.update_layout(legend=dict(font=dict(size=14)))
    st.plotly_chart(fig_cumulative, use_container_width=True)

with col4:
    st.subheader("Total Cost of Ownership")
    
    tco_df = pd.DataFrame(list(tco_list.items()), columns=['Pricing Model', 'Total Cost'])
    tco_df['Pricing Model'] = tco_df['Pricing Model'].str.replace(' TCO', '')
    
    # --- MODIFICATION: Filter DataFrame before plotting ---
    tco_df_filtered = tco_df[tco_df['Pricing Model'].isin(models_to_plot)]

    fig_tco_bar = px.bar(
        tco_df_filtered, # Use filtered data
        x='Pricing Model',
        y='Total Cost',
        color='Pricing Model',
        labels={'Total Cost': f'Final TCO ({currency})'},
        text_auto='.2s',
        color_discrete_map=color_map,
        category_orders={"Pricing Model": ["Pay-Per-Vessel", "Scheduled Flat Fee", "Single Flat Fee"]} # Keep consistent order
    )
    fig_tco_bar.update_traces(textfont_size=16)
    fig_tco_bar.update_yaxes(tickformat=',')
    fig_tco_bar.update_xaxes(title_text="", tickfont_size=14)
    fig_tco_bar.update_layout(legend=dict(font=dict(size=14)))

    # --- MODIFICATION: Make annotations conditional ---
    if enable_scheduled_fee and tco_ppv > 0 and tco_scheduled < tco_ppv:
        saving_scheduled_vs_ppv_tco = ((tco_ppv - tco_scheduled) / tco_ppv) * 100
        fig_tco_bar.add_annotation(
            x='Scheduled Flat Fee', y=tco_scheduled,
            text=f"<b>{saving_scheduled_vs_ppv_tco:.1f}% saving</b><br>vs. Pay-Per-Vessel",
            showarrow=False, yshift=25,
            font=dict(color="#186e80", size=14)
        )
    
    if enable_scheduled_fee and tco_scheduled > 0 and single_flat_fee_tco < tco_scheduled:
        saving_single_vs_scheduled_tco = ((tco_scheduled - single_flat_fee_tco) / tco_scheduled) * 100
        fig_tco_bar.add_annotation(
            x='Single Flat Fee', y=single_flat_fee_tco,
            text=f"<b>{saving_single_vs_scheduled_tco:.1f}% saving</b><br>vs. Scheduled",
            showarrow=False, yshift=25,
            font=dict(color="#4fb18c", size=14)
        )
        
    st.plotly_chart(fig_tco_bar, use_container_width=True)


# --- DATA TABLE ---
st.markdown("---")
st.header("🔢 Detailed Data Breakdown")
with st.expander("Click to view the month-by-month data"):
    display_df = cost_df.copy()
    
    # --- MODIFICATION: Conditionally drop columns if model is disabled ---
    if not enable_scheduled_fee:
        display_df = display_df.drop(columns=['Scheduled Flat Fee', 'Cumulative Scheduled Flat Fee'])

    for col in display_df.columns:
        if col not in ['Month', 'Onboarded Vessels']:
            display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}")
    st.dataframe(display_df, use_container_width=True)
