# =======================================================
# File: bakery_ai_manager/supabase_client.py
# Replaces firestore_client.py — Supabase Python client
# =======================================================

import os
from supabase import create_client, Client

def initialize_and_get_client() -> Client:
    """
    Initializes the Supabase client using environment variables.
    Returns a Supabase client instance.
    """
    try:
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError(
                "The 'SUPABASE_URL' and 'SUPABASE_SERVICE_ROLE_KEY' "
                "environment variables must be set."
            )

        client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized successfully.")
        return client

    except Exception as e:
        print("=" * 80)
        print("🔥 FATAL ERROR: Failed to initialize Supabase client.")
        print(f"Error: {e}")
        print("\nCheck that SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set correctly.")
        print("=" * 80)
        exit(1)


# Initialize the client once when the app starts
supabase: Client = initialize_and_get_client()


def get_supabase_client() -> Client:
    """Returns the globally initialized Supabase client instance."""
    return supabase
