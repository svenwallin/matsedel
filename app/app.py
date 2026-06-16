import os
import uuid
import logging
from flask import Flask, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from database import (init_db, get_all_recipes, get_recipe, add_recipe, update_recipe,
                      delete_recipe,
                      get_recipes_by_category, get_categories, search_recipes,
                      create_menu, get_all_menus, get_menu, update_menu_item,
                      delete_menu, get_menu_shopping_list, MEAL_TYPES,
                      get_all_pantry_items, add_pantry_item, update_pantry_item,
                      delete_pantry_item, get_all_pantry_locations,
                      add_pantry_location, update_pantry_location,
                      delete_pantry_location, consume_menu_from_pantry)

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
    """Update a menu item."""
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
