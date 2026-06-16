function ingredientRowTemplate() {
    return `
        <div class="editor-ingredient-row">
            <input type="text" class="ingredient-name" placeholder="Ingrediens" required>
            <input type="number" class="ingredient-amount" placeholder="Mängd" min="0" step="0.01" required>
            <select class="ingredient-unit" required>
                <option value="" disabled selected>Enhet</option>
                <option value="g">g</option>
                <option value="kg">kg</option>
                <option value="ml">ml</option>
                <option value="cl">cl</option>
                <option value="dl">dl</option>
                <option value="l">l</option>
                <option value="tsk">tsk</option>
                <option value="msk">msk</option>
                <option value="krm">krm</option>
                <option value="st">st</option>
                <option value="pkt">pkt</option>
                <option value="burk">burk</option>
                <option value="knippe">knippe</option>
            </select>
            <button type="button" class="btn btn-secondary remove-ingredient-btn">Ta bort</button>
        </div>
    `;
}

function addIngredientRow() {
    const rows = document.getElementById('ingredientsRows');
    rows.insertAdjacentHTML('beforeend', ingredientRowTemplate());
}

function clearIngredientRows() {
    document.getElementById('ingredientsRows').innerHTML = '';
}

function addIngredientRowWithValues(ingredient) {
    addIngredientRow();
    const rows = document.querySelectorAll('.editor-ingredient-row');
    const row = rows[rows.length - 1];

    row.querySelector('.ingredient-name').value = ingredient.name || '';
    row.querySelector('.ingredient-amount').value = Number.isFinite(ingredient.amount)
        ? ingredient.amount
        : '';
    row.querySelector('.ingredient-unit').value = ingredient.unit || '';
}

function normalizeInstructions(instructionsValue) {
    if (Array.isArray(instructionsValue)) {
        return instructionsValue
            .map((step) => String(step || '').trim())
            .filter((step) => step.length > 0)
            .map((step, index) => `${index + 1}. ${step.replace(/^\d+\.\s*/, '')}`)
            .join('\n');
    }

    if (typeof instructionsValue === 'string') {
        return instructionsValue
            .split('\n')
            .map((line) => line.trim())
            .filter((line) => line.length > 0)
            .join('\n');
    }

    return '';
}

function sanitizeJsonInput(raw) {
    const trimmed = raw.trim();
    if (!trimmed.startsWith('```')) {
        return trimmed;
    }

    return trimmed
        .replace(/^```(?:json)?\s*/i, '')
        .replace(/\s*```$/, '')
        .trim();
}

function importRecipeFromJson() {
    const importBox = document.getElementById('recipeImportJson');
    const raw = importBox.value;

    if (!raw.trim()) {
        showMessage('Klistra in JSON först.', true);
        return;
    }

    let parsed;
    try {
        parsed = JSON.parse(sanitizeJsonInput(raw));
    } catch (error) {
        showMessage('Ogiltig JSON. Kontrollera formatet och försök igen.', true);
        return;
    }

    const recipe = parsed && typeof parsed === 'object' && parsed.recipe && typeof parsed.recipe === 'object'
        ? parsed.recipe
        : parsed;

    if (!recipe || typeof recipe !== 'object') {
        showMessage('JSON måste innehålla ett receptobjekt.', true);
        return;
    }

    const ingredients = Array.isArray(recipe.ingredients) ? recipe.ingredients : [];
    if (!recipe.name || ingredients.length === 0) {
        showMessage('JSON saknar obligatoriska fält: name och ingredients.', true);
        return;
    }

    document.getElementById('recipeName').value = String(recipe.name || '').trim();
    document.getElementById('recipeDescription').value = String(recipe.description || '').trim();
    document.getElementById('recipeTime').value = String(recipe.cooking_time || '').trim();

    const servings = parseInt(recipe.base_servings, 10);
    document.getElementById('recipeServings').value = Number.isFinite(servings) && servings > 0 ? servings : 4;

    const instructions = normalizeInstructions(recipe.instructions);
    document.getElementById('recipeInstructions').value = instructions;

    const categorySelect = document.getElementById('recipeCategory');
    const category = String(recipe.category || 'Övrigt').trim() || 'Övrigt';
    const hasOption = Array.from(categorySelect.options).some((opt) => opt.value === category);
    if (!hasOption) {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        categorySelect.appendChild(option);
    }
    categorySelect.value = category;

    clearIngredientRows();
    ingredients.forEach((ingredient) => {
        const normalized = {
            name: String(ingredient.name || '').trim(),
            amount: Number(ingredient.amount),
            unit: String(ingredient.unit || '').trim()
        };

        if (!normalized.name || !Number.isFinite(normalized.amount) || !normalized.unit) {
            return;
        }

        addIngredientRowWithValues(normalized);
    });

    if (document.querySelectorAll('.editor-ingredient-row').length === 0) {
        addIngredientRow();
    }

    showMessage('Recept importerat till formuläret. Kontrollera och spara.', false);
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

async function submitRecipe(event) {
    event.preventDefault();

    const ingredients = collectIngredients();
    if (ingredients.length === 0) {
        showMessage('Lagg till minst en ingrediens.', true);
        return;
    }

    const instructionsRaw = document.getElementById('recipeInstructions').value
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0);

    if (instructionsRaw.length === 0) {
        showMessage('Lagg till minst ett instruktionsteg.', true);
        return;
    }

    const instructions = instructionsRaw
        .map((line, index) => `${index + 1}. ${line.replace(/^\d+\.\s*/, '')}`)
        .join('\n');

    let imageUrl = '';
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
            showMessage('Nagot gick fel vid bilduppladdning.', true);
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
        const response = await fetch('/api/recipes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            showMessage(data.error || 'Kunde inte spara receptet.', true);
            return;
        }

        showMessage('Recept sparat! Skickar dig till receptsidan...', false);
        setTimeout(() => {
            window.location.href = `/recipe/${data.id}`;
        }, 800);
    } catch (error) {
        console.error('Error saving recipe:', error);
        showMessage('Nagot gick fel vid sparning.', true);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadCategoryOptions();
    addIngredientRow();
    addIngredientRow();

    document.getElementById('addIngredientBtn').addEventListener('click', addIngredientRow);

    document.getElementById('ingredientsRows').addEventListener('click', (event) => {
        if (!event.target.classList.contains('remove-ingredient-btn')) return;
        const row = event.target.closest('.editor-ingredient-row');
        row.remove();

        if (document.querySelectorAll('.editor-ingredient-row').length === 0) {
            addIngredientRow();
        }
    });

    document.getElementById('recipeEditorForm').addEventListener('submit', submitRecipe);
    document.getElementById('importRecipeJsonBtn').addEventListener('click', importRecipeFromJson);
});
