import os
import uuid
import logging
from flask import Flask, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from database import (init_db, get_all_recipes, get_recipe, add_recipe, update_recipe,
                      delete_recipe,
                      get_recipes_by_category, get_categories, search_recipes,
                      create_menu, get_all_menus, get_menu, update_menu_item, update_menu_meal_servings,
                      add_menu_recipe, remove_menu_recipe, update_recipe_servings,
                      delete_menu, get_menu_shopping_list, MEAL_TYPES,
                      get_all_pantry_items, add_pantry_item, update_pantry_item,
                      delete_pantry_item, get_all_pantry_locations,
                      add_pantry_location, update_pantry_location,
                      delete_pantry_location, consume_menu_from_pantry)
from gemini_service import (is_gemini_available, match_ingredients_to_ica_products,
                            generate_ica_shopping_summary)
from ica_service import (is_ica_available, search_ica_products, search_products_batch,
                         generate_ica_cart_links, get_ica_search_url)

app = Flask(__name__, static_folder='../static', template_folder='../templates')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Initialize database on startup
init_db()
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if uploaded file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Home page with all recipes."""
    return render_template('index.html')

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    """Recipe detail page."""
    return render_template('recipe.html', recipe_id=recipe_id)

@app.route('/menus')
def menus_page():
    """Menu planning page."""
    return render_template('menus.html')

@app.route('/recipe/<int:recipe_id>/edit')
def recipe_edit_page(recipe_id):
    """Recipe edit page."""
    return render_template('recipe_edit.html', recipe_id=recipe_id)

@app.route('/editor')
def recipe_editor_page():
    """Recipe editor page."""
    return render_template('recipe_editor.html')

@app.route('/recipe-delete')
def recipe_delete_page():
    """Recipe delete admin page."""
    return render_template('recipe_delete.html')

@app.route('/recipe-manage-edit')
def recipe_manage_edit_page():
    """Recipe edit admin list page."""
    return render_template('recipe_manage_edit.html')

@app.route('/skafferi')
def pantry_page():
    """Pantry inventory page."""
    return render_template('pantry.html')

@app.route('/menu/<int:menu_id>')
def menu_detail(menu_id):
    """Menu detail/edit page."""
    return render_template('menu_detail.html', menu_id=menu_id)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded recipe photos from persistent storage."""
    logger.debug(f'Serving upload: {filename}')
    logger.debug(f'Upload folder: {UPLOAD_FOLDER}')
    logger.debug(f'Files in upload folder: {os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else "Directory not found"}')
    return send_from_directory(UPLOAD_FOLDER, filename)

# API Routes
@app.route('/api/recipes')
def api_recipes():
    """Get all recipes or filter by category."""
    category = request.args.get('category')
    search = request.args.get('search')
    
    if search:
        recipes = search_recipes(search)
    elif category:
        recipes = get_recipes_by_category(category)
    else:
        recipes = get_all_recipes()
    
    return jsonify(recipes)

@app.route('/api/recipes/<int:recipe_id>')
def api_recipe(recipe_id):
    """Get a single recipe with ingredients."""
    recipe = get_recipe(recipe_id)
    if recipe:
        return jsonify(recipe)
    return jsonify({'error': 'Recipe not found'}), 404

@app.route('/api/recipes', methods=['POST'])
def api_add_recipe():
    """Add a new recipe."""
    data = request.json
    
    required = ['name', 'ingredients']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    recipe_id = add_recipe(
        name=data['name'],
        description=data.get('description', ''),
        category=data.get('category', 'Övrigt'),
        base_servings=data.get('base_servings', 4),
        cooking_time=data.get('cooking_time', ''),
        instructions=data.get('instructions', ''),
        image_url=data.get('image_url', ''),
        ingredients=data['ingredients']
    )
    
    return jsonify({'id': recipe_id, 'message': 'Recipe added successfully'}), 201


