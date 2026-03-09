import streamlit as st
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="SSIHL × NHRD — Event Display",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Auto-refresh every 5 seconds ──────────────────────────────────────────────
st.markdown('<meta http-equiv="refresh" content="5">', unsafe_allow_html=True)

GSCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# ── Google Sheets connection ──────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_sheet():
    creds  = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=GSCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["SHEET_ID"])


def get_latest_checkin():
    rows = get_sheet().worksheet("checkins").get_all_records()
    return rows[-1] if rows else None


def get_user_by_email(email: str):
    records = get_sheet().worksheet("users").get_all_records()
    for r in records:
        if r["email"].strip().lower() == email.strip().lower():
            return r
    return None


def get_recent_checkins(n: int = 8):
    rows = get_sheet().worksheet("checkins").get_all_records()
    return list(reversed(rows[-n:])) if rows else []


# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background: #080818;
        color: white;
    }
    #MainMenu, footer, header { visibility: hidden; }

    .top-bar {
        background: linear-gradient(90deg, #0077B6 0%, #1a1a2e 100%);
        border-radius: 14px;
        padding: 18px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 28px rgba(0,119,182,0.3);
    }
    .top-bar h1 { margin: 0; font-size: 1.8rem; color: white; }
    .top-bar .clock { color: rgba(255,255,255,0.65); font-size: 0.95rem; }

    .checkin-banner {
        background: linear-gradient(135deg, #00b09b18, #96c93d18);
        border: 1px solid #00b09b44;
        border-radius: 14px;
        padding: 18px 24px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .pulse {
        width: 13px; height: 13px;
        background: #00b09b;
        border-radius: 50%;
        flex-shrink: 0;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0%,100% { opacity:1; transform:scale(1); }
        50%      { opacity:0.4; transform:scale(1.4); }
    }
    .b-name { font-size: 1.25rem; font-weight: 700; }
    .b-meta { font-size: 0.88rem; color: rgba(255,255,255,0.6); margin-top: 4px; }
    .badge {
        background: #0077B633;
        border: 1px solid #0077B666;
        border-radius: 6px;
        padding: 4px 12px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #4fc3f7;
        white-space: nowrap;
    }

    .profile-img img {
        border-radius: 14px;
        box-shadow: 0 8px 40px rgba(0,119,182,0.3);
        max-height: 68vh;
        object-fit: contain;
    }

    .waiting {
        text-align: center;
        color: rgba(255,255,255,0.28);
        font-size: 1.6rem;
        margin-top: 130px;
    }

    table.recent {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.88rem;
        margin-top: 8px;
    }
    table.recent th {
        color: rgba(255,255,255,0.4);
        text-align: left;
        padding: 6px 12px;
        border-bottom: 1px solid #222;
        font-weight: 500;
    }
    table.recent td {
        padding: 7px 12px;
        color: rgba(255,255,255,0.8);
        border-bottom: 1px solid #1a1a2e;
    }
</style>
""", unsafe_allow_html=True)

# ── Top bar ───────────────────────────────────────────────────────────────────
now = datetime.now().strftime("%A, %d %B %Y  ·  %I:%M %p")
st.markdown(f"""
<div class="top-bar">
    <h1>🎓 SSIHL × NHRD Event</h1>
    <span class="clock">🕐 {now}</span>
</div>
""", unsafe_allow_html=True)

# ── Main display ──────────────────────────────────────────────────────────────
try:
    latest = get_latest_checkin()

    if latest:
        user = get_user_by_email(latest["email"])

        name  = latest.get("name", "Guest")
        meth  = latest.get("method", "")
        ts    = latest.get("time", "")
        desg  = user.get("designation", "") if user else ""
        org   = user.get("organization", "") if user else ""
        role  = user.get("role", "") if user else ""

        # ── Check-in banner ───────────────────────────────────────────────────
        st.markdown(f"""
        <div class="checkin-banner">
            <div class="pulse"></div>
            <div style="flex:1;">
                <div class="b-name">✅ {name} just checked in!</div>
                <div class="b-meta">{desg} · {org}</div>
                <div class="b-meta" style="margin-top:5px;">🕐 {ts} &nbsp;|&nbsp; 📲 via {meth}</div>
            </div>
            <div class="badge">{role}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Profile image (Google Drive public URL) ───────────────────────────
        template_url = user.get("template_file", "") if user else ""
        if template_url:
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                st.markdown('<div class="profile-img">', unsafe_allow_html=True)
                st.image(template_url, use_column_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ No profile image found for this guest.")

        # ── Recent check-ins table ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📋 Recent Check-ins")
        recent = get_recent_checkins(8)
        if recent:
            rows_html = "".join(
                f"<tr><td>{r.get('name','')}</td>"
                f"<td>{r.get('method','')}</td>"
                f"<td>{r.get('time','')}</td></tr>"
                for r in recent
            )
            st.markdown(f"""
            <table class="recent">
              <thead><tr>
                <th>Name</th><th>Method</th><th>Time</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
            """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="waiting">⏳ Waiting for guests to check in…</div>
        """, unsafe_allow_html=True)

except Exception as exc:
    st.error(f"Display error: {exc}")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<hr style="margin-top:32px;border-color:#1a1a2e;" />
<p style="text-align:center;color:#333;font-size:0.76rem;">
SSIHL × NHRD · Event Display · Auto-refreshes every 5 s
</p>
""", unsafe_allow_html=True)
