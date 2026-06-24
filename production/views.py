# =======================================================
# File: production/views.py (Migrated to Supabase)
# =======================================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timezone
import time
from bakery_ai_manager.supabase_client import get_supabase_client

db = get_supabase_client()


# --- Ingredient Management Views ---
@api_view(['GET', 'POST'])
def manage_ingredients_by_outlet(request, outlet_id):
    if request.method == 'GET':
        try:
            result = db.table('outlet_ingredients').select('*').eq('outlet_id', outlet_id).order('name').execute()
            return Response(result.data)
        except Exception as e:
            return Response({'error': f'Failed to fetch ingredients: {e}'}, status=500)
    
    if request.method == 'POST':
        data = request.data
        name, unit = data.get('name'), data.get('unit')
        stock = float(data.get('stock', 0))
        cost_per_unit = float(data.get('cost_per_unit', 0))
        if not all([name, unit]):
            return Response({'error': 'Ingredient name and unit are required.'}, status=400)
        
        ingredient_id = name.lower().replace(' ', '_')
        ingredient_data = {
            'id': ingredient_id,
            'outlet_id': outlet_id,
            'name': name,
            'unit': unit,
            'stock': stock,
            'cost_per_unit': cost_per_unit
        }
        db.table('outlet_ingredients').upsert(ingredient_data).execute()
        return Response({'id': ingredient_id, 'message': 'Ingredient added.'}, status=201)


@api_view(['PUT', 'DELETE'])
def manage_single_ingredient_by_outlet(request, outlet_id, ingredient_id):
    if request.method == 'PUT':
        try:
            update_data = dict(request.data)
            update_data.pop('id', None)
            update_data.pop('outlet_id', None)
            db.table('outlet_ingredients').update(update_data).eq('id', ingredient_id).eq('outlet_id', outlet_id).execute()
            return Response({'message': 'Ingredient updated.'})
        except Exception as e:
            return Response({'error': f'Failed to update ingredient: {e}'}, status=500)
    
    if request.method == 'DELETE':
        try:
            db.table('outlet_ingredients').delete().eq('id', ingredient_id).eq('outlet_id', outlet_id).execute()
            return Response(status=204)
        except Exception as e:
            return Response({'error': f'Failed to delete ingredient: {e}'}, status=500)


@api_view(['GET'])
def get_all_ingredients(request):
    """Sum stock from all production units for each ingredient."""
    all_ingredients = {}
    try:
        # Get all production outlets
        outlets_result = db.table('outlets').select('id').eq('type', 'production').execute()
        production_unit_ids = [o['id'] for o in outlets_result.data]
        
        if not production_unit_ids:
            return Response([])
        
        # Get all ingredients for production units
        ingredients_result = db.table('outlet_ingredients').select('*').in_('outlet_id', production_unit_ids).execute()
        
        for doc_data in ingredients_result.data:
            ingredient_id = doc_data['id']
            
            if ingredient_id in all_ingredients:
                all_ingredients[ingredient_id]['stock'] += doc_data.get('stock', 0)
            else:
                all_ingredients[ingredient_id] = {
                    'id': ingredient_id,
                    'name': doc_data.get('name'),
                    'unit': doc_data.get('unit'),
                    'stock': doc_data.get('stock', 0),
                    'cost_per_unit': doc_data.get('cost_per_unit', 0)
                }
        
        ingredient_list = list(all_ingredients.values())
        return Response(ingredient_list)
    except Exception as e:
        print(f"ERROR fetching all ingredients: {e}")
        return Response({"error": "Could not fetch master ingredient list."}, status=500)


