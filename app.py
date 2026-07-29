import streamlit as st
import random
import time

# ------------------------------------------------------------------
# RideTag MVP — the page that opens when someone scans the QR code
# ------------------------------------------------------------------

st.set_page_config(page_title="RideTag", page_icon="🚗", layout="centered")

# ---- FAKE DATABASE (for now, just one hardcoded vehicle/owner) ----
# Later this becomes a real database with many vehicles.
# For your FIRST customer, just edit these values manually.
OWNER_DATA = {
    "vehicle_nickname": "White Swift Dzire - DL 3C AB 1234",
    "owner_name": "Rashi",
    "owner_phone": "+91XXXXXXXXXX",       # owner's real number (never shown to scanner)
    "emergency_contact": "+91YYYYYYYYYY", # emergency contact number
}

# ---- SESSION STATE = "memory" for this one visit ----
# Streamlit forgets everything on refresh unless you store it in session_state
if "step" not in st.session_state:
    st.session_state.step = "landing"
if "otp" not in st.session_state:
    st.session_state.otp = None
if "mobile" not in st.session_state:
    st.session_state.mobile = ""

st.title("🚗 RideTag")
st.caption("Scan. Connect. No personal details shared.")

# ------------------- STEP 1: LANDING -------------------
if st.session_state.step == "landing":
    st.subheader(f"Vehicle: {OWNER_DATA['vehicle_nickname']}")
    st.write("You're about to contact this vehicle's owner. For safety, we verify your number first.")
    if st.button("Continue →", use_container_width=True):
        st.session_state.step = "mobile_entry"
        st.rerun()

# ------------------- STEP 2: ENTER MOBILE -------------------
elif st.session_state.step == "mobile_entry":
    st.subheader("Enter your mobile number")
    mobile = st.text_input("Mobile Number", placeholder="9876543210", max_chars=10)
    if st.button("Send OTP", use_container_width=True):
        if len(mobile) == 10 and mobile.isdigit():
            st.session_state.mobile = mobile
            # DEMO MODE: we generate a fake OTP and show it on screen.
            # In the REAL version, this gets sent via SMS using Twilio/MSG91
            # instead of being shown here.
            st.session_state.otp = str(random.randint(100000, 999999))
            st.session_state.step = "otp_verify"
            st.rerun()
        else:
            st.error("Please enter a valid 10-digit mobile number")

# ------------------- STEP 3: OTP VERIFICATION -------------------
elif st.session_state.step == "otp_verify":
    st.subheader("Enter the OTP")
    st.info(f"DEMO MODE — your OTP is: **{st.session_state.otp}**  \n"
            f"(In the real version, this is sent by SMS, not shown here)")
    entered_otp = st.text_input("OTP", max_chars=6)
    if st.button("Verify", use_container_width=True):
        if entered_otp == st.session_state.otp:
            st.session_state.step = "access_page"
            st.rerun()
        else:
            st.error("Incorrect OTP, try again")

# ------------------- STEP 4: ACCESS PAGE (main menu) -------------------
elif st.session_state.step == "access_page":
    st.success(f"Verified: {st.session_state.mobile}")
    st.subheader("What would you like to do?")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📞 Call Owner", use_container_width=True):
            st.session_state.step = "call"
            st.rerun()
    with col2:
        if st.button("💬 Message Owner", use_container_width=True):
            st.session_state.step = "message"
            st.rerun()
    with col3:
        if st.button("🚨 Emergency", use_container_width=True):
            st.session_state.step = "emergency"
            st.rerun()

# ------------------- CALL FLOW -------------------
elif st.session_state.step == "call":
    st.subheader("📞 Connecting you to the owner")
    st.write("In the real version, this uses a masking service (like Ola/Uber calls) "
             "so neither of you sees the other's real number.")
    st.write("For now (demo), here's what happens: the owner gets notified "
             f"that **{st.session_state.mobile}** wants to talk, and can call back.")
    if st.button("← Back"):
        st.session_state.step = "access_page"
        st.rerun()

# ------------------- MESSAGE FLOW -------------------
elif st.session_state.step == "message":
    st.subheader("💬 Send a message to the owner")
    msg = st.text_area("Your message", placeholder="Your car is blocking my gate, please move it.")
    if st.button("Send Message"):
        st.success("Message sent! The owner has been notified.")
        st.caption("(Demo: in the real version this arrives via SMS/WhatsApp to the owner)")
    if st.button("← Back"):
        st.session_state.step = "access_page"
        st.rerun()

# ------------------- EMERGENCY FLOW -------------------
elif st.session_state.step == "emergency":
    st.subheader("🚨 Emergency Contact")
    st.write("Choose an option:")
    if st.button("Call Emergency Contact", use_container_width=True):
        st.warning("Connecting to owner's emergency contact...")
    if st.button("Send Emergency Alert", use_container_width=True):
        st.error("🚨 Alert sent to owner AND emergency contact!")
    if st.button("← Back"):
        st.session_state.step = "access_page"
        st.rerun()
