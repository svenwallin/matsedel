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
let pantryLocations = [];
let currentShoppingData = null;

// Load menu on page load
document.addEventListener('DOMContentLoaded', () => {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    
    loadMenu(menuId);
    loadAllRecipes();
    loadPantryLocations();
});

function showShoppingPantryMessage(text, isError) {
    const el = document.getElementById('shoppingPantryMessage');
    el.textContent = text;
    el.classList.toggle('error', !!isError);
    el.classList.toggle('success', !isError);
}

async function loadPantryLocations() {
    try {
        const response = await fetch('/api/pantry-locations');
        pantryLocations = await response.json();
        const select = document.getElementById('shoppingPantrySelect');

        if (!Array.isArray(pantryLocations) || pantryLocations.length === 0) {
            select.innerHTML = '<option value="">Inga skafferier</option>';
            select.disabled = true;
            return;
        }

        select.disabled = false;
        select.innerHTML = pantryLocations.map((location) => `
            <option value="${location.id}">${location.name}</option>
        `).join('');

        select.addEventListener('change', loadShoppingList);
    } catch (error) {
        console.error('Error loading pantry locations:', error);
    }
}

function getSelectedPantryLocationId() {
    const select = document.getElementById('shoppingPantrySelect');
    return select && select.value ? parseInt(select.value, 10) : null;
}

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
            const meal = dayData[mealType] || { recipes: [], day_servings: null };
            const recipes = meal.recipes || [];
            const hasRecipes = recipes.length > 0;
            
            if (hasRecipes) {
                const recipesHtml = recipes.map(recipe => {
                    const recipeServings = recipe.servings != null ? recipe.servings : '';
                    return `
                    <div class="recipe-card-multi">
                        <div class="recipe-card-name">${recipe.recipe_name}</div>
                        ${recipe.cooking_time ? `<div class="recipe-card-time">⏱️ ${recipe.cooking_time}</div>` : ''}
                        <div class="recipe-servings-control" onclick="event.stopPropagation()">
                            <input
                                class="recipe-servings-input"
                                type="number"
                                min="1"
                                step="1"
                                value="${recipeServings}"
                                placeholder="${menu.servings}"
                                title="Portioner för detta recept"
                                onclick="event.stopPropagation()"
                                onchange="updateRecipeServings(${recipe.id}, this.value)"
                            >
                            <span class="recipe-servings-label">port.</span>
                        </div>
                        <button class="remove-recipe-btn-small" onclick="event.stopPropagation(); removeRecipe(${day}, '${mealType}', ${recipe.id})" title="Ta bort recept">
                            ✕
                        </button>
                    </div>
                `}).join('');
                
                html += `
                    <td class="meal-cell has-recipe">
                        <div class="recipes-list">
                            ${recipesHtml}
                        </div>
                        <button class="add-more-recipe-btn" onclick="event.stopPropagation(); openRecipeSelector(${day}, '${mealType}')" title="Lägg till recept">
                            + Lägg till
                        </button>
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

async function updateMealServings(day, mealType, value) {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    const trimmed = String(value ?? '').trim();

    if (trimmed !== '' && (!Number.isInteger(Number(trimmed)) || Number(trimmed) < 1)) {
        alert('Portionsoverride måste vara ett heltal från 1 och uppåt.');
        loadMenu(menuId);
        return;
    }

    try {
        const response = await fetch(`/api/menus/${menuId}/meal-servings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                day_number: day,
                meal_type: mealType,
                servings_override: trimmed === '' ? null : Number(trimmed)
            })
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            alert(data.error || 'Kunde inte uppdatera dagsportioner.');
        }

        loadMenu(menuId);
    } catch (error) {
        console.error('Error updating day servings:', error);
        alert('Kunde inte uppdatera dagsportioner.');
        loadMenu(menuId);
    }
}

// Update servings for a specific recipe in the menu
async function updateRecipeServings(menuItemId, value) {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    const trimmed = String(value ?? '').trim();

    if (trimmed !== '' && (!Number.isInteger(Number(trimmed)) || Number(trimmed) < 1)) {
        alert('Portioner måste vara ett heltal från 1 och uppåt.');
        loadMenu(menuId);
        return;
    }

    try {
        const response = await fetch(`/api/menus/${menuId}/recipes/${menuItemId}/servings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                servings: trimmed === '' ? null : Number(trimmed)
            })
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            alert(data.error || 'Kunde inte uppdatera portioner.');
        }

        loadMenu(menuId);
    } catch (error) {
        console.error('Error updating recipe servings:', error);
        alert('Kunde inte uppdatera portioner.');
        loadMenu(menuId);
    }
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

// Select a recipe - now adds to the meal slot instead of replacing
async function selectRecipe(recipeId) {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    
    try {
        const response = await fetch(`/api/menus/${menuId}/recipes`, {
            method: 'POST',
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
            alert('Kunde inte lägga till receptet');
        }
    } catch (error) {
        console.error('Error adding recipe:', error);
        alert('Kunde inte lägga till receptet');
    }
}

// Remove a specific recipe from a meal slot
async function removeRecipe(day, mealType, menuItemId) {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    
    try {
        const response = await fetch(`/api/menus/${menuId}/recipes/${menuItemId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                day_number: day,
                meal_type: mealType
            })
        });
        
        if (response.ok) {
            loadMenu(menuId);
        } else {
            alert('Kunde inte ta bort receptet');
        }
    } catch (error) {
        console.error('Error removing recipe:', error);
        alert('Kunde inte ta bort receptet');
    }
}

