#!/usr/bin/env python3
"""
============================================================
SIMPLE Firebase Firestore → JSON export script
Run this FIRST to download all your Firebase data as JSON files
Then run migrate_firestore_to_supabase.py to upload to Supabase

Usage:
  1. Put your Firebase service account JSON file path below
  2. pip install firebase-admin
  3. python export_firebase_data.py

This creates a folder called 'firebase_export/' with one JSON
file per Firestore collection.
============================================================
"""

import os
import json
from datetime import datetime

# =============================================
# CHANGE THIS to the path of your downloaded
# Firebase service account key JSON file
# =============================================
FIREBASE_KEY_PATH = r"c:\Users\mxsab\OneDrive\Desktop\bakery-backend\manger-ai-firebase-adminsdk-fbsvc-dd153f7c46.json"
# or wherever you saved it, e.g.:
# FIREBASE_KEY_PATH = r"C:\Users\mxsab\Desktop\manger-ai-firebase-key.json"


OUTPUT_DIR = "firebase_export"


def safe_serialize(val):
    """Convert Firestore-specific types to JSON-safe values."""
    if hasattr(val, 'isoformat'):  # datetime / date
        return val.isoformat()
    if hasattr(val, '_seconds'):   # Firestore Timestamp
        return datetime.fromtimestamp(val._seconds).isoformat()
    if isinstance(val, list):
        return [safe_serialize(v) for v in val]
    if isinstance(val, dict):
        return {k: safe_serialize(v) for k, v in val.items()}
    return val


def export_collection(db, collection_name, output_dir):
    """Export a top-level Firestore collection to a JSON file."""
    print(f"  📥 Exporting '{collection_name}'...")
    docs = list(db.collection(collection_name).stream())
    
    if not docs:
        print(f"     ⚠️  Empty collection — skipping")
        return []

    rows = []
    for doc in docs:
        data = doc.to_dict() or {}
        row = {'_id': doc.id}
        for k, v in data.items():
            row[k] = safe_serialize(v)
        rows.append(row)

    filepath = os.path.join(output_dir, f"{collection_name}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"     ✅ {len(rows)} documents → {filepath}")
    return rows


def export_outlet_ingredients(db, outlet_docs, output_dir):
    """Export all outlet ingredient subcollections."""
    print(f"  📥 Exporting 'outlet_ingredients' (subcollections)...")
    all_ingredients = []
    
    for outlet_doc in outlet_docs:
        outlet_id = outlet_doc['_id']
        ing_docs = list(db.collection('outlets').document(outlet_id).collection('ingredients').stream())
        
        for doc in ing_docs:
            data = doc.to_dict() or {}
            row = {'_id': doc.id, 'outlet_id': outlet_id}
            for k, v in data.items():
                row[k] = safe_serialize(v)
            all_ingredients.append(row)
    
    if all_ingredients:
        filepath = os.path.join(output_dir, 'outlet_ingredients.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(all_ingredients, f, ensure_ascii=False, indent=2, default=str)
        print(f"     ✅ {len(all_ingredients)} ingredients → {filepath}")
    else:
        print(f"     ⚠️  No ingredients found in subcollections")


def main():
    # Check key file
    if not os.path.exists(FIREBASE_KEY_PATH):
        print(f"\n❌ ERROR: Firebase key file not found at:")
        print(f"   {FIREBASE_KEY_PATH}")
        print(f"\n👉 Please update FIREBASE_KEY_PATH at the top of this script")
        print(f"   with the path to your downloaded service account JSON file.")
        return

    # Import Firebase
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        print("❌ firebase-admin not installed. Run: pip install firebase-admin")
        return

    # Init Firebase
    print(f"\n🔌 Connecting to Firebase (manger-ai)...")
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Connected!\n")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 Saving exports to: ./{OUTPUT_DIR}/\n")

    # Export all collections
    collections = [
        'outlets',
        'items',
        'recipes',
        'sales',
        'production_logs',
        'staff',
        'attendance_records',
        'attendance',
        'salary_payments',
        'expenses',
        'cctv_observations',
    ]

    outlet_docs = []
    for col in collections:
        rows = export_collection(db, col, OUTPUT_DIR)
        if col == 'outlets':
            outlet_docs = rows

    # Export subcollections (ingredients)
    if outlet_docs:
        export_outlet_ingredients(db, outlet_docs, OUTPUT_DIR)

    print(f"\n{'='*50}")
    print(f"✅ Export complete! Check the '{OUTPUT_DIR}/' folder.")
    print(f"{'='*50}")
    print(f"\nNext step: Run migrate_firestore_to_supabase.py to upload to Supabase")


if __name__ == '__main__':
    main()
