# items/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime 
from bakery_ai_manager.firestore_client import get_firestore_client
from google.cloud.firestore import Client as FirestoreClient # Explicitly import Client

db = get_firestore_client()

@api_view(["GET", "POST"])
def manage_products(request):
    items_collection_ref = db.collection('items')

    if request.method == 'GET':
        products_list = []
        try:
            docs = items_collection_ref.stream()
            for doc in docs:
                product_data = doc.to_dict()
                product_data['id'] = doc.id 
                products_list.append(product_data)
            return Response(products_list, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"ERROR: Failed to fetch products: {e}")
            return Response({"error": "Failed to fetch products", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'POST':
        required_fields = ["name", "price", "stock", "img"] 
        for field in required_fields:
            if field not in request.data:
                return Response({"error": f"Missing required field: {field}"}, status=status.HTTP_400_BAD_REQUEST)
        
        product_name = request.data.get("name").strip()
        product_id = product_name.lower().replace(" ", "_") 
        
        existing_doc = items_collection_ref.document(product_id).get()
        if existing_doc.exists:
            return Response({"error": f"Product with name '{product_name}' already exists (ID: {product_id})."}, status=status.HTTP_409_CONFLICT)

        new_product_data = {
            "name": product_name,
            "price": float(request.data.get("price")),
            "stock": int(request.data.get("stock")),
            "img": request.data.get("img"),
            "created_at": datetime.now().isoformat() 
        }
        try:
            items_collection_ref.document(product_id).set(new_product_data)
            print(f"DEBUG: Added new product '{product_name}' with ID: {product_id}")
            return Response(
                {"message": "Product added successfully", "product_id": product_id},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            print(f"ERROR: Failed to add product: {e}")
            return Response(
                {"error": "Failed to add product", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return Response({"error": "Method Not Allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


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
        docs = items_collection_ref.order_by('name').stream() # Order by name for readability
        
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

