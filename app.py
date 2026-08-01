import streamlit as st
import re
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from sms_utils import send_sms

# Streamlit Cloud servers run on UTC time, not Indian time.
# IST = UTC + 5 hours 30 minutes. We use this offset to show the correct local time.
IST = timezone(timedelta(hours=5, minutes=30))

# ------------------------------------------------------------------
# RideTag / OwnrTag — v2
# Change from v1: NO OTP (removed for smooth first-customer experience)
# Instead: just validate phone number FORMAT (is it a real-looking number?)
# Added: purpose selection + REAL email notification to the owner
# ------------------------------------------------------------------

st.set_page_config(page_title="OwnrTag", page_icon="🚗", layout="centered")

# ---- ALL VEHICLES/OWNERS LIVE HERE ----
# One app, many customers. Each customer gets a unique "vehicle" ID.
# To add a new customer: just add a new entry below with the next number.
VEHICLES = {
    "001": {
        "vehicle_nickname": "White Swift Dzire - DL 3C AB 1234",
        "owner_name": "Mahendra",
        "owner_phone": "8306862533",
        "owner_email": "verma.rashi210@gmail.com",
    },
    # "002": {
    #     "vehicle_nickname": "Black Activa - DL 5S CD 5678",
    #     "owner_name": "Customer 2 Name",
    #     "owner_phone": "9XXXXXXXXX",
    #     "owner_email": "customer2email@gmail.com",
    # },
}

# ---- FIGURE OUT WHICH VEHICLE THIS SCAN IS FOR ----
# Reads the "?vehicle=001" part from the URL that was encoded into the QR code
query_params = st.query_params
vehicle_id = query_params.get("vehicle", "001")  # defaults to "001" if missing

if vehicle_id not in VEHICLES:
    st.error("Invalid or unknown vehicle tag. Please check the QR code.")
    st.stop()

OWNER_DATA = VEHICLES[vehicle_id]

PURPOSE_OPTIONS = [
    "Vehicle Accident",
    "Emergency",
    "Wrong Parking",
    "Others",
]

# ------------------------------------------------------------------
# EMAIL SENDING FUNCTION
# This is the "connectivity" — every action calls this to alert the owner.
# Uses Gmail's SMTP server + an "App Password" (explained in the steps below)
# Credentials are read from Streamlit secrets — NEVER written in this file directly.
# ------------------------------------------------------------------
def notify_owner(action_type, scanner_name, scanner_phone, purpose, message_text=""):
    email_ok, email_msg = False, "Email not attempted"
    sms_ok, sms_msg = False, "SMS not attempted"

    # ---- Try SMS first (this is the urgent, real-time channel) ----
    try:
        sms_api_key = st.secrets["FAST2SMS_API_KEY"]
        short_text = (f"OwnrTag Alert: {action_type} ({purpose}). "
                      f"Contact: {scanner_phone}"
                      f"{' - ' + scanner_name if scanner_name else ''}. "
                      f"Vehicle: {OWNER_DATA['vehicle_nickname']}")
        sms_ok, sms_msg = send_sms(sms_api_key, OWNER_DATA["owner_phone"], short_text)
    except Exception as e:
        sms_msg = f"SMS skipped: {e}"

    # ---- Also send email as a backup record (in case SMS credits run out) ----
    try:
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_APP_PASSWORD"]

        subject = f"🚨 OwnrTag Alert: {action_type} — {purpose}"
        body = f"""
Hello {OWNER_DATA['owner_name']},

Someone scanned your vehicle tag ({OWNER_DATA['vehicle_nickname']}).

Action: {action_type}
Purpose: {purpose}
Contacted by: {scanner_name if scanner_name else "Not provided"}
Their phone number: {scanner_phone}
Time: {datetime.now(IST).strftime("%d-%b-%Y %I:%M %p")} IST

{"Message: " + message_text if message_text else ""}

— OwnrTag Notification System
        """

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = OWNER_DATA["owner_email"]

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)

        email_ok = True
        email_msg = "Email sent."
    except Exception as e:
        email_msg = f"Email failed: {e}"

    # ---- Overall result: success if AT LEAST ONE channel worked ----
    if sms_ok or email_ok:
        return True, f"Notified owner. SMS: {'✅' if sms_ok else '❌ ' + sms_msg} | Email: {'✅' if email_ok else '❌ ' + email_msg}"
    else:
        return False, f"Both channels failed. SMS: {sms_msg} | Email: {email_msg}"


