
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

if 'num_scheduled_periods' not in st.session_state:

    st.session_state.num_scheduled_periods = 3



# --- HELPER FUNCTIONS ---



def get_fee_for_month(month, tiers_dict):

    """Gets the correct fee for a given month from a dictionary of tiers."""

    fee = 0

    for tier_month, tier_fee in sorted(tiers_dict.items(), reverse=True):

        if month >= tier_month:

            fee = tier_fee

            break

    return fee



def calculate_costs_over_time(total_units, contract_months, units_per_month,

                              price_per_unit, single_flat_monthly_fee,

                              scheduled_fee_tiers, enable_scheduled_fee):

    """Calculates monthly and cumulative costs over time for all models."""

    if units_per_month > 0:

        onboarding_duration = math.ceil(total_units / units_per_month)

    else:

        onboarding_duration = 0



    monthly_units = []

    current_units = 0

    for month in range(1, contract_months + 1):

        if current_units < total_units:

            remaining_to_onboard = total_units - current_units

            units_to_add = min(units_per_month, remaining_to_onboard)

            current_units += units_to_add

        monthly_units.append(current_units)



    costs_pp_unit = [price_per_unit * u for u in monthly_units]

    costs_single_flat = [single_flat_monthly_fee] * contract_months

    

    if enable_scheduled_fee:

        costs_scheduled_flat = [get_fee_for_month(m, scheduled_fee_tiers) for m in range(1, contract_months + 1)]

    else:

        costs_scheduled_flat = [0] * contract_months



    df = pd.DataFrame({

        'Month': range(1, contract_months + 1),

        'Onboarded Units': monthly_units,

        'Pay-Per-Unit': costs_pp_unit,

        'Scheduled Flat Fee': costs_scheduled_flat,

        'Single Flat Fee': costs_single_flat,

    })

    

    df['Cumulative Pay-Per-Unit'] = df['Pay-Per-Unit'].cumsum()

    df['Cumulative Scheduled Flat Fee'] = df['Scheduled Flat Fee'].cumsum()

    df['Cumulative Single Flat Fee'] = df['Single Flat Fee'].cumsum()

    

    return df, onboarding_duration



# --- UI & APP LOGIC ---



st.title("🚢 Pricing Model Simulator")



with st.sidebar:

    st.header("⚙️ Configuration")

    tab1, tab2 = st.tabs(["📄 Contract Setup", "💰 Pricing Inputs"])

    with tab1:

        st.subheader("Client & Contract")

        currency = st.selectbox("Currency", ["USD", "EUR", "DKK"])

        unit_of_measure = st.selectbox("Select Unit of Measure", ["Vessel", "Voyage", "MT Bunker"])

        unit_plural = f"{unit_of_measure}s" if unit_of_measure != "MT Bunker" else "MT Bunker"

        total_units = st.number_input(f"Total Number of {unit_plural}", min_value=1, value=50, step=1)

        contract_months = st.number_input("Contract Period (Months)", min_value=1, value=48, step=1)

        st.markdown("---")

        st.subheader("Onboarding Plan")

        units_per_month = st.number_input(f"{unit_plural} Added Per Month", min_value=1, value=5, step=1, help=f"The number of {unit_plural.lower()} to add each month until the total is reached.")

        onboarding_duration_placeholder = st.empty()

    with tab2:

        st.subheader("Model Configuration")

        pp_unit_label = f"Pay-Per-{unit_of_measure}"

        st.markdown(f"**Model 1: {pp_unit_label}**")

        price_per_unit = st.number_input(f"Price Per {unit_of_measure} Per Month ({currency})", min_value=0, value=1000, step=50)

        st.markdown("---")

        with st.expander("**Model 2: Scheduled Flat Fee**", expanded=True):

            enable_scheduled_fee = st.toggle("Enable this model", value=True)

            if enable_scheduled_fee:

                st.write("Define multiple periods with custom start months and fees.")

                def add_scheduled_period():

                    if st.session_state.num_scheduled_periods < 5: st.session_state.num_scheduled_periods += 1

                def remove_scheduled_period():

                    if st.session_state.num_scheduled_periods > 1: st.session_state.num_scheduled_periods -= 1

                b_col1, b_col2 = st.columns(2)

                b_col1.button("Add Period", on_click=add_scheduled_period, use_container_width=True, key="add_ramp")

                b_col2.button("Remove Last Period", on_click=remove_scheduled_period, use_container_width=True, key="remove_ramp")

                scheduled_fee_tiers = {}

                last_month = 1

                default_scheduled_values = [{'month': 1, 'fee': 15000}, {'month': 6, 'fee': 35000}, {'month': 12, 'fee': 45000}]

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

                scheduled_fee_tiers = {}

        st.markdown("---")

        st.markdown("**Model 3: Single Flat Fee**")

        single_flat_monthly_fee = st.number_input(f"Flat Monthly Fee ({currency})", min_value=0, value=35000, step=500, help="A single, fixed fee charged every month for the entire contract period.")



