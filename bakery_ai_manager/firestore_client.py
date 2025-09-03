# In your firebase_config.py

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_and_get_client():
    """
    Initializes the Firebase Admin SDK using credentials from an environment
    variable containing the JSON content. Returns a Firestore client.
    """
    if not firebase_admin._apps:
        print("DEBUG: Initializing Firebase Admin SDK...")
        try:
            # Get the JSON credentials content from the environment variable
            creds_json_str = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')

            if not creds_json_str:
                raise ValueError("The 'GOOGLE_APPLICATION_CREDENTIALS_JSON' environment variable is not set.")

            # Parse the JSON string into a dictionary
            creds_json = json.loads(creds_json_str)
            
            # Initialize the app with the credentials object
            cred = credentials.Certificate(creds_json)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Admin SDK initialized successfully.")

        except Exception as e:
            print("="*80)
            print("🔥 FATAL ERROR: Failed to initialize Firebase Admin SDK.")
            print(f"Error: {e}")
            print("\nCheck that the 'GOOGLE_APPLICATION_CREDENTIALS_JSON' variable is set correctly in Railway.")
            print("="*80)
            exit(1) # Stop the server if authentication fails.

    return firestore.client()

# Initialize the client once when the app starts
db = initialize_and_get_client()

def get_firestore_client():
    """Returns the globally initialized Firestore client instance."""
    return db
