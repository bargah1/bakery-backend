# =======================================================
# File: reports/views.py (NEW FILE)
# =======================================================

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta, timezone 
from collections import Counter # <--- FIX: Added the missing import for Counter
from bakery_ai_manager.firestore_client import get_firestore_client
from google.cloud.firestore_v1.base_query import FieldFilter

db = get_firestore_client()

@api_view(['GET'])
def get_dashboard_summary(request):
    """
    Calculates and returns key performance indicators for the current day.
    """
    today_str = datetime.now(timezone.utc).date().isoformat()
    
    try:
        # Today's Revenue
        sales_query = db.collection('sales').where(filter=FieldFilter('date', '==', today_str))
        todays_revenue = sum(doc.to_dict().get('total_amount', 0.0) for doc in sales_query.stream())

        # Today's Cost of Goods Sold
        prod_query = db.collection('production_logs').where(filter=FieldFilter('date', '==', today_str))
        todays_cogs = sum(doc.to_dict().get('total_cost', 0.0) for doc in prod_query.stream())

        # Today's Operating Expenses
        expenses_query = db.collection('expenses').where(filter=FieldFilter('date', '==', today_str))
        todays_op_expenses = sum(doc.to_dict().get('amount', 0.0) for doc in expenses_query.stream())
        
        # Today's Salary Expenses (Approximation)
        staff_docs = db.collection('staff').stream()
        total_daily_salary_cost = sum(doc.to_dict().get('salary', 0.0) * 8 for doc in staff_docs) # Assumes 8-hour workday
        
        # Top Selling Item Today
        item_counts = Counter()
        sales_docs_for_items = db.collection('sales').where(filter=FieldFilter('date', '==', today_str)).stream()
        for doc in sales_docs_for_items:
            for item in doc.to_dict().get('items', []):
                item_id = item.get('product_id')
                if item_id:
                    # Consider both quantity and weight for top selling item
                    item_counts[item_id] += item.get('quantity', 0) + (item.get('weight_grams',0) / 1000)

        top_item = item_counts.most_common(1)[0][0] if item_counts else "N/A"

        # Final Calculations
        todays_profit = todays_revenue - (todays_cogs + todays_op_expenses + total_daily_salary_cost)

        summary_data = {
            'todays_revenue': todays_revenue,
            'todays_profit': todays_profit,
            'top_selling_item': top_item.replace('_', ' ').title(),
        }
        return Response(summary_data, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"ERROR generating dashboard summary: {e}")
        return Response({'error': f'An unexpected error occurred: {e}'}, status=500)


