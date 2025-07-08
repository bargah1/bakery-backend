# In bakery_ai_manager/firestore_client.py

import os
import firebase_admin
from firebase_admin import credentials, firestore

# --- THIS IS THE SINGLE SOURCE OF AUTHENTICATION ---
# This method uses a dedicated Service Account key file, which is the most reliable
# way to authenticate a server application.

# 1. Define the path to your service account key file.
#    This assumes you have a 'config' folder in your project's root directory
#    containing your key file.
SERVICE_ACCOUNT_KEY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), # The 'bakery_ai_manager' directory
    '..',                                       # Go up one level to the project root
    'config',                                   # Go into the 'config' folder
    'service_account_key.json'                  # Your key file
)

# 2. Check if the key file exists.
if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
    print("="*60)
    print(f"FATAL ERROR: Service Account Key not found at: {SERVICE_ACCOUNT_KEY_PATH}")
    print("Please ensure you have a 'config' folder in your project root")
    print("and that your downloaded service account key is inside it,")
    print("named 'service_account_key.json'.")
    print("="*60)
    exit(1) # Stop the server if the key is missing.

# 3. Set an environment variable that ALL Google Cloud libraries will automatically use.
#    This is the key to unifying authentication.
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_KEY_PATH

# 4. Initialize Firebase Admin SDK (it will use the environment variable automatically).
if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app()
        print("DEBUG: Firebase Admin SDK initialized successfully using Service Account.")
    except Exception as e:
        print(f"FATAL ERROR: Failed to initialize Firebase with Service Account. Error: {e}")
        exit(1)

# 5. Get a Firestore client instance that uses these credentials.
db = firestore.client()

def get_firestore_client():
    """Returns the globally initialized Firestore client."""
    return db