@app.route('/api/uploads', methods=['POST'])
def api_upload_image():
    """Upload a recipe image and return its URL."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    image = request.files['image']
    if not image or image.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(image.filename):
        return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400

    try:
        # Ensure upload directory exists with proper permissions
        os.makedirs(UPLOAD_FOLDER, mode=0o755, exist_ok=True)
        
        filename = secure_filename(image.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        save_path = os.path.join(UPLOAD_FOLDER, unique_name)

        # Save the image file
        image.save(save_path)
        
        # Verify file was saved
        if not os.path.exists(save_path):
            return jsonify({'error': 'Failed to save image file'}), 500
        
        return jsonify({'url': f'/uploads/{unique_name}'}), 201
    except Exception as e:
        app.logger.error(f'Error uploading image: {str(e)}')
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/recipes/<int:recipe_id>', methods=['PUT'])
def api_update_recipe(recipe_id):
    """Update an existing recipe."""
    data = request.json
    
    # Check if recipe exists
    existing_recipe = get_recipe(recipe_id)
    if not existing_recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    
    required = ['name', 'ingredients']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Use existing image_url if no new image provided
    image_url = data.get('image_url', existing_recipe['image_url'])
    
    update_recipe(
        recipe_id=recipe_id,
        name=data['name'],
        description=data.get('description', ''),
        category=data.get('category', 'Övrigt'),
        base_servings=data.get('base_servings', 4),
        cooking_time=data.get('cooking_time', ''),
        instructions=data.get('instructions', ''),
        image_url=image_url,
        ingredients=data['ingredients']
    )
    
    return jsonify({'id': recipe_id, 'message': 'Recipe updated successfully'}), 200

@app.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
def api_delete_recipe(recipe_id):
    """Delete an existing recipe."""
    existing_recipe = get_recipe(recipe_id)
    if not existing_recipe:
        return jsonify({'error': 'Recipe not found'}), 404

    delete_recipe(recipe_id)
    return jsonify({'message': 'Recipe deleted successfully'}), 200

@app.route('/api/categories')
def api_categories():
    """Get all categories."""
    categories = get_categories()
    return jsonify(categories)

@app.route('/api/pantry')
def api_pantry_items():
    """Get all pantry items."""
    pantry_location_id = request.args.get('pantry_location_id', type=int)
    return jsonify(get_all_pantry_items(pantry_location_id))

@app.route('/api/pantry-locations')
def api_pantry_locations():
    """Get all pantry locations."""
    return jsonify(get_all_pantry_locations())

@app.route('/api/pantry-locations', methods=['POST'])
def api_add_pantry_location():
    """Add a pantry location."""
    data = request.json
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    try:
        location_id = add_pantry_location(data['name'].strip())
    except Exception:
        return jsonify({'error': 'Kunde inte skapa skafferi. Namnet kanske redan finns.'}), 400

    return jsonify({'id': location_id, 'message': 'Pantry location added successfully'}), 201

@app.route('/api/pantry-locations/<int:location_id>', methods=['PUT'])
def api_update_pantry_location(location_id):
    """Rename a pantry location."""
    data = request.json
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    try:
        update_pantry_location(location_id, data['name'].strip())
    except Exception:
        return jsonify({'error': 'Kunde inte byta namn på skafferiet.'}), 400

    return jsonify({'message': 'Pantry location updated successfully'})

@app.route('/api/pantry-locations/<int:location_id>', methods=['DELETE'])
def api_delete_pantry_location(location_id):
    """Delete a pantry location."""
    try:
        delete_pantry_location(location_id)
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    return jsonify({'message': 'Pantry location deleted successfully'})

@app.route('/api/pantry', methods=['POST'])
def api_add_pantry_item():
    """Add a pantry item."""
    data = request.json

    required = ['pantry_location_id', 'name', 'amount', 'unit']
    if not data or not all(k in data for k in required):
        return jsonify({'error': 'pantry_location_id, name, amount and unit are required'}), 400

    try:
        pantry_location_id = int(data['pantry_location_id'])
        amount = float(data['amount'])
    except (TypeError, ValueError):
        return jsonify({'error': 'pantry_location_id and amount must be numbers'}), 400

    if amount < 0:
        return jsonify({'error': 'amount must be zero or greater'}), 400

    item_id = add_pantry_item(pantry_location_id, data['name'].strip(), amount, data['unit'].strip())
    return jsonify({'id': item_id, 'message': 'Pantry item added successfully'}), 201

@app.route('/api/pantry/<int:item_id>', methods=['PUT'])
def api_update_pantry(item_id):
    """Update a pantry item."""
    data = request.json

    required = ['name', 'amount', 'unit']
    if not data or not all(k in data for k in required):
        return jsonify({'error': 'name, amount and unit are required'}), 400

    try:
        amount = float(data['amount'])
    except (TypeError, ValueError):
        return jsonify({'error': 'amount must be a number'}), 400

    if amount < 0:
        return jsonify({'error': 'amount must be zero or greater'}), 400

    update_pantry_item(item_id, data['name'].strip(), amount, data['unit'].strip())
    return jsonify({'message': 'Pantry item updated successfully'})

@app.route('/api/pantry/<int:item_id>', methods=['DELETE'])
def api_delete_pantry(item_id):
    """Delete a pantry item."""
    delete_pantry_item(item_id)
    return jsonify({'message': 'Pantry item deleted successfully'})

@app.route('/api/calculate/<int:recipe_id>')
def api_calculate(recipe_id):
    """Calculate ingredients for specified number of servings."""
    servings = request.args.get('servings', type=int, default=4)
    recipe = get_recipe(recipe_id)
    
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    
    base = recipe['base_servings']
    multiplier = servings / base
    
    calculated_ingredients = []
    for ing in recipe['ingredients']:
        calculated_ingredients.append({
            'name': ing['name'],
            'amount': round(ing['amount'] * multiplier, 2),
            'unit': ing['unit']
        })
    
    return jsonify({
        'recipe_name': recipe['name'],
        'servings': servings,
        'base_servings': base,
        'ingredients': calculated_ingredients
    })

# Menu API Routes
@app.route('/api/menus')
def api_menus():
    """Get all menus."""
    menus = get_all_menus()
    return jsonify(menus)

@app.route('/api/menus', methods=['POST'])
def api_create_menu():
    """Create a new menu."""
    data = request.json
    
    if not data.get('name') or not data.get('num_days'):
        return jsonify({'error': 'Name and num_days are required'}), 400
    
    menu_id = create_menu(
        name=data['name'],
        num_days=data['num_days'],
        servings=data.get('servings', 10),
        start_date=data.get('start_date')
    )
    
    return jsonify({'id': menu_id, 'message': 'Menu created successfully'}), 201

@app.route('/api/menus/<int:menu_id>')
def api_menu(menu_id):
    """Get a single menu with all items."""
    menu = get_menu(menu_id)
    if menu:
        return jsonify(menu)
    return jsonify({'error': 'Menu not found'}), 404

@app.route('/api/menus/<int:menu_id>', methods=['DELETE'])
def api_delete_menu(menu_id):
    """Delete a menu."""
    delete_menu(menu_id)
    return jsonify({'message': 'Menu deleted successfully'})

@app.route('/api/menus/<int:menu_id>/items', methods=['PUT'])
def api_update_menu_item(menu_id):
    """Update a menu item (legacy - for backward compatibility)."""
    data = request.json
    
    required = ['day_number', 'meal_type']
    if not all(k in data for k in required):
        return jsonify({'error': 'day_number and meal_type are required'}), 400
    
    if data['meal_type'] not in MEAL_TYPES:
        return jsonify({'error': f'Invalid meal_type. Must be one of: {MEAL_TYPES}'}), 400
    
    update_menu_item(
        menu_id=menu_id,
        day_number=data['day_number'],
        meal_type=data['meal_type'],
        recipe_id=data.get('recipe_id')
    )
    
    return jsonify({'message': 'Menu item updated successfully'})


@app.route('/api/menus/<int:menu_id>/recipes', methods=['POST'])
def api_add_menu_recipe(menu_id):
    """Add a recipe to a menu meal slot (supports multiple recipes per meal with individual servings)."""
    data = request.json
    
    required = ['day_number', 'meal_type', 'recipe_id']
    if not all(k in data for k in required):
        return jsonify({'error': 'day_number, meal_type, and recipe_id are required'}), 400
    
    if data['meal_type'] not in MEAL_TYPES:
        return jsonify({'error': f'Invalid meal_type. Must be one of: {MEAL_TYPES}'}), 400
    
    # Optional servings parameter for this specific recipe
    servings = data.get('servings')
    if servings is not None:
        try:
            servings = int(servings)
            if servings < 1:
                return jsonify({'error': 'servings must be at least 1'}), 400
        except (TypeError, ValueError):
            return jsonify({'error': 'servings must be a number'}), 400
    
    add_menu_recipe(
        menu_id=menu_id,
        day_number=data['day_number'],
        meal_type=data['meal_type'],
        recipe_id=data['recipe_id'],
        servings=servings
    )
    
    return jsonify({'message': 'Recipe added to menu successfully'}), 201


@app.route('/api/menus/<int:menu_id>/recipes/<int:menu_item_id>', methods=['DELETE'])
def api_remove_menu_recipe(menu_id, menu_item_id):
    """Remove a specific recipe from a menu meal slot."""
    data = request.json or {}
    
    required = ['day_number', 'meal_type']
    if not all(k in data for k in required):
        return jsonify({'error': 'day_number and meal_type are required'}), 400
    
    if data['meal_type'] not in MEAL_TYPES:
        return jsonify({'error': f'Invalid meal_type. Must be one of: {MEAL_TYPES}'}), 400
    
    remove_menu_recipe(
        menu_id=menu_id,
        day_number=data['day_number'],
        meal_type=data['meal_type'],
        menu_item_id=menu_item_id
    )
    
    return jsonify({'message': 'Recipe removed from menu successfully'})


@app.route('/api/menus/<int:menu_id>/recipes/<int:menu_item_id>/servings', methods=['PUT'])
def api_update_recipe_servings(menu_id, menu_item_id):
    """Update servings for a specific recipe in a meal slot."""
    data = request.json or {}
    
    servings = data.get('servings')
    if servings in ('', None):
        servings = None
    else:
        try:
            servings = int(servings)
        except (TypeError, ValueError):
            return jsonify({'error': 'servings must be a number'}), 400
        
        if servings < 1:
            return jsonify({'error': 'servings must be at least 1'}), 400
    
    update_recipe_servings(
        menu_item_id=menu_item_id,
        servings=servings
    )
    
    return jsonify({'message': 'Recipe servings updated successfully'})

@app.route('/api/menus/<int:menu_id>/meal-servings', methods=['PUT'])
def api_update_menu_meal_servings(menu_id):
    """Update meal-level servings override for a menu."""
    data = request.json or {}

    required = ['day_number', 'meal_type']
    if not all(k in data for k in required):
        return jsonify({'error': 'day_number and meal_type are required'}), 400

    try:
        day_number = int(data['day_number'])
    except (TypeError, ValueError):
        return jsonify({'error': 'day_number must be a number'}), 400

    meal_type = data.get('meal_type')
    if meal_type not in MEAL_TYPES:
        return jsonify({'error': f'Invalid meal_type. Must be one of: {MEAL_TYPES}'}), 400

    servings_override = data.get('servings_override')
    if servings_override in ('', None):
        servings_override = None
    else:
        try:
            servings_override = int(servings_override)
        except (TypeError, ValueError):
            return jsonify({'error': 'servings_override must be a number'}), 400

        if servings_override < 1:
            return jsonify({'error': 'servings_override must be at least 1'}), 400

    update_menu_meal_servings(
        menu_id=menu_id,
        day_number=day_number,
        meal_type=meal_type,
        servings_override=servings_override
    )
    return jsonify({'message': 'Meal servings override updated successfully'})

@app.route('/api/menus/<int:menu_id>/shopping-list')
def api_shopping_list(menu_id):
    """Get shopping list for a menu."""
    servings = request.args.get('servings', type=int)
    pantry_location_id = request.args.get('pantry_location_id', type=int)
    result = get_menu_shopping_list(menu_id, servings, pantry_location_id)
    
    if result:
        return jsonify(result)
    return jsonify({'error': 'Menu not found'}), 404

@app.route('/api/menus/<int:menu_id>/consume-pantry', methods=['POST'])
def api_consume_pantry(menu_id):
    """Deduct covered ingredients from a selected pantry location."""
    data = request.json or {}
    pantry_location_id = data.get('pantry_location_id')
    servings = data.get('servings')

    if pantry_location_id is None:
        return jsonify({'error': 'pantry_location_id is required'}), 400

    try:
        pantry_location_id = int(pantry_location_id)
        servings = int(servings) if servings is not None else None
    except (TypeError, ValueError):
        return jsonify({'error': 'pantry_location_id and servings must be numbers'}), 400

    result = consume_menu_from_pantry(menu_id, pantry_location_id, servings)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Menu not found'}), 404

@app.route('/api/meal-types')
def api_meal_types():
    """Get available meal types."""
    return jsonify(MEAL_TYPES)


# ===== ICA Integration API Routes =====

@app.route('/api/ica/status')
def api_ica_status():
    """Check if ICA and Gemini integrations are available."""
    return jsonify({
        'gemini_available': is_gemini_available(),
        'ica_available': is_ica_available(),
    })


@app.route('/api/ica/search')
def api_ica_search():
    """Search for a product on ICA."""
    search_term = request.args.get('q', '')
    limit = request.args.get('limit', 5, type=int)
    
    if not search_term:
        return jsonify({'error': 'Search term required'}), 400
    
    if not is_ica_available():
        return jsonify({'error': 'ICA integration not available'}), 503
    
    products = search_ica_products(search_term, limit)
    return jsonify({
        'search_term': search_term,
        'products': products,
        'search_url': get_ica_search_url(search_term),
    })


@app.route('/api/menus/<int:menu_id>/ica-shopping-list')
def api_ica_shopping_list(menu_id):
    """Get AI-enhanced shopping list with ICA product suggestions."""
    servings = request.args.get('servings', type=int)
    pantry_location_id = request.args.get('pantry_location_id', type=int)
    
    # First get the regular shopping list
    shopping_list = get_menu_shopping_list(menu_id, servings, pantry_location_id)
    
    if not shopping_list:
        return jsonify({'error': 'Menu not found'}), 404
    
    ingredients = shopping_list.get('ingredients', [])
    
    if not ingredients:
        return jsonify({
            **shopping_list,
            'ica_products': [],
            'ica_summary': None,
            'ica_cart_links': None,
        })
    
    # Use Gemini to match ingredients to ICA products if available
    ai_matched = None
    ica_summary = None
    
    if is_gemini_available():
        try:
            ai_matched = match_ingredients_to_ica_products(ingredients)
            if ai_matched:
                ica_summary = generate_ica_shopping_summary(ingredients, ai_matched)
        except Exception as e:
            logger.error(f"Gemini matching error: {e}")
    
    # Generate cart links
    ica_cart_links = None
    if ai_matched:
        ica_cart_links = generate_ica_cart_links(ai_matched)
    else:
        # Fallback: generate links based on original ingredient names
        simple_products = [{'original_name': ing['name'], 'amount': ing['amount'], 'unit': ing['unit']}
                          for ing in ingredients]
        ica_cart_links = generate_ica_cart_links(simple_products)
    
    # Search ICA for products (if ICA scraping available)
    ica_products = []
    if is_ica_available() and ai_matched:
        # Use AI-suggested search terms
        ica_products = search_products_batch(ai_matched[:10])  # Limit to avoid too many requests
    elif is_ica_available():
        # Use original ingredient names
        simple_ingredients = [{'name': ing['name'], 'amount': ing['amount'], 'unit': ing['unit']}
                             for ing in ingredients[:10]]
        ica_products = search_products_batch(simple_ingredients)
    
    return jsonify({
        **shopping_list,
        'ai_matched_products': ai_matched,
        'ica_products': ica_products,
        'ica_summary': ica_summary,
        'ica_cart_links': ica_cart_links,
        'gemini_available': is_gemini_available(),
        'ica_available': is_ica_available(),
    })


# ===== AI Smart Shopping List API Routes =====

@app.route('/api/ai/status')
def api_ai_status():
    """Check if AI (Gemini) integration is available."""
    return jsonify({
        'gemini_available': is_gemini_available(),
    })


@app.route('/api/menus/<int:menu_id>/smart-shopping-list')
def api_smart_shopping_list(menu_id):
    """Get AI-enhanced smart shopping list."""
    servings = request.args.get('servings', type=int)
    pantry_location_id = request.args.get('pantry_location_id', type=int)
    
    # First get the regular shopping list
    shopping_list = get_menu_shopping_list(menu_id, servings, pantry_location_id)
    
    if not shopping_list:
        return jsonify({'error': 'Menu not found'}), 404
    
    ingredients = shopping_list.get('ingredients', [])
    
    if not ingredients:
        return jsonify({
            **shopping_list,
            'ai_products': [],
            'ai_summary': None,
        })
    
    # Use Gemini to enhance the shopping list
    ai_products = None
    ai_summary = None
    
    if is_gemini_available():
        try:
            ai_products = match_ingredients_to_ica_products(ingredients)
            if ai_products:
                ai_summary = generate_ica_shopping_summary(ingredients, ai_products)
        except Exception as e:
            logger.error(f"Gemini error: {e}")
    
    return jsonify({
        **shopping_list,
        'ai_products': ai_products,
        'ai_summary': ai_summary,
        'gemini_available': is_gemini_available(),
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
