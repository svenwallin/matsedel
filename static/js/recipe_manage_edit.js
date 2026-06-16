function editRecipeRowTemplate(recipe) {
    return `
        <div class="recipe-delete-item">
            <div>
                <p class="recipe-delete-name">${recipe.name}</p>
                <p class="editor-help">${recipe.category || 'Övrigt'} • ${recipe.cooking_time || 'Tid saknas'}</p>
            </div>
            <div class="recipe-delete-actions">
                <a href="/recipe/${recipe.id}" class="btn btn-secondary">Visa</a>
                <a href="/recipe/${recipe.id}/edit" class="btn btn-primary">Redigera</a>
            </div>
        </div>
    `;
}

async function loadEditRecipes() {
    try {
        const response = await fetch('/api/recipes');
        const recipes = await response.json();
        const list = document.getElementById('editRecipeList');

        if (!Array.isArray(recipes) || recipes.length === 0) {
            list.innerHTML = '<p class="loading">Inga recept att visa.</p>';
            return;
        }

        list.innerHTML = recipes
            .sort((a, b) => a.name.localeCompare(b.name, 'sv'))
            .map((recipe) => editRecipeRowTemplate(recipe))
            .join('');
    } catch (error) {
        console.error('Error loading recipes for edit page:', error);
        document.getElementById('editRecipeList').innerHTML = '<p class="loading">Kunde inte ladda recept.</p>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadEditRecipes();
});
