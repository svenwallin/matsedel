// Menu detail page
const MEAL_LABELS = {
    'breakfast': '🌅 Frukost',
    'lunch': '☀️ Lunch',
    'dinner': '🌙 Middag',
    'evening_fika': '🍪 Kvällsfika'
};

let currentMenu = null;
let allRecipes = [];
let currentSelection = { day: null, meal: null };

// Load menu on page load
document.addEventListener('DOMContentLoaded', () => {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    
    loadMenu(menuId);
    loadAllRecipes();
});

// Load menu data
async function loadMenu(menuId) {
    try {
        const response = await fetch(`/api/menus/${menuId}`);
        
        if (!response.ok) {
            throw new Error('Menu not found');
        }
        
        currentMenu = await response.json();
        displayMenu(currentMenu);
        document.getElementById('shoppingServings').value = currentMenu.servings;
        loadShoppingList();
    } catch (error) {
        console.error('Error loading menu:', error);
        document.getElementById('menuHeader').innerHTML = 
            '<p class="loading">Matsedeln kunde inte hittas.</p>';
    }
}

// Load all recipes for selection
async function loadAllRecipes() {
    try {
        const response = await fetch('/api/recipes');
        allRecipes = await response.json();
    } catch (error) {
        console.error('Error loading recipes:', error);
    }
}

