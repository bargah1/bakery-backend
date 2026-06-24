# =======================================================
# File: sales/views.py (Migrated to Supabase)
# =======================================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timezone
import time

from bakery_ai_manager.supabase_client import get_supabase_client

db = get_supabase_client()


@api_view(["POST"])
def process_sale(request):
    """
    Records a sale and intelligently calculates the cost of goods sold (COGS)
    for each item at the time of sale.
    """
    try:
        sale_data = request.data
        items = sale_data.get('items', [])
        total_amount = sale_data.get('total_amount', 0)
        
        if not items or total_amount == 0:
            return Response({'error': 'Cannot process an empty sale'}, status=400)

        processed_items = []
        total_cogs = 0.0

        for item in items:
            product_id = item.get('product_id')
            if not product_id or 'custom_' in product_id:
                item['cost'] = 0.0
                processed_items.append(item)
                continue

            # Fetch the product from Supabase
            product_result = db.table('items').select('*').eq('id', product_id).execute()

            if product_result.data:
                product_data = product_result.data[0]
                item_cost = 0.0
                
                if product_data.get('type') == 'wholesale':
                    item_cost = float(product_data.get('cost_price', 0.0)) * item.get('quantity', 0)
                else:
                    item_cost = 0.0

                item['cost'] = item_cost
                total_cogs += item_cost

            processed_items.append(item)
            
            # Decrement stock for piece items
            if product_result.data and product_result.data[0].get('unit_type') == 'piece':
                quantity_sold = item.get('quantity', 0)
                if quantity_sold > 0:
                    db.rpc('decrement_stock', {
                        'item_id': product_id,
                        'qty': quantity_sold
                    }).execute()

        numeric_bill_id = str(int(time.time() * 100))[-7:]

        sale_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'date': datetime.now(timezone.utc).date().isoformat(),
            'numeric_bill_id': numeric_bill_id,
            'total_amount': total_amount,
            'total_cogs': total_cogs,
            'items': processed_items,
            'outlet_id': sale_data.get('outlet_id'),
            'staff_id': sale_data.get('staff_id')
        }
        
        result = db.table('sales').insert(sale_record).execute()
        sale_id = result.data[0]['id'] if result.data else None

        return Response({
            'message': 'Sale processed',
            'sale_id': sale_id,
            'numeric_bill_id': numeric_bill_id
        }, status=201)

    except Exception as e:
        print(f"ERROR processing sale: {e}")
        return Response({'error': f'An unexpected error occurred: {e}'}, status=500)


