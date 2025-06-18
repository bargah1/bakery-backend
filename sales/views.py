# sales/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from bakery_ai_manager.firestore_client import get_firestore_client
import firebase_admin.firestore 
from ownerbot.gpt_handler import get_sales_report 

db = get_firestore_client()

@api_view(["POST"])
def record_sale(request):
    """
    API endpoint to record a sale transaction from a billing system.
    Expected data in request.data:
    {
        "outlet_id": "outlet_1",
        "items": [
            {"item_id": "croissant", "quantity": 2, "unit_price": 2.50},
            {"item_id": "coffee", "quantity": 1, "unit_price": 3.00}
        ],
        "total_amount": 8.00,
        "payment_method": "cash",
        "customer_id": "customer_abc_123" # NEW: Optional customer ID
        "payment_status": "Paid" # NEW: Optional payment status (e.g., 'Paid', 'Pending', 'Refunded')
    }
    This version also attempts to decrement inventory in the 'items' collection.
    """
    required_fields = ["outlet_id", "items", "total_amount", "payment_method"]
    for field in required_fields:
        if field not in request.data:
            return Response(
                {"error": f"Missing required field: {field}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    sale_data = {
        "outlet_id": request.data.get("outlet_id"),
        "items": request.data.get("items"),
        "total_amount": request.data.get("total_amount"),
        "payment_method": request.data.get("payment_method"),
        "customer_id": request.data.get("customer_id", "anonymous"), # NEW: Default to anonymous
        "payment_status": request.data.get("payment_status", "Paid"), # NEW: Default to Paid
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().date().isoformat(), 
    }

    try:
        # 1. Add to sales collection
        sales_ref = db.collection('sales')
        update_time, doc_ref = sales_ref.add(sale_data)
        
        # 2. Decrement Inventory in 'items' collection
        items_collection_ref = db.collection('items')
        
        for sold_item in sale_data["items"]:
            item_id = sold_item.get("item_id")
            quantity = sold_item.get("quantity", 0)

            if item_id and quantity > 0:
                item_doc_ref = items_collection_ref.document(item_id)
                
                try:
                    item_doc_ref.update({
                        'stock': firebase_admin.firestore.FieldValue.increment(-quantity) 
                    })
                    print(f"DEBUG: Decremented stock for {item_id} by {quantity}")
                except Exception as update_error:
                    print(f"WARNING: Could not decrement stock for {item_id}: {update_error}")
        
        return Response(
            {"message": "Sale recorded successfully and inventory updated (if items exist)", "sale_id": doc_ref.id},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        print(f"ERROR: Failed to record sale or update inventory: {e}")
        return Response(
            {"error": "Failed to record sale or update inventory", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
def get_sales_summary_report(request): 
    """
    API endpoint to retrieve aggregated sales report as plain text for chatbot.
    Query parameters: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), outlet_id
    """
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    outlet_id = request.query_params.get('outlet_id')

    try:
        report_text = get_sales_report(start_date=start_date, end_date=end_date, outlet_id=outlet_id) 
        return Response({"report": report_text}, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Failed to get sales summary: {e}")
        return Response({"error": "Failed to retrieve sales report", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def get_structured_sales_report(request):
    """
    API endpoint to retrieve structured sales data for charting.
    Query parameters: start_date (YYYY-MM-DD, optional), end_date (YYYY-MM-DD, optional), outlet_id (optional)
    Returns: List of sales records, each with date, total_amount, items, etc.
    """
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    outlet_id = request.query_params.get('outlet_id')

    sales_ref = db.collection('sales')
    query = sales_ref

    if start_date_str:
        query = query.where('date', '>=', start_date_str)
    if end_date_str:
        query = query.where('date', '<=', end_date_str)
    if outlet_id:
        query = query.where('outlet_id', '==', outlet_id)
    
    # Order by date for charting
    query = query.order_by('date').order_by('timestamp')

    structured_data = []
    try:
        docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id # Include doc ID if useful for frontend
            structured_data.append(data)
        
        if not structured_data:
            return Response({"message": "No sales data found for selected criteria."}, status=status.HTTP_200_OK)
        
        return Response(structured_data, status=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Failed to retrieve structured sales data: {e}")
        return Response(
            {"error": "Failed to retrieve structured sales data", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["GET"])
def get_customer_transactions_report(request): # NEW: Customer Transactions Report Endpoint
    """
    API endpoint to retrieve a report of customer transactions.
    Query parameters: customer_id (optional), start_date (YYYY-MM-DD, optional), end_date (YYYY-MM-DD, optional)
    """
    customer_id = request.query_params.get('customer_id')
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')

    sales_ref = db.collection('sales')
    query = sales_ref

    if customer_id:
        query = query.where('customer_id', '==', customer_id)
    if start_date_str:
        query = query.where('date', '>=', start_date_str)
    if end_date_str:
        query = query.where('date', '<=', end_date_str)

    query = query.order_by('customer_id').order_by('timestamp') # Order for consistent reporting

    customer_transactions = {} # {customer_id: {total_spent: 0, visit_count: 0, transactions: []}}
    found_data = False

    try:
        docs = query.stream()
        for doc in docs:
            found_data = True
            record = doc.to_dict()
            c_id = record.get('customer_id', 'anonymous')
            total_amount = record.get('total_amount', 0.0)
            payment_status = record.get('payment_status', 'N/A')
            timestamp = record.get('timestamp', 'N/A')
            
            if c_id not in customer_transactions:
                customer_transactions[c_id] = {
                    'customer_id': c_id,
                    'total_spent': 0.0,
                    'visit_count': 0,
                    'transactions': []
                }
            
            customer_transactions[c_id]['total_spent'] += total_amount
            customer_transactions[c_id]['visit_count'] += 1
            customer_transactions[c_id]['transactions'].append({
                'timestamp': timestamp,
                'total_amount': total_amount,
                'payment_method': record.get('payment_method', 'N/A'),
                'payment_status': payment_status,
                'items_purchased': [{"item_id": item['item_id'], "quantity": item['quantity']} for item in record.get('items', [])]
            })

        report_lines = []
        report_lines.append("Customer Transactions Report:\n")
        report_lines.append("----------------------------------\n")

        if not found_data:
            report_lines.append("No customer transaction data found for the selected criteria.")
        else:
            for c_id, data in sorted(customer_transactions.items(), key=lambda item: item[0]): # Sort by customer ID
                report_lines.append(f"\nCustomer ID: {data['customer_id']}\n")
                report_lines.append(f"  Total Spent: ${data['total_spent']:.2f}\n")
                report_lines.append(f"  Total Visits: {data['visit_count']}\n")
                report_lines.append("  Transactions:\n")
                
                sorted_transactions = sorted(data['transactions'], key=lambda x: x['timestamp'])
                for transaction in sorted_transactions:
                    items_str = ", ".join([f"{item['item_id']} ({item['quantity']})" for item in transaction['items_purchased']])
                    report_lines.append(
                        f"    - At {datetime.fromisoformat(transaction['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}: "
                        f"Amount: ${transaction['total_amount']:.2f}, "
                        f"Method: {transaction['payment_method']}, "
                        f"Status: {transaction['payment_status']}\n"
                    )
                    if items_str:
                        report_lines.append(f"      Items: {items_str}\n")
        
        report_text = "".join(report_lines)
        return Response({"report": report_text, "structured_data": customer_transactions}, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"ERROR: Failed to retrieve customer transactions report: {e}")
        return Response(
            {"error": "Failed to retrieve customer transactions report", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

