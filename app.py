import streamlit as st
import pandas as pd
import numpy as np

# 1. PAGE SETUP
st.set_page_config(page_title="ACE Project Leads", layout="wide")

# Google Sheets CSV Link
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRa24rAJi4KblnAu8PythuMYMjU2Uf35YMGbkg4Ze2shIk3zqTSZIAc9c0MfqjMz-z4FTGhtKPfj75H/pub?gid=1049124143&single=true&output=csv"

# 2. LOAD DATA FROM WEB
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        if '__lp_created_date__1' in df.columns:
            df['__lp_created_date__1'] = pd.to_datetime(df['__lp_created_date__1'])
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

st.title("📊 ACE Project Leads")

if df.empty:
    st.stop() # Stop the app if no data is found

# 3. FILTERS (SIDEBAR)
st.sidebar.header("🔍 Filters")

min_date = df['__lp_created_date__1'].min().date() if pd.notnull(df['__lp_created_date__1'].min()) else None
max_date = df['__lp_created_date__1'].max().date() if pd.notnull(df['__lp_created_date__1'].max()) else None

if min_date and max_date:
    date_range = st.sidebar.date_input("Creation Date Range:", [min_date, max_date])
else:
    date_range = []

available_regions = df['Region'].dropna().unique().tolist()
selected_regions = st.sidebar.multiselect("Select Region(s):", available_regions, default=available_regions)

# 4. APPLY FILTERS
df_filtered = df.copy()

if len(date_range) == 2:
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    df_filtered = df_filtered[(df_filtered['__lp_created_date__1'] >= start_date) & (df_filtered['__lp_created_date__1'] <= end_date)]

if selected_regions:
    df_filtered = df_filtered[df_filtered['Region'].isin(selected_regions)]

# 5. AGGREGATION ENGINE (Rebuilding the Pivots)
if not df_filtered.empty:
    base_agg = df_filtered.groupby('Region').agg(
        Leads_Claimed=('__opp_id__1', 'count'),
        Is_Eligible=('Is Eligible', 'mean'),
        Is_Not_Started=('Is Not Started', 'mean'),
        Is_Abandoned=('Is Abandoned', 'mean'),
        NA_Number=('Has Need Ass', 'sum'),
        AS_Number=('Has Appt Set', 'sum'),
        Pitch_Number=('Has Pitch', 'sum'),
        CW_Number=('Has CW', 'sum'),
        AVG_TT_Pitch=('Days to Pitch', 'mean'),
        AVG_TT_CW=('Days to CW', 'mean')
    ).reset_index()

    total_row = pd.DataFrame({
        'Region': ['Grand Total'],
        'Leads_Claimed': [df_filtered['__opp_id__1'].count()],
        'Is_Eligible': [df_filtered['Is Eligible'].mean()],
        'Is_Not_Started': [df_filtered['Is Not Started'].mean()],
        'Is_Abandoned': [df_filtered['Is Abandoned'].mean()],
        'NA_Number': [df_filtered['Has Need Ass'].sum()],
        'AS_Number': [df_filtered['Has Appt Set'].sum()],
        'Pitch_Number': [df_filtered['Has Pitch'].sum()],
        'CW_Number': [df_filtered['Has CW'].sum()],
        'AVG_TT_Pitch': [df_filtered['Days to Pitch'].mean()],
        'AVG_TT_CW': [df_filtered['Days to CW'].mean()]
    })
    
    df_metrics = pd.concat([base_agg, total_row], ignore_index=True)
    
    # Calculated Fields for Performance
    df_metrics['Eligible > NA'] = np.where((df_metrics['Leads_Claimed'] * df_metrics['Is_Eligible']) > 0, df_metrics['NA_Number'] / (df_metrics['Leads_Claimed'] * df_metrics['Is_Eligible']), 0)
    df_metrics['NA > AS'] = np.where(df_metrics['NA_Number'] > 0, df_metrics['AS_Number'] / df_metrics['NA_Number'], 0)
    df_metrics['AS > Pitch'] = np.where(df_metrics['AS_Number'] > 0, df_metrics['Pitch_Number'] / df_metrics['AS_Number'], 0)
    df_metrics['Pitch > CW'] = np.where(df_metrics['Pitch_Number'] > 0, df_metrics['CW_Number'] / df_metrics['Pitch_Number'], 0)

    # 6. UI: TABS (The 3 Panels)
    tab1, tab2, tab3 = st.tabs(["📊 Usage", "📈 Performance", "⏱️ Velocity"])
    
    with tab1:
        st.subheader("Usage Dashboard")
        df_usage = df_metrics[['Region', 'Leads_Claimed', 'Is_Eligible', 'Is_Not_Started', 'Is_Abandoned', 'NA_Number', 'AS_Number', 'Pitch_Number', 'CW_Number']].copy()
        df_usage.columns = ['Region', 'Leads Claimed', '% Eligibility', '% Not Started', '% Abandoned', 'NA Number', 'AS Number', 'Pitch Number', 'CW Number']
        st.dataframe(df_usage.style.format({'% Eligibility': '{:.2%}', '% Not Started': '{:.2%}', '% Abandoned': '{:.2%}'}), use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Performance Dashboard")
        df_perf = df_metrics[['Region', 'Eligible > NA', 'NA > AS', 'AS > Pitch', 'Pitch > CW']].copy()
        st.dataframe(df_perf.style.format({'Eligible > NA': '{:.2%}', 'NA > AS': '{:.2%}', 'AS > Pitch': '{:.2%}', 'Pitch > CW': '{:.2%}'}), use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Velocity Dashboard")
        df_velocity = df_metrics[['Region', 'AVG_TT_Pitch', 'AVG_TT_CW']].copy()
        df_velocity.columns = ['Region', 'AVG TT Pitch (Days)', 'AVG TT CW (Days)']
        st.dataframe(df_velocity.style.format({'AVG TT Pitch (Days)': '{:.1f}', 'AVG TT CW (Days)': '{:.1f}'}, na_rep="-"), use_container_width=True, hide_index=True)
else:
    st.warning("No data found for the selected filters.")