@api_view(["POST"])
def record_sale(request):
    """
    API endpoint to record a sale transaction from a billing system.
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
        "customer_id": request.data.get("customer_id", "anonymous"),
        "payment_status": request.data.get("payment_status", "Paid"),
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().date().isoformat(), 
    }

    try:
        result = db.table('sales').insert(sale_data).execute()
        sale_id = result.data[0]['id'] if result.data else None
        
        # Update stock for each sold item
        for sold_item in sale_data["items"]:
            item_id = sold_item.get("item_id")
            quantity = sold_item.get("quantity", 0)

            if item_id and quantity > 0:
                try:
                    db.rpc('decrement_stock', {
                        'item_id': item_id,
                        'qty': quantity
                    }).execute()
                    print(f"DEBUG: Decremented stock for {item_id} by {quantity}")
                except Exception as update_error:
                    print(f"WARNING: Could not decrement stock for {item_id}: {update_error}")
        
        return Response(
            {"message": "Sale recorded successfully and inventory updated (if items exist)", "sale_id": sale_id},
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
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    outlet_id = request.query_params.get('outlet_id')

    try:
        query = db.table('sales').select('*')
        if start_date:
            query = query.gte('date', start_date)
        if end_date:
            query = query.lte('date', end_date)
        if outlet_id and outlet_id != 'All Outlets':
            query = query.eq('outlet_id', outlet_id)

        result = query.execute()
        docs = result.data
        
        if not docs:
            report_text = f"No sales data found for outlet '{outlet_id or 'all outlets'}' from {start_date} to {end_date}."
            return Response({"report": report_text}, status=status.HTTP_200_OK)

        total_sales = 0.0
        items_sold = {}
        for sale_data in docs:
            total_sales += sale_data.get('total_amount', 0.0)
            for item in sale_data.get('items', []):
                if isinstance(item, dict) and item.get('product_id'):
                    item_name = item.get('product_id').replace('_', ' ').title()
                    
                    if item.get('quantity', 0) > 0:
                        key = f"{item_name} (x{item.get('quantity')})"
                        items_sold[key] = items_sold.get(key, 0) + item.get('quantity')
                    elif item.get('weight_grams', 0.0) > 0:
                        key = f"{item_name} ({item.get('weight_grams')} gm)"
                        items_sold[key] = items_sold.get(key, 0.0) + item.get('weight_grams')
                    elif item.get('custom_price', 0.0) > 0:
                        key = f"{item_name} (Custom Price)"
                        items_sold[key] = items_sold.get(key, 0.0) + item.get('custom_price')

        report_lines = [
            f"Sales Report for outlet '{outlet_id or 'all outlets'}' from {start_date} to {end_date}:",
            f"Total Sales: ₹{total_sales:,.2f}",
            "Items Sold:"
        ]
        
        if not items_sold:
            report_lines.append("  - No items were sold in this period.")
        else:
            for item_description in sorted(items_sold.keys()):
                report_lines.append(f"  - {item_description}")

        return Response({"report": "\n".join(report_lines)}, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"ERROR generating sales summary: {e}")
        return Response({"error": f"Failed to get sales summary: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_structured_sales_report(request):
    query = db.table('sales').select('*')
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    outlet_id = request.query_params.get('outlet_id')

    if start_date_str:
        query = query.gte('date', start_date_str)
    if end_date_str:
        query = query.lte('date', end_date_str)
    if outlet_id and outlet_id != 'All Outlets':
        query = query.eq('outlet_id', outlet_id)
    
    query = query.order('date').order('timestamp')

    try:
        result = query.execute()
        return Response(result.data, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"ERROR: Failed to retrieve structured sales data: {e}")
        return Response(
            {"error": "Failed to retrieve structured sales data", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def get_customer_transactions_report(request):
    query = db.table('sales').select('*')
    customer_id = request.query_params.get('customer_id')
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')

    if customer_id:
        query = query.eq('customer_id', customer_id)
    if start_date_str:
        query = query.gte('date', start_date_str)
    if end_date_str:
        query = query.lte('date', end_date_str)

    query = query.order('customer_id').order('timestamp')
    customer_transactions = {}
    found_data = False

    try:
        result = query.execute()
        for record in result.data:
            found_data = True
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
                'items_purchased': [{"item_id": item['item_id'], "quantity": item['quantity']} for item in record.get('items', []) if isinstance(item, dict)]
            })

        report_lines = []
        report_lines.append("Customer Transactions Report:\n")
        report_lines.append("----------------------------------\n")

        if not found_data:
            report_lines.append("No customer transaction data found for the selected criteria.")
        else:
            for c_id, data in sorted(customer_transactions.items(), key=lambda item: item[0]):
                report_lines.append(f"\nCustomer ID: {data['customer_id']}\n")
                report_lines.append(f"  Total Spent: ₹{data['total_spent']:.2f}\n")
                report_lines.append(f"  Total Visits: {data['visit_count']}\n")
                report_lines.append("  Transactions:\n")
                
                sorted_transactions = sorted(data['transactions'], key=lambda x: x['timestamp'])
                for transaction in sorted_transactions:
                    items_str = ", ".join([f"{item['item_id']} ({item['quantity']})" for item in transaction['items_purchased']])
                    report_lines.append(
                        f"    - At {datetime.fromisoformat(transaction['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}: "
                        f"Amount: ₹{transaction['total_amount']:.2f}, "
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


@api_view(["GET"])
def find_sale_by_bill_number(request, bill_number):
    try:
        result = db.table('sales').select('*').eq('numeric_bill_id', bill_number).limit(1).execute()
        if not result.data:
            return Response({'error': 'Bill not found with that number.'}, status=404)
        response_data = result.data[0]
        return Response(response_data, status=200)
    except Exception as e:
        print(f"ERROR finding sale by bill number {bill_number}: {e}")
        return Response({'error': f'An unexpected error occurred: {e}'}, status=500)


@api_view(["GET"])
def get_sale_details(request, sale_id):
    try:
        result = db.table('sales').select('*').eq('id', sale_id).execute()
        if not result.data:
            return Response({'error': 'Bill not found with that ID'}, status=404)
        return Response(result.data[0], status=200)
    except Exception as e:
        print(f"ERROR fetching sale {sale_id}: {e}")
        return Response({'error': f'An unexpected error occurred: {e}'}, status=500)

    
@api_view(["DELETE"])
def delete_sales_data(request):
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        outlet_id = request.query_params.get('outlet_id')
        if not start_date or not end_date:
            return Response({'error': 'Start date and end date are required for deletion.'}, status=400)
        
        query = db.table('sales').delete().gte('date', start_date).lte('date', end_date)
        if outlet_id and outlet_id != 'All Outlets':
            query = query.eq('outlet_id', outlet_id)
        
        result = query.execute()
        deleted_count = len(result.data) if result.data else 0
        
        if deleted_count == 0:
            return Response({'message': 'No sales data found to delete for the selected criteria.'}, status=200)
        return Response({'message': f'Successfully deleted {deleted_count} sales records.'}, status=200)
    except Exception as e:
        print(f"ERROR deleting sales data: {e}")
        return Response({'error': f'An unexpected error occurred during deletion: {e}'}, status=500)


@api_view(["GET"])
def get_sales_history(request):
    """
    Fetches a list of sales records within a given date range.
    """
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    try:
        query = db.table('sales').select('*')

        if start_date:
            query = query.gte('date', start_date)
        if end_date:
            query = query.lte('date', end_date)

        query = query.order('date', desc=True).order('timestamp', desc=True)

        result = query.execute()
        return Response(result.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"Failed to get sales history: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def find_sale_by_bill_id(request, numeric_bill_id):
    """
    Finds a single sale record by its numeric_bill_id.
    """
    if not numeric_bill_id:
        return Response({"error": "Bill number is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = db.table('sales').select('*').eq('numeric_bill_id', numeric_bill_id).limit(1).execute()

        if not result.data:
            return Response({"error": "Bill not found"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(result.data[0], status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": f"An error occurred while finding the bill: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
