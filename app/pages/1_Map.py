import streamlit as st
from utils.predictor import predict_needs
from utils.map_utils import create_map

def show_map():
    st.header("Opportunities Map")
    try:
        df = predict_needs(None)
    except Exception as e:
        st.error(f"Cannot load scores: {e}")
        return

    st.write(df.head())
    m = create_map(df)
    st.components.v1.html(m.get_root().render(), height=600)
import pandas as pd
import folium
from folium import Popup
from streamlit_folium import st_folium

def _marker_color(row):
    try:
        if str(row.get("active_posting","False")).lower() in ["1","true","yes"]:
            return "green"
        if str(row.get("high_likelihood","False")).lower() in ["1","true","yes"]:
            return "red"
        if str(row.get("specialty","HO")).upper() == "PDH":
            return "lightblue"
    except Exception:
        pass
    return "yellow"

def show_map():
    df = pd.read_csv("app/data/processed/scores_latest.csv")
    # Basic validation
    if df.empty:
        return None

    # Center map
    if "lat" in df.columns and "lon" in df.columns:
        center = [df["lat"].astype(float).mean(), df["lon"].astype(float).mean()]
    else:
        center = [39.5, -98.35]

    m = folium.Map(location=center, zoom_start=6)

    # Load contacts if present
    try:
        contacts = pd.read_csv("app/data/processed/contacts.csv")
    except Exception:
        contacts = pd.DataFrame()

    for _, r in df.iterrows():
        try:
            lat = float(r.get("lat", 0))
            lon = float(r.get("lon", 0))
        except Exception:
            continue
        color = _marker_color(r)
        import pandas as pd
        import folium
        from folium import Popup
        from streamlit_folium import st_folium


        def color_for_row(row):
            # green: active posting
            if str(row.get("active_posting", False)).lower() in ["1", "true", "yes"]:
                return "green"
            # red: model predicts high likelihood
            if str(row.get("high_likelihood", False)).lower() in ["1", "true", "yes"]:
                return "red"
            # specialty-based colors
            spec = str(row.get("specialty", "")).upper()
            if spec == "HO":
                return "yellow"
            if spec == "PDH":
                return "lightblue"
            return "gray"


        def build_popup(row, contacts_df=None):
            lines = []
            lines.append(f"<b>{row.get('facility_name','')}</b>")
            lines.append(f"Score: {float(row.get('score',0)):.2f}")

            if contacts_df is not None and not contacts_df.empty:
                subset = contacts_df[contacts_df['facility_id'] == row.get('facility_id')]
                if not subset.empty:
                    lines.append('<hr>')
                    for _, c in subset.sort_values(['contact_rank','last_verified'], ascending=[True, False]).head(4).iterrows():
                        name = f"{c.get('first_name','')} {c.get('last_name','')}"
                        title = c.get('title','') or ''
                        email = c.get('email','') or ''
                        phone = c.get('phone','') or ''
                        mobile = c.get('mobile','') or ''
                        contact_line = f"<b>{name}</b> — {title}<br/>{email}<br/>{phone}{(' • ' + mobile) if mobile else ''}"
                        lines.append(contact_line)

            # Cold-Call Prep placeholder
            lines.append('<hr>')
            lines.append('<i>Cold-Call Prep: check recent postings, outreach history, and notes in the facility profile.</i>')
            return '<br/>'.join(lines)


        def show_map():
            df = pd.read_csv('app/data/processed/scores_latest.csv')
            try:
                contacts = pd.read_csv('app/data/processed/contacts.csv')
            except Exception:
                contacts = pd.DataFrame()

            if df.empty:
                st_folium(folium.Map(location=[39.5, -98.35], zoom_start=4), width=700, height=500)
                return

            center = [df['lat'].astype(float).mean() if 'lat' in df.columns else 39.5,
                      df['lon'].astype(float).mean() if 'lon' in df.columns else -98.35]
            m = folium.Map(location=center, zoom_start=5)

            for _, r in df.iterrows():
                try:
                    lat = float(r.get('lat', 0))
                    lon = float(r.get('lon', 0))
                except Exception:
                    continue
                color = color_for_row(r)
                popup = build_popup(r, contacts)
                folium.CircleMarker(location=[lat, lon], radius=7, color=color, fill=True, fill_color=color,
                                    popup=Popup(popup, max_width=400)).add_to(m)

            st_folium(m, width=900, height=600)
