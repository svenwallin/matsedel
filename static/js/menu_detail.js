// Menu detail page
const MEAL_LABELS = {
    'breakfast': '🌅 Frukost',
    'lunch': '☀️ Lunch',
    'dinner': '🌙 Middag',
    'evening_fika': '🍪 Kvällsfika'
};

const DAY_NAMES = ['Söndag', 'Måndag', 'Tisdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lördag'];

function getDayLabel(dayNumber, startDate) {
    if (!startDate) {
        return `Dag ${dayNumber}`;
    }
    const date = new Date(startDate);
    date.setDate(date.getDate() + dayNumber - 1);
    const dayName = DAY_NAMES[date.getDay()];
    const dateStr = date.toLocaleDateString('sv-SE', { day: 'numeric', month: 'short' });
    return `${dayName} ${dateStr}`;
}

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
    const startDateInfo = menu.start_date 
        ? `<span>🗓️ Start: ${new Date(menu.start_date).toLocaleDateString('sv-SE', { weekday: 'long', day: 'numeric', month: 'long' })}</span>` 
        : '';
    document.getElementById('menuHeader').innerHTML = `
        <div class="menu-title-section">
            <h1>${menu.name}</h1>
            <div class="menu-meta">
                <span>📅 ${menu.num_days} dagar</span>
                ${startDateInfo}
                <span>👥 ${menu.servings} portioner</span>
                <button class="print-btn" onclick="printMenu()">
                    <span class="print-btn-icon">🖨️</span>
                    <span>Skriv ut</span>
                </button>
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
        html += `<td class="day-cell"><span class="day-number">${getDayLabel(day, menu.start_date)}</span></td>`;
        
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
    const pantryLocationId = getSelectedPantryLocationId();
    const query = pantryLocationId ? `?pantry_location_id=${pantryLocationId}` : '';
    
    try {
        const response = await fetch(`/api/menus/${menuId}/shopping-list${query}`);
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
                pantry_location_id: pantryLocationId
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
    const actionsDiv = document.getElementById('shoppingActions');
    const pantryCoverage = Array.isArray(data.pantry_coverage) ? data.pantry_coverage : [];
    
    if ((!data.ingredients || data.ingredients.length === 0) && !data.all_covered) {
        container.innerHTML = '<p class="loading">Lägg till recept i matsedeln för att se inköpslistan.</p>';
        if (actionsDiv) actionsDiv.style.display = 'none';
        return;
    }

    // Show action buttons when we have data
    if (actionsDiv) actionsDiv.style.display = 'flex';

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
        ${pantryHtml}
        ${shoppingHtml}
    `;
}

// Format amount
function formatAmount(amount) {
    const rounded = Math.round(amount * 100) / 100;
    return rounded.toString().replace('.', ',');
}

// Print menu
function printMenu() {
    window.print();
}

// ===== Shopping List Export Functions =====

// Copy shopping list to clipboard
async function copyShoppingList() {
    if (!currentShoppingData || !currentShoppingData.ingredients || currentShoppingData.ingredients.length === 0) {
        showCopyStatus('Ingen inköpslista att kopiera', true);
        return;
    }
    
    // Build text from shopping list
    let text = `Inköpslista\n\n`;
    
    // Add pantry coverage if available
    if (currentShoppingData.pantry_coverage && currentShoppingData.pantry_coverage.length > 0) {
        text += 'FRÅN SKAFFERIET:\n';
        currentShoppingData.pantry_coverage.forEach(ing => {
            text += `• ${ing.name}: ${formatAmount(ing.amount)} ${ing.unit}\n`;
        });
        text += '\n';
    }
    
    // Add items to buy
    text += 'BEHÖVER KÖPAS:\n';
    currentShoppingData.ingredients.forEach(ing => {
        text += `• ${ing.name}: ${formatAmount(ing.amount)} ${ing.unit}\n`;
    });
    
    try {
        await navigator.clipboard.writeText(text);
        showCopyStatus('✅ Inköpslistan kopierad!', false);
    } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showCopyStatus('✅ Inköpslistan kopierad!', false);
    }
}