cost_df, onboarding_duration = calculate_costs_over_time(total_units, contract_months, units_per_month, price_per_unit, single_flat_monthly_fee, scheduled_fee_tiers, enable_scheduled_fee)

onboarding_duration_placeholder.metric(label="Calculated Onboarding Duration", value=f"{onboarding_duration} Months")



pp_unit_label = f"Pay-Per-{unit_of_measure}"

cost_df.rename(columns={'Pay-Per-Unit': pp_unit_label, 'Cumulative Pay-Per-Unit': f'Cumulative {pp_unit_label}', 'Onboarded Units': f'Onboarded {unit_plural}'}, inplace=True)



color_map = {pp_unit_label: '#003143', 'Scheduled Flat Fee': '#186e80', 'Single Flat Fee': '#4fb18c'}

models_to_plot = [pp_unit_label, 'Single Flat Fee']

if enable_scheduled_fee:

    models_to_plot.append('Scheduled Flat Fee')

category_order_for_plots = [model for model in [pp_unit_label, 'Scheduled Flat Fee', 'Single Flat Fee'] if model in models_to_plot]



tco_pp_unit = cost_df[pp_unit_label].sum()

tco_scheduled = cost_df['Scheduled Flat Fee'].sum()

single_flat_fee_tco = single_flat_monthly_fee * contract_months



st.markdown(f"A tool to compare **{pp_unit_label}**, **Scheduled Flat Fee**, and **Single Flat Fee** models.")



row1_col1, row1_col2 = st.columns(2)

row2_col1, row2_col2 = st.columns(2)



legend_config = dict(title_text='', orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=14))



# Chart 1 (Top-Left): Total Cost Through Contract

with row1_col1:

    st.subheader("Total Cost Through Contract")

    tco_list = {f"{pp_unit_label} TCO": tco_pp_unit, "Scheduled Flat Fee TCO": tco_scheduled, "Single Flat Fee TCO": single_flat_fee_tco}

    tco_df = pd.DataFrame(list(tco_list.items()), columns=['Pricing Model', 'Total Cost'])

    tco_df['Pricing Model'] = tco_df['Pricing Model'].str.replace(' TCO', '')

    tco_df_filtered = tco_df[tco_df['Pricing Model'].isin(models_to_plot)]

    

    fig_tco_bar = px.bar(tco_df_filtered, x='Pricing Model', y='Total Cost', color='Pricing Model', labels={'Total Cost': f'Total Cost ({currency})'}, text_auto='.2s', color_discrete_map=color_map, category_orders={"Pricing Model": category_order_for_plots})

    fig_tco_bar.update_traces(textfont_size=16, textposition='inside', textfont=dict(color='white'))

    fig_tco_bar.update_yaxes(tickformat=',')

    fig_tco_bar.update_xaxes(title_text="", tickfont_size=14)

    fig_tco_bar.update_layout(legend=legend_config)



    line_style = dict(color="grey", dash="dash", width=1)

    if enable_scheduled_fee:

        if tco_pp_unit > tco_scheduled > 0:

            saving = ((tco_pp_unit - tco_scheduled) / tco_pp_unit) * 100

            fig_tco_bar.add_shape(type="line", x0=0, y0=tco_pp_unit, x1=1, y1=tco_pp_unit, line=line_style)

            fig_tco_bar.add_shape(type="line", x0=1, y0=tco_pp_unit, x1=1, y1=tco_scheduled, line=line_style)

            # --- MODIFICATION: Changed x position to align with the vertical line ---

            fig_tco_bar.add_annotation(x=1, y=tco_pp_unit, text=f"<b>-{saving:.1f}%</b>", showarrow=False, yshift=10, xshift=-10, xanchor='right', font=dict(color="#186e80", size=14))

        if tco_scheduled > single_flat_fee_tco > 0:

            saving = ((tco_scheduled - single_flat_fee_tco) / tco_scheduled) * 100

            fig_tco_bar.add_shape(type="line", x0=1, y0=tco_scheduled, x1=2, y1=tco_scheduled, line=line_style)

            fig_tco_bar.add_shape(type="line", x0=2, y0=tco_scheduled, x1=2, y1=single_flat_fee_tco, line=line_style)

            # --- MODIFICATION: Changed x position to align with the vertical line ---

            fig_tco_bar.add_annotation(x=2, y=tco_scheduled, text=f"<b>-{saving:.1f}%</b>", showarrow=False, yshift=10, xshift=-10, xanchor='right', font=dict(color="#4fb18c", size=14))

        if tco_pp_unit > single_flat_fee_tco > 0:

            total_saving = ((tco_pp_unit - single_flat_fee_tco) / tco_pp_unit) * 100

            fig_tco_bar.add_shape(type="line", x0=0, y0=tco_pp_unit, x1=2, y1=tco_pp_unit, line=line_style)

            fig_tco_bar.add_shape(type="line", x0=2, y0=tco_pp_unit, x1=2, y1=single_flat_fee_tco, line=line_style)

            fig_tco_bar.add_annotation(x=2, y=tco_pp_unit, text=f"<b>-{total_saving:.1f}%</b>", showarrow=False, yshift=10, xshift=-20, font=dict(color="#4fb18c", size=14))

    else:

        if tco_pp_unit > single_flat_fee_tco > 0:

            saving = ((tco_pp_unit - single_flat_fee_tco) / tco_pp_unit) * 100

            fig_tco_bar.add_shape(type="line", x0=0, y0=tco_pp_unit, x1=1, y1=tco_pp_unit, line=line_style)

            fig_tco_bar.add_shape(type="line", x0=1, y0=tco_pp_unit, x1=1, y1=single_flat_fee_tco, line=line_style)

            fig_tco_bar.add_annotation(x=1, y=tco_pp_unit, text=f"<b>-{saving:.1f}%</b>", showarrow=False, yshift=10, xshift=-20, font=dict(color="#4fb18c", size=14))



    st.plotly_chart(fig_tco_bar, use_container_width=True)



