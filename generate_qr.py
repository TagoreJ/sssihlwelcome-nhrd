import qrcode

# ── Replace with your actual login app URL after deploying ────────────────────
APP_URL = "https://ssihl-login.streamlit.app/"

img = qrcode.make(APP_URL)
img.save("event_qr.png")
print("✅ QR code saved as event_qr.png")
print("   Print it and place at the venue entrance / registration desk.")
