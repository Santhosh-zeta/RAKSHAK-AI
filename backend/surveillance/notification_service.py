import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================
# SMTP Email Service
# ============================================================

def send_email_alert(to_email: str, subject: str, body: str, company_name: str = "RAKSHAK AI"):
    """
    Send an alert email via SMTP.
    Configure via .env:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL
    Falls back to a console log if SMTP is not configured.
    """
    smtp_host     = os.getenv("SMTP_HOST", "")
    smtp_port     = int(os.getenv("SMTP_PORT", "587"))
    smtp_user     = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    from_email    = os.getenv("SMTP_FROM_EMAIL", smtp_user)

    if not all([smtp_host, smtp_user, smtp_password, to_email]):
        logger.warning(
            f"[EMAIL SUPPRESSED] SMTP not configured or no recipient. "
            f"Would send to: {to_email} | Subject: {subject}"
        )
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[{company_name}] {subject}"
        msg["From"]    = from_email
        msg["To"]      = to_email

        # Plain text
        text_body = body
        # HTML body
        html_body = f"""
        <html><body>
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
          <div style="background:#c0392b;padding:15px;border-radius:6px 6px 0 0">
            <h2 style="color:white;margin:0">🚨 {company_name} — Security Alert</h2>
          </div>
          <div style="background:#f9f9f9;padding:20px;border:1px solid #ddd">
            <pre style="font-size:14px;white-space:pre-wrap">{body}</pre>
          </div>
          <div style="background:#eee;padding:10px;font-size:12px;color:#888;text-align:center">
            RAKSHAK AI Cargo Surveillance System · {datetime.now().strftime('%Y-%m-%d %H:%M')}
          </div>
        </div></body></html>
        """
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body,  "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())

        logger.info(f"Email sent to {to_email} | Subject: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


# ============================================================
# Twilio SMS Service
# ============================================================

def send_sms_alert(to_phone: str, message: str):
    """
    Send an SMS via Twilio.
    Configure via .env:
      TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE
    Falls back to console log if not configured.
    """
    twilio_sid   = os.getenv("TWILIO_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone = os.getenv("TWILIO_PHONE", "")

    if not all([twilio_sid, twilio_token, twilio_phone, to_phone]):
        logger.warning(
            f"[SMS SUPPRESSED] Twilio not configured or no recipient. "
            f"Would send to: {to_phone} | Message: {message[:80]}"
        )
        return False

    try:
        from twilio.rest import Client
        client = Client(twilio_sid, twilio_token)
        msg = client.messages.create(
            body=message,
            from_=twilio_phone,
            to=to_phone
        )
        logger.info(f"SMS sent to {to_phone} | SID: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_phone}: {e}")
        return False


# ============================================================
# Unified Alert Dispatcher
# Notifies BOTH the logistics company control area AND the truck driver
# ============================================================

def dispatch_alert(alert, trip, truck, company=None):
    """
    Send SMS + Email to:
      1. Logistics company control area (email + phone from LogisticsCompany)
      2. Truck driver (phone from Truck.driver_phone)
      3. All ControlAreaContact entries for the company

    Args:
        alert   : Alert model instance
        trip    : Trip model instance
        truck   : Truck model instance
        company : LogisticsCompany instance (optional, fetched from truck if None)
    """
    if company is None and hasattr(truck, 'company') and truck.company:
        company = truck.company

    severity_emoji = {
        "Critical": "🔴",
        "High":     "🟠",
        "Medium":   "🟡",
        "Low":      "🟢",
    }.get(alert.severity, "⚠️")

    subject = f"{severity_emoji} {alert.severity} Security Alert — Truck {truck.license_plate}"

    body = (
        f"RAKSHAK AI SECURITY ALERT\n"
        f"{'=' * 45}\n"
        f"Severity   : {alert.severity}\n"
        f"Alert Type : {alert.type}\n"
        f"Risk Score : {alert.risk_score:.1f}/100\n"
        f"Truck      : {truck.license_plate} ({truck.vehicle_make_model or 'N/A'})\n"
        f"Driver     : {truck.driver_name} ({truck.driver_phone or 'N/A'})\n"
        f"Trip       : {str(trip.trip_id)[:8]} | {trip.start_location_name} → {trip.destination_name}\n"
        f"Status     : {trip.status}\n"
        f"Time       : {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if alert.timestamp else 'N/A'}\n"
        f"{'=' * 45}\n"
        f"Description:\n{alert.description}\n"
    )
    if alert.ai_explanation:
        body += f"\nAI Analysis:\n{alert.ai_explanation}\n"

    company_name = company.name if company else "RAKSHAK AI"

    # ---------- 1. Company control area ----------
    if company:
        if company.control_email:
            send_email_alert(company.control_email, subject, body, company_name)
        if company.control_phone:
            sms = (
                f"[{company_name}] {severity_emoji} {alert.severity} ALERT\n"
                f"Truck: {truck.license_plate} | Risk: {alert.risk_score:.0f}/100\n"
                f"{trip.start_location_name}→{trip.destination_name}\n"
                f"{alert.description[:120]}"
            )
            send_sms_alert(company.control_phone, sms)

        # All registered control contacts for this company
        for contact in company.contacts.all():
            if contact.notify_email and contact.email:
                send_email_alert(contact.email, subject, body, company_name)
            if contact.notify_sms and contact.phone:
                send_sms_alert(contact.phone,
                    f"[{company_name}] {severity_emoji} {alert.severity} | "
                    f"Truck {truck.license_plate} | Score {alert.risk_score:.0f}/100"
                )

    # ---------- 2. Driver ----------
    driver_sms = (
        f"[RAKSHAK AI] {severity_emoji} SECURITY ALERT on your vehicle {truck.license_plate}\n"
        f"Type: {alert.type} | Severity: {alert.severity}\n"
        f"Please contact your control area immediately."
    )
    if truck.driver_phone:
        send_sms_alert(truck.driver_phone, driver_sms)
    if hasattr(truck, 'driver_email') and truck.driver_email:
        send_email_alert(truck.driver_email, f"Vehicle Alert — {truck.license_plate}", body, company_name)

    logger.info(
        f"Alert {alert.alert_id} dispatched | company={company_name} | "
        f"driver={truck.driver_name}"
    )
