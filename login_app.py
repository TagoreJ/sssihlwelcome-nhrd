import streamlit as st
import requests
import random
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from authlib.integrations.requests_client import OAuth2Session

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SSIHL × NHRD Check-In",
    page_icon="🎓",
    layout="centered",
)

# ── Secrets ───────────────────────────────────────────────────────────────────
CLIENT_ID     = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
FAST2SMS_KEY  = st.secrets["FAST2SMS_KEY"]

# ⬇️  Update this to your Streamlit Cloud login app URL after deploying
REDIRECT_URI = "https://sssihlxnhrd.streamlit.app/"

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

GSCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
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


def get_user_by_email(email: str):
    records = get_sheet().worksheet("users").get_all_records()
    for r in records:
        if r["email"].strip().lower() == email.strip().lower():
            return r
    return None


def get_user_by_phone(phone: str):
    records = get_sheet().worksheet("users").get_all_records()
    for r in records:
        if str(r["mobile"]).strip() == str(phone).strip():
            return r
    return None


def log_checkin(name: str, email: str, method: str):
    get_sheet().worksheet("checkins").append_row([
        name, email, method,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ])


def send_otp(phone: str, otp: str) -> bool:
    try:
        resp = requests.get(
            "https://www.fast2sms.com/dev/bulkV2",
            params={
                "authorization": FAST2SMS_KEY,
                "variables_values": otp,
                "route": "otp",
                "numbers": phone,
            },
            timeout=10,
        )
        return resp.ok
    except Exception:
        return False


# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .event-header {
        background: linear-gradient(135deg, #0077B6 0%, #1a1a2e 100%);
        border-radius: 16px;
        padding: 32px 24px 24px;
        text-align: center;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0,119,182,0.25);
    }
    .event-header h1 { font-size: 1.85rem; margin: 0 0 4px; }
    .event-header h2 { font-size: 1.3rem; font-weight: 400; opacity: 0.9; margin: 0 0 8px; }
    .event-header p  { font-size: 0.95rem; opacity: 0.75; margin: 0; }

    .g-btn a {
        display: block;
        background: #4285F4;
        color: white !important;
        text-decoration: none;
        padding: 14px;
        border-radius: 10px;
        font-size: 1rem;
        font-weight: 600;
        text-align: center;
        margin: 24px auto;
        max-width: 320px;
        box-shadow: 0 4px 14px rgba(66,133,244,0.4);
        transition: opacity 0.2s;
    }
    .g-btn a:hover { opacity: 0.88; }

    .welcome-box {
        background: linear-gradient(135deg, #00b09b, #96c93d);
        border-radius: 12px;
        padding: 22px 20px;
        text-align: center;
        color: white;
        font-size: 1.2rem;
        font-weight: 700;
        margin-top: 16px;
    }
    .welcome-box span { font-size: 0.9rem; font-weight: 400; opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="event-header">
    <h1>🎓 Welcome to</h1>
    <h2>SSIHL × NHRD Event</h2>
    <p>Please check in before entering the venue 🙏</p>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🔵 Login via Google", "📱 Login via Phone OTP"])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — GOOGLE LOGIN
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    code = st.query_params.get("code")

    # Step 1 — Show sign-in button
    if "google_token" not in st.session_state and not code:
        oauth           = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                                        redirect_uri=REDIRECT_URI,
                                        scope="openid email profile")
        auth_url, state = oauth.create_authorization_url(GOOGLE_AUTH_URL)
        st.session_state["g_state"] = state

        st.markdown(f"""
        <div class="g-btn">
            <a href="{auth_url}" target="_self">🔵 Sign in with Google</a>
        </div>
        <p style="text-align:center;color:#888;font-size:0.85rem;">
            Use the Google account registered for this event
        </p>
        """, unsafe_allow_html=True)

    # Step 2 — Handle OAuth callback
    if code and "google_token" not in st.session_state:
        with st.spinner("Verifying with Google…"):
            try:
                oauth = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                                      redirect_uri=REDIRECT_URI)
                token = oauth.fetch_token(GOOGLE_TOKEN_URL, code=code)
                st.session_state["google_token"] = token["access_token"]
                st.rerun()
            except Exception as exc:
                st.error(f"Google login failed: {exc}")

    # Step 3 — Fetch profile and check in
    if "google_token" in st.session_state:
        if "google_user" not in st.session_state:
            headers = {"Authorization": f"Bearer {st.session_state['google_token']}"}
            st.session_state["google_user"] = requests.get(
                GOOGLE_USER_URL, headers=headers
            ).json()

        email = st.session_state["google_user"].get("email", "")
        user  = get_user_by_email(email)

        if user:
            # Log only once per session
            if f"logged_{email}" not in st.session_state:
                log_checkin(user["name"], user["email"], "Google")
                st.session_state[f"logged_{email}"] = True

            st.markdown(f"""
            <div class="welcome-box">
                ✅ Welcome, {user['name']}!<br>
                <span>{user['designation']} · {user['organization']}</span>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
            st.info("💻 Your profile card is now live on the event screen!")
        else:
            st.error("❌ Your Google account is not registered for this event.")
            st.caption(f"Tried: `{email}`")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — PHONE OTP
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("##### Enter your registered mobile number")
    phone = st.text_input("Mobile Number", max_chars=10,
                          placeholder="98XXXXXXXX",
                          label_visibility="collapsed")

    if st.button("📨 Send OTP", use_container_width=True):
        if len(phone) == 10 and phone.isdigit():
            user = get_user_by_phone(phone)
            if user:
                otp = str(random.randint(100000, 999999))
                st.session_state["otp"]       = otp
                st.session_state["otp_phone"] = phone
                if send_otp(phone, otp):
                    st.success("✅ OTP sent! Check your SMS.")
                else:
                    st.warning("⚠️ SMS delivery failed — try Google login or ask the desk.")
            else:
                st.error("❌ This number is not registered for the event.")
        else:
            st.warning("⚠️ Enter a valid 10-digit mobile number.")

    if "otp" in st.session_state:
        st.markdown("---")
        entered = st.text_input("Enter OTP", max_chars=6, type="password",
                                placeholder="6-digit OTP")
        if st.button("✅ Verify & Check In", use_container_width=True):
            if entered == st.session_state["otp"]:
                user = get_user_by_phone(st.session_state["otp_phone"])
                if f"logged_{user['email']}" not in st.session_state:
                    log_checkin(user["name"], user["email"], "Phone OTP")
                    st.session_state[f"logged_{user['email']}"] = True

                st.markdown(f"""
                <div class="welcome-box">
                    ✅ Welcome, {user['name']}!<br>
                    <span>{user['designation']} · {user['organization']}</span>
                </div>
                """, unsafe_allow_html=True)
                st.balloons()
                st.info("💻 Your profile card is now live on the event screen!")
                del st.session_state["otp"]
                del st.session_state["otp_phone"]
            else:
                st.error("❌ Wrong OTP. Please try again.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<hr style="margin-top:48px;opacity:0.15;" />
<p style="text-align:center;color:#aaa;font-size:0.78rem;">
SSIHL × NHRD · Powered by Streamlit
</p>
""", unsafe_allow_html=True)
