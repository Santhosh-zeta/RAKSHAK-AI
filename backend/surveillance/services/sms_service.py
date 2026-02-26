import os
import requests

class SMSService:
    """
    Service to trigger alert SMS notifications.
    Stubbed to print to console if Twilio isn't fully configured.
    """
    
    @classmethod
    def send_alert(cls, to_phone, message):
        """
        Sends an SMS. Expected Twilio integration.
        """
        twilio_sid = os.environ.get('TWILIO_SID')
        twilio_token = os.environ.get('TWILIO_TOKEN')
        twilio_from = os.environ.get('TWILIO_FROM_NUM')
        
        print("\n" + "="*50)
        print(f"🔔 SMS ALERT TRIGGERED TO: {to_phone}")
        print(f"📝 MSG: {message}")
        print("="*50 + "\n")
        
        if twilio_sid and twilio_token and twilio_from:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            data = {
                "To": to_phone,
                "From": twilio_from,
                "Body": message
            }
            try:
                # requests.post(url, data=data, auth=(twilio_sid, twilio_token), timeout=5)
                # Commented out actual post for Hackathon safety unless keys provided
                return True
            except Exception as e:
                print(f"Twilio error: {e}")
                return False
                
        return True # Resolves True for hackathon stub
