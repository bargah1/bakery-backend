#!/usr/bin/env python3
"""
=============================================================
migrate_firestore_to_supabase.py
One-time data migration script: Firebase Firestore → Supabase PostgreSQL

Usage:
  1. Set env vars: GOOGLE_APPLICATION_CREDENTIALS_JSON, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  2. pip install firebase-admin supabase
  3. python migrate_firestore_to_supabase.py

This script reads every Firestore collection and inserts data
into the corresponding Supabase PostgreSQL table.
=============================================================
"""

import os
import json
import sys
from datetime import datetime

# ---- Load env ----
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---- Init Firebase ----
import firebase_admin
from firebase_admin import credentials, firestore as fb_firestore

def init_firebase():
    cred = credentials.Certificate(r"c:\Users\mxsab\OneDrive\Desktop\bakery-backend\manger-ai-firebase-adminsdk-fbsvc-dd153f7c46.json")
    firebase_admin.initialize_app(cred)
    return fb_firestore.client()

# ---- Init Supabase ----
from supabase import create_client

def init_supabase():
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def safe_isoformat(val):
    """Convert Firestore timestamps to ISO strings."""
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return val


def to_dict_safe(doc):
    """Convert a Firestore doc to a plain dict, serializing timestamps."""
    d = doc.to_dict() or {}
    result = {}
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            result[k] = v.isoformat()
        elif isinstance(v, list):
            result[k] = [
                (item.isoformat() if hasattr(item, 'isoformat') else item)
                for item in v
            ]
        else:
            result[k] = v
    return result


def batch_upsert(supabase, table: str, rows: list, pk: str = 'id', batch_size=100):
    """Upsert rows in batches."""
    total = len(rows)
    for i in range(0, total, batch_size):
        chunk = rows[i:i + batch_size]
        try:
            supabase.table(table).upsert(chunk).execute()
            print(f"  ✅ Upserted {min(i + batch_size, total)}/{total} rows into '{table}'")
        except Exception as e:
            print(f"  ❌ Error upserting to '{table}': {e}")


def migrate_outlets(fb, sb):
    print("\n📦 Migrating: outlets")
    docs = list(fb.collection('outlets').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'id': doc.id,
            'name': d.get('name', ''),
            'phone': d.get('phone', ''),
            'type': d.get('type', 'sales'),
        })
    batch_upsert(sb, 'outlets', rows)
    return {doc.id for doc in docs}


def migrate_items(fb, sb):
    print("\n📦 Migrating: items")
    docs = list(fb.collection('items').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'id': doc.id,
            'name': d.get('name', ''),
            'price': float(d.get('price', 0)),
            'stock': float(d.get('stock', 0)),
            'unit_type': d.get('unit_type', 'piece'),
            'low_stock_threshold': float(d.get('low_stock_threshold', 10.0)),
            'barcode': d.get('barcode'),
            'type': d.get('type', 'production'),
            'cost_price': float(d.get('cost_price', 0.0)),
            'image_url': d.get('image_url', ''),
            'is_active': d.get('is_active', True),
            'outlet_ids': d.get('outlet_ids', []),
            'malayalam_name': d.get('malayalam_name', ''),
            'created_at': d.get('created_at', datetime.now().isoformat()),
        })
    batch_upsert(sb, 'items', rows)


def migrate_recipes(fb, sb):
    print("\n📦 Migrating: recipes")
    docs = list(fb.collection('recipes').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'id': doc.id,
            'name': d.get('name', ''),
            'unit_type': d.get('unit_type'),
            'ingredients': d.get('ingredients', []),
            'shelf_life_days': d.get('shelf_life_days'),
            'calories': d.get('calories'),
            'energy': d.get('energy'),
            'nutrition_info': d.get('nutrition_info'),
            'rate': d.get('rate'),
        })
    batch_upsert(sb, 'recipes', rows)


def migrate_sales(fb, sb):
    print("\n📦 Migrating: sales")
    docs = list(fb.collection('sales').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'id': doc.id,
            'date': d.get('date', ''),
            'timestamp': d.get('timestamp'),
            'numeric_bill_id': str(d.get('numeric_bill_id', '')),
            'total_amount': float(d.get('total_amount', 0)),
            'total_cogs': float(d.get('total_cogs', 0)),
            'items': d.get('items', []),
            'outlet_id': d.get('outlet_id'),
            'staff_id': d.get('staff_id'),
            'customer_id': d.get('customer_id', 'anonymous'),
            'payment_method': d.get('payment_method'),
            'payment_status': d.get('payment_status', 'Paid'),
        })
    batch_upsert(sb, 'sales', rows, pk='id')


def migrate_production_logs(fb, sb):
    print("\n📦 Migrating: production_logs")
    docs = list(fb.collection('production_logs').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'batch_id': doc.id,
            'recipe_id': d.get('recipe_id'),
            'quantity_produced': float(d.get('quantity_produced', 0)),
            'production_unit_id': d.get('production_unit_id'),
            'total_cost': float(d.get('total_cost', 0)),
            'date': d.get('date', ''),
            'timestamp': d.get('timestamp'),
        })
    batch_upsert(sb, 'production_logs', rows, pk='batch_id')