# --- Recipe (Product) Management ---
@api_view(['GET', 'POST'])
def manage_recipes(request):
    if request.method == 'GET':
        try:
            result = db.table('recipes').select('*').order('name').execute()
            return Response(result.data)
        except Exception as e:
            return Response({'error': f'Failed to fetch recipes: {e}'}, status=500)

    if request.method == 'POST':
        data = request.data
        name = data.get('name')
        if not name:
            return Response({'error': 'Product name is required.'}, status=400)
        
        recipe_id = name.lower().replace(' ', '_')
        
        recipe_data = {
            'id': recipe_id,
            'name': name,
            'unit_type': data.get('unit_type'),
            'ingredients': data.get('ingredients', []),
            'shelf_life_days': data.get('shelf_life_days'),
            'calories': data.get('calories'),
            'energy': data.get('energy'),
            'nutrition_info': data.get('nutrition_info')
        }
        
        item_data = {
            'id': recipe_id,
            'name': name,
            'unit_type': data.get('unit_type'),
            'price': data.get('price', 0),
            'stock': data.get('stock', 0)
        }
        
        db.table('recipes').upsert(recipe_data).execute()
        db.table('items').upsert(item_data).execute()
        
        return Response({'id': recipe_id, 'message': 'Recipe added/updated.'}, status=201)


@api_view(['PUT', 'DELETE'])
def manage_single_recipe(request, recipe_id):
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

        recipe_updates = {k: v for k, v in recipe_data.items() if v is not None}
        item_updates = {k: v for k, v in item_data.items() if v is not None}
        
        try:
            if recipe_updates:
                db.table('recipes').update(recipe_updates).eq('id', recipe_id).execute()
            if item_updates:
                db.table('items').update(item_updates).eq('id', recipe_id).execute()
            return Response({'message': 'Recipe updated.'})
        except Exception as e:
            return Response({'error': f'Failed to update recipe: {e}'}, status=500)
        
    if request.method == 'DELETE':
        try:
            db.table('recipes').delete().eq('id', recipe_id).execute()
            db.table('items').delete().eq('id', recipe_id).execute()
            return Response(status=204)
        except Exception as e:
            return Response({'error': f'Failed to delete recipe: {e}'}, status=500)


# --- Production Recording ---
@api_view(['POST'])
def record_production(request):
    """
    Records production using a PostgreSQL transaction function (RPC).
    """
    data = request.data
    recipe_id = data.get('recipe_id')
    unit_id = data.get('production_unit_id')
    quantity = float(data.get('quantity', 0))

    if not all([recipe_id, unit_id, quantity > 0]):
        return Response({'error': 'Recipe, Production Unit, and a positive quantity are required.'}, status=400)

    try:
        timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        batch_id = f"{recipe_id.upper()}-{timestamp_str}"

        # Get recipe ingredients
        recipe_result = db.table('recipes').select('ingredients').eq('id', recipe_id).execute()
        if not recipe_result.data:
            return Response({'error': f"Recipe '{recipe_id}' not found."}, status=404)
        
        ingredients = recipe_result.data[0].get('ingredients', [])

        # Call the PostgreSQL transaction function
        result = db.rpc('record_production_transaction', {
            'p_batch_id': batch_id,
            'p_recipe_id': recipe_id,
            'p_quantity': quantity,
            'p_production_unit_id': unit_id,
            'p_ingredients': ingredients,
            'p_date': datetime.now(timezone.utc).date().isoformat(),
            'p_timestamp': datetime.now(timezone.utc).isoformat()
        }).execute()

        return Response({
            'message': 'Production recorded and stock/cost updated.',
            'batch_id': batch_id
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
        
        query = db.table('production_logs').select('*')

        if start_date_str:
            query = query.gte('date', start_date_str)
        if end_date_str:
            query = query.lte('date', end_date_str)
        if production_unit_id and production_unit_id != 'All Production Units':
            query = query.eq('production_unit_id', production_unit_id)
        
        query = query.order('date', desc=True).order('timestamp', desc=True)

        result = query.execute()
        return Response(result.data, status=status.HTTP_200_OK)

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
        query = db.table('production_logs').delete().gte('date', start_date).lte('date', end_date)
        if production_unit_id and production_unit_id != 'All Production Units':
            query = query.eq('production_unit_id', production_unit_id)
        
        result = query.execute()
        deleted_count = len(result.data) if result.data else 0
        
        if deleted_count == 0:
            return Response({'message': 'No logs found to delete.'}, status=200)
        return Response({'message': f'Deleted {deleted_count} production logs.'}, status=200)
    except Exception as e:
        return Response({'error': f'Failed to delete logs: {e}'}, status=500)
