from flask import Flask, render_template, jsonify, request
from database import (init_db, get_all_recipes, get_recipe, add_recipe, 
                      get_recipes_by_category, get_categories, search_recipes,
                      create_menu, get_all_menus, get_menu, update_menu_item, 
                      delete_menu, get_menu_shopping_list, MEAL_TYPES)

app = Flask(__name__, static_folder='../static', template_folder='../templates')

# Initialize database on startup
init_db()

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

@app.route('/menu/<int:menu_id>')
def menu_detail(menu_id):
    """Menu detail/edit page."""
    return render_template('menu_detail.html', menu_id=menu_id)

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

@app.route('/api/categories')
def api_categories():
    """Get all categories."""
    categories = get_categories()
    return jsonify(categories)

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
    result = get_menu_shopping_list(menu_id, servings)
    
    if result:
        return jsonify(result)
    return jsonify({'error': 'Menu not found'}), 404

@app.route('/api/meal-types')
def api_meal_types():
    """Get available meal types."""
    return jsonify(MEAL_TYPES)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
