function formatPantryAmount(amount) {
    const rounded = Math.round(amount * 100) / 100;
    return rounded.toString().replace('.', ',');
}

const LOW_STOCK_THRESHOLDS = {
    g: 200,
    kg: 0.2,
    ml: 200,
    cl: 20,
    dl: 2,
    l: 0.5,
    tsk: 2,
    msk: 1,
    krm: 5,
    st: 2,
    pkt: 1,
    burk: 1,
    knippe: 1
};

function showPantryMessage(text, isError) {
    const el = document.getElementById('pantryMessage');
    el.textContent = text;
    el.classList.toggle('error', !!isError);
    el.classList.toggle('success', !isError);
}

function resetPantryForm() {
    document.getElementById('pantryForm').reset();
}

function getSelectedPantryLocationId() {
    return parseInt(document.getElementById('pantryLocationSelect').value, 10);
}

function pantryCardTemplate(item) {
    return `
        <article class="pantry-card" data-item-id="${item.id}">
            <div class="pantry-card-header">
                <h3>${item.name}</h3>
                <div class="pantry-card-actions">
                    <button type="button" class="btn btn-secondary pantry-edit-btn">Redigera</button>
                    <button type="button" class="btn btn-secondary pantry-delete-btn">Ta bort</button>
                </div>
            </div>
            <p class="pantry-amount">${formatPantryAmount(item.amount)} ${item.unit}</p>
            <form class="pantry-edit-form" hidden>
                <div class="pantry-edit-grid">
                    <input type="text" name="name" value="${item.name}" required>
                    <input type="number" name="amount" min="0" step="0.01" value="${item.amount}" required>
                    <input type="text" name="unit" value="${item.unit}" required>
                </div>
                <div class="pantry-inline-actions">
                    <button type="submit" class="btn btn-primary">Spara</button>
                    <button type="button" class="btn btn-secondary pantry-cancel-btn">Avbryt</button>
                </div>
            </form>
        </article>
    `;
}

function getPantrySummary(items) {
    const unitTotals = items.reduce((accumulator, item) => {
        const unit = item.unit || 'st';
        accumulator[unit] = (accumulator[unit] || 0) + Number(item.amount || 0);
        return accumulator;
    }, {});

    const uniqueIngredients = new Set(
        items.map((item) => item.name.trim().toLowerCase())
    ).size;

    return {
        rowCount: items.length,
        uniqueIngredients,
        unitTotals
    };
}

function pantrySummaryBadges(summary) {
    const totals = Object.entries(summary.unitTotals)
        .sort(([left], [right]) => left.localeCompare(right, 'sv'))
        .map(([unit, amount]) => `
            <span class="pantry-summary-badge">${formatPantryAmount(amount)} ${unit}</span>
        `)
        .join('');

    return `
        <div class="pantry-summary-badges">
            <span class="pantry-summary-badge pantry-summary-badge-strong">${summary.rowCount} poster</span>
            <span class="pantry-summary-badge">${summary.uniqueIngredients} ingredienser</span>
            ${totals}
        </div>
    `;
}

function getLowStockItems(items) {
    return items.filter((item) => {
        const unit = (item.unit || '').trim().toLowerCase();
        const threshold = LOW_STOCK_THRESHOLDS[unit] ?? 1;
        return Number(item.amount || 0) <= threshold;
    });
}

function lowStockTemplate(items, compact = false) {
    if (!Array.isArray(items) || items.length === 0) {
        return '<p class="pantry-low-stock-empty">Inga varor har låg nivå just nu.</p>';
    }

    return `
        <div class="pantry-low-stock ${compact ? 'pantry-low-stock-compact' : ''}">
            <p class="pantry-low-stock-title">Lågt i lager</p>
            <ul class="pantry-low-stock-list">
                ${items.map((item) => `
                    <li>
                        <span>${item.name}</span>
                        <span>${formatPantryAmount(item.amount)} ${item.unit}</span>
                    </li>
                `).join('')}
            </ul>
        </div>
    `;
}

function renderCurrentPantrySummary(items) {
    const container = document.getElementById('pantryCurrentSummary');

    if (!Array.isArray(items) || items.length === 0) {
        container.innerHTML = '<p class="loading">Ingen sammanfattning ännu.</p>';
        return;
    }

    container.innerHTML = `
        ${pantrySummaryBadges(getPantrySummary(items))}
        ${lowStockTemplate(getLowStockItems(items), true)}
    `;
}

