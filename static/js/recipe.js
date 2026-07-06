// Recipe icons mapping
const RECIPE_ICONS = {
    'Huvudrätt': '🍲',
    'Frukost': '🥞',
    'Soppa': '🍜',
    'Bröd': '🥖',
    'Tillbehör': '🥔',
    'Dessert': '🍰',
    'default': '🍽️'
};

let currentRecipe = null;

// Load recipe on page load
document.addEventListener('DOMContentLoaded', () => {
    // Get recipe ID from URL
    const pathParts = window.location.pathname.split('/');
    const recipeId = pathParts[pathParts.length - 1];
    
    loadRecipe(recipeId);
});

// Load single recipe
async function loadRecipe(recipeId) {
    try {
        const response = await fetch(`/api/recipes/${recipeId}`);
        
        if (!response.ok) {
            throw new Error('Recipe not found');
        }
        
        currentRecipe = await response.json();
        console.log('Recipe loaded:', currentRecipe);
        console.log('Image URL:', currentRecipe.image_url);
        displayRecipe(currentRecipe);
    } catch (error) {
        console.error('Error loading recipe:', error);
        document.getElementById('recipeContent').innerHTML = 
            '<p class="loading">Receptet kunde inte hittas.</p>';
    }
}

// Display recipe
function displayRecipe(recipe) {
    const container = document.getElementById('recipeContent');
    const icon = RECIPE_ICONS[recipe.category] || RECIPE_ICONS.default;
    
    console.log('Displaying recipe, image_url:', recipe.image_url, 'type:', typeof recipe.image_url);
    
    const hasImage = recipe.image_url && recipe.image_url.trim() !== '';
    const imageMarkup = `
        <span class="recipe-detail-icon">${icon}</span>
        ${hasImage
            ? `<img src="${recipe.image_url}" alt="${recipe.name}" class="recipe-photo-large" onerror="this.remove();">`
            : ''}
    `;
    
    // Parse instructions into steps
    const instructionSteps = recipe.instructions ? 
        recipe.instructions.split('\n').filter(step => step.trim()) : [];
    
    container.innerHTML = `
        <div class="recipe-header">
            <div class="recipe-image-large">${imageMarkup}</div>
            <div class="recipe-title-section">
                <span class="recipe-category">${recipe.category || 'Övrigt'}</span>
                <h1>${recipe.name}</h1>
                <p class="recipe-description">${recipe.description || ''}</p>
                <div class="recipe-details">
                    <div class="detail-item">
                        <span>⏱️</span>
                        <span>${recipe.cooking_time || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span>👥</span>
                        <span>${recipe.base_servings} portioner (bas)</span>
                    </div>
                    <button class="print-btn" onclick="printRecipe()">
                        <span class="print-btn-icon">🖨️</span>
                        <span>Skriv ut</span>
                    </button>
                </div>
                <div class="servings-calculator">
                    <h3>🔢 Beräkna ingredienser</h3>
                    <p>Ange antal portioner för att räkna om ingrediensmängderna:</p>
                    <div class="servings-input">
                        <input type="number" id="servingsInput" min="1" max="100" value="${recipe.base_servings}">
                        <span>portioner</span>
                        <button onclick="calculateIngredients()">Beräkna</button>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="recipe-body">
            <div class="ingredients-section">
                <h2>Ingredienser</h2>
                <p id="servingsInfo">För ${recipe.base_servings} portioner:</p>
                <ul class="ingredients-list" id="ingredientsList">
                    ${recipe.ingredients.map(ing => `
                        <li>
                            <span>${ing.name}</span>
                            <span class="ingredient-amount">${formatAmount(ing.amount)} ${ing.unit}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
            
            <div class="instructions-section">
                <h2>Instruktioner</h2>
                <ol>
                    ${instructionSteps.map(step => `<li>${step.replace(/^\d+\.\s*/, '')}</li>`).join('')}
                </ol>
            </div>
        </div>
    `;
    
    // Update page title
    document.title = `${recipe.name} - Matsedel`;
}

// Calculate ingredients for different servings
async function calculateIngredients() {
    const servings = parseInt(document.getElementById('servingsInput').value);
    
    if (!servings || servings < 1) {
        alert('Ange ett giltigt antal portioner (minst 1)');
        return;
    }
    
    try {
        const response = await fetch(`/api/calculate/${currentRecipe.id}?servings=${servings}`);
        const data = await response.json();
        
        // Update servings info
        document.getElementById('servingsInfo').textContent = `För ${servings} portioner:`;
        
        // Update ingredients list
        const list = document.getElementById('ingredientsList');
        list.innerHTML = data.ingredients.map(ing => `
            <li>
                <span>${ing.name}</span>
                <span class="ingredient-amount">${formatAmount(ing.amount)} ${ing.unit}</span>
            </li>
        `).join('');
        
        // Highlight the change
        list.style.animation = 'none';
        list.offsetHeight; // Trigger reflow
        list.style.animation = 'highlight 0.5s ease';
    } catch (error) {
        console.error('Error calculating ingredients:', error);
        alert('Kunde inte beräkna ingredienser. Försök igen.');
    }
}

// Format amount nicely
function formatAmount(amount) {
    // Round to 2 decimal places and remove trailing zeros
    const rounded = Math.round(amount * 100) / 100;
    
    // Format with comma for Swedish locale
    return rounded.toString().replace('.', ',');
}

// Add highlight animation to CSS dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes highlight {
        0% { background-color: rgba(0, 99, 65, 0.2); }
        100% { background-color: transparent; }
    }
`;
document.head.appendChild(style);

// Print recipe
function printRecipe() {
    window.print();
}
