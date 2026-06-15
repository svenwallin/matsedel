import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'recipes.db')

def get_db():
    """Get database connection."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with schema."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create recipes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            base_servings INTEGER DEFAULT 4,
            cooking_time TEXT,
            instructions TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create ingredients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            unit TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    ''')
    
    # Create menus table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_date TEXT,
            num_days INTEGER NOT NULL,
            servings INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create menu_items table (links menus to recipes for specific days/meals)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_id INTEGER NOT NULL,
            day_number INTEGER NOT NULL,
            meal_type TEXT NOT NULL,
            recipe_id INTEGER,
            FOREIGN KEY (menu_id) REFERENCES menus(id) ON DELETE CASCADE,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def get_all_recipes():
    """Get all recipes."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM recipes ORDER BY name')
    recipes = cursor.fetchall()
    conn.close()
    return [dict(row) for row in recipes]

def get_recipe(recipe_id):
    """Get a single recipe with ingredients."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM recipes WHERE id = ?', (recipe_id,))
    recipe = cursor.fetchone()
    
    if recipe:
        recipe = dict(recipe)
        cursor.execute('SELECT * FROM ingredients WHERE recipe_id = ?', (recipe_id,))
        recipe['ingredients'] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return recipe

def add_recipe(name, description, category, base_servings, cooking_time, instructions, image_url, ingredients):
    """Add a new recipe with ingredients."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO recipes (name, description, category, base_servings, cooking_time, instructions, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, category, base_servings, cooking_time, instructions, image_url))
    
    recipe_id = cursor.lastrowid
    
    for ingredient in ingredients:
        cursor.execute('''
            INSERT INTO ingredients (recipe_id, name, amount, unit)
            VALUES (?, ?, ?, ?)
        ''', (recipe_id, ingredient['name'], ingredient['amount'], ingredient['unit']))
    
    conn.commit()
    conn.close()
    return recipe_id

def get_recipes_by_category(category):
    """Get recipes by category."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM recipes WHERE category = ? ORDER BY name', (category,))
    recipes = cursor.fetchall()
    conn.close()
    return [dict(row) for row in recipes]

def get_categories():
    """Get all unique categories."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM recipes WHERE category IS NOT NULL ORDER BY category')
    categories = cursor.fetchall()
    conn.close()
    return [row['category'] for row in categories]

def search_recipes(query):
    """Search recipes by name or description."""
    conn = get_db()
    cursor = conn.cursor()
    search_term = f'%{query}%'
    cursor.execute('''
        SELECT * FROM recipes 
        WHERE name LIKE ? OR description LIKE ?
        ORDER BY name
    ''', (search_term, search_term))
    recipes = cursor.fetchall()
    conn.close()
    return [dict(row) for row in recipes]

# Menu planning functions
MEAL_TYPES = ['breakfast', 'lunch', 'dinner', 'evening_fika']

def create_menu(name, num_days, servings=10, start_date=None):
    """Create a new menu plan."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO menus (name, num_days, servings, start_date)
        VALUES (?, ?, ?, ?)
    ''', (name, num_days, servings, start_date))
    
    menu_id = cursor.lastrowid
    
    # Create empty menu items for each day and meal type
    for day in range(1, num_days + 1):
        for meal_type in MEAL_TYPES:
            cursor.execute('''
                INSERT INTO menu_items (menu_id, day_number, meal_type, recipe_id)
                VALUES (?, ?, ?, NULL)
            ''', (menu_id, day, meal_type))
    
    conn.commit()
    conn.close()
    return menu_id

def get_all_menus():
    """Get all menus."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM menus ORDER BY created_at DESC')
    menus = cursor.fetchall()
    conn.close()
    return [dict(row) for row in menus]

def get_menu(menu_id):
    """Get a menu with all its items."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM menus WHERE id = ?', (menu_id,))
    menu = cursor.fetchone()
    
    if not menu:
        conn.close()
        return None
    
    menu = dict(menu)
    
    # Get all menu items with recipe details
    cursor.execute('''
        SELECT mi.*, r.name as recipe_name, r.category, r.cooking_time, r.base_servings
        FROM menu_items mi
        LEFT JOIN recipes r ON mi.recipe_id = r.id
        WHERE mi.menu_id = ?
        ORDER BY mi.day_number, 
            CASE mi.meal_type 
                WHEN 'breakfast' THEN 1 
                WHEN 'lunch' THEN 2 
                WHEN 'dinner' THEN 3 
                WHEN 'evening_fika' THEN 4 
            END
    ''', (menu_id,))
    
    items = cursor.fetchall()
    
    # Organize items by day
    menu['days'] = {}
    for item in items:
        item = dict(item)
        day = item['day_number']
        if day not in menu['days']:
            menu['days'][day] = {}
        menu['days'][day][item['meal_type']] = item
    
    conn.close()
    return menu

def update_menu_item(menu_id, day_number, meal_type, recipe_id):
    """Update a specific meal in a menu."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE menu_items 
        SET recipe_id = ?
        WHERE menu_id = ? AND day_number = ? AND meal_type = ?
    ''', (recipe_id, menu_id, day_number, meal_type))
    
    conn.commit()
    conn.close()

def delete_menu(menu_id):
    """Delete a menu and all its items."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM menu_items WHERE menu_id = ?', (menu_id,))
    cursor.execute('DELETE FROM menus WHERE id = ?', (menu_id,))
    conn.commit()
    conn.close()

def get_menu_shopping_list(menu_id, servings=None):
    """Get aggregated shopping list for a menu."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get menu details
    cursor.execute('SELECT * FROM menus WHERE id = ?', (menu_id,))
    menu = cursor.fetchone()
    if not menu:
        conn.close()
        return None
    
    menu = dict(menu)
    target_servings = servings or menu['servings']
    
    # Get all recipes in the menu with their ingredients
    cursor.execute('''
        SELECT mi.recipe_id, r.base_servings, i.name, i.amount, i.unit
        FROM menu_items mi
        JOIN recipes r ON mi.recipe_id = r.id
        JOIN ingredients i ON r.id = i.recipe_id
        WHERE mi.menu_id = ? AND mi.recipe_id IS NOT NULL
    ''', (menu_id,))
    
    items = cursor.fetchall()
    conn.close()
    
    # Aggregate ingredients
    shopping_list = {}
    for item in items:
        item = dict(item)
        multiplier = target_servings / item['base_servings']
        amount = item['amount'] * multiplier
        key = (item['name'].lower(), item['unit'])
        
        if key in shopping_list:
            shopping_list[key]['amount'] += amount
        else:
            shopping_list[key] = {
                'name': item['name'],
                'amount': amount,
                'unit': item['unit']
            }
    
    # Convert to list and sort
    result = list(shopping_list.values())
    result.sort(key=lambda x: x['name'].lower())
    
    return {
        'menu_name': menu['name'],
        'servings': target_servings,
        'ingredients': result
    }
