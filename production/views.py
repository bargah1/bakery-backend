# =======================================================
# File: production/views.py (Final Corrected Version)
# =======================================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timezone
import time
from firebase_admin import firestore
from bakery_ai_manager.firestore_client import get_firestore_client
from google.cloud.firestore_v1.base_query import FieldFilter
from google.api_core import exceptions

db = get_firestore_client()

# --- Ingredient Management Views ---
@api_view(['GET', 'POST'])
def manage_ingredients_by_outlet(request, outlet_id):
    ingredients_ref = db.collection('outlets').document(outlet_id).collection('ingredients')
    if request.method == 'GET':
        docs = ingredients_ref.order_by('name').stream()
        return Response([{'id': doc.id, **doc.to_dict()} for doc in docs])
    
    if request.method == 'POST':
        data = request.data
        name, unit = data.get('name'), data.get('unit')
        stock = float(data.get('stock', 0))
        cost_per_unit = float(data.get('cost_per_unit', 0))
        if not all([name, unit]):
            return Response({'error': 'Ingredient name and unit are required.'}, status=400)
        
        ingredient_id = name.lower().replace(' ', '_')
        ingredients_ref.document(ingredient_id).set({
            'name': name, 'unit': unit, 'stock': stock, 'cost_per_unit': cost_per_unit
        })
        return Response({'id': ingredient_id, 'message': 'Ingredient added.'}, status=201)

@api_view(['PUT', 'DELETE'])
def manage_single_ingredient_by_outlet(request, outlet_id, ingredient_id):
    ingredient_ref = db.collection('outlets').document(outlet_id).collection('ingredients').document(ingredient_id)
    if request.method == 'PUT':
        ingredient_ref.update(request.data)
        return Response({'message': 'Ingredient updated.'})
    if request.method == 'DELETE':
        ingredient_ref.delete()
        return Response(status=204)

# *** FIX: Corrected logic to properly sum stock from all units ***
@api_view(['GET'])
def get_all_ingredients(request):
    all_ingredients = {}
    try:
        outlets_ref = db.collection('outlets')
        # We only care about production units for total ingredient stock
        query = outlets_ref.where(filter=FieldFilter('type', '==', 'production'))
        production_units = list(query.stream())
        
        for unit in production_units:
            ingredients_ref = unit.reference.collection('ingredients')
            for doc in ingredients_ref.stream():
                doc_data = doc.to_dict()
                ingredient_id = doc.id
                
                # If we've seen this ingredient before, add to its stock
                if ingredient_id in all_ingredients:
                    all_ingredients[ingredient_id]['stock'] += doc_data.get('stock', 0)
                # Otherwise, add it to our dictionary for the first time
                else:
                    all_ingredients[ingredient_id] = doc_data
        
        # Convert the dictionary to a list for the final response
        ingredient_list = [{'id': key, **value} for key, value in all_ingredients.items()]
        return Response(ingredient_list)
    except Exception as e:
        print(f"ERROR fetching all ingredients: {e}")
        return Response({"error": "Could not fetch master ingredient list."}, status=500)

# --- Recipe (Product) Management ---
@api_view(['GET', 'POST'])
def manage_recipes(request):
    recipes_ref = db.collection('recipes')
    if request.method == 'GET':
        docs = recipes_ref.order_by('name').stream()
        recipes = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        return Response(recipes)
    if request.method == 'POST':
        data = request.data
        name = data.get('name')
        if not name:
            return Response({'error': 'Product name is required.'}, status=400)
        
        recipe_id = name.lower().replace(' ', '_')
        
        recipe_data = {
            'name': name,
            'unit_type': data.get('unit_type'),
            'ingredients': data.get('ingredients', []),
            'shelf_life_days': data.get('shelf_life_days'),
            'calories': data.get('calories'),
            'energy': data.get('energy'),
            'nutrition_info': data.get('nutrition_info')
        }
        
        item_data = {
            'name': name,
            'unit_type': data.get('unit_type'),
            'price': data.get('price', 0),
            'stock': data.get('stock', 0)
        }
        
        recipes_ref.document(recipe_id).set(recipe_data)
        db.collection('items').document(recipe_id).set(item_data, merge=True)
        
        return Response({'id': recipe_id, 'message': 'Recipe added/updated.'}, status=201)
@api_view(['PUT', 'DELETE'])
def manage_single_recipe(request, recipe_id):
    recipe_ref = db.collection('recipes').document(recipe_id)
    item_ref = db.collection('items').document(recipe_id)

    if request.method == 'PUT':
        data = request.data
        
        recipe_data = {
            'name': data.get('name'),
            'unit_type': data.get('unit_type'),
            'ingredients': data.get('ingredients'),
            'shelf_life_days': data.get('shelf_life_days'),
            'calories': data.get('calories'),
            'energy': data.get('energy'),
            'nutrition_info': data.get('nutrition_info'),
            'rate': data.get('rate') 
        }

        item_data = {
            'name': data.get('name'),
            'unit_type': data.get('unit_type'),
            'price': data.get('rate') 
        }

        # *** FIXED: Changed comma to colon in both lines ***
        recipe_updates = {k: v for k, v in recipe_data.items() if v is not None}
        item_updates = {k: v for k, v in item_data.items() if v is not None}
        
        if recipe_updates:
            recipe_ref.update(recipe_updates)
        
        if item_updates:
            item_ref.update(item_updates)
        
        return Response({'message': 'Recipe updated.'})
        
    if request.method == 'DELETE':
        recipe_ref.delete()
        item_ref.delete()
        return Response(status=204)
