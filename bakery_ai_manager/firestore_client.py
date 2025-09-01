# In bakery_ai_manager/firestore_client.py

import os
import firebase_admin
from firebase_admin import credentials, firestore

# --- THIS IS THE UPDATED, SECURE, AND CLOUD-NATIVE METHOD ---
# This method relies on the 'GOOGLE_APPLICATION_CREDENTIALS' environment variable
# being set securely by your hosting provider (e.g., Render's Secret Files).
# It does NOT look for a local 'config' folder.

def initialize_and_get_client():
    """
    Initializes the Firebase Admin SDK using credentials from the environment
    and returns a Firestore client. This is the single source of truth for auth.
    """
    # This check prevents the app from crashing if the server reloads the module.
    if not firebase_admin._apps:
        print("DEBUG: Initializing Firebase Admin SDK...")
        try:
            # The SDK will AUTOMATICALLY find and use the credentials from the
            # GOOGLE_APPLICATION_CREDENTIALS environment variable. No file path is needed here.
            firebase_admin.initialize_app()
            print("DEBUG: Firebase Admin SDK initialized successfully.")

        except Exception as e:
            # This error typically happens if the environment variable is missing or points to an invalid file.
            print("="*80)
            print("FATAL ERROR: Failed to initialize Firebase Admin SDK.")
            print(f"Error: {e}")
            print("\nThis usually means the 'GOOGLE_APPLICATION_CREDENTIALS' environment")
            print("variable is not set correctly in your hosting environment (e.g., Render).")
            print("Please ensure your 'Secret File' is set up correctly.")
            print("="*80)
            exit(1) # Stop the server if authentication fails.

    # Return the Firestore client from the initialized app.
    return firestore.client()

# --- GLOBAL FIRESTORE CLIENT ---
# Initialize the client once when the app starts and make it available
# for other parts of your Django project to import and use.
db = initialize_and_get_client()

def get_firestore_client():
    """
    Returns the globally initialized Firestore client instance.
    This function is kept for compatibility with other parts of your app.
    """
    return db
