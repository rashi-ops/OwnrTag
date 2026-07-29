import re
from datetime import datetime

import streamlit as st

# ------------------------------------------------------------------
# RideTag MVP — the page that opens when someone scans the QR code
# ------------------------------------------------------------------

st.set_page_config(page_title="RideTag", page_icon="🚗", layout="centered")

# ---- OWNER DETAILS ----
OWNER_DATA = {
    "vehicle_nickname": "White Swift Dzire - DL 3C AB 1234",
    "owner_name": "Mahendra",
    "owner_phone": "+919590403444",
    "emergency_contact": "+919590403444",
}

PURPOSE_OPTIONS = ["vehicle accident", "Emergency", "wrong parking", "others"]

# ---- SESSION STATE = "memory" for this one visit ----
if "step" not in st.session_state:
    st.session_state.step = "landing"
if "mobile" not in st.session_state:
    st.session_state.mobile = ""
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "purpose" not in st.session_state:
    st.session_state.purpose = PURPOSE_OPTIONS[0]
if "owner_alerts" not in st.session_state:
    st.session_state.owner_alerts = []


def is_valid_phone(phone: str) -> bool:
    cleaned = re.sub(r"\D", "", phone)
    return len(cleaned) == 10 and cleaned.startswith(("6", "7", "8", "9"))


def notify_owner(action: str, details: str) -> None:
    alert = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "action": action,
        "details": details,
    }
    st.session_state.owner_alerts.insert(0, alert)
    if len(st.session_state.owner_alerts) > 8:
        st.session_state.owner_alerts = st.session_state.owner_alerts[:8]
    print(f"[OWNER ALERT] {OWNER_DATA['owner_name']} ({OWNER_DATA['owner_phone']}): {details}")


st.title("🚗 RideTag")
st.caption("Scan. Connect. No personal details shared.")

with st.sidebar:
    st.subheader("Owner alert feed")
    if st.session_state.owner_alerts:
        for item in st.session_state.owner_alerts:
            st.info(f"{item['timestamp']} • {item['action']}\n{item['details']}")
    else:
        st.info("No owner alerts yet.")

# ------------------- STEP 1: LANDING -------------------
if st.session_state.step == "landing":
    st.subheader(f"Vehicle: {OWNER_DATA['vehicle_nickname']}")
    st.write(
        f"You are contacting {OWNER_DATA['owner_name']} on {OWNER_DATA['owner_phone']}. "
        "The owner will be notified immediately on every action."
    )
    if st.button("Continue →", use_container_width=True):
        st.session_state.step = "contact_form"
        st.rerun()

# ------------------- STEP 2: BARCODE / CONTACT FORM -------------------
elif st.session_state.step == "contact_form":
    st.subheader("Scan details")
    st.write("This step simulates the barcode scan and notifies the owner with your number, name, and purpose.")

    user_name = st.text_input("Your name", value=st.session_state.user_name, placeholder="Enter your name")
    mobile = st.text_input("Your phone number", value=st.session_state.mobile, placeholder="9876543210")
    purpose = st.selectbox(
        "Purpose of contact",
        PURPOSE_OPTIONS,
        index=PURPOSE_OPTIONS.index(st.session_state.purpose) if st.session_state.purpose in PURPOSE_OPTIONS else 0,
    )

    if st.button("Notify Owner and Continue", use_container_width=True):
        if not user_name.strip():
            st.error("Please enter your name.")
        elif not is_valid_phone(mobile):
            st.error("Please enter a valid phone number.")
        else:
            st.session_state.user_name = user_name.strip()
            st.session_state.mobile = mobile.strip()
            st.session_state.purpose = purpose
            notify_owner(
                "Barcode scan",
                f"{user_name.strip()} ({mobile.strip()}) scanned the tag for purpose: {purpose}",
            )
            st.success(f"Owner {OWNER_DATA['owner_name']} has been notified.")
            st.session_state.step = "access_page"
            st.rerun()

# ------------------- STEP 3: ACCESS PAGE (main menu) -------------------
elif st.session_state.step == "access_page":
    st.success(f"Contact ready: {st.session_state.user_name or 'Guest'} • {st.session_state.mobile}")
    st.subheader("What would you like to do?")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📞 Call Owner", use_container_width=True):
            notify_owner(
                "Call request",
                f"{st.session_state.user_name or 'Unknown'} requested a call for purpose: {st.session_state.purpose}",
            )
            st.session_state.step = "call"
            st.rerun()
    with col2:
        if st.button("💬 Message Owner", use_container_width=True):
            notify_owner(
                "Message request",
                f"{st.session_state.user_name or 'Unknown'} sent a message for purpose: {st.session_state.purpose}",
            )
            st.session_state.step = "message"
            st.rerun()
    with col3:
        if st.button("🚨 Emergency", use_container_width=True):
            notify_owner(
                "Emergency alert",
                f"{st.session_state.user_name or 'Unknown'} raised an emergency alert for purpose: {st.session_state.purpose}",
            )
            st.session_state.step = "emergency"
            st.rerun()

# ------------------- CALL FLOW -------------------
elif st.session_state.step == "call":
    st.subheader("📞 Connecting you to the owner")
    st.write(
        f"The owner {OWNER_DATA['owner_name']} is being notified that {st.session_state.mobile} wants to talk."
    )
    st.success("Owner notification sent.")
    if st.button("← Back"):
        st.session_state.step = "access_page"
        st.rerun()

# ------------------- MESSAGE FLOW -------------------
elif st.session_state.step == "message":
    st.subheader("💬 Send a message to the owner")
    msg = st.text_area(
        "Your message",
        placeholder="Your car is blocking my gate, please move it.",
    )
    if st.button("Send Message"):
        notify_owner(
            "Message sent",
            f"{st.session_state.user_name or 'Unknown'} sent: {msg or 'No message provided'}",
        )
        st.success("Message sent! The owner has been notified.")
    if st.button("← Back"):
        st.session_state.step = "access_page"
        st.rerun()

# ------------------- EMERGENCY FLOW -------------------
elif st.session_state.step == "emergency":
    st.subheader("🚨 Emergency Contact")
    st.write("Choose an option:")
    if st.button("Call Emergency Contact", use_container_width=True):
        notify_owner(
            "Emergency call",
            f"{st.session_state.user_name or 'Unknown'} requested an emergency call.",
        )
        st.warning("Connecting to the owner's emergency contact...")
    if st.button("Send Emergency Alert", use_container_width=True):
        notify_owner(
            "Emergency alert",
            f"{st.session_state.user_name or 'Unknown'} sent an emergency alert to the owner.",
        )
        st.error("🚨 Alert sent to owner and emergency contact.")
    if st.button("← Back"):
        st.session_state.step = "access_page"
        st.rerun()