# --- Production Recording ---
@api_view(['POST'])
def record_production(request):
    data = request.data
    recipe_id, unit_id, quantity = data.get('recipe_id'), data.get('production_unit_id'), float(data.get('quantity', 0))

    if not all([recipe_id, unit_id, quantity > 0]):
        return Response({'error': 'Recipe, Production Unit, and a positive quantity are required.'}, status=400)

    try:
        timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        batch_id = f"{recipe_id.upper()}-{timestamp_str}"

        @firestore.transactional
        def update_stock_in_transaction(transaction):
            recipe_ref = db.collection('recipes').document(recipe_id)
            recipe_doc_snapshot = recipe_ref.get(transaction=transaction)
            if not recipe_doc_snapshot.exists: raise Exception(f"Recipe '{recipe_id}' not found.")
            recipe_doc = recipe_doc_snapshot.to_dict()
            
            total_batch_cost = 0.0
            
            for req_ingredient in recipe_doc.get('ingredients', []):
                ing_id, ing_qty_needed = req_ingredient['id'], float(req_ingredient['quantity'])
                
                ing_ref = db.collection('outlets').document(unit_id).collection('ingredients').document(ing_id)
                ing_doc_snapshot = ing_ref.get(transaction=transaction)
                if not ing_doc_snapshot.exists: raise Exception(f"Ingredient '{ing_id}' not found in this unit.")
                ing_doc = ing_doc_snapshot.to_dict()

                ing_cost_per_unit = float(ing_doc.get('cost_per_unit', 0))
                total_needed = ing_qty_needed * quantity
                
                if total_needed > ing_doc.get('stock', 0):
                    raise Exception(f"Not enough stock for {ing_doc.get('name')}. Required: {total_needed}, Available: {ing_doc.get('stock', 0)}")

                total_batch_cost += total_needed * ing_cost_per_unit
                
                transaction.update(ing_ref, {'stock': firestore.Increment(-total_needed)})

            product_ref = db.collection('items').document(recipe_id)
            transaction.update(product_ref, {'stock': firestore.Increment(quantity)})
            
            log_ref = db.collection('production_logs').document(batch_id)
            transaction.set(log_ref, {
                'batch_id': batch_id,
                'recipe_id': recipe_id, 'quantity_produced': quantity,
                'production_unit_id': unit_id, 'total_cost': total_batch_cost,
                'timestamp': datetime.now(timezone.utc), 'date': datetime.now(timezone.utc).date().isoformat()
            })
            return batch_id

        final_batch_id = update_stock_in_transaction(db.transaction())
        
        return Response({
            'message': 'Production recorded and stock/cost updated.',
            'batch_id': final_batch_id 
        }, status=200)

    except Exception as e:
        return Response({'error': f'An error occurred: {e}'}, status=500)
    
    
# --- Reporting Views ---
@api_view(["GET"])
def get_structured_production_report(request):
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        production_unit_id = request.GET.get('production_unit_id')
        
        query = db.collection('production_logs')

        if start_date_str: query = query.where(filter=FieldFilter('date', '>=', start_date_str))
        if end_date_str: query = query.where(filter=FieldFilter('date', '<=', end_date_str))
        if production_unit_id and production_unit_id != 'All Production Units':
            query = query.where(filter=FieldFilter('production_unit_id', '==', production_unit_id))
        
        query = query.order_by('date', direction=firestore.Query.DESCENDING).order_by('timestamp', direction=firestore.Query.DESCENDING)

        docs = query.stream()
        data = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        return Response(data, status=status.HTTP_200_OK)

    except exceptions.FailedPrecondition as e:
        error_message = f"Database Index Missing: Your query requires a custom index in Firestore. Please check your Django server console log. It should contain a URL to create the required index automatically. Error details: {e}"
        print(f"ERROR: {error_message}")
        return Response({"error": error_message}, status=500)
    except Exception as e:
        print(f"ERROR: Failed to retrieve structured production data: {e}")
        return Response({"error": "An unknown error occurred while fetching production data.", "details": str(e)}, status=500)


@api_view(['DELETE'])
def delete_production_logs(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    production_unit_id = request.GET.get('production_unit_id')

    if not start_date or not end_date:
        return Response({'error': 'Start and end dates are required.'}, status=400)
    try:
        query = db.collection('production_logs').where(filter=FieldFilter('date', '>=', start_date)).where(filter=FieldFilter('date', '<=', end_date))
        if production_unit_id and production_unit_id != 'All Production Units':
            query = query.where(filter=FieldFilter('production_unit_id', '==', production_unit_id))
        
        docs_to_delete = list(query.stream())
        if not docs_to_delete:
            return Response({'message': 'No logs found to delete.'}, status=200)
        
        batch = db.batch()
        for doc in docs_to_delete:
            batch.delete(doc.reference)
        batch.commit()
        return Response({'message': f'Deleted {len(docs_to_delete)} production logs.'}, status=200)
    except Exception as e:
        return Response({'error': f'Failed to delete logs: {e}'}, status=500)
