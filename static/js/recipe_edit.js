function ingredientRowTemplate(ingredient = null) {
    const name = ingredient ? ingredient.name : '';
    const amount = ingredient ? ingredient.amount : '';
    const unit = ingredient ? ingredient.unit : '';
    
    return `
        <div class="editor-ingredient-row">
            <input type="text" class="ingredient-name" placeholder="Ingrediens" value="${name}" required>
            <input type="number" class="ingredient-amount" placeholder="Mängd" min="0" step="0.01" value="${amount}" required>
            <select class="ingredient-unit" required>
                <option value="" disabled ${!unit ? 'selected' : ''}>Enhet</option>
                <option value="g" ${unit === 'g' ? 'selected' : ''}>g</option>
                <option value="kg" ${unit === 'kg' ? 'selected' : ''}>kg</option>
                <option value="ml" ${unit === 'ml' ? 'selected' : ''}>ml</option>
                <option value="cl" ${unit === 'cl' ? 'selected' : ''}>cl</option>
                <option value="dl" ${unit === 'dl' ? 'selected' : ''}>dl</option>
                <option value="l" ${unit === 'l' ? 'selected' : ''}>l</option>
                <option value="tsk" ${unit === 'tsk' ? 'selected' : ''}>tsk</option>
                <option value="msk" ${unit === 'msk' ? 'selected' : ''}>msk</option>
                <option value="krm" ${unit === 'krm' ? 'selected' : ''}>krm</option>
                <option value="st" ${unit === 'st' ? 'selected' : ''}>st</option>
                <option value="pkt" ${unit === 'pkt' ? 'selected' : ''}>pkt</option>
                <option value="burk" ${unit === 'burk' ? 'selected' : ''}>burk</option>
                <option value="knippe" ${unit === 'knippe' ? 'selected' : ''}>knippe</option>
            </select>
            <button type="button" class="btn btn-secondary remove-ingredient-btn">Ta bort</button>
        </div>
    `;
}

function addIngredientRow(ingredient = null) {
    const rows = document.getElementById('ingredientsRows');
    rows.insertAdjacentHTML('beforeend', ingredientRowTemplate(ingredient));
}

function showMessage(text, isError) {
    const el = document.getElementById('editorMessage');
    el.textContent = text;
    el.classList.toggle('error', !!isError);
    el.classList.toggle('success', !isError);
}

function collectIngredients() {
    const rows = document.querySelectorAll('.editor-ingredient-row');
    const ingredients = [];

    rows.forEach((row) => {
        const name = row.querySelector('.ingredient-name').value.trim();
        const amount = parseFloat(row.querySelector('.ingredient-amount').value);
        const unit = row.querySelector('.ingredient-unit').value.trim();

        if (name && Number.isFinite(amount) && unit) {
            ingredients.push({ name, amount, unit });
        }
    });

    return ingredients;
}