function pantryOverviewTemplate(locationName, items) {
    const summary = getPantrySummary(items);
    const lowStockItems = getLowStockItems(items);

    return `
        <section class="pantry-overview-card">
            <h3>${locationName}</h3>
            ${pantrySummaryBadges(summary)}
            ${lowStockTemplate(lowStockItems)}
            ${items.length === 0 ? '<p class="loading">Tomt skafferi.</p>' : `
                <ul class="pantry-overview-list">
                    ${items.map((item) => `
                        <li>
                            <span>${item.name}</span>
                            <span class="ingredient-amount">${formatPantryAmount(item.amount)} ${item.unit}</span>
                        </li>
                    `).join('')}
                </ul>
            `}
        </section>
    `;
}

async function loadPantryLocations(selectedLocationId = null) {
    try {
        const response = await fetch('/api/pantry-locations');
        const locations = await response.json();
        const select = document.getElementById('pantryLocationSelect');

        if (!Array.isArray(locations) || locations.length === 0) {
            select.innerHTML = '<option value="">Inga skafferier</option>';
            return;
        }

        select.innerHTML = locations.map((location) => `
            <option value="${location.id}">${location.name}</option>
        `).join('');

        select.value = String(selectedLocationId || locations[0].id);
    } catch (error) {
        console.error('Error loading pantry locations:', error);
        showPantryMessage('Kunde inte ladda skafferier.', true);
    }
}

async function loadPantryItems() {
    try {
        const pantryLocationId = getSelectedPantryLocationId();
        const response = await fetch(`/api/pantry?pantry_location_id=${pantryLocationId}`);
        const items = await response.json();
        const container = document.getElementById('pantryItems');

        if (!Array.isArray(items) || items.length === 0) {
            container.innerHTML = '<p class="loading">Skafferiet är tomt. Lägg till din första ingrediens ovan.</p>';
            renderCurrentPantrySummary([]);
            return;
        }

        container.innerHTML = items.map(pantryCardTemplate).join('');
        renderCurrentPantrySummary(items);
    } catch (error) {
        console.error('Error loading pantry items:', error);
        document.getElementById('pantryItems').innerHTML = '<p class="loading">Kunde inte ladda skafferiet.</p>';
        document.getElementById('pantryCurrentSummary').innerHTML = '<p class="loading">Kunde inte ladda sammanfattningen.</p>';
    }
}

async function loadPantryOverview() {
    try {
        const response = await fetch('/api/pantry');
        const items = await response.json();
        const container = document.getElementById('pantryOverview');

        if (!Array.isArray(items) || items.length === 0) {
            container.innerHTML = '<p class="loading">Inga skafferivaror ännu.</p>';
            return;
        }

        const grouped = items.reduce((accumulator, item) => {
            const key = item.pantry_location_name || 'Okänt skafferi';
            if (!accumulator[key]) {
                accumulator[key] = [];
            }
            accumulator[key].push(item);
            return accumulator;
        }, {});

        container.innerHTML = Object.entries(grouped)
            .sort(([left], [right]) => left.localeCompare(right, 'sv'))
            .map(([locationName, locationItems]) => pantryOverviewTemplate(locationName, locationItems))
            .join('');
    } catch (error) {
        console.error('Error loading pantry overview:', error);
        document.getElementById('pantryOverview').innerHTML = '<p class="loading">Kunde inte ladda översikten.</p>';
    }
}

async function addPantryItem(event) {
    event.preventDefault();

    const payload = {
        pantry_location_id: getSelectedPantryLocationId(),
        name: document.getElementById('pantryName').value.trim(),
        amount: parseFloat(document.getElementById('pantryAmount').value),
        unit: document.getElementById('pantryUnit').value.trim()
    };

    if (!payload.pantry_location_id || !payload.name || !Number.isFinite(payload.amount) || !payload.unit) {
        showPantryMessage('Fyll i ingrediens, mängd och enhet.', true);
        return;
    }

    try {
        const response = await fetch('/api/pantry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            showPantryMessage(data.error || 'Kunde inte spara varan.', true);
            return;
        }

        showPantryMessage('Ingrediens sparad i skafferiet.', false);
        resetPantryForm();
        loadPantryItems();
        loadPantryOverview();
    } catch (error) {
        console.error('Error saving pantry item:', error);
        showPantryMessage('Kunde inte spara varan.', true);
    }
}

