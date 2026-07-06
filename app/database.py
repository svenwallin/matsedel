import sqlite3
import os
import math

DATABASE_PATH = os.getenv(
    'DATABASE_PATH',
    os.path.join(os.path.dirname(__file__), '..', 'data', 'recipes.db')
)

UNIT_CONVERSIONS = {
    'g': ('weight', 1),
    'kg': ('weight', 1000),
    'ml': ('volume', 1),
    'cl': ('volume', 10),
    'dl': ('volume', 100),
    'l': ('volume', 1000),
    'krm': ('spoon', 1),
    'tsk': ('spoon', 5),
    'msk': ('spoon', 15),
}


def normalize_unit_amount(amount, unit):
    """Convert a supported unit to its family base unit."""
    unit_info = UNIT_CONVERSIONS.get(unit)
    if not unit_info:
        return (None, None)

    family, factor = unit_info
    return (family, amount * factor)


def convert_from_base_unit(amount, unit):
    """Convert a base-unit amount back to the requested unit."""
    unit_info = UNIT_CONVERSIONS.get(unit)
    if not unit_info:
        return amount

    _, factor = unit_info
    return amount / factor

def get_db():
    """Get database connection."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(cursor, table_name, column_name, column_definition):
    """Add a column to a table when it does not already exist."""
    cursor.execute(f'PRAGMA table_info({table_name})')
    existing_columns = {row['name'] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_definition}')

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
            day_servings INTEGER,
            recipe_id INTEGER,
            FOREIGN KEY (menu_id) REFERENCES menus(id) ON DELETE CASCADE,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
        )
    ''')

    _ensure_column(cursor, 'menu_items', 'day_servings', 'day_servings INTEGER')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pantry_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pantry_location_id INTEGER,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            unit TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pantry_location_id) REFERENCES pantry_locations(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pantry_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    _ensure_column(cursor, 'pantry_items', 'pantry_location_id', 'pantry_location_id INTEGER')

    cursor.execute('SELECT id FROM pantry_locations WHERE LOWER(name) = LOWER(?)', ('Hemma',))
    default_location = cursor.fetchone()
    if default_location:
        default_location_id = default_location['id']
    else:
        cursor.execute('INSERT INTO pantry_locations (name) VALUES (?)', ('Hemma',))
        default_location_id = cursor.lastrowid

    cursor.execute(
        '''
        UPDATE pantry_items
        SET pantry_location_id = ?
        WHERE pantry_location_id IS NULL
        ''',
        (default_location_id,)
    )
    
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

def update_recipe(recipe_id, name, description, category, base_servings, cooking_time, instructions, image_url, ingredients):
    """Update an existing recipe with ingredients."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE recipes 
        SET name = ?, description = ?, category = ?, base_servings = ?, cooking_time = ?, instructions = ?, image_url = ?
        WHERE id = ?
    ''', (name, description, category, base_servings, cooking_time, instructions, image_url, recipe_id))

    # Delete old ingredients
    cursor.execute('DELETE FROM ingredients WHERE recipe_id = ?', (recipe_id,))

    # Add new ingredients
    for ingredient in ingredients:
        cursor.execute('''
            INSERT INTO ingredients (recipe_id, name, amount, unit)
            VALUES (?, ?, ?, ?)
        ''', (recipe_id, ingredient['name'], ingredient['amount'], ingredient['unit']))

    conn.commit()
    conn.close()
    return recipe_id

def delete_recipe(recipe_id):
    """Delete a recipe and detach it from menu items."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('UPDATE menu_items SET recipe_id = NULL WHERE recipe_id = ?', (recipe_id,))
    cursor.execute('DELETE FROM ingredients WHERE recipe_id = ?', (recipe_id,))
    cursor.execute('DELETE FROM recipes WHERE id = ?', (recipe_id,))

    conn.commit()
    conn.close()

def get_all_pantry_locations():
    """Get all pantry locations."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pantry_locations ORDER BY name COLLATE NOCASE')
    items = cursor.fetchall()
    conn.close()
    return [dict(row) for row in items]


def add_pantry_location(name):
    """Add a pantry location."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO pantry_locations (name) VALUES (?)', (name,))
    location_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return location_id


def update_pantry_location(location_id, name):
    """Rename a pantry location."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE pantry_locations SET name = ? WHERE id = ?',
        (name, location_id)
    )
    conn.commit()
    conn.close()


def delete_pantry_location(location_id):
    """Delete a pantry location and its pantry items."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) AS count FROM pantry_locations')
    location_count = cursor.fetchone()['count']
    if location_count <= 1:
        conn.close()
        raise ValueError('At least one pantry location must remain')

    cursor.execute('DELETE FROM pantry_items WHERE pantry_location_id = ?', (location_id,))
    cursor.execute('DELETE FROM pantry_locations WHERE id = ?', (location_id,))

    conn.commit()
    conn.close()


def get_all_pantry_items(pantry_location_id=None):
    """Get all pantry items."""
    conn = get_db()
    cursor = conn.cursor()
    if pantry_location_id is None:
        cursor.execute(
            '''
            SELECT pi.*, pl.name AS pantry_location_name
            FROM pantry_items pi
            JOIN pantry_locations pl ON pl.id = pi.pantry_location_id
            ORDER BY pl.name COLLATE NOCASE, pi.name COLLATE NOCASE
            '''
        )
    else:
        cursor.execute(
            '''
            SELECT pi.*, pl.name AS pantry_location_name
            FROM pantry_items pi
            JOIN pantry_locations pl ON pl.id = pi.pantry_location_id
            WHERE pi.pantry_location_id = ?
            ORDER BY pi.name COLLATE NOCASE
            ''',
            (pantry_location_id,)
        )
    items = cursor.fetchall()
    conn.close()
    return [dict(row) for row in items]

def add_pantry_item(pantry_location_id, name, amount, unit):
    """Add a pantry item or increase the amount of an existing item."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT id, amount
        FROM pantry_items
        WHERE pantry_location_id = ? AND LOWER(name) = LOWER(?) AND unit = ?
        ''',
        (pantry_location_id, name, unit)
    )
    existing_item = cursor.fetchone()

    if existing_item:
        new_amount = existing_item['amount'] + amount
        cursor.execute(
            '''
            UPDATE pantry_items
            SET amount = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''',
            (new_amount, existing_item['id'])
        )
        pantry_item_id = existing_item['id']
    else:
        cursor.execute(
            '''
            INSERT INTO pantry_items (pantry_location_id, name, amount, unit)
            VALUES (?, ?, ?, ?)
            ''',
            (pantry_location_id, name, amount, unit)
        )
        pantry_item_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return pantry_item_id

