import requests

# ------------------------------------------------------------------
# sms_utils.py — Your own tiny reusable "SMS sending library"
# Right now it's built on Fast2SMS, but if you ever switch providers,
# you only need to change the code INSIDE this one function — nothing
# else in your app needs to change. That's the whole point of keeping
# this separate from app.py.
# ------------------------------------------------------------------

FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"


def send_sms(api_key: str, phone_number: str, message: str) -> tuple[bool, str]:
    """
    Sends a real SMS to phone_number with the given message text.

    api_key       -> your Fast2SMS API key (get this after signing up, free)
    phone_number  -> 10-digit Indian mobile number, e.g. "9590403444"
    message       -> the text you want the owner to receive

    Returns (True, "success message") or (False, "error message")
    """
    headers = {
        "authorization": api_key,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    payload = {
        "route": "q",              # "q" = Quick/Transactional route (works on free credits)
        "message": message,
        "language": "english",
        "flash": 0,
        "numbers": phone_number,
    }

    try:
        response = requests.post(FAST2SMS_URL, headers=headers, data=payload, timeout=10)
        result = response.json()

        if result.get("return") is True:
            return True, "SMS sent successfully."
        else:
            return False, f"SMS failed: {result}"

    except Exception as e:
        return False, f"SMS request failed: {e}"