# Chart 2 (Top-Right): Monthly Cost of Contract

with row1_col2:

    st.subheader("Monthly Cost of Contract")

    plot_df_monthly = cost_df.melt(id_vars='Month', value_vars=models_to_plot, var_name='Pricing Model', value_name='Monthly Cost')

    fig_monthly = px.line(plot_df_monthly, x='Month', y='Monthly Cost', color='Pricing Model', labels={'Monthly Cost': f'Monthly Cost ({currency})'}, color_discrete_map=color_map)

    if 'Scheduled Flat Fee' in models_to_plot:

        fig_monthly.update_traces(selector={"name": "Scheduled Flat Fee"}, line_shape='hv')

    fig_monthly.update_traces(selector={"name": pp_unit_label}, line_shape='hv')

    fig_monthly.update_yaxes(tickformat=',')

    fig_monthly.update_layout(legend=legend_config)

    st.plotly_chart(fig_monthly, use_container_width=True)



# Chart 3 (Bottom-Left): Effective Cost of Contract per Unit

with row2_col1:

    st.subheader(f"Effective Cost of Contract per {unit_of_measure}")

    total_unit_months = cost_df[f'Onboarded {unit_plural}'].sum()

    if total_unit_months > 0:

        avg_price_pp_unit = price_per_unit

        avg_price_scheduled = tco_scheduled / total_unit_months if enable_scheduled_fee else 0

        avg_price_single_flat = single_flat_fee_tco / total_unit_months

    else:

        avg_price_pp_unit, avg_price_scheduled, avg_price_single_flat = price_per_unit, 0, 0

    

    bar_data = {'Pricing Model': [pp_unit_label, 'Scheduled Flat Fee', 'Single Flat Fee'], f'Average Price Per {unit_of_measure}': [avg_price_pp_unit, avg_price_scheduled, avg_price_single_flat]}

    bar_df = pd.DataFrame(bar_data)

    bar_df_filtered = bar_df[bar_df['Pricing Model'].isin(models_to_plot)]

    

    fig_bar = px.bar(bar_df_filtered, x='Pricing Model', y=f'Average Price Per {unit_of_measure}', color='Pricing Model', labels={f'Average Price Per {unit_of_measure}': f'Avg. Price/{unit_of_measure} ({currency})'}, text_auto=True, color_discrete_map=color_map, category_orders={"Pricing Model": category_order_for_plots})

    fig_bar.update_traces(texttemplate='%{value:,.0f}', textfont_size=16, textposition='inside', textfont=dict(color='white'))

    fig_bar.update_yaxes(tickformat=',')

    fig_bar.update_xaxes(title_text="", tickfont_size=14)

    fig_bar.update_layout(legend=legend_config)



    line_style = dict(color="grey", dash="dash", width=1)

    if enable_scheduled_fee:

        if avg_price_pp_unit > avg_price_scheduled > 0:

            saving = ((avg_price_pp_unit - avg_price_scheduled) / avg_price_pp_unit) * 100

            fig_bar.add_shape(type="line", x0=0, y0=avg_price_pp_unit, x1=1, y1=avg_price_pp_unit, line=line_style)

            fig_bar.add_shape(type="line", x0=1, y0=avg_price_pp_unit, x1=1, y1=avg_price_scheduled, line=line_style)

            # --- MODIFICATION: Changed x position to align with the vertical line ---

            fig_bar.add_annotation(x=1, y=avg_price_pp_unit, text=f"<b>-{saving:.1f}%</b>", showarrow=False, yshift=10, xshift=-10, xanchor='right', font=dict(color="#186e80", size=14))

        if avg_price_scheduled > avg_price_single_flat > 0:

            saving = ((avg_price_scheduled - avg_price_single_flat) / avg_price_scheduled) * 100

            fig_bar.add_shape(type="line", x0=1, y0=avg_price_scheduled, x1=2, y1=avg_price_scheduled, line=line_style)

            fig_bar.add_shape(type="line", x0=2, y0=avg_price_scheduled, x1=2, y1=avg_price_single_flat, line=line_style)

            # --- MODIFICATION: Changed x position to align with the vertical line ---

            fig_bar.add_annotation(x=2, y=avg_price_scheduled, text=f"<b>-{saving:.1f}%</b>", showarrow=False, yshift=10, xshift=-10, xanchor='right', font=dict(color="#4fb18c", size=14))

        if avg_price_pp_unit > avg_price_single_flat > 0:

            total_saving = ((avg_price_pp_unit - avg_price_single_flat) / avg_price_pp_unit) * 100

            fig_bar.add_shape(type="line", x0=0, y0=avg_price_pp_unit, x1=2, y1=avg_price_pp_unit, line=line_style)

            fig_bar.add_shape(type="line", x0=2, y0=avg_price_pp_unit, x1=2, y1=avg_price_single_flat, line=line_style)

            fig_bar.add_annotation(x=2, y=avg_price_pp_unit, text=f"<b>-{total_saving:.1f}%</b>", showarrow=False, yshift=10, xshift=-20, font=dict(color="#4fb18c", size=14))

    else:

        if avg_price_pp_unit > avg_price_single_flat > 0:

            saving = ((avg_price_pp_unit - avg_price_single_flat) / avg_price_pp_unit) * 100

            fig_bar.add_shape(type="line", x0=0, y0=avg_price_pp_unit, x1=1, y1=avg_price_pp_unit, line=line_style)

            fig_bar.add_shape(type="line", x0=1, y0=avg_price_pp_unit, x1=1, y1=avg_price_single_flat, line=line_style)

            fig_bar.add_annotation(x=1, y=avg_price_pp_unit, text=f"<b>-{saving:.1f}%</b>", showarrow=False, yshift=10, xshift=-20, font=dict(color="#4fb18c", size=14))

    

    st.plotly_chart(fig_bar, use_container_width=True)



