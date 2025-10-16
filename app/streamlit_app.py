import streamlit as st
import pandas as pd
from utils.map_utils import create_map
from utils.predictor import predict_needs

st.set_page_config(page_title="Locum Tracker", layout="wide")

st.title("Hospitalist & Pediatric Hospitalist Locum Tracker")

uploaded_file = st.file_uploader("Upload job data Excel file", type=["xlsx"])
if uploaded_file:
    data = pd.read_excel(uploaded_file, engine="openpyxl")
    filtered = st.multiselect("Filter by Specialty", options=data['Specialty'].unique())
    if filtered:
        data = data[data['Specialty'].isin(filtered)]

    data = predict_needs(data)
    st.dataframe(data)

    st.subheader("Interactive Map")
    map_html = create_map(data).get_root().render()
    st.components.v1.html(map_html, height=600)

    st.subheader("Calendar View (Coming Soon)")
    st.info("Calendar integration will show predicted openings by date.")

    st.subheader("Contact Outreach Tracker")
    st.write(data[['Facility Name', 'Contact Name', 'Contact Email', 'Predicted Need']])
import streamlit as st
from app.pages import _1_Map

st.set_page_config(page_title="Locums Map", layout="wide")

st.title("Locums Opportunities Map")
st.markdown("Use the map to explore top opportunities. Markers: Green=Active posting, Red=High likelihood, Yellow=HO, Light Blue=PDH.")

with st.sidebar:
    st.header("Controls")
    st.write("No controls yet. Add filters in the Map page later.")

import streamlit as st
import pandas as pd
from utils.map_utils import create_map
from utils.predictor import predict_needs

st.set_page_config(page_title="Locum Tracker", layout="wide")

st.title("Hospitalist & Pediatric Hospitalist Locum Tracker")

uploaded_file = st.file_uploader("Upload job data Excel file", type=["xlsx"]) 
if uploaded_file:
    data = pd.read_excel(uploaded_file, engine="openpyxl")
    filtered = st.multiselect("Filter by Specialty", options=data['Specialty'].unique())
    if filtered:
        data = data[data['Specialty'].isin(filtered)]

    data = predict_needs(data)
    st.dataframe(data)

    st.subheader("Interactive Map")
    m = create_map(data)
    map_html = m.get_root().render()
    st.components.v1.html(map_html, height=600)

    st.subheader("Calendar View (Coming Soon)")
    st.info("Calendar integration will show predicted openings by date.")

    st.subheader("Contact Outreach Tracker")
    # best effort to show common columns
    cols = [c for c in ['Facility Name', 'Contact Name', 'Contact Email', 'Predicted Need'] if c in data.columns]
    if cols:
        st.write(data[cols])
    else:
        st.write("No contact columns available in uploaded data.")

else:
    st.info("Upload an Excel file to begin or ensure scores are generated in app/data/processed/scores_latest.csv and use the 'Run Predictor' button.")

if st.button("Load latest scores and show map"):
    try:
        df = predict_needs(None)
        st.write(df.head())
        m = create_map(df)
        st.components.v1.html(m.get_root().render(), height=600)
    except Exception as e:
        st.error(str(e))