@api_view(['GET'])
def get_profit_loss_report(request):
    """
    Generates a comprehensive profit and loss report including sales, 
    cost of goods sold (COGS), operating expenses, and salary expenses.
    """
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        return Response({'error': 'Start date and end date are required.'}, status=400)

    try:
        # --- 1. Calculate Revenue and a more ACCURATE Cost of Goods Sold (COGS) ---
        total_revenue = 0.0
        cost_of_goods_sold = 0.0
        
        sales_query = db.collection('sales').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        for sale_doc in sales_query.stream():
            sale_data = sale_doc.to_dict()
            total_revenue += sale_data.get('total_amount', 0.0)
            
            # Calculate COGS for each item in the sale based on its type
            for item_sold in sale_data.get('items', []):
                product_ref = db.collection('items').document(item_sold.get('product_id'))
                product_doc = product_ref.get()
                if product_doc.exists:
                    product_data = product_doc.to_dict()
                    qty = item_sold.get('quantity', 0)
                    
                    if product_data.get('type') == 'wholesale':
                        # For wholesale items, cost is the stored purchase price
                        cost_of_goods_sold += product_data.get('cost_price', 0.0) * qty
                    # Note: Production item costs are calculated separately below

        # Add production costs for items made in-house during the period
        prod_query = db.collection('production_logs').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        production_cogs = sum(doc.to_dict().get('total_cost', 0.0) for doc in prod_query.stream())
        cost_of_goods_sold += production_cogs


        # --- 2. Calculate Operating Expenses ---
        expenses_query = db.collection('expenses').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        total_op_expenses = 0.0
        expense_breakdown = {}
        for doc in expenses_query.stream():
            expense = doc.to_dict()
            amount, category = expense.get('amount', 0.0), expense.get('category', 'Uncategorized')
            total_op_expenses += amount
            expense_breakdown[category] = expense_breakdown.get(category, 0.0) + amount
        

        # --- 3. Calculate Salary Expenses based on actual hours worked ---
        staff_salaries = {doc.id: doc.to_dict().get('salary', 0.0) for doc in db.collection('staff').stream()}
        attendance_query = db.collection('attendance_records').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        
        staff_hours = {}
        for punch in attendance_query.order_by('timestamp').stream():
            record = punch.to_dict()
            s_id = record.get('staff_id')
            if s_id:
                if s_id not in staff_hours:
                    staff_hours[s_id] = {'punches': []}
                staff_hours[s_id]['punches'].append(record)

        total_salary_expense = 0.0
        for staff_id, data in staff_hours.items():
            total_duration = timedelta()
            clock_in_time = None
            for punch in data['punches']:
                punch_time = datetime.fromisoformat(punch['timestamp'])
                if punch['punch_type'] == 'clock_in':
                    clock_in_time = punch_time
                elif punch['punch_type'] == 'clock_out' and clock_in_time:
                    duration = punch_time - clock_in_time
                    total_duration += duration
                    clock_in_time = None # Reset for next shift
            
            hours_worked = total_duration.total_seconds() / 3600
            salary_per_hour = staff_salaries.get(staff_id, 0.0)
            total_salary_expense += hours_worked * salary_per_hour
        
        if total_salary_expense > 0:
            expense_breakdown['Salaries'] = expense_breakdown.get('Salaries', 0.0) + total_salary_expense


        # --- 4. Final Calculation ---
        total_expenses = cost_of_goods_sold + total_op_expenses + total_salary_expense
        net_profit = total_revenue - total_expenses

        report_data = {
            'total_revenue': total_revenue,
            'cost_of_goods_sold': cost_of_goods_sold,
            'operating_expenses': total_op_expenses,
            'salary_expenses': total_salary_expense,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'expense_breakdown': expense_breakdown,
        }
        return Response(report_data, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"ERROR generating P&L report: {e}")
        return Response({'error': f'An unexpected error occurred: {e}'}, status=500)
@api_view(['DELETE'])
def clear_transaction_data(request):
    """
    Deletes all sales and expenses within a specified date range.
    """
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        return Response({'error': 'Start date and end date are required for deletion.'}, status=400)

    try:
        batch = db.batch()
        # Delete Sales
        sales_query = db.collection('sales').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        for doc in sales_query.stream():
            batch.delete(doc.reference)
        
        # Delete Expenses
        expenses_query = db.collection('expenses').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        for doc in expenses_query.stream():
            batch.delete(doc.reference)

        batch.commit()
        return Response({'message': 'Sales and expense data for the selected range have been cleared.'}, status=200)

    except Exception as e:
        return Response({'error': f'An unexpected error occurred: {e}'}, status=500)


@api_view(['GET'])
def get_low_stock_alerts(request):
    """
    Scans all products and ingredients and returns a list of items
    that are at or below their defined low_stock_threshold.
    """
    low_stock_products = []
    low_stock_ingredients = []

    try:
        # Check final products
        products_docs = db.collection('items').stream()
        for doc in products_docs:
            product = doc.to_dict()
            stock = product.get('stock', 0.0)
            threshold = product.get('low_stock_threshold', 0.0)
            if stock <= threshold:
                low_stock_products.append({
                    'name': product.get('name', doc.id),
                    'stock': stock,
                    'unit': product.get('unit', 'pieces'),
                    'threshold': threshold
                })

        # Check ingredients across all production outlets
        outlets_docs = db.collection('outlets').where(filter=FieldFilter('type', '==', 'production')).stream()
        for outlet in outlets_docs:
            ingredients_docs = outlet.reference.collection('ingredients').stream()
            for doc in ingredients_docs:
                ingredient = doc.to_dict()
                stock = ingredient.get('stock', 0.0)
                threshold = ingredient.get('low_stock_threshold', 0.0)
                if stock <= threshold:
                    low_stock_ingredients.append({
                        'name': ingredient.get('name', doc.id),
                        'stock': stock,
                        'unit': ingredient.get('unit', 'kg'),
                        'threshold': threshold,
                        'outlet_name': outlet.to_dict().get('name', outlet.id)
                    })
        
        return Response({
            'low_stock_products': low_stock_products,
            'low_stock_ingredients': low_stock_ingredients
        }, status=200)

    except Exception as e:
        print(f"ERROR checking low stock alerts: {e}")
        return Response({'error': f'An unexpected error occurred: {e}'}, status=500)