async function loadCategoryOptions() {
    const categorySelect = document.getElementById('recipeCategory');
    const existingOptions = Array.from(categorySelect.querySelectorAll('option'))
        .map((opt) => opt.value)
        .filter((value) => value);
    const categorySet = new Set(existingOptions);

    try {
        const response = await fetch('/api/categories');
        const categories = await response.json();
        if (!Array.isArray(categories)) return;

        categories.forEach((category) => {
            if (category) categorySet.add(category);
        });

        const sorted = Array.from(categorySet)
            .filter((category) => category !== 'Övrigt')
            .sort((a, b) => a.localeCompare(b, 'sv'));

        if (categorySet.has('Övrigt')) {
            sorted.push('Övrigt');
        }

        const placeholder = categorySelect.querySelector('option[value=""]');
        categorySelect.innerHTML = '';
        if (placeholder) {
            categorySelect.appendChild(placeholder);
        }

        sorted.forEach((category) => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            categorySelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

let currentRecipeId = null;
let currentImageUrl = null;

async function loadRecipe(recipeId) {
    try {
        const response = await fetch(`/api/recipes/${recipeId}`);
        
        if (!response.ok) {
            throw new Error('Recipe not found');
        }
        
        const recipe = await response.json();
        currentRecipeId = recipe.id;
        currentImageUrl = recipe.image_url;
        
        // Populate form
        document.getElementById('recipeName').value = recipe.name || '';
        document.getElementById('recipeDescription').value = recipe.description || '';
        document.getElementById('recipeCategory').value = recipe.category || 'Övrigt';
        document.getElementById('recipeTime').value = recipe.cooking_time || '';
        document.getElementById('recipeServings').value = recipe.base_servings || 4;
        document.getElementById('recipeInstructions').value = recipe.instructions || '';
        
        // Clear existing ingredients and add recipe ingredients
        document.getElementById('ingredientsRows').innerHTML = '';
        if (recipe.ingredients && recipe.ingredients.length > 0) {
            recipe.ingredients.forEach(ing => addIngredientRow(ing));
        } else {
            addIngredientRow();
            addIngredientRow();
        }
        
        // Show current image if it exists
        if (recipe.image_url) {
            const previewContainer = document.getElementById('currentImageContainer');
            previewContainer.innerHTML = `
                <div class="editor-current-image">
                    <p>Nuvarande bild:</p>
                    <img src="${recipe.image_url}" alt="${recipe.name}" style="max-width: 200px; max-height: 200px;">
                </div>
            `;
        }
        
    } catch (error) {
        console.error('Error loading recipe:', error);
        showMessage('Receptet kunde inte hittas.', true);
    }
}

async function submitRecipe(event) {
    event.preventDefault();

    if (!currentRecipeId) {
        showMessage('Receptet kunde inte hittas.', true);
        return;
    }

    const ingredients = collectIngredients();
    if (ingredients.length === 0) {
        showMessage('Lägg till minst en ingrediens.', true);
        return;
    }

    const instructionsRaw = document.getElementById('recipeInstructions').value
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0);

    if (instructionsRaw.length === 0) {
        showMessage('Lägg till minst ett instruktionsteg.', true);
        return;
    }

    const instructions = instructionsRaw
        .map((line, index) => `${index + 1}. ${line.replace(/^\d+\.\s*/, '')}`)
        .join('\n');

    let imageUrl = currentImageUrl;
    const imageInput = document.getElementById('recipeImage');
    const imageFile = imageInput.files && imageInput.files[0] ? imageInput.files[0] : null;

    if (imageFile) {
        try {
            const formData = new FormData();
            formData.append('image', imageFile);

            const uploadResponse = await fetch('/api/uploads', {
                method: 'POST',
                body: formData
            });

            const uploadData = await uploadResponse.json();
            if (!uploadResponse.ok) {
                showMessage(uploadData.error || 'Kunde inte ladda upp bild.', true);
                return;
            }

            imageUrl = uploadData.url || '';
        } catch (error) {
            console.error('Error uploading image:', error);
            showMessage('Något gick fel vid bilduppladdning.', true);
            return;
        }
    }

    const payload = {
        name: document.getElementById('recipeName').value.trim(),
        description: document.getElementById('recipeDescription').value.trim(),
        category: document.getElementById('recipeCategory').value.trim(),
        base_servings: parseInt(document.getElementById('recipeServings').value, 10),
        cooking_time: document.getElementById('recipeTime').value.trim(),
        instructions,
        image_url: imageUrl,
        ingredients
    };

    try {
        const response = await fetch(`/api/recipes/${currentRecipeId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            showMessage(data.error || 'Kunde inte spara receptet.', true);
            return;
        }

        showMessage('Recept uppdaterat! Skickar dig till receptsidan...', false);
        setTimeout(() => {
            window.location.href = `/recipe/${currentRecipeId}`;
        }, 800);
    } catch (error) {
        console.error('Error saving recipe:', error);
        showMessage('Något gick fel vid sparning.', true);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Get recipe ID from URL
    const pathParts = window.location.pathname.split('/');
    const recipeId = parseInt(pathParts[2], 10);
    
    loadCategoryOptions();
    loadRecipe(recipeId);

    document.getElementById('addIngredientBtn').addEventListener('click', () => addIngredientRow());

    document.getElementById('ingredientsRows').addEventListener('click', (event) => {
        if (!event.target.classList.contains('remove-ingredient-btn')) return;
        const row = event.target.closest('.editor-ingredient-row');
        row.remove();

        if (document.querySelectorAll('.editor-ingredient-row').length === 0) {
            addIngredientRow();
        }
    });

    document.getElementById('recipeEditorForm').addEventListener('submit', submitRecipe);
});
