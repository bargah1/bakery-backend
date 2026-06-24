import csv
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- CONFIGURATION ---
SERVICE_ACCOUNT_FILE = os.path.join('config', 'service_account_key.json')
CSV_FILE_TO_UPLOAD = os.path.join('config', 'items.csv')
# --- END CONFIGURATION ---

def initialize_firestore():
    """Initializes the Firestore client using the service account key."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"ERROR: Service account key file not found at '{SERVICE_ACCOUNT_FILE}'")
        return None
    
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase connection successful.")
        return db
    except Exception as e:
        print(f"🔥 Firebase connection failed: {e}")
        return None

def upload_products_from_csv(db):
    """Reads the CSV and uploads only new products to the 'items' collection."""
    if not os.path.exists(CSV_FILE_TO_UPLOAD):
        print(f"ERROR: CSV file not found: '{CSV_FILE_TO_UPLOAD}'")
        return

    items_ref = db.collection('items')
    print(f"Uploading data from '{CSV_FILE_TO_UPLOAD}'...")
    
    try:
        with open(CSV_FILE_TO_UPLOAD, mode='r', encoding='latin-1') as csvfile:
            reader = csv.reader(csvfile)
            
            # Skip header rows
            for _ in range(6):
                next(reader)

            products_added = 0
            products_skipped = 0
            for i, row in enumerate(reader, start=7): # Start counting from row 7 for logging
                # --- FIX: Wrap each row's processing in a try-except block ---
                try:
                    if len(row) < 13:
                        continue

                    item_name = row[3].strip()
                    if not item_name:
                        continue

                    # Sanitize the item name to create a valid ID, removing invalid characters
                    product_id = item_name.lower().replace(' ', '_').replace('.', '').replace('=', '').replace('-', '_').replace('/', '_')
                    
                    if not product_id:
                        print(f"⚠️ Skipping row {i} with original name '{item_name}' because it resulted in an empty ID.")
                        continue

                    doc_ref = items_ref.document(product_id)
                    if doc_ref.get().exists:
                        # This part is fine, no changes needed here.
                        # print(f"  - Skipping '{item_name}' (already exists)") 
                        products_skipped += 1
                        continue

                    supplier = row[6].strip()
                    stock_qty_str = row[7].strip()
                    cost_price_str = row[9].strip()
                    selling_price_str = row[12].strip()
                    barcode = row[1].strip()
                    product_type = 'production' if 'ASTHANA' in supplier.upper() else 'wholesale'

                    stock = int(float(stock_qty_str)) if stock_qty_str else 0
                    cost_price = float(cost_price_str) if cost_price_str else 0.0
                    selling_price = float(selling_price_str) if selling_price_str else 0.0

                    product_data = {
                        'name': item_name,
                        'price': selling_price,
                        'stock': stock,
                        'unit_type': 'piece',
                        'low_stock_threshold': 10,
                        'barcode': barcode if barcode else None,
                        'type': product_type,
                        'cost_price': cost_price if product_type == 'wholesale' else 0.0,
                        'image_url': '',
                        'created_at': datetime.now().isoformat()
                    }
                    
                    doc_ref.set(product_data)
                    products_added += 1
                    print(f"  -> Uploaded NEW: {item_name}")

                except Exception as row_error:
                    # This will catch the error for a single row and allow the script to continue
                    print(f"🔥 Error on row {i} with data '{row}'. Skipping. Reason: {row_error}")
                    continue
            
            # Print a summary at the end
            print(f"\n✅ Upload complete!")
            print(f"   - {products_added} new products added.")
            print(f"   - {products_skipped} products skipped (already existed).")

    except Exception as e:
        print(f"🔥 A fatal error occurred during the file reading process: {e}")

if __name__ == '__main__':
    db_client = initialize_firestore()
    if db_client:
        upload_products_from_csv(db_client)