# Chart 4 (Bottom-Right): Cumulative Cost of Contract

with row2_col2:

    st.subheader("Cumulative Cost of Contract")

    cumulative_cols_to_plot = [f'Cumulative {model}' for model in models_to_plot]

    plot_df_cumulative = cost_df.melt(id_vars='Month', value_vars=cumulative_cols_to_plot, var_name='Pricing Model', value_name='Cumulative Cost')

    plot_df_cumulative['Pricing Model'] = plot_df_cumulative['Pricing Model'].str.replace('Cumulative ', '')

    fig_cumulative = px.line(plot_df_cumulative, x='Month', y='Cumulative Cost', color='Pricing Model', labels={'Cumulative Cost': f'Cumulative Cost ({currency})'}, color_discrete_map=color_map)

    fig_cumulative.update_yaxes(tickformat=',')

    fig_cumulative.update_layout(legend=legend_config)

    st.plotly_chart(fig_cumulative, use_container_width=True)





# --- DATA TABLE ---

st.markdown("---")

st.header("🔢 Detailed Data Breakdown")

with st.expander("Click to view the month-by-month data"):

    display_df = cost_df.copy()

    if not enable_scheduled_fee:

        display_df = display_df.drop(columns=['Scheduled Flat Fee', 'Cumulative Scheduled Flat Fee'])

    for col in display_df.columns:

        if col not in ['Month', f'Onboarded {unit_plural}']:

            display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}")

    st.dataframe(display_df, use_container_width=True)
