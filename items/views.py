# ===================================================================
# File: items/views.py (Migrated to Supabase)
# ===================================================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from bakery_ai_manager.supabase_client import get_supabase_client
import time

# Initialize Supabase client
db = get_supabase_client()


# --- NEW: View to generate a unique barcode number ---
@api_view(['GET'])
def generate_barcode(request):
    """
    Generates a unique 13-digit EAN-13 style barcode number based on the current timestamp.
    """
    barcode = str(int(time.time() * 1000))[-12:]
    
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
    if request.method == 'GET':
        try:
            search_query = request.GET.get('search', '').lower().strip()
            
            result = db.table('items').select('*').order('name').execute()
            products_list = []
            for row in result.data:
                if search_query:
                    if search_query in row.get('name', '').lower():
                        products_list.append(row)
                else:
                    products_list.append(row)
            
            return Response(products_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to fetch products: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'POST':
        data = request.data
        name = data.get("name", "").strip()
        if not name:
            return Response({"error": "Product name cannot be empty"}, status=400)
        
        product_id = name.lower().replace(" ", "_")
        
        new_product_data = {
            "id": product_id,
            "name": name,
            "price": float(data.get("price", 0)),
            "stock": int(data.get("stock", 0)),
            "unit_type": data.get("unit_type", "piece"),
            "low_stock_threshold": float(data.get("low_stock_threshold", 10.0)),
            "barcode": data.get("barcode"),
            "type": data.get("type", "production"),
            "cost_price": float(data.get("cost_price", 0.0)),
            "image_url": data.get("image_url", ""),
            "created_at": datetime.now().isoformat()
        }
        db.table('items').upsert(new_product_data).execute()
        return Response({"message": "Product added", "id": product_id}, status=201)


@api_view(['GET', 'PUT', 'DELETE'])
def manage_single_product(request, product_id):
    """
    Handles viewing (GET), updating (PUT), and deleting (DELETE) a single product by its ID.
    """
    try:
        result = db.table('items').select('*').eq('id', product_id).execute()
        if not result.data:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        product_data = result.data[0]
    except Exception as e:
        return Response({"error": f"Failed to access product: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        return Response(product_data, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        try:
            update_data = dict(request.data)
            # Don't allow changing the primary key
            update_data.pop('id', None)
            db.table('items').update(update_data).eq('id', product_id).execute()
            return Response({"message": f"Product '{product_id}' updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Failed to update product: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'DELETE':
        try:
            db.table('items').delete().eq('id', product_id).execute()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": f"Failed to delete product: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_inventory_report(request):
    """
    API endpoint to retrieve a summary of current inventory levels.
    """
    inventory_report_lines = []
    total_items_in_stock = 0
    total_unique_products = 0

    try:
        result = db.table('items').select('*').order('name').execute()
        
        inventory_report_lines.append("Current Inventory Report:\n")
        inventory_report_lines.append("---------------------------\n")

        if not result.data:
            inventory_report_lines = ["No inventory data found. Please add products via the billing system."]
        else:
            for row in result.data:
                product_name = row.get('name', 'Unknown Product')
                stock = row.get('stock', 0)
                
                inventory_report_lines.append(f"- {product_name}: {stock} units\n")
                total_items_in_stock += stock
                total_unique_products += 1
            
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
    """
    Uploads a product image to Supabase Storage.
    """
    if 'file' not in request.FILES:
        return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

    file = request.FILES['file']

    file_path = f"product_images/{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.name}"

    try:
        file_bytes = file.read()
        
        db.storage.from_('product-images').upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": file.content_type}
        )
        
        # Get the public URL
        public_url = db.storage.from_('product-images').get_public_url(file_path)
        
        return Response({"image_url": public_url}, status=201)
    except Exception as e:
        print(f"ERROR uploading product image: {e}")
        return Response({"error": f"Failed to upload image: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)