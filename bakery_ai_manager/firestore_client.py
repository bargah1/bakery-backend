
import os
import firebase_admin
from firebase_admin import credentials, firestore

    # Path to your service account key file
    # Ensure this path is correct relative to where your Django app runs
SERVICE_ACCOUNT_KEY_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), # Path to bakery_ai_manager directory
        'config', 
        'manger-ai-firebase-adminsdk-fbsvc-639cb34b21.json' # REPLACE WITH YOUR ACTUAL FILE NAME
    )

    # Initialize Firebase Admin SDK only once
if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            firebase_admin.initialize_app(cred)
            print("DEBUG: Firebase Admin SDK initialized successfully.")
        except FileNotFoundError:
            print(f"ERROR: Firebase Service Account Key file not found at: {SERVICE_ACCOUNT_KEY_PATH}")
            print("Please ensure your Firebase service account JSON file is in the 'config' folder.")
            exit(1) # Exit if the key file is essential for startup
        except Exception as e:
            print(f"ERROR: Failed to initialize Firebase Admin SDK: {e}")
            exit(1) # Exit if initialization fails

    # Get a Firestore client instance
db = firestore.client()

def get_firestore_client():
        """Returns the initialized Firestore client."""
        return db

    