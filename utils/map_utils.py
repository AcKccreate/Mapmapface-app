import folium
from folium.features import DivIcon
from folium import Popup
import pandas as pd
import os


def _choose_color(row):
    # Green if active_posting, Red if high_likelihood, otherwise Yellow for HO and LightBlue for PDH
    try:
        if bool(row.get("active_posting", False)):
            return "green"
        if bool(row.get("high_likelihood", False)):
            return "red"
        spec = str(row.get("specialty", "")).upper()
        if spec == "PDH":
            return "lightblue"
        return "yellow"
    except Exception:
        return "gray"


def _format_contacts_html(contacts_df):
    lines = []
    for _, c in contacts_df.iterrows():
        name = " ".join([str(c.get('first_name','')).strip(), str(c.get('last_name','')).strip()]).strip()
        title = c.get('title','')
        email = c.get('email','')
        phone = c.get('phone','')
        ext = c.get('ext','')
        mobile = c.get('mobile','')
        pieces = []
        if name:
            pieces.append(f"<b>{name}</b>")
        if title:
            pieces.append(title)
        top = " — ".join(pieces) if pieces else ""
        contact_lines = top
        if email and email not in ['nan','']:
            contact_lines += f"<br>📧 <a href='mailto:{email}'>{email}</a>"
        phone_line = ""
        if phone and phone not in ['nan','']:
            phone_line = f"📞 {phone}"
            if ext and ext not in ['nan','']:
                phone_line += f" x{ext}"
        if mobile and mobile not in ['nan','']:
            phone_line += (" • " if phone_line else "") + f"📱 {mobile}"
        if phone_line:
            contact_lines += f"<br>{phone_line}"
        lines.append(contact_lines)
    return "<br><div style='margin-top:6px;'>" + "<hr style='border:none;border-top:1px solid #eee'/>".join([f"<div style='font-size:13px;color:#222'>{l}</div>" for l in lines]) + "</div>" if lines else ""


def create_map(df, contacts_path="app/data/processed/contacts.csv"):
    # Center map on mean lat/lon if available
    lat = df["lat"].dropna() if "lat" in df.columns else []
    lon = df["lon"].dropna() if "lon" in df.columns else []
    if len(lat) and len(lon):
        center = [lat.mean(), lon.mean()]
    else:
        center = [39.5, -98.35]  # center of US fallback

    # attempt to load contacts file if present
    contacts = None
    if contacts_path and os.path.exists(contacts_path):
        try:
            contacts = pd.read_csv(contacts_path)
        except Exception:
            contacts = None

    m = folium.Map(location=center, zoom_start=6)

    for _, r in df.iterrows():
        try:
            color = _choose_color(r)
            fname = r.get('facility_name','Unknown')
            score = float(r.get('score',0)) if r.get('score',None) is not None else 0.0
            spec = r.get('specialty','')

            # Cold-call prep pieces
            prep = []
            if 'likely_procedures' in r and r.get('likely_procedures'):
                prep.append(f"Likely procedures: {r.get('likely_procedures')}")
            if 'avg_volume' in r and r.get('avg_volume'):
                prep.append(f"Avg volume: {r.get('avg_volume')}")
            if 'pay_expect' in r and r.get('pay_expect'):
                prep.append(f"Pay: {r.get('pay_expect')}")
            prep_html = "<br>".join(prep) if prep else ""

            # contacts
            contact_html = ""
            if contacts is not None and 'facility_id' in contacts.columns and 'facility_id' in r:
                subset = contacts[(contacts['facility_id'] == r.get('facility_id')) & (contacts.get('specialty', pd.Series()).fillna('') == spec)].copy()
                if subset.empty:
                    # try by facility only
                    subset = contacts[contacts['facility_id'] == r.get('facility_id')].copy()
                if not subset.empty:
                    subset = subset.sort_values(['contact_rank','last_verified'] if 'contact_rank' in subset.columns else [], ascending=[True, False] if 'contact_rank' in subset.columns else [False])
                    subset = subset.head(4)
                    contact_html = _format_contacts_html(subset)

            popup_html = f"<div style='max-width:320px'><div style='font-weight:700;font-size:15px'>{fname}</div><div style='font-size:13px;color:#555'>Score: {score:.2f} • {spec}</div>"
            if prep_html:
                popup_html += f"<div style='margin-top:6px;font-size:13px;color:#333'>{prep_html}</div>"
            if contact_html:
                popup_html += f"<div style='margin-top:8px'><div style='font-weight:600'>Top contacts</div>{contact_html}</div>"
            else:
                popup_html += "<div style='margin-top:8px;color:#777;font-size:13px'>No contacts on file</div>"
            popup_html += "</div>"

            folium.CircleMarker(location=[r.get('lat', center[0]), r.get('lon', center[1])], radius=7, color=color, fill=True, fill_color=color, popup=Popup(popup_html, max_width=400)).add_to(m)
        except Exception:
            continue

    return m
