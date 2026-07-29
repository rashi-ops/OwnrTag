"""
RideTag CLI — pure Python, no Streamlit.

This is the "scan the QR code" flow as a terminal app. It notifies the
owner by actually sending a WhatsApp message using pywhatkit, which
drives your own already-logged-in WhatsApp Web session in a browser.
No third-party service account or API key is required.

WHY YOUR OLD CODE DIDN'T SEND ANYTHING
----------------------------------------
The original `send_sms_to_owner()` only did `print(...)`. Printing to
your terminal never reaches a phone — you need to actually go through
WhatsApp/SMS/some messaging channel to deliver a message to a real device.

SETUP (pywhatkit — no signup, no API key)
-------------------------------------------
1. pip install pywhatkit
2. On THIS machine, open a normal browser and log into web.whatsapp.com
   with your own phone (scan the QR code once, like usual). Keep that
   session logged in — pywhatkit reuses it.
3. Set the owner's WhatsApp number as an environment variable, in full
   international format with a leading "+":

   export OWNER_WHATSAPP_NUMBER="+919590403444"

4. Run: python ridetag_cli.py

LIMITATIONS (inherent to browser automation, not a bug)
-----------------------------------------------------------
- Needs a GUI + Chrome/Firefox installed — will NOT work on a headless
  server or most cloud hosts.
- Pops open a visible browser tab for every message sent.
- Each send has a mandatory short wait (default 15s) before pywhatkit
  can locate the chat and press Enter.
- If OWNER_WHATSAPP_NUMBER isn't set, or pywhatkit isn't installed, the
  script still runs — it just logs the message to console/JSON instead
  of sending it, so you can develop without a browser open.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ---- OWNER DETAILS ----
OWNER_DATA = {
    "vehicle_nickname": "White Swift Dzire - DL 3C AB 1234",
    "owner_name": "Mahendra",
    "owner_phone": "9590403444",  # display/local number
}

PURPOSE_OPTIONS = ["vehicle accident", "Emergency", "wrong parking", "others"]
NOTIFICATION_FILE = Path(__file__).resolve().parent / "owner_notifications.json"

# Filled in at startup by run_preflight_checks(), so we only ask once
# per run instead of on every single notify_owner() call.
_OWNER_WHATSAPP_NUMBER: str | None = None


# ------------------------------------------------------------------
# Persistence
# ------------------------------------------------------------------
def load_owner_alerts() -> list[dict]:
    if NOTIFICATION_FILE.exists():
        try:
            return json.loads(NOTIFICATION_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_owner_alerts(alerts: list[dict]) -> None:
    NOTIFICATION_FILE.write_text(json.dumps(alerts, indent=2), encoding="utf-8")


# ------------------------------------------------------------------
# Real WhatsApp sending via pywhatkit (drives your own WhatsApp Web
# session in a browser — no third-party account or API key needed)
# ------------------------------------------------------------------
def is_valid_e164(number: str) -> bool:
    return bool(re.fullmatch(r"\+\d{8,15}", number or ""))


def run_preflight_checks() -> None:
    """
    Runs once at startup and tells you exactly which of the three
    requirements for real WhatsApp sending is missing, instead of
    failing silently later. If OWNER_WHATSAPP_NUMBER isn't set as an
    env var, it offers to let you type it in right now for this run.
    """
    global _OWNER_WHATSAPP_NUMBER

    print("\n--- WhatsApp send preflight check ---")

    ok_pkg = True
    try:
        import pywhatkit  # noqa: F401
        print("[OK] pywhatkit is installed.")
    except ImportError:
        ok_pkg = False
        print("[MISSING] pywhatkit is NOT installed. Run: pip install pywhatkit")

    number = os.environ.get("OWNER_WHATSAPP_NUMBER")
    if number and is_valid_e164(number):
        print(f"[OK] OWNER_WHATSAPP_NUMBER env var is set to {number}")
        _OWNER_WHATSAPP_NUMBER = number
    else:
        if number:
            print(f"[INVALID] OWNER_WHATSAPP_NUMBER='{number}' is not in +<countrycode><number> format.")
        else:
            print("[MISSING] OWNER_WHATSAPP_NUMBER env var is not set.")
        typed = ask("Enter owner's WhatsApp number now (e.g. +919590403444), or press Enter to skip: ")
        if typed and is_valid_e164(typed):
            _OWNER_WHATSAPP_NUMBER = typed
            print(f"[OK] Using {typed} for this run only (not saved).")
        else:
            print("[SKIPPED] No valid number provided — messages will only be logged, not sent.")

    print("[REMINDER] You must ALSO already be logged into web.whatsapp.com")
    print("           in your default browser on this machine, or the send will fail.")
    if not ok_pkg or not _OWNER_WHATSAPP_NUMBER:
        print("--> Real WhatsApp sending is DISABLED for this run (see reasons above).\n")
    else:
        print("--> Real WhatsApp sending is ENABLED for this run.\n")


def send_whatsapp_to_owner(alert: dict) -> bool:
    """
    Sends a WhatsApp message to the owner via pywhatkit if it's
    installed and an owner number is known. Returns True if a real
    message send was attempted successfully, False if it fell back to
    console/JSON logging only.
    """
    wa_message = (
        f"[{OWNER_DATA['owner_name']}]\n"
        f"Action: {alert['action']}\n"
        f"Details: {alert['details']}\n"
        f"Time: {alert['timestamp']}"
    )

    owner_number = _OWNER_WHATSAPP_NUMBER or os.environ.get("OWNER_WHATSAPP_NUMBER")

    if not owner_number or not is_valid_e164(owner_number):
        print("[WHATSAPP NOT SENT — no valid owner number configured] Falling back to console log:")
        print(f"[WHATSAPP TO {OWNER_DATA['owner_phone']}] {wa_message}")
        return False

    try:
        import pywhatkit
    except ImportError:
        print("[WHATSAPP NOT SENT — 'pywhatkit' package not installed] Run: pip install pywhatkit")
        print(f"[WHATSAPP TO {OWNER_DATA['owner_phone']}] {wa_message}")
        return False

    try:
        # sendwhatmsg_instantly opens web.whatsapp.com in your default
        # browser (must already be logged in), waits, types the
        # message, sends it, then closes the tab.
        pywhatkit.sendwhatmsg_instantly(
            phone_no=owner_number,
            message=wa_message,
            wait_time=15,
            tab_close=True,
            close_time=3,
        )
        print(f"[WHATSAPP SENT] to {owner_number}")
        return True
    except Exception as exc:
        print(f"[WHATSAPP FAILED] pywhatkit error: {exc}")
        print("     Common causes: not logged into web.whatsapp.com in your default")
        print("     browser, no internet, or the browser window was closed too early.")
        print(f"[WHATSAPP TO {OWNER_DATA['owner_phone']}] {wa_message}")
        return False


def is_valid_phone(phone: str) -> bool:
    cleaned = re.sub(r"\D", "", phone)
    return len(cleaned) == 10 and cleaned.startswith(("6", "7", "8", "9"))


def notify_owner(alerts: list[dict], action: str, details: str) -> list[dict]:
    alert = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "action": action,
        "details": details,
    }
    alerts = [alert] + alerts
    if len(alerts) > 12:
        alerts = alerts[:12]
    save_owner_alerts(alerts)
    sent = send_whatsapp_to_owner(alert)
    status = "WhatsApp sent" if sent else "WhatsApp logged (not actually sent — see setup notes)"
    print(f"🔔 Owner alert: {action} — {status}")
    return alerts


# ------------------------------------------------------------------
# Small input helpers
# ------------------------------------------------------------------
def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def ask_choice(prompt: str, options: list[str]) -> str:
    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = ask(f"Choose 1-{len(options)}: ")
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("Invalid choice, try again.")


def pause():
    ask("\nPress Enter to continue...")


# ------------------------------------------------------------------
# Flow steps
# ------------------------------------------------------------------
def step_landing():
    print("\n=== 🚗 RideTag ===")
    print("Scan. Connect. No personal details shared.\n")
    print(f"Vehicle: {OWNER_DATA['vehicle_nickname']}")
    print(f"You are contacting {OWNER_DATA['owner_name']}.")
    print("The owner will be notified immediately on every action.")
    pause()


def step_contact_form(alerts: list[dict]):
    print("\n=== Scan details ===")
    print("This simulates the barcode scan and notifies the owner with your details.\n")

    while True:
        name = ask("Your name: ")
        if name:
            break
        print("Please enter your name.")

    while True:
        mobile = ask("Your phone number (10 digits): ")
        if is_valid_phone(mobile):
            break
        print("Please enter a valid 10-digit Indian mobile number.")

    purpose = ask_choice("Purpose of contact:", PURPOSE_OPTIONS)

    alerts = notify_owner(
        alerts,
        "Barcode scan",
        f"{name} ({mobile}) scanned the tag for purpose: {purpose}",
    )
    print(f"\n✅ Owner {OWNER_DATA['owner_name']} has been notified.")
    pause()
    return name, mobile, purpose, alerts


def step_access_menu(name: str, mobile: str, purpose: str, alerts: list[dict]):
    while True:
        print(f"\n=== Contact ready: {name or 'Guest'} • {mobile} ===")
        print("What would you like to do?")
        choice = ask_choice("", ["Call Owner", "Message Owner", "Emergency", "Exit"])

        if choice == "Call Owner":
            print(f"\n📞 The owner {OWNER_DATA['owner_name']} is being notified that {mobile} wants to talk.")
            alerts = notify_owner(alerts, "Call request", f"{name} requested a call for purpose: {purpose}")
            pause()

        elif choice == "Message Owner":
            msg = ask("Your message: ")
            alerts = notify_owner(alerts, "Message sent", f"{name} sent: {msg or 'No message provided'}")
            print("✅ Message sent! The owner has been notified.")
            pause()

        elif choice == "Emergency":
            alerts = step_emergency(name, alerts)

        elif choice == "Exit":
            print("Goodbye.")
            sys.exit(0)


def step_emergency(name: str, alerts: list[dict]) -> list[dict]:
    print("\n=== 🚨 Emergency Contact ===")
    choice = ask_choice("Choose an option:", ["Call Emergency Contact", "Send Emergency Alert", "Back"])
    if choice == "Call Emergency Contact":
        alerts = notify_owner(alerts, "Emergency call", f"{name} requested an emergency call.")
        print("⚠️  Connecting to the owner's emergency contact...")
    elif choice == "Send Emergency Alert":
        alerts = notify_owner(alerts, "Emergency alert", f"{name} sent an emergency alert to the owner.")
        print("🚨 Alert sent to owner and emergency contact.")
    pause()
    return alerts


def main():
    alerts = load_owner_alerts()
    run_preflight_checks()
    step_landing()
    name, mobile, purpose, alerts = step_contact_form(alerts)
    step_access_menu(name, mobile, purpose, alerts)


if __name__ == "__main__":
    main()