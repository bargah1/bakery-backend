# ===================================================================
# File: items/views.py (Corrected and with Search)
# ===================================================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime 
from bakery_ai_manager.firestore_client import get_firestore_client
from google.cloud.firestore_v1.base_query import FieldFilter
import time 

# --- NEW/FIX: Import and initialize Google Cloud Storage client ---
from google.cloud import storage 

# Initialize Firestore DB client
db = get_firestore_client()

# Initialize Google Cloud Storage client
# Ensure your GOOGLE_APPLICATION_CREDENTIALS environment variable is set
# or you are running this on a GCP service with appropriate permissions.
# Replace 'your-gcs-bucket-name' with your actual GCS bucket name.
try:
    storage_client = storage.Client()
    # Replace 'your-gcs-bucket-name' with the actual name of your GCS bucket
    bucket = storage_client.bucket('asthana-bakery-items-images') 
except Exception as e:
    print(f"ERROR: Failed to initialize Google Cloud Storage client or bucket: {e}")
    # Handle this error appropriately in a real application (e.g., log, raise an exception)
    bucket = None # Set to None if initialization fails


# --- NEW: View to generate a unique barcode number ---
@api_view(['GET'])
def generate_barcode(request):
    """
    Generates a unique 13-digit EAN-13 style barcode number based on the current timestamp.
    """
    # Generate a unique number using the timestamp. This is not a registered EAN, but is unique.
    barcode = str(int(time.time() * 1000))[-12:] # Get 12 unique digits
    
    # Calculate checksum digit (standard EAN-13 algorithm)
    digits = [int(d) for d in barcode]
    odd_sum = sum(digits[0::2])
    even_sum = sum(digits[1::2])
    checksum = (10 - ((odd_sum + even_sum * 3) % 10)) % 10
    
    full_barcode = barcode + str(checksum)
    return Response({'barcode': full_barcode})

@api_view(['GET', 'POST'])
def manage_products(request):
    """
    Handles listing all products (GET) with optional search, 
    and creating a new product (POST).
    """
    items_collection_ref = db.collection('items')

    if request.method == 'GET':
        try:
            search_query = request.GET.get('search', '').lower().strip()
            
            docs = items_collection_ref.order_by('name').stream()
            products_list = []
            for doc in docs:
                product_data = doc.to_dict()
                product_data['id'] = doc.id
                
                if search_query:
                    if search_query in product_data.get('name', '').lower():
                        products_list.append(product_data)
                else:
                    products_list.append(product_data)
            
            return Response(products_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to fetch products: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    elif request.method == 'POST':
        data = request.data
        name = data.get("name", "").strip()
        if not name:
            return Response({"error": "Product name cannot be empty"}, status=400)
        
        product_id = name.lower().replace(" ", "_")
        
        # --- FIX: Add all new fields for product type and costing ---
        new_product_data = {
            "name": name,
            "price": float(data.get("price", 0)),
            "stock": int(data.get("stock", 0)),
            "unit_type": data.get("unit_type", "piece"),
            "low_stock_threshold": float(data.get("low_stock_threshold", 10.0)),
            "barcode": data.get("barcode"),
            "type": data.get("type", "production"), # 'production' or 'wholesale'
            "cost_price": float(data.get("cost_price", 0.0)), # Cost for wholesale items
            "image_url": data.get("image_url", ""), # URL for the product image
            "created_at": datetime.now().isoformat()
        }
        items_collection_ref.document(product_id).set(new_product_data)
        return Response({"message": "Product added", "id": product_id}, status=201)



@api_view(['GET', 'PUT', 'DELETE'])
def manage_single_product(request, product_id):
    """
    Handles viewing (GET), updating (PUT), and deleting (DELETE) a single product by its ID.
    This view is already correct and will work with the frontend.
    """
    product_ref = db.collection('items').document(product_id)
    
    try:
        product_snapshot = product_ref.get()
        if not product_snapshot.exists:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": f"Failed to access product: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        return Response(product_snapshot.to_dict(), status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        try:
            # Using .update() will correctly save all fields sent from the frontend.
            product_ref.update(request.data)
            return Response({"message": f"Product '{product_id}' updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to update product: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'DELETE':
        try:
            product_ref.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": f"Failed to delete product: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_inventory_report(request):
    """
    API endpoint to retrieve a summary of current inventory levels.
    """
    items_collection_ref = db.collection('items')
    inventory_report_lines = []
    total_items_in_stock = 0
    total_unique_products = 0

    try:
        docs = items_collection_ref.order_by('name').stream()
        
        inventory_report_lines.append("Current Inventory Report:\n")
        inventory_report_lines.append("---------------------------\n")

        found_items = False
        for doc in docs:
            found_items = True
            data = doc.to_dict()
            product_name = data.get('name', 'Unknown Product')
            stock = data.get('stock', 0)
            
            inventory_report_lines.append(f"- {product_name}: {stock} units\n")
            total_items_in_stock += stock
            total_unique_products += 1
        
        if not found_items:
            inventory_report_lines = ["No inventory data found. Please add products via the billing system."]
        else:
            inventory_report_lines.append("\n---------------------------\n")
            inventory_report_lines.append(f"Total Unique Products: {total_unique_products}\n")
            inventory_report_lines.append(f"Total Items In Stock: {total_items_in_stock} units\n")

        report_text = "".join(inventory_report_lines)
        return Response({"report": report_text}, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Failed to get inventory report: {e}")
        return Response({"error": "Failed to retrieve inventory report", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def upload_product_image(request):
    if 'file' not in request.FILES:
        return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

    file = request.FILES['file']

    if bucket is None:
        return Response({"error": "Google Cloud Storage bucket not initialized."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    destination_blob_name = f"product_images/{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.name}"
    blob = bucket.blob(destination_blob_name)

    try:
        blob.upload_from_file(file, content_type=file.content_type)
        # blob.make_public() # <--- REMOVE OR COMMENT OUT THIS LINE
        return Response({"image_url": blob.public_url}, status=201)
    except Exception as e:
        print(f"ERROR uploading product image: {e}")
        return Response({"error": f"Failed to upload image: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)