def update_pantry_item(item_id, name, amount, unit):
    """Update a pantry item."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''
        UPDATE pantry_items
        SET name = ?, amount = ?, unit = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        ''',
        (name, amount, unit, item_id)
    )
    conn.commit()
    conn.close()

def delete_pantry_item(item_id):
    """Delete a pantry item."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM pantry_items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()


def _build_pantry_lookup(pantry_items):
    pantry_lookup = {}
    for item in pantry_items:
        item = dict(item)
        family, normalized_amount = normalize_unit_amount(item['amount'], item['unit'])
        if family:
            pantry_key = (item['name'].lower(), family)
            pantry_lookup[pantry_key] = pantry_lookup.get(pantry_key, 0) + normalized_amount
        else:
            pantry_key = (item['name'].lower(), item['unit'])
            pantry_lookup[pantry_key] = pantry_lookup.get(pantry_key, 0) + item['amount']
    return pantry_lookup


def _get_menu_required_ingredients(menu_id, target_servings):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT mi.recipe_id, mi.day_number, mi.day_servings, r.base_servings, i.name, i.amount, i.unit
        FROM menu_items mi
        JOIN recipes r ON mi.recipe_id = r.id
        JOIN ingredients i ON r.id = i.recipe_id
        WHERE mi.menu_id = ? AND mi.recipe_id IS NOT NULL
        ''',
        (menu_id,)
    )
    items = cursor.fetchall()
    conn.close()

    shopping_list = {}
    for item in items:
        item = dict(item)
        effective_servings = item['day_servings'] if item['day_servings'] is not None else target_servings
        multiplier = effective_servings / item['base_servings']
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

    return shopping_list


def _calculate_menu_pantry_coverage(shopping_list, pantry_items):
    pantry_lookup = _build_pantry_lookup(pantry_items)

    result = []
    pantry_coverage = []
    for ingredient in shopping_list.values():
        family, normalized_required_amount = normalize_unit_amount(ingredient['amount'], ingredient['unit'])

        if family:
            pantry_key = (ingredient['name'].lower(), family)
            pantry_amount = pantry_lookup.get(pantry_key, 0)
            missing_amount = max(normalized_required_amount - pantry_amount, 0)
            covered_amount = min(normalized_required_amount, pantry_amount)
            missing_amount = convert_from_base_unit(missing_amount, ingredient['unit'])
            covered_amount = convert_from_base_unit(covered_amount, ingredient['unit'])
        else:
            pantry_key = (ingredient['name'].lower(), ingredient['unit'])
            pantry_amount = pantry_lookup.get(pantry_key, 0)
            missing_amount = max(ingredient['amount'] - pantry_amount, 0)
            covered_amount = min(ingredient['amount'], pantry_amount)

        if covered_amount > 0:
            pantry_coverage.append({
                'name': ingredient['name'],
                'amount': covered_amount,
                'unit': ingredient['unit']
            })

        if missing_amount > 0:
            result.append({
                'name': ingredient['name'],
                'amount': missing_amount,
                'unit': ingredient['unit'],
                'required_amount': ingredient['amount'],
                'pantry_amount': covered_amount
            })

    result.sort(key=lambda x: x['name'].lower())
    pantry_coverage.sort(key=lambda x: x['name'].lower())

    return {
        'ingredients': result,
        'pantry_coverage': pantry_coverage,
        'all_covered': len(shopping_list) > 0 and len(result) == 0
    }


def consume_menu_from_pantry(menu_id, pantry_location_id, servings=None):
    """Consume pantry stock used to cover a menu shopping list."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM menus WHERE id = ?', (menu_id,))
    menu = cursor.fetchone()
    if not menu:
        conn.close()
        return None

    menu = dict(menu)
    target_servings = servings or menu['servings']
    conn.close()

    shopping_list = _get_menu_required_ingredients(menu_id, target_servings)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT *
        FROM pantry_items
        WHERE pantry_location_id = ?
        ORDER BY name COLLATE NOCASE, id
        ''',
        (pantry_location_id,)
    )
    pantry_items = [dict(row) for row in cursor.fetchall()]

    consumed_items = []
    for ingredient in shopping_list.values():
        family, normalized_required_amount = normalize_unit_amount(ingredient['amount'], ingredient['unit'])
        matching_items = []
        available_total = 0

        for pantry_item in pantry_items:
            if pantry_item['name'].lower() != ingredient['name'].lower():
                continue

            if family:
                pantry_family, normalized_amount = normalize_unit_amount(pantry_item['amount'], pantry_item['unit'])
                if pantry_family != family:
                    continue
                matching_items.append((pantry_item, normalized_amount))
                available_total += normalized_amount
            elif pantry_item['unit'] == ingredient['unit']:
                matching_items.append((pantry_item, pantry_item['amount']))
                available_total += pantry_item['amount']

        amount_to_consume = min(normalized_required_amount, available_total) if family else min(ingredient['amount'], available_total)

        for pantry_item, available_amount in matching_items:
            if amount_to_consume <= 0:
                break

            used_amount = min(amount_to_consume, available_amount)
            reduction = convert_from_base_unit(used_amount, pantry_item['unit']) if family else used_amount
            new_amount = max(pantry_item['amount'] - reduction, 0)

            if new_amount <= 0.00001:
                cursor.execute('DELETE FROM pantry_items WHERE id = ?', (pantry_item['id'],))
            else:
                cursor.execute(
                    '''
                    UPDATE pantry_items
                    SET amount = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    ''',
                    (new_amount, pantry_item['id'])
                )

            pantry_item['amount'] = new_amount
            amount_to_consume -= used_amount

            consumed_items.append({
                'name': ingredient['name'],
                'amount': convert_from_base_unit(used_amount, ingredient['unit']) if family else used_amount,
                'unit': ingredient['unit']
            })

    conn.commit()
    conn.close()

    return {
        'menu_name': menu['name'],
        'servings': target_servings,
        'consumed_items': consumed_items
    }

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
    """Get a menu with all its items (supporting multiple recipes per meal)."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM menus WHERE id = ?', (menu_id,))
    menu = cursor.fetchone()
    
    if not menu:
        conn.close()
        return None
    
    menu = dict(menu)
    menu['day_servings'] = {}
    
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
            END,
            mi.id
    ''', (menu_id,))
    
    items = cursor.fetchall()
    
    # Organize items by day - now supporting multiple recipes per meal
    menu['days'] = {}
    for item in items:
        item = dict(item)
        day = item['day_number']
        meal_type = item['meal_type']
        
        if day not in menu['days']:
            menu['days'][day] = {}
        if day not in menu['day_servings']:
            menu['day_servings'][day] = item.get('day_servings')
        
        # Initialize meal slot as array if not exists
        if meal_type not in menu['days'][day]:
            menu['days'][day][meal_type] = {
                'recipes': [],
                'day_servings': item.get('day_servings')
            }
        
        # Only add if there's an actual recipe (skip NULL placeholder items)
        if item.get('recipe_id') is not None:
            menu['days'][day][meal_type]['recipes'].append({
                'id': item['id'],
                'recipe_id': item['recipe_id'],
                'recipe_name': item['recipe_name'],
                'category': item['category'],
                'cooking_time': item['cooking_time'],
                'base_servings': item['base_servings'],
                'servings': item['day_servings']
            })
    
    conn.close()
    return menu

def update_menu_item(menu_id, day_number, meal_type, recipe_id):
    """Update a specific meal in a menu (legacy - replaces first item)."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE menu_items 
        SET recipe_id = ?
        WHERE menu_id = ? AND day_number = ? AND meal_type = ?
    ''', (recipe_id, menu_id, day_number, meal_type))
    
    conn.commit()
    conn.close()


def add_menu_recipe(menu_id, day_number, meal_type, recipe_id, servings=None):
    """Add a recipe to a specific meal slot (supports multiple recipes with individual servings)."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if there's an empty placeholder (recipe_id IS NULL)
    cursor.execute('''
        SELECT id FROM menu_items
        WHERE menu_id = ? AND day_number = ? AND meal_type = ? AND recipe_id IS NULL
        LIMIT 1
    ''', (menu_id, day_number, meal_type))
    placeholder = cursor.fetchone()
    
    if placeholder:
        # Update the placeholder with the new recipe and servings
        cursor.execute('''
            UPDATE menu_items SET recipe_id = ?, day_servings = ? WHERE id = ?
        ''', (recipe_id, servings, placeholder['id']))
    else:
        # Insert a new menu item for this meal slot with its own servings
        cursor.execute('''
            INSERT INTO menu_items (menu_id, day_number, meal_type, recipe_id, day_servings)
            VALUES (?, ?, ?, ?, ?)
        ''', (menu_id, day_number, meal_type, recipe_id, servings))
    
    conn.commit()
    conn.close()


def remove_menu_recipe(menu_id, day_number, meal_type, menu_item_id):
    """Remove a specific recipe from a meal slot."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Delete the specific menu item
    cursor.execute('''
        DELETE FROM menu_items
        WHERE id = ? AND menu_id = ? AND day_number = ? AND meal_type = ?
    ''', (menu_item_id, menu_id, day_number, meal_type))
    
    # Check if any items remain for this meal slot
    cursor.execute('''
        SELECT COUNT(*) as count FROM menu_items
        WHERE menu_id = ? AND day_number = ? AND meal_type = ?
    ''', (menu_id, day_number, meal_type))
    remaining = cursor.fetchone()['count']
    
    # If no items remain, create an empty placeholder
    if remaining == 0:
        cursor.execute('''
            INSERT INTO menu_items (menu_id, day_number, meal_type, recipe_id)
            VALUES (?, ?, ?, NULL)
        ''', (menu_id, day_number, meal_type))
    
    conn.commit()
    conn.close()

def update_menu_meal_servings(menu_id, day_number, meal_type, servings_override):
    """Update servings override for a specific meal in a menu."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE menu_items
        SET day_servings = ?
        WHERE menu_id = ? AND day_number = ? AND meal_type = ?
        ''',
        (servings_override, menu_id, day_number, meal_type)
    )

    conn.commit()
    conn.close()


