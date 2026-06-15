// Load menus on page load
document.addEventListener('DOMContentLoaded', () => {
    loadMenus();
    
    // Handle form submission
    document.getElementById('createMenuForm').addEventListener('submit', createMenu);
});

// Load all menus
async function loadMenus() {
    try {
        const response = await fetch('/api/menus');
        const menus = await response.json();
        displayMenus(menus);
    } catch (error) {
        console.error('Error loading menus:', error);
        document.getElementById('menusGrid').innerHTML = 
            '<p class="loading">Kunde inte ladda matsedlar.</p>';
    }
}

// Display menus in grid
function displayMenus(menus) {
    const grid = document.getElementById('menusGrid');
    
    if (menus.length === 0) {
        grid.innerHTML = '<p class="loading">Inga matsedlar än. Skapa din första ovan!</p>';
        return;
    }
    
    grid.innerHTML = menus.map(menu => `
        <article class="menu-card" onclick="window.location.href='/menu/${menu.id}'">
            <div class="menu-card-icon">📋</div>
            <div class="menu-card-info">
                <h3>${menu.name}</h3>
                <div class="menu-card-meta">
                    <span>📅 ${menu.num_days} dagar</span>
                    <span>👥 ${menu.servings} portioner</span>
                </div>
                <p class="menu-card-date">Skapad: ${formatDate(menu.created_at)}</p>
            </div>
            <button class="delete-btn" onclick="event.stopPropagation(); deleteMenu(${menu.id})">🗑️</button>
        </article>
    `).join('');
}

// Create new menu
async function createMenu(e) {
    e.preventDefault();
    
    const name = document.getElementById('menuName').value.trim();
    const numDays = parseInt(document.getElementById('numDays').value);
    const servings = parseInt(document.getElementById('servings').value);
    
    if (!name || numDays < 1) {
        alert('Fyll i alla fält korrekt');
        return;
    }
    
    try {
        const response = await fetch('/api/menus', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, num_days: numDays, servings })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Redirect to the new menu
            window.location.href = `/menu/${data.id}`;
        } else {
            alert(data.error || 'Kunde inte skapa matsedel');
        }
    } catch (error) {
        console.error('Error creating menu:', error);
        alert('Kunde inte skapa matsedel');
    }
}

// Delete menu
async function deleteMenu(menuId) {
    if (!confirm('Är du säker på att du vill ta bort denna matsedel?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/menus/${menuId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadMenus();
        } else {
            alert('Kunde inte ta bort matsedel');
        }
    } catch (error) {
        console.error('Error deleting menu:', error);
        alert('Kunde inte ta bort matsedel');
    }
}

// Format date
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('sv-SE');
}
