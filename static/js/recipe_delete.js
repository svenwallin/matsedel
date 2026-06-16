function showDeleteMessage(text, isError) {
    const el = document.getElementById('deleteRecipeMessage');
    el.textContent = text;
    el.classList.toggle('error', !!isError);
    el.classList.toggle('success', !isError);
}

function recipeDeleteRowTemplate(recipe) {
    return `
        <div class="recipe-delete-item" data-recipe-id="${recipe.id}">
            <div>
                <p class="recipe-delete-name">${recipe.name}</p>
                <p class="editor-help">${recipe.category || 'Övrigt'} • ${recipe.cooking_time || 'Tid saknas'}</p>
            </div>
            <div class="recipe-delete-actions">
                <a href="/recipe/${recipe.id}" class="btn btn-secondary">Visa</a>
                <button type="button" class="btn btn-secondary recipe-delete-btn">Ta bort</button>
            </div>
        </div>
    `;
}

async function loadDeleteRecipes() {
    try {
        const response = await fetch('/api/recipes');
        const recipes = await response.json();
        const list = document.getElementById('deleteRecipeList');

        if (!Array.isArray(recipes) || recipes.length === 0) {
            list.innerHTML = '<p class="loading">Inga recept att visa.</p>';
            return;
        }

        list.innerHTML = recipes
            .sort((a, b) => a.name.localeCompare(b.name, 'sv'))
            .map((recipe) => recipeDeleteRowTemplate(recipe))
            .join('');
    } catch (error) {
        console.error('Error loading recipes for delete page:', error);
        document.getElementById('deleteRecipeList').innerHTML = '<p class="loading">Kunde inte ladda recept.</p>';
    }
}

async function deleteRecipe(recipeId, recipeName) {
    const ok = confirm(`Vill du ta bort receptet "${recipeName}"? Detta går inte att ångra.`);
    if (!ok) {
        return;
    }

    try {
        const response = await fetch(`/api/recipes/${recipeId}`, { method: 'DELETE' });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            showDeleteMessage(data.error || 'Kunde inte ta bort receptet.', true);
            return;
        }

        const row = document.querySelector(`.recipe-delete-item[data-recipe-id="${recipeId}"]`);
        if (row) {
            row.remove();
        }

        showDeleteMessage('Recept borttaget.', false);

        if (!document.querySelector('.recipe-delete-item')) {
            document.getElementById('deleteRecipeList').innerHTML = '<p class="loading">Inga recept att visa.</p>';
        }
    } catch (error) {
        console.error('Error deleting recipe:', error);
        showDeleteMessage('Något gick fel vid borttagning.', true);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadDeleteRecipes();

    document.getElementById('deleteRecipeList').addEventListener('click', (event) => {
        const button = event.target.closest('.recipe-delete-btn');
        if (!button) return;

        const row = event.target.closest('.recipe-delete-item');
        if (!row) return;

        const recipeId = row.dataset.recipeId;
        const recipeName = row.querySelector('.recipe-delete-name')?.textContent?.trim() || 'detta recept';
        deleteRecipe(recipeId, recipeName);
    });
});