async function addPantryLocation(event) {
    event.preventDefault();

    const name = document.getElementById('newPantryLocation').value.trim();
    if (!name) {
        showPantryMessage('Ange ett namn för skafferiet.', true);
        return;
    }

    try {
        const response = await fetch('/api/pantry-locations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });

        const data = await response.json();
        if (!response.ok) {
            showPantryMessage(data.error || 'Kunde inte skapa skafferiet.', true);
            return;
        }

        document.getElementById('pantryLocationForm').reset();
        showPantryMessage('Nytt skafferi skapat.', false);
        await loadPantryLocations(data.id);
        loadPantryItems();
        loadPantryOverview();
    } catch (error) {
        console.error('Error creating pantry location:', error);
        showPantryMessage('Kunde inte skapa skafferiet.', true);
    }
}

async function renamePantryLocation() {
    const pantryLocationId = getSelectedPantryLocationId();
    const select = document.getElementById('pantryLocationSelect');
    const currentName = select.options[select.selectedIndex]?.textContent || '';
    const newName = prompt('Nytt namn på skafferiet:', currentName);

    if (!newName || newName.trim() === '' || newName.trim() === currentName) {
        return;
    }

    try {
        const response = await fetch(`/api/pantry-locations/${pantryLocationId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newName.trim() })
        });

        const data = await response.json();
        if (!response.ok) {
            showPantryMessage(data.error || 'Kunde inte byta namn på skafferiet.', true);
            return;
        }

        showPantryMessage('Skafferiet bytte namn.', false);
        await loadPantryLocations(pantryLocationId);
        loadPantryOverview();
    } catch (error) {
        console.error('Error renaming pantry location:', error);
        showPantryMessage('Kunde inte byta namn på skafferiet.', true);
    }
}

async function deletePantryLocation() {
    const pantryLocationId = getSelectedPantryLocationId();
    const select = document.getElementById('pantryLocationSelect');
    const currentName = select.options[select.selectedIndex]?.textContent || 'detta skafferi';

    if (!confirm(`Vill du ta bort ${currentName}? Alla ingredienser i skafferiet tas också bort.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/pantry-locations/${pantryLocationId}`, {
            method: 'DELETE'
        });

        const data = await response.json();
        if (!response.ok) {
            showPantryMessage(data.error || 'Kunde inte ta bort skafferiet.', true);
            return;
        }

        showPantryMessage('Skafferiet togs bort.', false);
        await loadPantryLocations();
        loadPantryItems();
        loadPantryOverview();
    } catch (error) {
        console.error('Error deleting pantry location:', error);
        showPantryMessage('Kunde inte ta bort skafferiet.', true);
    }
}

async function savePantryEdit(form, itemId) {
    const payload = {
        name: form.elements.name.value.trim(),
        amount: parseFloat(form.elements.amount.value),
        unit: form.elements.unit.value.trim()
    };

    if (!payload.name || !Number.isFinite(payload.amount) || !payload.unit) {
        showPantryMessage('Fyll i ingrediens, mängd och enhet.', true);
        return;
    }

    const response = await fetch(`/api/pantry/${itemId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (!response.ok) {
        showPantryMessage(data.error || 'Kunde inte uppdatera varan.', true);
        return;
    }

    showPantryMessage('Skafferiet uppdaterat.', false);
    loadPantryItems();
    loadPantryOverview();
}

async function deletePantryItem(itemId) {
    if (!confirm('Vill du ta bort den här ingrediensen från skafferiet?')) {
        return;
    }

    const response = await fetch(`/api/pantry/${itemId}`, {
        method: 'DELETE'
    });

    if (!response.ok) {
        showPantryMessage('Kunde inte ta bort varan.', true);
        return;
    }

    showPantryMessage('Ingrediensen togs bort.', false);
    loadPantryItems();
    loadPantryOverview();
}

document.addEventListener('DOMContentLoaded', () => {
    loadPantryLocations().then(() => {
        loadPantryItems();
        loadPantryOverview();
    });

    document.getElementById('pantryForm').addEventListener('submit', addPantryItem);
    document.getElementById('pantryLocationForm').addEventListener('submit', addPantryLocation);
    document.getElementById('pantryLocationSelect').addEventListener('change', loadPantryItems);
    document.getElementById('pantryLocationSelect').addEventListener('change', loadPantryOverview);
    document.getElementById('reloadPantryBtn').addEventListener('click', loadPantryItems);
    document.getElementById('reloadPantryBtn').addEventListener('click', loadPantryOverview);
    document.getElementById('renamePantryLocationBtn').addEventListener('click', renamePantryLocation);
    document.getElementById('deletePantryLocationBtn').addEventListener('click', deletePantryLocation);

    document.getElementById('pantryItems').addEventListener('click', (event) => {
        const card = event.target.closest('.pantry-card');
        if (!card) return;

        const form = card.querySelector('.pantry-edit-form');
        const itemId = card.dataset.itemId;

        if (event.target.classList.contains('pantry-edit-btn')) {
            form.hidden = false;
            return;
        }

        if (event.target.classList.contains('pantry-cancel-btn')) {
            form.hidden = true;
            return;
        }

        if (event.target.classList.contains('pantry-delete-btn')) {
            deletePantryItem(itemId);
        }
    });

    document.getElementById('pantryItems').addEventListener('submit', (event) => {
        if (!event.target.classList.contains('pantry-edit-form')) return;
        event.preventDefault();
        const card = event.target.closest('.pantry-card');
        savePantryEdit(event.target, card.dataset.itemId);
    });
});
