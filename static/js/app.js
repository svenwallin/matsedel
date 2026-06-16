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

// Load recipes on page load
document.addEventListener('DOMContentLoaded', () => {
    loadCategories();
    loadRecipes();
    
    // Add search on enter key
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchRecipes();
        }
    });
});

// Load categories
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const categories = await response.json();
        
        const container = document.getElementById('categoryButtons');
        
        categories.forEach(category => {
            const btn = document.createElement('button');
            btn.className = 'category-btn';
            btn.dataset.category = category;
            btn.textContent = category;
            btn.onclick = () => filterByCategory(category);
            container.appendChild(btn);
        });
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

// Load all recipes
async function loadRecipes(category = null, search = null) {
    try {
        let url = '/api/recipes';
        if (category) {
            url += `?category=${encodeURIComponent(category)}`;
        } else if (search) {
            url += `?search=${encodeURIComponent(search)}`;
        }
        
        const response = await fetch(url);
        const recipes = await response.json();
        
        displayRecipes(recipes);
    } catch (error) {
        console.error('Error loading recipes:', error);
        document.getElementById('recipesGrid').innerHTML = 
            '<p class="loading">Kunde inte ladda recept. Försök igen senare.</p>';
    }
}

// Display recipes in grid
function displayRecipes(recipes) {
    const grid = document.getElementById('recipesGrid');
    
    if (recipes.length === 0) {
        grid.innerHTML = '<p class="loading">Inga recept hittades.</p>';
        return;
    }
    
    grid.innerHTML = recipes.map(recipe => {
        const icon = RECIPE_ICONS[recipe.category] || RECIPE_ICONS.default;
        const hasImage = recipe.image_url && recipe.image_url.trim() !== '';
        console.log(`Recipe "${recipe.name}": image_url="${recipe.image_url}", hasImage=${hasImage}`);
        return `
        <article class="recipe-card" onclick="window.location.href='/recipe/${recipe.id}'">
            <div class="recipe-image">
                ${hasImage
                    ? `<img src="${recipe.image_url}" alt="${recipe.name}" class="recipe-photo-card" onerror="this.parentElement.textContent='${icon}';">`
                    : icon}
            </div>
            <div class="recipe-info">
                <span class="recipe-category">${recipe.category || 'Övrigt'}</span>
                <h3>${recipe.name}</h3>
                <p>${recipe.description || ''}</p>
                <div class="recipe-meta">
                    <span>⏱️ ${recipe.cooking_time || 'N/A'}</span>
                    <span>👥 ${recipe.base_servings} portioner</span>
                </div>
            </div>
        </article>
    `}).join('');
}

// Filter by category
function filterByCategory(category) {
    // Update active button
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.category === category || (category === 'all' && btn.dataset.category === 'all')) {
            btn.classList.add('active');
        }
    });
    
    // Reset search input
    document.getElementById('searchInput').value = '';
    
    // Load recipes
    if (category === 'all') {
        loadRecipes();
    } else {
        loadRecipes(category);
    }
}

// Search recipes
function searchRecipes() {
    const query = document.getElementById('searchInput').value.trim();
    
    // Reset category buttons
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector('.category-btn[data-category="all"]').classList.add('active');
    
    if (query) {
        loadRecipes(null, query);
    } else {
        loadRecipes();
    }
}