def update_recipe_servings(menu_item_id, servings):
    """Update servings for a specific recipe in a meal slot."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE menu_items
        SET day_servings = ?
        WHERE id = ?
        ''',
        (servings, menu_item_id)
    )

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

def get_menu_shopping_list(menu_id, servings=None, pantry_location_id=None):
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
    
    conn.close()
    shopping_list = _get_menu_required_ingredients(menu_id, target_servings)
    pantry_items = get_all_pantry_items(pantry_location_id) if pantry_location_id else []
    coverage_data = _calculate_menu_pantry_coverage(shopping_list, pantry_items)

    # Convert marshmallows from pieces to bags (40 pieces per bag) for shopping output.
    for ingredient in coverage_data['ingredients']:
        if ingredient['name'].lower() == 'marshmallows' and ingredient['unit'] == 'st':
            ingredient['amount'] = math.ceil(ingredient['amount'] / 40)
            ingredient['unit'] = 'påse'
            if 'required_amount' in ingredient:
                ingredient['required_amount'] = math.ceil(ingredient['required_amount'] / 40)
            if 'pantry_amount' in ingredient:
                ingredient['pantry_amount'] = round(ingredient['pantry_amount'] / 40, 2)

    for ingredient in coverage_data['pantry_coverage']:
        if ingredient['name'].lower() == 'marshmallows' and ingredient['unit'] == 'st':
            ingredient['amount'] = round(ingredient['amount'] / 40, 2)
            ingredient['unit'] = 'påse'
    
    return {
        'menu_name': menu['name'],
        'servings': target_servings,
        'ingredients': coverage_data['ingredients'],
        'pantry_coverage': coverage_data['pantry_coverage'],
        'all_covered': coverage_data['all_covered']
    }
