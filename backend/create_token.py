import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rakshak.settings")
django.setup()

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

def get_or_create_token(username="admin", password="password"):
    try:
        user = User.objects.get(username=username)
        print(f"User '{username}' already exists.")
    except User.DoesNotExist:
        user = User.objects.create_superuser(username=username, email='admin@rakshak.local', password=password)
        print(f"Created Superuser '{username}'.")

    token, created = Token.objects.get_or_create(user=user)
    
    if created:
        print(f"Provisioned new API Token for {username}.")
    else:
        print(f"Retrieved existing API Token for {username}.")
        
    print("\n" + "="*50)
    print(f"🔐 YOUR API TOKEN: {token.key}")
    print("="*50)
    print("\nHow to use in Postman / Frontend / IoT Script:")
    print(f"Header => Authorization: Token {token.key}\n")

if __name__ == "__main__":
    if len(sys.argv) == 3:
        get_or_create_token(sys.argv[1], sys.argv[2])
    else:
        print("Using default credentials (admin / password)...")
        get_or_create_token()