// Show copy status message
function showCopyStatus(message, isError) {
    const statusEl = document.getElementById('copyStatus');
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.classList.toggle('error', isError);
        statusEl.classList.toggle('success', !isError);
        
        setTimeout(() => {
            statusEl.textContent = '';
        }, 3000);
    }
}

// Export shopping list to PDF
function exportShoppingListPdf() {
    if (!currentShoppingData || !currentShoppingData.ingredients || currentShoppingData.ingredients.length === 0) {
        showCopyStatus('Ingen lista att exportera', true);
        return;
    }
    
    // Get menu name from page title
    const menuTitle = document.querySelector('h1')?.textContent || 'Inköpslista';
    const today = new Date().toLocaleDateString('sv-SE');
    
    // Build pantry section HTML
    let pantryHtml = '';
    if (currentShoppingData.pantry_coverage && currentShoppingData.pantry_coverage.length > 0) {
        pantryHtml = `
            <h4>📦 Från skafferiet</h4>
            <ul class="covered">
                ${currentShoppingData.pantry_coverage.map(ing => 
                    `<li><span class="name">${ing.name}</span><span class="amount">${formatAmount(ing.amount)} ${ing.unit}</span></li>`
                ).join('')}
            </ul>
        `;
    }
    
    // Build shopping items HTML
    const shoppingHtml = `
        <h4>🛒 Behöver köpas</h4>
        <ul>
            ${currentShoppingData.ingredients.map(ing => 
                `<li><span class="name">${ing.name}</span><span class="amount">${formatAmount(ing.amount)} ${ing.unit}</span></li>`
            ).join('')}
        </ul>
    `;
    
    // Create print window
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Inköpslista - ${menuTitle}</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    color: #333;
                    line-height: 1.6;
                }
                h1 {
                    color: #2e7d32;
                    border-bottom: 3px solid #2e7d32;
                    padding-bottom: 10px;
                    margin-bottom: 5px;
                }
                .date {
                    color: #666;
                    font-size: 0.9rem;
                    margin-bottom: 20px;
                }
                .servings {
                    background: #e8f5e9;
                    padding: 10px 15px;
                    border-radius: 8px;
                    margin-bottom: 25px;
                    font-weight: 600;
                }
                h4 {
                    color: #2e7d32;
                    font-size: 1.1rem;
                    margin: 25px 0 10px 0;
                    padding-bottom: 5px;
                    border-bottom: 2px solid #2e7d32;
                }
                ul {
                    list-style: none;
                    padding: 0;
                    margin: 0 0 20px 0;
                }
                ul.covered li {
                    background: #f0f0f0;
                    border-left: 3px solid #999;
                }
                li {
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 15px;
                    margin-bottom: 5px;
                    background: #f5f5f5;
                    border-left: 3px solid #2e7d32;
                    border-radius: 0 4px 4px 0;
                }
                .name {
                    font-weight: 500;
                }
                .amount {
                    color: #666;
                    font-weight: 600;
                }
                .footer {
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 0.8rem;
                    color: #999;
                    text-align: center;
                }
                @media print {
                    body { padding: 0; }
                    h1 { font-size: 1.5rem; }
                    h4 { font-size: 1rem; }
                    li { padding: 6px 10px; }
                }
            </style>
        </head>
        <body>
            <h1>🛒 ${menuTitle}</h1>
            <p class="date">Skapad: ${today}</p>
            ${pantryHtml}
            ${shoppingHtml}
            <div class="footer">
                Genererad av Matsedel-appen
            </div>
        </body>
        </html>
    `);
    printWindow.document.close();
    
    // Wait for content to load then print
    printWindow.onload = function() {
        printWindow.print();
    };
    
    showCopyStatus('📄 PDF-export öppnad i nytt fönster', false);
}