def migrate_outlet_ingredients(fb, sb, outlet_ids: set):
    print("\n📦 Migrating: outlet_ingredients (subcollections)")
    rows = []
    for outlet_id in outlet_ids:
        ing_docs = list(fb.collection('outlets').document(outlet_id).collection('ingredients').stream())
        for doc in ing_docs:
            d = to_dict_safe(doc)
            rows.append({
                'id': doc.id,
                'outlet_id': outlet_id,
                'name': d.get('name', ''),
                'unit': d.get('unit', ''),
                'stock': float(d.get('stock', 0)),
                'cost_per_unit': float(d.get('cost_per_unit', 0)),
                'low_stock_threshold': float(d.get('low_stock_threshold', 0)),
            })
    if rows:
        batch_upsert(sb, 'outlet_ingredients', rows)
    else:
        print("  ⚠️  No outlet ingredients found")


def migrate_staff(fb, sb):
    print("\n📦 Migrating: staff")
    docs = list(fb.collection('staff').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'id': doc.id,
            'name': d.get('name', ''),
            'role': d.get('role', ''),
            'contact_number': d.get('contact_number', ''),
            'address': d.get('address', ''),
            'emergency_contact': d.get('emergency_contact', ''),
            'image_urls': d.get('image_urls', []),
            'face_encodings': [],  # Not migrating face data
            'location_id': d.get('location_id', ''),
            'salary': float(d.get('salary', 0)),
            'created_at': d.get('created_at', datetime.now().isoformat()),
        })
    batch_upsert(sb, 'staff', rows)


def migrate_attendance_records(fb, sb):
    print("\n📦 Migrating: attendance_records")
    docs = list(fb.collection('attendance_records').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'id': doc.id,
            'staff_id': d.get('staff_id'),
            'date': d.get('date', ''),
            'punch_type': d.get('punch_type', 'clock_in'),
            'timestamp': d.get('timestamp', datetime.now().isoformat()),
            'location_id': d.get('location_id', ''),
            'staff_name': d.get('staff_name', ''),
        })
    batch_upsert(sb, 'attendance_records', rows)


def migrate_attendance(fb, sb):
    print("\n📦 Migrating: attendance (simple status)")
    docs = list(fb.collection('attendance').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'id': doc.id,
            'staff_id': d.get('staff_id'),
            'date': d.get('date', ''),
            'status': d.get('status', ''),
            'timestamp': d.get('timestamp', datetime.now().isoformat()),
        })
    if rows:
        batch_upsert(sb, 'attendance', rows)


def migrate_salary_payments(fb, sb):
    print("\n📦 Migrating: salary_payments")
    docs = list(fb.collection('salary_payments').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'id': doc.id,
            'staff_id': d.get('staff_id'),
            'amount': float(d.get('amount', 0)),
            'payment_date': d.get('payment_date'),
            'period_start': d.get('period_start'),
            'period_end': d.get('period_end'),
            'expense_doc_id': d.get('expense_doc_id'),
        })
    if rows:
        batch_upsert(sb, 'salary_payments', rows)


def migrate_expenses(fb, sb):
    print("\n📦 Migrating: expenses")
    docs = list(fb.collection('expenses').stream())
    rows = []
    for doc in docs:
        d = to_dict_safe(doc)
        rows.append({
            'id': doc.id,
            'description': d.get('description'),
            'amount': float(d.get('amount', 0)),
            'category': d.get('category'),
            'date': d.get('date', ''),
            'outlet_id': d.get('outlet_id', 'general'),
            'created_at': d.get('created_at', datetime.now().isoformat()),
        })
    batch_upsert(sb, 'expenses', rows)


def main():
    print("=" * 60)
    print("🚀 Bakery Firestore → Supabase Migration")
    print("=" * 60)

    print("\n🔌 Initializing Firebase...")
    fb = init_firebase()
    print("✅ Firebase connected")

    print("\n🔌 Initializing Supabase...")
    sb = init_supabase()
    print("✅ Supabase connected")

    print("\n▶️  Starting migration...\n")

    # Order matters — FK dependencies first
    outlet_ids = migrate_outlets(fb, sb)
    migrate_items(fb, sb)
    migrate_recipes(fb, sb)
    migrate_sales(fb, sb)
    migrate_production_logs(fb, sb)
    migrate_outlet_ingredients(fb, sb, outlet_ids)
    migrate_staff(fb, sb)
    migrate_attendance_records(fb, sb)
    migrate_attendance(fb, sb)
    migrate_salary_payments(fb, sb)
    migrate_expenses(fb, sb)

    print("\n" + "=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Verify row counts in Supabase dashboard")
    print("  2. Run the app against Supabase")
    print("  3. Delete Firebase project when satisfied")


if __name__ == '__main__':
    main()