// Clear a meal (legacy - kept for backward compatibility)
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
    const pantryLocationId = getSelectedPantryLocationId();
    const pantryQuery = pantryLocationId ? `&pantry_location_id=${pantryLocationId}` : '';
    
    try {
        const response = await fetch(`/api/menus/${menuId}/shopping-list?servings=${servings}${pantryQuery}`);
        const data = await response.json();
        currentShoppingData = data;
        
        displayShoppingList(data);
    } catch (error) {
        console.error('Error loading shopping list:', error);
    }
}

async function consumePantryForMenu() {
    const pathParts = window.location.pathname.split('/');
    const menuId = pathParts[pathParts.length - 1];
    const pantryLocationId = getSelectedPantryLocationId();
    const servings = parseInt(document.getElementById('shoppingServings').value, 10);

    if (!pantryLocationId) {
        showShoppingPantryMessage('Välj ett skafferi först.', true);
        return;
    }

    if (!currentShoppingData || !Array.isArray(currentShoppingData.pantry_coverage) || currentShoppingData.pantry_coverage.length === 0) {
        showShoppingPantryMessage('Det finns inget i valt skafferi att dra av för den här matsedeln.', true);
        return;
    }

    const pantryName = pantryLocations.find((location) => location.id === pantryLocationId)?.name || 'valt skafferi';
    const confirmationLines = currentShoppingData.pantry_coverage
        .map((item) => `- ${item.name}: ${formatAmount(item.amount)} ${item.unit}`)
        .join('\n');

    const shouldConsume = confirm(
        `Dra av följande från ${pantryName}?\n\n${confirmationLines}`
    );

    if (!shouldConsume) {
        return;
    }

    try {
        const response = await fetch(`/api/menus/${menuId}/consume-pantry`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pantry_location_id: pantryLocationId,
                servings
            })
        });

        const data = await response.json();
        if (!response.ok) {
            showShoppingPantryMessage(data.error || 'Kunde inte använda skafferiet.', true);
            return;
        }

        showShoppingPantryMessage('Valt skafferi har uppdaterats efter användning.', false);
        loadShoppingList();
    } catch (error) {
        console.error('Error consuming pantry:', error);
        showShoppingPantryMessage('Kunde inte använda skafferiet.', true);
    }
}

// Display shopping list
function displayShoppingList(data) {
    const container = document.getElementById('shoppingList');
    const pantryCoverage = Array.isArray(data.pantry_coverage) ? data.pantry_coverage : [];
    
    if ((!data.ingredients || data.ingredients.length === 0) && !data.all_covered) {
        container.innerHTML = '<p class="loading">Lägg till recept i matsedeln för att se inköpslistan.</p>';
        return;
    }

    const pantryHtml = pantryCoverage.length > 0
        ? `
            <div class="shopping-coverage">
                <h3>Från skafferiet</h3>
                <ul class="shopping-items shopping-items-covered">
                    ${pantryCoverage.map(ing => `
                        <li>
                            <span class="ingredient-name">${ing.name}</span>
                            <span class="ingredient-amount">${formatAmount(ing.amount)} ${ing.unit}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `
        : '';

    const shoppingHtml = data.ingredients.length > 0
        ? `
            <div class="shopping-needed">
                <h3>Behöver köpas</h3>
                <ul class="shopping-items">
                    ${data.ingredients.map(ing => `
                        <li>
                            <div>
                                <span class="ingredient-name">${ing.name}</span>
                                ${ing.pantry_amount > 0 ? `<div class="shopping-item-note">Behov: ${formatAmount(ing.required_amount)} ${ing.unit}, i skafferi: ${formatAmount(ing.pantry_amount)} ${ing.unit}</div>` : ''}
                            </div>
                            <span class="ingredient-amount">${formatAmount(ing.amount)} ${ing.unit}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `
        : '<p class="shopping-all-covered">Allt som behövs finns redan i skafferiet.</p>';
    
    container.innerHTML = `
        <p class="shopping-list-info">Inköpslista för ${data.servings} portioner:</p>
        ${pantryHtml}
        ${shoppingHtml}
    `;
}

// Format amount
function formatAmount(amount) {
    const rounded = Math.round(amount * 100) / 100;
    return rounded.toString().replace('.', ',');
}