# ---- PHONE NUMBER FORMAT VALIDATION (no OTP, just format check) ----
def is_valid_phone(number):
    # Indian mobile numbers: 10 digits, starting with 6, 7, 8, or 9
    pattern = r"^[6-9]\d{9}$"
    return re.match(pattern, number) is not None


# ---- SESSION STATE ----
if "step" not in st.session_state:
    st.session_state.step = "landing"
if "scanner_name" not in st.session_state:
    st.session_state.scanner_name = ""
if "scanner_phone" not in st.session_state:
    st.session_state.scanner_phone = ""
if "purpose" not in st.session_state:
    st.session_state.purpose = ""

st.title("🚗 OwnrTag")
st.caption("Scan. Connect. No personal details shared.")

# ------------------- STEP 1: LANDING -------------------
if st.session_state.step == "landing":
    st.subheader(f"Vehicle: {OWNER_DATA['vehicle_nickname']}")
    st.write("You're about to contact this vehicle's owner.")
    if st.button("Continue →", use_container_width=True):
        st.session_state.step = "details_entry"
        st.rerun()

# ------------------- STEP 2: NAME + PHONE + PURPOSE (all in one, no OTP) -------------------
elif st.session_state.step == "details_entry":
    st.subheader("Your details")
    name = st.text_input("Your Name (optional)", placeholder="e.g. Ramesh")
    phone = st.text_input("Your Mobile Number", placeholder="9876543210", max_chars=10)
    purpose = st.selectbox("Purpose of contacting", PURPOSE_OPTIONS)

    if st.button("Continue →", use_container_width=True):
        if is_valid_phone(phone):
            st.session_state.scanner_name = name
            st.session_state.scanner_phone = phone
            st.session_state.purpose = purpose
            st.session_state.step = "access_page"
            st.rerun()
        else:
            st.error("Please enter a valid 10-digit Indian mobile number (starting with 6-9)")

# ------------------- STEP 3: ACCESS PAGE -------------------
elif st.session_state.step == "access_page":
    st.success(f"Contacting on behalf of: {st.session_state.scanner_phone} | Purpose: {st.session_state.purpose}")
    st.subheader("What would you like to do?")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📞 Call Owner", use_container_width=True):
            with st.spinner("Notifying owner..."):
                ok, msg = notify_owner("Call Request", st.session_state.scanner_name,
                                        st.session_state.scanner_phone, st.session_state.purpose)
            if ok:
                st.success(f"{OWNER_DATA['owner_name']} has been notified of your call request!")
            else:
                st.error(msg)
            st.caption(msg)  # always show the detailed SMS/Email breakdown for debugging

    with col2:
        if st.button("💬 Message Owner", use_container_width=True):
            st.session_state.step = "message"
            st.rerun()

    with col3:
        if st.button("🚨 Emergency", use_container_width=True):
            with st.spinner("Sending emergency alert..."):
                ok, msg = notify_owner("EMERGENCY ALERT", st.session_state.scanner_name,
                                        st.session_state.scanner_phone, st.session_state.purpose)
            if ok:
                st.error(f"🚨 Emergency alert sent to {OWNER_DATA['owner_name']}!")
            else:
                st.error(msg)

    if st.button("← Start Over"):
        st.session_state.step = "landing"
        st.rerun()

# ------------------- MESSAGE FLOW -------------------
elif st.session_state.step == "message":
    st.subheader("💬 Send a message to the owner")
    text = st.text_area("Your message", placeholder="Your car is blocking my gate, please move it.")
    if st.button("Send Message"):
        with st.spinner("Sending..."):
            ok, msg = notify_owner("Message", st.session_state.scanner_name,
                                    st.session_state.scanner_phone, st.session_state.purpose,
                                    message_text=text)
        if ok:
            st.success("Message sent to the owner!")
        else:
            st.error(msg)
    if st.button("← Back"):
        st.session_state.step = "access_page"
        st.rerun()
