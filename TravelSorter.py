import streamlit as st
import pandas as pd
import io
from datetime import datetime, date

# Set page configuration
st.set_page_config(page_title="Travel Sorter", layout="wide")

st.title("✈️ Group Travel Sorter")
st.markdown("""
This tool groups individual traveler data by event.
1. Define your **Events**, **Cities**, and **Date Ranges** below.
2. Upload your **Travel Report** (CSV or Excel).
""")

# ==========================================
# 1. EVENT CONFIGURATION SECTION
# ==========================================
st.header("1. Define Events")
st.info("Tip: For 'Cities', you can enter multiple locations separated by a comma (e.g. 'Dallas, Ft. Worth').")

default_events = [
    {
        "Event Name": "Sacramento Event", 
        "Cities": "Sacramento", 
        "Start Date": date(2026, 3, 18), 
        "End Date": date(2026, 3, 24)
    },
    {
        "Event Name": "Phoenix Gathering", 
        "Cities": "Phoenix, Mesa", 
        "Start Date": date(2026, 4, 15), 
        "End Date": date(2026, 4, 21)
    },
    {
        "Event Name": "Ontario Convention", 
        "Cities": "Ontario", 
        "Start Date": date(2026, 4, 29), 
        "End Date": date(2026, 5, 5)
    }
]

column_config = {
    "Start Date": st.column_config.DateColumn("Start Date", format="YYYY-MM-DD"),
    "End Date": st.column_config.DateColumn("End Date", format="YYYY-MM-DD"),
    "Cities": st.column_config.TextColumn("Cities (comma-separated)"),
}

events_df = st.data_editor(
    pd.DataFrame(default_events),
    column_config=column_config,
    num_rows="dynamic",
    use_container_width=True
)

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def format_travel_time(date_val, time_val):
    """
    Takes raw date and time and converts to format: Friday March 19 12:36 pm
    """
    try:
        d_str = str(date_val).split(' ')[0]
        t_str = str(time_val)
        dt = pd.to_datetime(f"{d_str} {t_str}")
        formatted_str = dt.strftime("%A %B %d %I:%M %p")
        return formatted_str.replace("AM", "am").replace("PM", "pm")
    except:
        return f"{date_val} {time_val}"

# ==========================================
# 2. FILE UPLOAD SECTION
# ==========================================
st.header("2. Upload Travel Data")
uploaded_file = st.file_uploader("Upload Report", type=['csv', 'xlsx'])

# ==========================================
# 3. PROCESSING LOGIC
# ==========================================
if uploaded_file is not None and not events_df.empty:
    try:
        header_row_index = 0
        df = None

        # --- LOAD DATA ---
        if uploaded_file.name.endswith('.csv'):
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            lines = stringio.readlines()
            found = False
            for i, line in enumerate(lines):
                if line.startswith("Traveler Name"):
                    header_row_index = i
                    found = True
                    break
            if not found:
                st.error("Could not find 'Traveler Name' in the CSV.")
                st.stop()
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, skiprows=header_row_index)

        elif uploaded_file.name.endswith('.xlsx'):
            temp_df = pd.read_excel(uploaded_file, header=None)
            match = temp_df[temp_df.iloc[:, 0].astype(str) == "Traveler Name"]
            if not match.empty:
                header_row_index = match.index[0]
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, skiprows=header_row_index)
            else:
                st.error("Could not find 'Traveler Name' in Excel.")
                st.stop()

        # Cleanup
        df.columns = df.columns.str.strip()
        df['Arrival Date'] = pd.to_datetime(df['Arrival Date'])
        df['Departure Date'] = pd.to_datetime(df['Departure Date'])

        # --- RESULTS ---
        st.divider()
        st.header("3. Results")

        for index, event in events_df.iterrows():
            event_name = event['Event Name']
            
            # Parse Cities and Dates
            raw_cities = str(event['Cities'])
            target_cities = [c.strip() for c in raw_cities.split(',')]
            start_date = event['Start Date']
            end_date = event['End Date']

            # Filter Arrivals (Destination matches City List AND Date in Range)
            arrivals = df[
                (df['Arrival City'].isin(target_cities)) & 
                (df['Arrival Date'].dt.date >= start_date) & 
                (df['Arrival Date'].dt.date <= end_date)
            ].copy()

            # Filter Departures (Origin matches City List AND Date in Range)
            departures = df[
                (df['Departure City Name'].isin(target_cities)) & 
                (df['Departure Date'].dt.date >= start_date) & 
                (df['Departure Date'].dt.date <= end_date)
            ].copy()

            if arrivals.empty:
                continue
            
            report_data = []

            for _, row in arrivals.iterrows():
                name = row['Traveler Name']
                home_city = row['Departure City Name'] 
                
                # Arrival Details
                arr_formatted = format_travel_time(row['Arrival Date'], row['Arrival Time'])
                arr_flight = f"{row['Airline Code']} {row['Flight Number']}"
                arr_airport = row.get('Arrive Airport', '-') # The airport they land AT
                
                # Departure Details
                person_dep = departures[departures['Traveler Name'] == name]
                
                if not person_dep.empty:
                    dep_row = person_dep.iloc[0]
                    dep_formatted = format_travel_time(dep_row['Departure Date'], dep_row['Departure Time'])
                    dep_flight = f"{dep_row['Airline Code']} {dep_row['Flight Number']}"
                    dep_airport = dep_row.get('Depart Airport', '-') # The airport they fly FROM
                else:
                    dep_formatted = "No Return Flight"
                    dep_flight = "-"
                    dep_airport = "-"

                report_data.append({
                    "Name": name,
                    "Home City": home_city,
                    "Arr Time": arr_formatted,
                    "Arr Flight": arr_flight,
                    "Arr Airport": arr_airport,
                    "Dep Time": dep_formatted,
                    "Dep Flight": dep_flight,
                    "Dep Airport": dep_airport
                })
            
            st.subheader(f"{event_name}")
            st.caption(f"Cities: {', '.join(target_cities)} | Dates: {start_date} to {end_date}")
            
            result_df = pd.DataFrame(report_data)
            st.dataframe(result_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"An error occurred: {e}")

elif uploaded_file is None:
    st.info("Awaiting file upload...")