// Display menu
function displayMenu(menu) {
    // Header
    document.getElementById('menuHeader').innerHTML = `
        <div class="menu-title-section">
            <h1>${menu.name}</h1>
            <div class="menu-meta">
                <span>📅 ${menu.num_days} dagar</span>
                <span>👥 ${menu.servings} portioner</span>
            </div>
        </div>
    `;
    
    // Build table-based layout
    const content = document.getElementById('menuContent');
    
    let html = `
        <div class="menu-table-wrapper">
            <table class="menu-table">
                <thead>
                    <tr>
                        <th class="day-column">Dag</th>
                        <th class="meal-column">🌅 Frukost</th>
                        <th class="meal-column">☀️ Lunch</th>
                        <th class="meal-column">🌙 Middag</th>
                        <th class="meal-column">🍪 Kvällsfika</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    for (let day = 1; day <= menu.num_days; day++) {
        const dayData = menu.days[day] || {};
        
        html += `<tr class="menu-row">`;
        html += `<td class="day-cell"><span class="day-number">Dag ${day}</span></td>`;
        
        for (const mealType of ['breakfast', 'lunch', 'dinner', 'evening_fika']) {
            const meal = dayData[mealType] || {};
            const hasRecipe = meal.recipe_id != null;
            
            if (hasRecipe) {
                html += `
                    <td class="meal-cell has-recipe" onclick="openRecipeSelector(${day}, '${mealType}')">
                        <div class="recipe-card">
                            <div class="recipe-card-name">${meal.recipe_name}</div>
                            ${meal.cooking_time ? `<div class="recipe-card-time">⏱️ ${meal.cooking_time}</div>` : ''}
                            <button class="remove-recipe-btn" onclick="event.stopPropagation(); clearMeal(${day}, '${mealType}')" title="Ta bort recept">
                                ✕ Ta bort
                            </button>
                        </div>
                    </td>
                `;
            } else {
                html += `
                    <td class="meal-cell empty" onclick="openRecipeSelector(${day}, '${mealType}')">
                        <div class="empty-slot">
                            <span class="plus-icon">+</span>
                            <span class="add-text">Välj recept</span>
                        </div>
                    </td>
                `;
            }
        }
        
        html += `</tr>`;
    }
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    // Add legend
    html += `
        <div class="menu-legend">
            <div class="legend-item">
                <span class="legend-box empty"></span>
                <span>Tomt - klicka för att välja recept</span>
            </div>
            <div class="legend-item">
                <span class="legend-box filled"></span>
                <span>Recept valt</span>
            </div>
        </div>
    `;
    
    content.innerHTML = html;
    
    // Show shopping list section
    document.getElementById('shoppingListSection').style.display = 'block';
}

// Open recipe selector modal
function openRecipeSelector(day, mealType) {
    currentSelection = { day, meal: mealType };
    
    displayModalRecipes(allRecipes);
    document.getElementById('modalSearch').value = '';
    document.getElementById('recipeModal').classList.add('active');
}

// Display recipes in modal
function displayModalRecipes(recipes) {
    const container = document.getElementById('modalRecipes');
    
    if (recipes.length === 0) {
        container.innerHTML = '<p class="loading">Inga recept hittades.</p>';
        return;
    }
    
    container.innerHTML = recipes.map(recipe => `
        <div class="modal-recipe" onclick="selectRecipe(${recipe.id})">
            <div class="modal-recipe-info">
                <h4>${recipe.name}</h4>
                <p>${recipe.description || ''}</p>
            </div>
            <div class="modal-recipe-meta">
                <span>${recipe.category || 'Övrigt'}</span>
                <span>${recipe.cooking_time || ''}</span>
            </div>
        </div>
    `).join('');
}

// Filter recipes in modal
function filterModalRecipes() {
    const query = document.getElementById('modalSearch').value.toLowerCase().trim();
    
    if (!query) {
        displayModalRecipes(allRecipes);
        return;
    }
    
    const filtered = allRecipes.filter(r => 
        r.name.toLowerCase().includes(query) || 
        (r.description && r.description.toLowerCase().includes(query))
    );
    
    displayModalRecipes(filtered);
}

// Select a recipe
async function selectRecipe(recipeId) {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    
    try {
        const response = await fetch(`/api/menus/${menuId}/items`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                day_number: currentSelection.day,
                meal_type: currentSelection.meal,
                recipe_id: recipeId
            })
        });
        
        if (response.ok) {
            closeModal();
            loadMenu(menuId);
        } else {
            alert('Kunde inte uppdatera matsedeln');
        }
    } catch (error) {
        console.error('Error updating menu:', error);
        alert('Kunde inte uppdatera matsedeln');
    }
}

// Clear a meal
async function clearMeal(day, mealType) {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    
    try {
        const response = await fetch(`/api/menus/${menuId}/items`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                day_number: day,
                meal_type: mealType,
                recipe_id: null
            })
        });
        
        if (response.ok) {
            loadMenu(menuId);
        } else {
            alert('Kunde inte ta bort receptet');
        }
    } catch (error) {
        console.error('Error clearing meal:', error);
        alert('Kunde inte ta bort receptet');
    }
}

// Close modal
function closeModal() {
    document.getElementById('recipeModal').classList.remove('active');
}

// Close modal on outside click
document.addEventListener('click', (e) => {
    const modal = document.getElementById('recipeModal');
    if (e.target === modal) {
        closeModal();
    }
});

// Load shopping list
async function loadShoppingList() {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    const servings = document.getElementById('shoppingServings').value;
    
    try {
        const response = await fetch(`/api/menus/${menuId}/shopping-list?servings=${servings}`);
        const data = await response.json();
        
        displayShoppingList(data);
    } catch (error) {
        console.error('Error loading shopping list:', error);
    }
}

// Display shopping list
function displayShoppingList(data) {
    const container = document.getElementById('shoppingList');
    
    if (!data.ingredients || data.ingredients.length === 0) {
        container.innerHTML = '<p class="loading">Lägg till recept i matsedeln för att se inköpslistan.</p>';
        return;
    }
    
    container.innerHTML = `
        <p class="shopping-list-info">Inköpslista för ${data.servings} portioner:</p>
        <ul class="shopping-items">
            ${data.ingredients.map(ing => `
                <li>
                    <span class="ingredient-name">${ing.name}</span>
                    <span class="ingredient-amount">${formatAmount(ing.amount)} ${ing.unit}</span>
                </li>
            `).join('')}
        </ul>
    `;
}

// Format amount
function formatAmount(amount) {
    const rounded = Math.round(amount * 100) / 100;
    return rounded.toString().replace('.', ',');
}
