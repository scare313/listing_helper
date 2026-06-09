/* =============================================================
   Listing Helper — Single-Page Application Logic
   ============================================================= */

// ----- Constants & State -----
const API_BASE = '/api';

let currentPage = 'dashboard';
let products = [];

// Wizard State
let wizardStep = 1;
let wizardProduct = null;
let wizardVariations = [];
let activePreviewMarketplace = 'all';

// Step 3 Variation Tab State
let wizardStep3ActiveTab = 'base';
let wizardStep3Data = {
  base: {
    amazon_title: '',
    amazon_bullets: '',
    amazon_desc: '',
    flipkart_title: '',
    flipkart_features: '',
    flipkart_desc: '',
    meesho_title: '',
    meesho_desc: ''
  },
  variations: {}
};


// =============================================================
// Core Utilities
// =============================================================

/**
 * Fetch wrapper with JSON parsing and error handling.
 * @param {string} endpoint - API endpoint (relative to API_BASE)
 * @param {string} [method='GET'] - HTTP method
 * @param {object|null} [body=null] - Request body (will be JSON-stringified)
 * @returns {Promise<object>} Parsed JSON response
 */
async function api(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body && method !== 'GET') {
    options.body = JSON.stringify(body);
  }
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Request failed (${response.status})`);
    }
    // Handle 204 No Content
    if (response.status === 204) return null;
    return await response.json();
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Network error — is the server running?');
    }
    throw err;
  }
}

/**
 * Show a toast notification.
 * @param {string} message - Toast message text
 * @param {'success'|'error'|'warning'|'info'} [type='info'] - Toast type
 */
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <span>${escapeHtml(message)}</span>
  `;
  container.appendChild(toast);

  // Auto-remove after animation completes
  setTimeout(() => toast.remove(), 3000);
}

/**
 * Escape HTML entities for safe insertion.
 * @param {string} str - Raw string
 * @returns {string} Escaped string
 */
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Show shimmer loading skeleton inside a container.
 * @param {string} containerId - Target container element ID
 */
function showLoading(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = `
    <div class="loading-container">
      <div class="shimmer-card">
        <div class="shimmer-line h-lg w-50"></div>
        <div class="shimmer-line w-75"></div>
        <div class="shimmer-line w-50"></div>
      </div>
      <div class="shimmer-card">
        <div class="shimmer-line h-lg w-25"></div>
        <div class="shimmer-line"></div>
        <div class="shimmer-line w-75"></div>
        <div class="shimmer-line w-50"></div>
      </div>
      <div class="shimmer-card">
        <div class="shimmer-line h-lg w-50"></div>
        <div class="shimmer-line w-25"></div>
      </div>
    </div>
  `;
}


// =============================================================
// SPA Navigation
// =============================================================

/**
 * Navigate to a page, update sidebar & title, render content.
 * @param {string} page - Page key (e.g. 'dashboard', 'products')
 */
function navigateTo(page) {
  const validPages = ['dashboard', 'products', 'settings'];
  if (!validPages.includes(page)) {
    page = 'dashboard';
  }

  currentPage = page;

  // Update sidebar active state
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.page === page);
  });

  // Update page title
  const titles = {
    dashboard: 'Dashboard',
    products: 'Products',
    settings: 'Settings',
  };
  document.getElementById('page-title').textContent = titles[page] || 'Dashboard';

  // Show/hide Add Product button (only on dashboard & products)
  const addBtn = document.getElementById('btn-add-product');
  addBtn.style.display = ['dashboard', 'products'].includes(page) ? '' : 'none';

  // Render page content
  const renderers = {
    dashboard: renderDashboard,
    products: renderProducts,
    settings: renderSettings,
  };

  const renderer = renderers[page];
  if (renderer) {
    renderer();
  }

  // Close mobile sidebar
  closeMobileSidebar();
}


// =============================================================
// Page Renderers
// =============================================================

/**
 * Render the Dashboard page with stat cards and the workflow Kanban board.
 */
async function renderDashboard() {
  const area = document.getElementById('content-area');
  showLoading('content-area');

  let stats = { total: 0, amazon: 0, flipkart: 0, meesho: 0 };
  let allProducts = [];

  try {
    // Attempt to fetch stats overview
    const statsRes = await api('/products/stats/overview');
    if (statsRes && statsRes.data) {
      const s = statsRes.data;
      stats.total = s.total_products || 0;
      stats.amazon = Object.values(s.marketplaces?.amazon || {}).reduce((a, b) => a + b, 0) - (s.marketplaces?.amazon?.draft || 0);
      stats.flipkart = Object.values(s.marketplaces?.flipkart || {}).reduce((a, b) => a + b, 0) - (s.marketplaces?.flipkart?.draft || 0);
      stats.meesho = Object.values(s.marketplaces?.meesho || {}).reduce((a, b) => a + b, 0) - (s.marketplaces?.meesho?.draft || 0);
    }
  } catch { /* ignore and use list-based values */ }

  try {
    const res = await api('/products');
    allProducts = res?.data?.products || res?.data || [];
    
    if (stats.total === 0) {
      stats.total = allProducts.length;
      stats.amazon = allProducts.filter(p => p.amazon_status === 'listed').length;
      stats.flipkart = allProducts.filter(p => p.flipkart_status === 'listed').length;
      stats.meesho = allProducts.filter(p => p.meesho_status === 'listed').length;
    }
  } catch (err) {
    showToast('Failed to load products list: ' + err.message, 'error');
  }

  area.innerHTML = `
    <!-- Stat Cards -->
    <div class="stat-cards">
      <div class="stat-card accent-primary animate-in" onclick="openProductWizard()" style="cursor:pointer;">
        <span class="stat-icon">📦</span>
        <div class="stat-value" data-count="${stats.total}">0</div>
        <div class="stat-label">Total Products</div>
        <div class="stat-card-cta">＋ Add</div>
      </div>
      <div class="stat-card accent-amazon animate-in">
        <span class="stat-icon">🛒</span>
        <div class="stat-value" data-count="${stats.amazon}">0</div>
        <div class="stat-label">Amazon Listed</div>
      </div>
      <div class="stat-card accent-flipkart animate-in">
        <span class="stat-icon">🛍️</span>
        <div class="stat-value" data-count="${stats.flipkart}">0</div>
        <div class="stat-label">Flipkart Listed</div>
      </div>
      <div class="stat-card accent-meesho animate-in">
        <span class="stat-icon">🏪</span>
        <div class="stat-value" data-count="${stats.meesho}">0</div>
        <div class="stat-label">Meesho Listed</div>
      </div>
    </div>

    <!-- Kanban Board OR Empty State Hero -->
    ${allProducts.length > 0 ? renderKanbanBoard(allProducts) : `
      <div class="empty-state animate-in" style="margin-top: 40px; padding: 60px 20px; text-align: center;">
        <span class="empty-icon" style="font-size: 64px; display: block; margin-bottom: 20px;">📦</span>
        <h3 style="font-size: 20px; font-weight: 700; color: #fff; margin-bottom: 8px;">No products yet</h3>
        <p style="color: var(--text-secondary); max-width: 440px; margin: 0 auto 24px; font-size: 14px; line-height: 1.6;">
          Get started by adding your first product using our step-by-step wizard.
        </p>
        <button class="btn btn-primary btn-pulse" onclick="openProductWizard()">
          <span class="btn-icon">+</span> Open Onboarding Wizard
        </button>
      </div>
    `}
  `;

  // Animate counter numbers
  animateCounters();
}

/**
 * Animate stat card numbers counting up from 0.
 */
function animateCounters() {
  document.querySelectorAll('.stat-value[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count, 10) || 0;
    if (target === 0) { el.textContent = '0'; return; }

    const duration = 800;
    const startTime = performance.now();

    function tick(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(eased * target).toLocaleString('en-IN');
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
}


/**
 * Render the Products page with search, filters, and full product table.
 */
async function renderProducts() {
  const area = document.getElementById('content-area');
  showLoading('content-area');

  try {
    const data = await api('/products');
    products = data?.data?.products || data?.data || [];
  } catch (err) {
    products = [];
    showToast('Failed to load products: ' + err.message, 'error');
  }

  area.innerHTML = `
    <!-- Filters -->
    <div class="filters-row">
      <div class="search-bar">
        <span class="search-icon">🔍</span>
        <input type="text" id="search-input" placeholder="Search by name, SKU, or brand..." oninput="filterProducts()">
      </div>
      <select class="filter-select" id="filter-category" onchange="filterProducts()">
        <option value="">All Categories</option>
        <option value="baseball_caps">Baseball Caps</option>
        <option value="home_kitchen_general">Home & Kitchen</option>
        <option value="kitchen_storage">Kitchen Storage</option>
        <option value="kitchen_tools">Kitchen Tools</option>
        <option value="home_decor">Home Decor</option>
        <option value="cleaning_supplies">Cleaning Supplies</option>
      </select>
      <select class="filter-select" id="filter-status" onchange="filterProducts()">
        <option value="">All Statuses</option>
        <option value="new">New</option>
        <option value="keywords_done">Keywords Done</option>
        <option value="content_ready">Content Ready</option>
        <option value="priced">Priced</option>
        <option value="exported">Exported</option>
        <option value="listed">Listed</option>
      </select>
    </div>

    <!-- Products Table -->
    <div id="products-table-wrapper">
      ${products.length > 0 ? renderProductsTable(products, false) : `
        <div class="empty-state">
          <span class="empty-icon">🏷️</span>
          <h3>No products found</h3>
          <p>Add your first product to get started with creating marketplace listings.</p>
          <button class="btn btn-primary btn-pulse" onclick="openProductWizard()">
            <span class="btn-icon">+</span> Add Product
          </button>
        </div>
      `}
    </div>
  `;
}

/**
 * Filter and re-render the products table based on search and filter values.
 */
function filterProducts() {
  const query = (document.getElementById('search-input')?.value || '').toLowerCase();
  const catFilter = document.getElementById('filter-category')?.value || '';
  const statusFilter = document.getElementById('filter-status')?.value || '';

  let filtered = products;

  if (query) {
    filtered = filtered.filter(p =>
      (p.name || '').toLowerCase().includes(query) ||
      (p.sku || '').toLowerCase().includes(query) ||
      (p.brand || '').toLowerCase().includes(query)
    );
  }

  if (catFilter) {
    filtered = filtered.filter(p => {
      if (catFilter === 'home_kitchen_general') {
        return p.category === 'home_kitchen_general' || p.category === 'home_kitchen';
      }
      return p.category === catFilter;
    });
  }

  if (statusFilter) {
    filtered = filtered.filter(p => (p.listing_status || 'new') === statusFilter);
  }

  const wrapper = document.getElementById('products-table-wrapper');
  if (!wrapper) return;

  if (filtered.length > 0) {
    wrapper.innerHTML = renderProductsTable(filtered, false);
  } else {
    wrapper.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">🔍</span>
        <h3>No matching products</h3>
        <p>Try adjusting your search or filters to find what you're looking for.</p>
      </div>
    `;
  }
}

/**
 * Generate HTML for a products table.
 * @param {Array} productList - Array of product objects
 * @param {boolean} compact - If true, show fewer columns (for dashboard)
 * @returns {string} HTML string
 */
function renderProductsTable(productList, compact) {
  const rows = productList.map(p => {
    const amazonBadge = statusBadge(p.amazon_status || 'draft');
    const flipkartBadge = statusBadge(p.flipkart_status || 'draft');
    const meeshoBadge = statusBadge(p.meesho_status || 'draft');
    const categoryLabel = formatCategory(p.category);
    const cost = p.cost_price != null ? `₹${Number(p.cost_price).toLocaleString('en-IN')}` : '—';

    if (compact) {
      return `
        <tr>
          <td style="color:var(--text-primary);font-weight:500">${escapeHtml(p.sku || '—')}</td>
          <td style="color:var(--text-primary)">${escapeHtml(p.name || '—')}</td>
          <td>${categoryLabel}</td>
          <td>${amazonBadge}</td>
          <td>${flipkartBadge}</td>
          <td>${meeshoBadge}</td>
        </tr>
      `;
    }

    return `
      <tr>
        <td style="color:var(--text-primary);font-weight:500">${escapeHtml(p.sku || '—')}</td>
        <td style="color:var(--text-primary)">${escapeHtml(p.name || '—')}</td>
        <td>${categoryLabel}</td>
        <td>${amazonBadge}</td>
        <td>${flipkartBadge}</td>
        <td>${meeshoBadge}</td>
        <td>${cost}</td>
        <td>
          <div class="row-actions">
            <button title="Wizard" onclick="openProductWizard(${p.id})">🧙‍♂️</button>
            <button title="Edit" onclick="openProductWizard(${p.id})">✏️</button>
            <button title="Delete" class="action-delete" onclick="confirmDeleteProduct(${p.id}, '${escapeHtml(p.name || p.sku || '')}')">🗑️</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  return `
    <div class="table-container">
      ${compact ? `<div class="table-header"><h3>Recent Products</h3></div>` : ''}
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Product Name</th>
              <th>Category</th>
              <th>Amazon</th>
              <th>Flipkart</th>
              <th>Meesho</th>
              ${compact ? '' : '<th>Cost</th><th>Actions</th>'}
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}

/**
 * Return a status badge HTML string.
 * @param {string} status - 'draft', 'ready', 'listed', or 'error'
 * @returns {string} HTML
 */
function statusBadge(status) {
  const labels = { draft: 'Draft', ready: 'Ready', listed: 'Listed', error: 'Error' };
  const safeStatus = ['draft', 'ready', 'listed', 'error'].includes(status) ? status : 'draft';
  return `<span class="status-badge status-${safeStatus}">${labels[safeStatus]}</span>`;
}

/**
 * Format category key to a human-readable label.
 * @param {string} cat - Category key
 * @returns {string} Formatted label
 */
function formatCategory(cat) {
  const map = {
    baseball_caps: 'Baseball Caps',
    home_kitchen: 'Home & Kitchen',
    home_kitchen_general: 'Home & Kitchen',
    kitchen_storage: 'Kitchen Storage',
    kitchen_tools: 'Kitchen Tools',
    home_decor: 'Home Decor',
    cleaning_supplies: 'Cleaning Supplies'
  };
  return map[cat] || cat || '—';
}


/** Toggle selection state of keyword pills */
function toggleKwPill(pill) {
  const isSelected = pill.classList.toggle('selected');
  const chk = pill.querySelector('.chk');
  if (chk) {
    chk.textContent = isSelected ? '✓' : '';
  }
}


async function renderSettings() {
  const area = document.getElementById('content-area');
  showLoading('content-area');

  let dbSettings = {};
  try {
    const res = await api('/settings');
    dbSettings = res?.data || {};
  } catch (err) {
    showToast('Failed to load settings from server: ' + err.message, 'error');
  }

  area.innerHTML = `
    <div class="settings-grid" style="animation: fadeIn 0.4s ease">
      <!-- Gemini API Key -->
      <div class="settings-card">
        <h4>🤖 Gemini AI API Key</h4>
        <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px">
          Used for AI-powered content generation, keyword suggestions, and image analysis.
        </p>
        <div class="form-group" style="margin-bottom:12px">
          <label for="s-gemini-key">API Key</label>
          <input type="password" id="s-gemini-key" value="${escapeHtml(dbSettings.gemini_api_key || '')}" placeholder="AIzaSy...">
        </div>
        <button class="btn btn-ghost btn-sm" onclick="testGeminiApiKey()">Test Key Connection</button>
      </div>

      <!-- Scraper Settings -->
      <div class="settings-card">
        <h4>🔍 Amazon Crawler Settings</h4>
        <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px">
          Configure delays and browser visibility for Selenium scraping.
        </p>
        <div class="form-grid">
          <div class="form-group">
            <label for="s-headless">Headless Browser</label>
            <select id="s-headless">
              <option value="true" ${dbSettings.headless_browser === 'True' || dbSettings.headless_browser === 'true' ? 'selected' : ''}>Enabled (Hidden)</option>
              <option value="false" ${dbSettings.headless_browser === 'False' || dbSettings.headless_browser === 'false' ? 'selected' : ''}>Disabled (Visible)</option>
            </select>
          </div>
          <div class="form-group">
            <label for="s-min-delay">Min Delay (s)</label>
            <input type="number" id="s-min-delay" value="${dbSettings.scraper_min_delay || '2'}" min="0.5" step="0.5">
          </div>
        </div>
      </div>

      <!-- General Defaults -->
      <div class="settings-card">
        <h4>⚙️ General Onboarding Defaults</h4>
        <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px">
          Default parameters for pricing calculators and listings.
        </p>
        <div class="form-grid">
          <div class="form-group">
            <label for="s-margin">Default Margin (%)</label>
            <input type="number" id="s-margin" value="${dbSettings.default_margin || '25'}" min="1" max="95">
          </div>
          <div class="form-group">
            <label for="s-brand">Default Brand</label>
            <input type="text" id="s-brand" value="${escapeHtml(dbSettings.default_brand || '')}" placeholder="e.g. Generic">
          </div>
        </div>
      </div>
    </div>

    <div style="margin-top:24px;display:flex;gap:12px">
      <button class="btn btn-primary" onclick="saveDbSettings()">Save Configurations</button>
    </div>
  `;
}

async function saveDbSettings() {
  const gemini = document.getElementById('s-gemini-key').value.trim();
  const headless = document.getElementById('s-headless').value;
  const minDelay = document.getElementById('s-min-delay').value;
  const margin = document.getElementById('s-margin').value;
  const brand = document.getElementById('s-brand').value.trim();

  try {
    await api(`/settings/gemini_api_key?value=${encodeURIComponent(gemini)}`, 'PUT');
    await api(`/settings/headless_browser?value=${encodeURIComponent(headless)}`, 'PUT');
    await api(`/settings/scraper_min_delay?value=${encodeURIComponent(minDelay)}`, 'PUT');
    await api(`/settings/default_margin?value=${encodeURIComponent(margin)}`, 'PUT');
    await api(`/settings/default_brand?value=${encodeURIComponent(brand)}`, 'PUT');

    showToast('Configurations successfully saved to server!', 'success');
  } catch (err) {
    showToast('Failed to save configurations: ' + err.message, 'error');
  }
}

async function testGeminiApiKey() {
  const key = document.getElementById('s-gemini-key').value.trim();
  showToast('Testing Gemini connectivity...', 'info');

  try {
    const res = await api(`/settings/test-gemini?api_key=${encodeURIComponent(key)}`, 'POST');
    showToast('Gemini API connection test successful! Response: ' + res.data.response, 'success');
  } catch (err) {
    showToast('Gemini connection failed: ' + err.message, 'error');
  }
}


function confirmDeleteProduct(productId, productName) {
  document.getElementById('delete-product-name').textContent = productName || `Product #${productId}`;
  document.getElementById('btn-confirm-delete').onclick = () => deleteProduct(productId);
  openModal('delete-modal');
}

/**
 * Delete a product.
 * @param {number} productId - Product ID to delete
 */
async function deleteProduct(productId) {
  try {
    await api(`/products/${productId}`, 'DELETE');
    showToast('Product deleted', 'success');
    closeDeleteModal();
    if (currentPage === 'products') renderProducts();
    else if (currentPage === 'dashboard') renderDashboard();
  } catch (err) {
    showToast('Delete failed: ' + err.message, 'error');
  }
}


// =============================================================
// Form Helpers
// =============================================================

function openModal(modalId) {
  const overlay = document.getElementById(modalId);
  if (overlay) {
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}



function closeDeleteModal() {
  const overlay = document.getElementById('delete-modal');
  if (overlay) {
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }
}


// =============================================================
// Mobile Sidebar
// =============================================================

function toggleMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  sidebar.classList.toggle('open');
  overlay.classList.toggle('active');
}

function closeMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (sidebar) sidebar.classList.remove('open');
  if (overlay) overlay.classList.remove('active');
}


// =============================================================
// Initialization
// =============================================================

document.addEventListener('DOMContentLoaded', () => {
  // Sidebar navigation click handlers
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const page = item.dataset.page;
      if (page) navigateTo(page);
    });
  });

  // Mobile hamburger
  const hamburger = document.getElementById('hamburger');
  if (hamburger) {
    hamburger.addEventListener('click', toggleMobileSidebar);
  }

  // Mobile overlay click to close
  const overlay = document.getElementById('sidebar-overlay');
  if (overlay) {
    overlay.addEventListener('click', closeMobileSidebar);
  }

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeDeleteModal();
      closeMobileSidebar();
      closeWizard();
    }
  });

  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = '';
      }
    });
  });

  // Render the default page
  navigateTo('dashboard');

  // Setup dropzone for wizard image scan
  setupWizardDropzone();
});


// =============================================================
// Product Onboarding Wizard Logic (Phase 5)
// =============================================================

/**
 * Open the Product Onboarding Wizard.
 * Resets or loads existing product details.
 * @param {object|number|null} [productOrId=null] - Product object or ID
 */
async function openProductWizard(productOrId = null) {
  wizardStep = 1;
  wizardProduct = null;
  
  // Reset Step 1 dropzone and inputs
  const fileInput = document.getElementById('w-file-input');
  if (fileInput) fileInput.value = '';
  document.getElementById('w-scan-status').innerHTML = '';
  const detectedAttrs = document.getElementById('w-detected-attrs');
  if (detectedAttrs) {
    detectedAttrs.innerHTML = '';
    detectedAttrs.style.display = 'none';
  }

  // Always reset variations state
  wizardVariations = [];
  const varList = document.getElementById('w-variations-list');
  if (varList) varList.innerHTML = '';

  // Reset Step 5 state
  activePreviewMarketplace = 'all';
  ['w-ptab-all', 'w-ptab-amazon', 'w-ptab-flipkart', 'w-ptab-meesho'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.classList.toggle('active', id === 'w-ptab-all');
  });
  ['w-listed-amazon', 'w-listed-flipkart', 'w-listed-meesho'].forEach(id => {
    const cb = document.getElementById(id);
    if (cb) cb.checked = false;
  });

  if (productOrId) {
    let product = productOrId;
    let existingVariations = [];
    if (typeof productOrId === 'number' || typeof productOrId === 'string') {
      try {
        const res = await api(`/products/${productOrId}`);
        product = res.data?.product || res.product || res;
        existingVariations = res.data?.variations || [];
      } catch (err) {
        showToast("Failed to load product for wizard: " + err.message, "error");
        return;
      }
    }

    wizardProduct = product;

    // Populate Step 1 fields
    document.getElementById('w-sku').value = product.sku || '';
    document.getElementById('w-name').value = product.name || '';
    document.getElementById('w-brand').value = product.brand || '';
    document.getElementById('w-category').value = product.category || '';
    document.getElementById('w-subcategory').value = product.subcategory || '';
    document.getElementById('w-cost').value = product.cost_price != null ? product.cost_price : '';
    document.getElementById('w-weight').value = product.weight_grams != null ? product.weight_grams : '';
    document.getElementById('w-hsn').value = product.hsn_code || '';

    // Pre-populate existing variations
    existingVariations.forEach(v => {
      addWizardVariation(v.variation_type, v.variation_value, v.sku, v.id);
    });
    wizardVariations = existingVariations;

    // Pre-populate Step 2 seed keyword
    document.getElementById('w-keyword-seed').value = product.name || '';
    document.getElementById('w-keyword-progress').style.display = 'none';

    // Render existing keywords if available
    if (product.keywords_data && product.keywords_data.applied_keywords) {
      renderWizardKeywordResults({
        primary: product.keywords_data.applied_keywords.slice(0, 10),
        secondary: product.keywords_data.applied_keywords.slice(10)
      });
    } else {
      document.getElementById('w-keyword-results').style.display = 'none';
      document.getElementById('w-pills-primary').innerHTML = '';
      document.getElementById('w-pills-secondary').innerHTML = '';
    }
  } else {
    // Reset all fields for new product onboarding
    document.getElementById('w-sku').value = '';
    document.getElementById('w-name').value = '';
    document.getElementById('w-brand').value = '';
    document.getElementById('w-category').value = '';
    document.getElementById('w-subcategory').value = '';
    document.getElementById('w-cost').value = '';
    document.getElementById('w-weight').value = '';
    document.getElementById('w-hsn').value = '';

    document.getElementById('w-keyword-seed').value = '';
    document.getElementById('w-keyword-progress').style.display = 'none';
    document.getElementById('w-keyword-results').style.display = 'none';
    document.getElementById('w-pills-primary').innerHTML = '';
    document.getElementById('w-pills-secondary').innerHTML = '';
  }
  
  openModal('wizard-modal');
  goToWizardStep(1);
}

/**
 * Close the onboarding wizard.
 */
function closeWizard() {
  const overlay = document.getElementById('wizard-modal');
  if (overlay) {
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }
  // Refresh page list
  if (currentPage === 'dashboard') {
    renderDashboard();
  } else if (currentPage === 'products') {
    renderProducts();
  }
}

/**
 * Navigate to a specific step in the wizard.
 * @param {number} step - Step index (1-5)
 */
function goToWizardStep(step) {
  if (step > 1 && !wizardProduct) {
    showToast("Please save specifications in Step 1 first!", "warning");
    return;
  }
  
  wizardStep = step;
  
  // Update wizard headers
  for (let i = 1; i <= 5; i++) {
    const stepEl = document.getElementById(`wstep-${i}`);
    if (stepEl) {
      stepEl.classList.toggle('active', i === step);
      stepEl.classList.toggle('completed', i < step);
    }
    
    const contentEl = document.getElementById(`wcontent-${i}`);
    if (contentEl) {
      contentEl.classList.toggle('active', i === step);
    }
  }
  
  // Footer navigation actions
  const btnPrev = document.getElementById('w-btn-prev');
  const btnNext = document.getElementById('w-btn-next');
  
  if (btnPrev) {
    btnPrev.style.display = step === 1 ? 'none' : 'inline-flex';
  }
  
  if (btnNext) {
    if (step === 5) {
      btnNext.textContent = 'Export & Close';
    } else {
      btnNext.textContent = 'Next';
    }
  }
  
  // Load step-specific contents
  if (step === 2) {
    const seedInput = document.getElementById('w-keyword-seed');
    if (seedInput && !seedInput.value && wizardProduct) {
      seedInput.value = wizardProduct.name || '';
    }
  } else if (step === 3) {
    attachWizardStep3Counters();
    loadWizardStep3Content();
  } else if (step === 4) {
    const marginInput = document.getElementById('w-pricing-margin');
    if (marginInput && !marginInput.value) {
      marginInput.value = '25';
    }
    calculateWizardPricing();
  } else if (step === 5) {
    // Ensure the active tab button matches current state when re-entering step 5
    ['w-ptab-all', 'w-ptab-amazon', 'w-ptab-flipkart', 'w-ptab-meesho'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.classList.toggle('active', id === `w-ptab-${activePreviewMarketplace}`);
    });
    loadWizardStep5Preview();
  }
}

/**
 * Handle Next button click in the wizard.
 */
async function nextWizardStep() {
  if (wizardStep === 1) {
    const success = await saveWizardStep1();
    if (!success) return;
    goToWizardStep(2);
  } else if (wizardStep === 2) {
    const success = await saveWizardStep2();
    if (!success) return;
    goToWizardStep(3);
  } else if (wizardStep === 3) {
    const success = await saveWizardStep3();
    if (!success) return;
    goToWizardStep(4);
  } else if (wizardStep === 4) {
    const success = await saveWizardStep4();
    if (!success) return;
    goToWizardStep(5);
  } else if (wizardStep === 5) {
    await finishWizard();
  }
}

/**
 * Handle Back button click in the wizard.
 */
function prevWizardStep() {
  if (wizardStep > 1) {
    goToWizardStep(wizardStep - 1);
  }
}

// ----- Step 1: Specs and Image Scan -----

/**
 * Initialize drag-and-drop listener for the wizard dropzone.
 */
function setupWizardDropzone() {
  const dropzone = document.getElementById('w-dropzone');
  const fileInput = document.getElementById('w-file-input');
  
  if (!dropzone || !fileInput) return;
  
  dropzone.addEventListener('click', () => fileInput.click());
  
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleWizardImageUpload(e.target.files[0]);
    }
  });
  
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  
  ['dragleave', 'dragend'].forEach(eventName => {
    dropzone.addEventListener(eventName, () => dropzone.classList.remove('dragover'));
  });
  
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleWizardImageUpload(e.dataTransfer.files[0]);
    }
  });
}

/**
 * Upload image and fill specifications automatically.
 * @param {File} file - Product image file
 */
async function handleWizardImageUpload(file) {
  const scanStatus = document.getElementById('w-scan-status');
  const detectedAttrs = document.getElementById('w-detected-attrs');
  
  if (!scanStatus || !detectedAttrs) return;
  
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    showToast("Unsupported file type. JPEG, PNG, or WebP only.", "warning");
    return;
  }
  
  if (file.size > 10 * 1024 * 1024) {
    showToast("File size too large (max 10MB).", "warning");
    return;
  }
  
  scanStatus.innerHTML = `<span class="spinner" style="width:20px;height:20px;margin:5px auto;border-width:2px;"></span> Analyzing with Gemini Vision...`;
  detectedAttrs.style.display = 'none';
  detectedAttrs.innerHTML = '';
  
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/vision/detect', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Scan failed (${response.status})`);
    }
    
    const result = await response.json();
    const data = result.data || {};
    
    scanStatus.innerHTML = `✅ Image analyzed successfully!`;
    showToast("Product attributes detected!", "success");
    
    // Prefill SKU
    const catPrefix = (data.category || 'PROD').substring(0, 3).toUpperCase();
    const randomNum = Math.floor(100 + Math.random() * 900);
    document.getElementById('w-sku').value = `${catPrefix}-${randomNum}`;
    
    document.getElementById('w-name').value = data.suggested_name || '';
    document.getElementById('w-brand').value = data.brand || 'Generic';
    
    // Match Category dropdown
    const catSelect = document.getElementById('w-category');
    if (catSelect) {
      let matched = false;
      const detectedCat = (data.category || '').toLowerCase();
      for (let i = 0; i < catSelect.options.length; i++) {
        const optVal = catSelect.options[i].value;
        if (optVal && (optVal.includes(detectedCat) || detectedCat.includes(optVal))) {
          catSelect.selectedIndex = i;
          matched = true;
          break;
        }
      }
      if (!matched && detectedCat.includes('cap')) {
        catSelect.value = 'baseball_caps';
      }
    }
    
    document.getElementById('w-subcategory').value = data.subcategory || '';

    // Auto-fill weight if Gemini returned a positive number
    if (typeof data.suggested_weight_grams === 'number' && data.suggested_weight_grams > 0) {
      document.getElementById('w-weight').value = Math.round(data.suggested_weight_grams);
    }

    // Auto-fill HSN code if Gemini returned a non-empty string (guard against literal "null")
    if (data.suggested_hsn_code && typeof data.suggested_hsn_code === 'string' && data.suggested_hsn_code !== 'null') {
      document.getElementById('w-hsn').value = data.suggested_hsn_code;
    }

    // Display detected attributes
    detectedAttrs.style.display = 'grid';
    let attrsHtml = '';
    const fields = [
      { label: 'Type', value: data.product_type },
      { label: 'Category', value: data.category },
      { label: 'Colors', value: Array.isArray(data.colors) ? data.colors.join(', ') : data.colors },
      { label: 'Material', value: data.material },
    ];
    fields.forEach(f => {
      if (f.value) {
        attrsHtml += `
          <div class="detected-attr-card">
            <span class="detected-attr-label">${f.label}</span>
            <span class="detected-attr-value">${escapeHtml(f.value)}</span>
          </div>
        `;
      }
    });
    detectedAttrs.innerHTML = attrsHtml;
    
  } catch (err) {
    scanStatus.innerHTML = `❌ Scan failed: ${escapeHtml(err.message)}`;
    showToast("Vision scan failed: " + err.message, "error");
  }
}

// ----- Step 1: Variation helpers -----

/**
 * Append a new variation row to #w-variations-list.
 * @param {string} varType - variation_type value
 * @param {string} varValue - variation_value value
 * @param {string} varSku - sku value
 * @param {string|number} varId - existing DB id, or '' for new rows
 * @returns {HTMLElement} the new row element
 */
function addWizardVariation(varType = '', varValue = '', varSku = '', varId = '') {
  const list = document.getElementById('w-variations-list');
  if (!list) return null;

  const row = document.createElement('div');
  row.className = 'w-var-row';
  row.dataset.varId = varId;
  row.innerHTML = `
    <select class="w-var-type" style="flex:0 0 120px;">
      <option value="Color"    ${varType === 'Color'    ? 'selected' : ''}>Color</option>
      <option value="Size"     ${varType === 'Size'     ? 'selected' : ''}>Size</option>
      <option value="Material" ${varType === 'Material' ? 'selected' : ''}>Material</option>
      <option value="Style"    ${varType === 'Style'    ? 'selected' : ''}>Style</option>
      <option value="Other"    ${varType === 'Other'    ? 'selected' : ''}>Other</option>
    </select>
    <input type="text" class="w-var-value" placeholder="e.g. Black, XL, Cotton" value="${escapeHtml(varValue)}" style="flex:1;">
    <input type="text" class="w-var-sku" placeholder="e.g. BC-BLK-001" value="${escapeHtml(varSku)}" style="flex:1;">
    <button type="button" class="btn-var-remove" onclick="removeWizardVariation(this.closest('.w-var-row'))" title="Remove variation">&times;</button>
  `;
  list.appendChild(row);
  return row;
}

/**
 * Remove a variation row from the DOM.
 * @param {HTMLElement} rowEl - the .w-var-row element to remove
 */
function removeWizardVariation(rowEl) {
  if (rowEl) rowEl.remove();
}

/**
 * Read all variation rows from #w-variations-list.
 * Skips rows where variation_value or sku is empty.
 * @returns {{var_id: string, variation_type: string, variation_value: string, sku: string}[]}
 */
function getWizardVariations() {
  const rows = document.querySelectorAll('#w-variations-list .w-var-row');
  const result = [];
  rows.forEach(row => {
    const variation_type  = row.querySelector('.w-var-type').value;
    const variation_value = row.querySelector('.w-var-value').value.trim();
    const sku             = row.querySelector('.w-var-sku').value.trim();
    const var_id          = row.dataset.varId || '';
    if (!variation_value || !sku) return;
    result.push({ var_id, variation_type, variation_value, sku });
  });
  return result;
}

/**
 * Save Step 1 specifications.
 */
async function saveWizardStep1() {
  const sku = document.getElementById('w-sku').value.trim();
  const name = document.getElementById('w-name').value.trim();
  const brand = document.getElementById('w-brand').value.trim() || null;
  const category = document.getElementById('w-category').value;
  const subcategory = document.getElementById('w-subcategory').value.trim() || null;
  const cost = parseFloat(document.getElementById('w-cost').value);
  const weight = parseInt(document.getElementById('w-weight').value, 10) || null;
  const hsn = document.getElementById('w-hsn').value.trim() || null;
  
  if (!sku) { showToast("SKU is required", "warning"); return false; }
  if (!name) { showToast("Product name is required", "warning"); return false; }
  if (!category) { showToast("Category is required", "warning"); return false; }
  if (isNaN(cost) || cost < 0) { showToast("Valid cost price is required", "warning"); return false; }
  
  const body = {
    sku,
    name,
    brand,
    category,
    subcategory,
    cost_price: cost,
    weight_grams: weight,
    hsn_code: hsn,
    gst_rate: 18.0,
    listing_status: 'new'
  };
  
  try {
    if (wizardProduct && wizardProduct.id) {
      await api(`/products/${wizardProduct.id}`, 'PUT', body);
      wizardProduct = { ...wizardProduct, ...body };
      showToast("Specs updated successfully", "success");
    } else {
      const res = await api('/products', 'POST', body);
      wizardProduct = res.data || res;
      showToast("Specs saved successfully", "success");
    }

    // Sync new variation rows (rows with no var_id are new)
    const varRows = document.querySelectorAll('#w-variations-list .w-var-row');
    for (const row of varRows) {
      if (row.dataset.varId) continue; // already saved
      const variation_type  = row.querySelector('.w-var-type').value;
      const variation_value = row.querySelector('.w-var-value').value.trim();
      const sku             = row.querySelector('.w-var-sku').value.trim();
      if (!variation_value || !sku) continue;
      try {
        const vRes = await api(`/products/${wizardProduct.id}/variations`, 'POST', {
          variation_type, variation_value, sku,
          additional_cost: 0, stock_quantity: 0,
        });
        const saved = vRes.data || {};
        row.dataset.varId = saved.id || '';
      } catch (vErr) {
        showToast(`Failed to save variation "${variation_value}": ${vErr.message}`, 'error');
      }
    }

    // Refresh wizardVariations from server so TASK-12 has current state
    const freshRes = await api(`/products/${wizardProduct.id}/variations`);
    wizardVariations = Array.isArray(freshRes?.data) ? freshRes.data : [];

    return true;
  } catch (err) {
    showToast("Failed to save product specs: " + err.message, "error");
    return false;
  }
}

// ----- Step 2: Keywords Crawl -----

/**
 * Start Amazon Autocomplete & competitor keyword scraping.
 */
async function startWizardKeywordResearch() {
  const seed = document.getElementById('w-keyword-seed').value.trim();
  if (!seed) {
    showToast("Please enter a seed keyword or URL first!", "warning");
    return;
  }
  
  const progressBox = document.getElementById('w-keyword-progress');
  const resultsContainer = document.getElementById('w-keyword-results');
  
  progressBox.style.display = 'block';
  resultsContainer.style.display = 'none';
  
  const progressStep = document.getElementById('w-progress-step');
  const progressPercent = document.getElementById('w-progress-percent');
  const progressBar = document.getElementById('w-progress-bar');
  const progressStatus = document.getElementById('w-progress-status');
  
  progressBar.style.width = '0%';
  progressPercent.textContent = '0%';
  progressStep.textContent = 'Initializing scraper...';
  progressStatus.textContent = '';
  
  const pid = wizardProduct ? wizardProduct.id : '';
  const url = `/api/keywords/research/stream?seed=${encodeURIComponent(seed)}&limit=25&product_id=${pid}&force_refresh=true`;
  
  const eventSource = new EventSource(url);
  
  eventSource.onmessage = function(e) {
    const data = JSON.parse(e.data);
    if (data.step === 'complete') {
      eventSource.close();
      progressBar.style.width = '100%';
      progressPercent.textContent = '100%';
      progressStep.textContent = 'Complete!';
      progressStatus.textContent += `[Complete] ${data.message}\n`;
      if (!data.results) {
        console.warn('[keyword-research] complete event missing results payload — ignoring');
        return;
      }
      showToast("Keyword research complete!", "success");
      renderWizardKeywordResults(data.results);
    } else if (data.step === 'error') {
      eventSource.close();
      progressStep.textContent = 'Error';
      progressStatus.textContent += `[Error] ${data.message}\n`;
      showToast("Keyword research failed: " + data.message, "error");
    } else {
      const steps = {
        'collecting_links': 10,
        'scraping_product': 50,
        'analyzing': 85,
        'autocomplete': 90
      };
      let displayPercent = steps[data.step] || 0;
      if (data.step === 'scraping_product' && data.total > 0) {
        displayPercent = 10 + Math.round((data.current / data.total) * 70);
      }
      progressBar.style.width = `${displayPercent}%`;
      progressPercent.textContent = `${displayPercent}%`;
      progressStep.textContent = data.step.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      progressStatus.textContent += `[${data.step}] ${data.message}\n`;
      progressStatus.scrollTop = progressStatus.scrollHeight;
    }
  };
  
  eventSource.onerror = function() {
    eventSource.close();
    progressStep.textContent = 'Connection Error';
    showToast("Connection error in keyword research", "error");
  };
}

/**
 * Render primary and secondary keyword pills.
 * @param {object} results - Scraped keyword results
 */
function renderWizardKeywordResults(results) {
  const pillsPrimary = document.getElementById('w-pills-primary');
  const pillsSecondary = document.getElementById('w-pills-secondary');
  const resultsContainer = document.getElementById('w-keyword-results');

  if (!pillsPrimary || !pillsSecondary || !resultsContainer) return;

  if (!results) {
    console.warn('[renderWizardKeywordResults] called with null/undefined results');
    pillsPrimary.innerHTML = '<span class="text-muted">No keyword data available.</span>';
    pillsSecondary.innerHTML = '';
    resultsContainer.style.display = 'grid';
    return;
  }
  
  pillsPrimary.innerHTML = (results.primary || []).map(kw => `
    <span class="kw-pill selected" onclick="toggleKwPill(this)" data-kw="${escapeHtml(kw)}">
      ${escapeHtml(kw)} <span class="chk">✓</span>
    </span>
  `).join('');
  
  pillsSecondary.innerHTML = (results.secondary || []).map(kw => `
    <span class="kw-pill selected" onclick="toggleKwPill(this)" data-kw="${escapeHtml(kw)}">
      ${escapeHtml(kw)} <span class="chk">✓</span>
    </span>
  `).join('');
  
  resultsContainer.style.display = 'grid';
}

/**
 * Save Step 2 keyword links.
 */
async function saveWizardStep2() {
  if (!wizardProduct) return true;
  
  const selectedPills = document.querySelectorAll('#w-keyword-results .kw-pill.selected');
  const keywords = Array.from(selectedPills).map(p => p.dataset.kw);
  
  if (keywords.length === 0) {
    if (!confirm("No keywords selected. Proceed without targeting keywords?")) {
      return false;
    }
    return true;
  }
  
  try {
    const url = `/keywords/apply-to-product?product_id=${wizardProduct.id}&` + keywords.map(k => `keywords=${encodeURIComponent(k)}`).join('&');
    await api(url, 'POST');
    showToast(`Successfully linked ${keywords.length} keywords to product SKU!`, "success");
    return true;
  } catch (err) {
    showToast("Failed to link keywords: " + err.message, "error");
    return false;
  }
}

// ----- Step 3: AI Copy Generation -----

/**
 * Load draft content for Step 3 text editors.
 */
// Character limit config for Wizard Step 3 counter fields.
// multiLine=true means measure the longest individual line, not the total.
const WIZARD_STEP3_FIELDS = [
  { id: 'w-amazon-title',      counterId: 'wc-cnt-amazon-title',      limit: 200,  unit: 'chars',            multiLine: false },
  { id: 'w-amazon-bullets',    counterId: 'wc-cnt-amazon-bullets',    limit: 500,  unit: 'chars per bullet',  multiLine: true  },
  { id: 'w-amazon-desc',       counterId: 'wc-cnt-amazon-desc',       limit: 2000, unit: 'chars',            multiLine: false },
  { id: 'w-flipkart-title',    counterId: 'wc-cnt-flipkart-title',    limit: 500,  unit: 'chars',            multiLine: false },
  { id: 'w-flipkart-features', counterId: 'wc-cnt-flipkart-features', limit: 200,  unit: 'chars per feature', multiLine: true  },
  { id: 'w-flipkart-desc',     counterId: 'wc-cnt-flipkart-desc',     limit: 5000, unit: 'chars',            multiLine: false },
  { id: 'w-meesho-title',      counterId: 'wc-cnt-meesho-title',      limit: 200,  unit: 'chars',            multiLine: false },
  { id: 'w-meesho-desc',       counterId: 'wc-cnt-meesho-desc',       limit: 2000, unit: 'chars',            multiLine: false },
];

function _updateStep3Counter(fieldCfg) {
  const el = document.getElementById(fieldCfg.id);
  const ctr = document.getElementById(fieldCfg.counterId);
  if (!el || !ctr) return;
  const value = el.value || '';
  const len = fieldCfg.multiLine
    ? value.split('\n').reduce((max, line) => Math.max(max, line.length), 0)
    : value.length;
  ctr.textContent = `${len} / ${fieldCfg.limit} ${fieldCfg.unit}`;
  ctr.classList.remove('warning', 'danger');
  if (len > fieldCfg.limit) {
    ctr.classList.add('danger');
  } else if (len > fieldCfg.limit * 0.8) {
    ctr.classList.add('warning');
  }
}

function refreshWizardStep3Counters() {
  WIZARD_STEP3_FIELDS.forEach(_updateStep3Counter);
}

function attachWizardStep3Counters() {
  WIZARD_STEP3_FIELDS.forEach(cfg => {
    const el = document.getElementById(cfg.id);
    if (!el) return;
    // Remove any previously-attached listener by replacing via clone
    const clone = el.cloneNode(true);
    el.parentNode.replaceChild(clone, el);
    clone.addEventListener('input', () => _updateStep3Counter(cfg));
  });
  refreshWizardStep3Counters();
}

/**
 * Save manual edits currently in the DOM inputs to our in-memory state.
 */
function saveCurrentTabEditsToMemory() {
  const current = {
    amazon_title: document.getElementById('w-amazon-title')?.value || '',
    amazon_bullets: document.getElementById('w-amazon-bullets')?.value || '',
    amazon_desc: document.getElementById('w-amazon-desc')?.value || '',
    flipkart_title: document.getElementById('w-flipkart-title')?.value || '',
    flipkart_features: document.getElementById('w-flipkart-features')?.value || '',
    flipkart_desc: document.getElementById('w-flipkart-desc')?.value || '',
    meesho_title: document.getElementById('w-meesho-title')?.value || '',
    meesho_desc: document.getElementById('w-meesho-desc')?.value || ''
  };

  if (wizardStep3ActiveTab === 'base') {
    wizardStep3Data.base = current;
  } else {
    wizardStep3Data.variations[wizardStep3ActiveTab] = current;
  }
}

/**
 * Load the active tab's copy content from in-memory state into the DOM inputs.
 */
function loadActiveTabContentToDOM() {
  let content;
  if (wizardStep3ActiveTab === 'base') {
    content = wizardStep3Data.base;
  } else {
    if (!wizardStep3Data.variations[wizardStep3ActiveTab]) {
      wizardStep3Data.variations[wizardStep3ActiveTab] = {
        amazon_title: '', amazon_bullets: '', amazon_desc: '',
        flipkart_title: '', flipkart_features: '', flipkart_desc: '',
        meesho_title: '', meesho_desc: ''
      };
    }
    content = wizardStep3Data.variations[wizardStep3ActiveTab];
  }

  document.getElementById('w-amazon-title').value = content.amazon_title || '';
  document.getElementById('w-amazon-bullets').value = content.amazon_bullets || '';
  document.getElementById('w-amazon-desc').value = content.amazon_desc || '';

  document.getElementById('w-flipkart-title').value = content.flipkart_title || '';
  document.getElementById('w-flipkart-features').value = content.flipkart_features || '';
  document.getElementById('w-flipkart-desc').value = content.flipkart_desc || '';

  document.getElementById('w-meesho-title').value = content.meesho_title || '';
  document.getElementById('w-meesho-desc').value = content.meesho_desc || '';

  refreshWizardStep3Counters();
}

/**
 * Render the variation tab strip in Step 3.
 */
function renderStep3VariationTabs() {
  const container = document.getElementById('w-variation-tabs');
  if (!container) return;

  container.innerHTML = '';

  // 1. Create Base Product Tab
  const baseTab = document.createElement('button');
  baseTab.className = `wizard-var-tab${wizardStep3ActiveTab === 'base' ? ' active' : ''}`;
  baseTab.textContent = 'Base Product';
  baseTab.addEventListener('click', () => switchStep3Tab('base'));
  container.appendChild(baseTab);

  // 2. Create tab for each variation
  wizardVariations.forEach(v => {
    const tab = document.createElement('button');
    tab.className = `wizard-var-tab${String(wizardStep3ActiveTab) === String(v.id) ? ' active' : ''}`;
    tab.textContent = v.variation_value || v.sku || `Var #${v.id}`;
    tab.addEventListener('click', () => switchStep3Tab(v.id));
    container.appendChild(tab);
  });
}

/**
 * Switch active tab to a new variation ID or 'base'.
 */
function switchStep3Tab(tabId) {
  if (String(wizardStep3ActiveTab) === String(tabId)) return;

  saveCurrentTabEditsToMemory();
  wizardStep3ActiveTab = tabId;
  renderStep3VariationTabs();
  loadActiveTabContentToDOM();
}

async function loadWizardStep3Content() {
  if (!wizardProduct) return;

  try {
    const res = await api(`/products/${wizardProduct.id}`);
    const product = res.data?.product || res.product || res;

    wizardStep3Data.base = {
      amazon_title: product.amazon_title || '',
      amazon_bullets: (product.amazon_bullets || []).join('\n'),
      amazon_desc: product.amazon_description || '',
      flipkart_title: product.flipkart_title || '',
      flipkart_features: (product.flipkart_key_features || []).join('\n'),
      flipkart_desc: product.flipkart_description || '',
      meesho_title: product.meesho_title || '',
      meesho_desc: product.meesho_description || ''
    };

    wizardStep3Data.variations = {};
    if (wizardVariations.length > 0) {
      try {
        const vRes = await api(`/products/${wizardProduct.id}/variation-content`);
        const list = vRes.data || vRes || [];
        list.forEach(r => {
          const vId = r.variation_id;
          if (!wizardStep3Data.variations[vId]) {
            wizardStep3Data.variations[vId] = {
              amazon_title: '', amazon_bullets: '', amazon_desc: '',
              flipkart_title: '', flipkart_features: '', flipkart_desc: '',
              meesho_title: '', meesho_desc: ''
            };
          }
          if (r.marketplace === 'amazon') {
            wizardStep3Data.variations[vId].amazon_title = r.title || '';
            wizardStep3Data.variations[vId].amazon_bullets = (r.bullets || []).join('\n');
            wizardStep3Data.variations[vId].amazon_desc = r.description || '';
          } else if (r.marketplace === 'flipkart') {
            wizardStep3Data.variations[vId].flipkart_title = r.title || '';
            wizardStep3Data.variations[vId].flipkart_features = (r.bullets || []).join('\n');
            wizardStep3Data.variations[vId].flipkart_desc = r.description || '';
          } else if (r.marketplace === 'meesho') {
            wizardStep3Data.variations[vId].meesho_title = r.title || '';
            wizardStep3Data.variations[vId].meesho_desc = r.description || '';
          }
        });
      } catch (vErr) {
        console.error("Failed to load variation contents:", vErr);
      }
    }

    wizardStep3ActiveTab = 'base';
    renderStep3VariationTabs();
    loadActiveTabContentToDOM();

  } catch (err) {
    showToast("Failed to load drafts: " + err.message, "error");
  }
}

/**
 * Trigger Gemini generation for all 3 marketplaces.
 * Uses /generate-with-variations when variations exist, /generate otherwise.
 */
async function startWizardContentGeneration() {
  if (!wizardProduct) return;

  const contentArea = document.getElementById('wcontent-3');
  if (!contentArea) return;

  // Collect selected keyword pills from the wizard keyword step
  const selectedPills = document.querySelectorAll('#w-keyword-results .kw-pill.selected');
  const selectedKeywords = Array.from(selectedPills).map(p => p.dataset.kw).filter(Boolean);

  const hasVariations = wizardVariations.length > 0;
  const varCount = wizardVariations.length;

  const overlayMessage = hasVariations
    ? `Gemini AI is generating listings for base product + ${varCount} variation${varCount !== 1 ? 's' : ''}...`
    : 'Gemini AI is generating listing copies...';

  showToast("Invoking Gemini content optimization...", "info");

  const overlay = document.createElement('div');
  overlay.style = 'position:absolute;inset:0;background:rgba(10,14,39,0.75);backdrop-filter:blur(4px);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:90';
  overlay.innerHTML = `
    <div class="spinner"></div>
    <h4 style="color:#fff">${escapeHtml(overlayMessage)}</h4>
    <p style="color:var(--text-secondary);font-size:12px;margin-top:4px">Integrating specs and keyword densities.</p>
  `;
  contentArea.style.position = 'relative';
  contentArea.appendChild(overlay);

  try {
    if (hasVariations) {
      await api('/content/generate-with-variations', 'POST', {
        product_id: wizardProduct.id,
        keywords: selectedKeywords,
      });
    } else {
      await api('/content/generate', 'POST', {
        product_id: wizardProduct.id,
        marketplace: 'all',
        keywords: selectedKeywords,
      });
    }

    showToast("Marketplace listings successfully generated!", "success");
    overlay.remove();
    await loadWizardStep3Content();
  } catch (err) {
    showToast("AI generation failed: " + err.message, "error");
    overlay.remove();
  }
}

/**
 * Save manual changes in editors back as drafts.
 */
async function saveWizardStep3() {
  if (!wizardProduct) return true;

  // 1. Save edits from current active tab to memory
  saveCurrentTabEditsToMemory();

  // 2. Prepare and save base product copy content
  const base = wizardStep3Data.base;
  const body = {
    amazon_title: base.amazon_title,
    amazon_bullets: base.amazon_bullets.split('\n').filter(b => b.trim() !== ''),
    amazon_description: base.amazon_desc,
    amazon_status: base.amazon_title ? 'ready' : 'draft',
    flipkart_title: base.flipkart_title,
    flipkart_key_features: base.flipkart_features.split('\n').filter(f => f.trim() !== ''),
    flipkart_description: base.flipkart_desc,
    flipkart_status: base.flipkart_title ? 'ready' : 'draft',
    meesho_title: base.meesho_title,
    meesho_description: base.meesho_desc,
    meesho_status: base.meesho_title ? 'ready' : 'draft',
    listing_status: 'content_ready'
  };

  try {
    await api(`/products/${wizardProduct.id}`, 'PUT', body);

    // 3. Prepare and save variations copy content
    const varPayload = {};
    for (const varId in wizardStep3Data.variations) {
      const vContent = wizardStep3Data.variations[varId];
      varPayload[varId] = {
        amazon: {
          title: vContent.amazon_title || '',
          bullets: vContent.amazon_bullets || '',
          description: vContent.amazon_desc || '',
          status: vContent.amazon_title ? 'ready' : 'draft'
        },
        flipkart: {
          title: vContent.flipkart_title || '',
          bullets: vContent.flipkart_features || '',
          description: vContent.flipkart_desc || '',
          status: vContent.flipkart_title ? 'ready' : 'draft'
        },
        meesho: {
          title: vContent.meesho_title || '',
          description: vContent.meesho_desc || '',
          status: vContent.meesho_title ? 'ready' : 'draft'
        }
      };
    }

    if (Object.keys(varPayload).length > 0) {
      await api(`/products/${wizardProduct.id}/variation-content`, 'PUT', varPayload);
    }

    showToast("Listing drafts updated", "success");
    return true;
  } catch (err) {
    showToast("Failed to save edits: " + err.message, "error");
    return false;
  }
}

// ----- Step 4: Pricing Review -----

/**
 * Recalculate marketplace margins on margin/zone input.
 */
async function calculateWizardPricing() {
  if (!wizardProduct) return;
  
  const margin = parseFloat(document.getElementById('w-pricing-margin').value);
  const zone = document.getElementById('w-pricing-zone').value;
  
  if (isNaN(margin) || margin < 0) return;
  
  try {
    const res = await api('/pricing/calculate', 'POST', {
      product_id: wizardProduct.id,
      cost_price: wizardProduct.cost_price,
      weight_grams: wizardProduct.weight_grams || 150,
      category: wizardProduct.category,
      target_margin: margin,
      shipping_zone: zone
    });
    
    const pricingData = res.data || {};
    const mps = ['amazon', 'flipkart', 'meesho'];
    mps.forEach(mp => {
      const data = pricingData[mp];
      if (!data) return;

      document.getElementById(`w-price-val-${mp}`).textContent = `₹${data.selling_price.toFixed(2)}`;

      const breakdownEl = document.getElementById(`w-price-breakdown-${mp}`);
      let feesHtml = '';
      Object.entries(data.fees || {}).forEach(([name, fee]) => {
        feesHtml += `
          <div class="pricing-breakdown-row">
            <span>${name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
            <span>₹${fee.toFixed(2)}</span>
          </div>
        `;
      });
      feesHtml += `
        <div class="pricing-breakdown-row">
          <span>Total Fees</span>
          <span>₹${data.total_fees.toFixed(2)}</span>
        </div>
        <div class="pricing-breakdown-row total">
          <span>Profit / Margin</span>
          <span>₹${data.profit.toFixed(2)} (${data.margin_percent.toFixed(1)}%)</span>
        </div>
      `;
      breakdownEl.innerHTML = feesHtml;
    });

    // Keep wizardProduct in sync so Step 5 preview reflects current prices
    if (wizardProduct && pricingData.amazon) {
      wizardProduct.amazon_price   = pricingData.amazon.selling_price;
      wizardProduct.flipkart_price = pricingData.flipkart?.selling_price ?? wizardProduct.flipkart_price;
      wizardProduct.meesho_price   = pricingData.meesho?.selling_price   ?? wizardProduct.meesho_price;
    }
    
  } catch (err) {
    showToast("Calculation failed: " + err.message, "error");
  }
}

/**
 * Save Step 4 pricing and margin snapshots.
 */
async function saveWizardStep4() {
  await calculateWizardPricing();
  return true;
}

// ----- Step 5: Export Preview & Save -----

/**
 * Render the flat preview table on Step 5.
 */
// Column definitions per marketplace for the Step 5 preview table.
const PREVIEW_COLUMNS = {
  all: [
    { label: 'SKU',             key: 'sku' },
    { label: 'Name',            key: 'name' },
    { label: 'Category',        key: 'category' },
    { label: 'Cost',            key: 'cost_price',     format: v => v != null ? `₹${v}` : '—' },
    { label: 'Amazon Title',    key: 'amazon_title' },
    { label: 'Amazon Price',    key: 'amazon_price',   format: v => v ? `₹${v}` : '—' },
    { label: 'Flipkart Title',  key: 'flipkart_title' },
    { label: 'Flipkart Price',  key: 'flipkart_price', format: v => v ? `₹${v}` : '—' },
    { label: 'Meesho Title',    key: 'meesho_title' },
    { label: 'Meesho Price',    key: 'meesho_price',   format: v => v ? `₹${v}` : '—' },
  ],
  amazon: [
    { label: 'SKU',             key: 'sku' },
    { label: 'Name',            key: 'name' },
    { label: 'Brand',           key: 'brand' },
    { label: 'Title',           key: 'amazon_title' },
    { label: 'Bullet 1',        key: 'amazon_bullet_1' },
    { label: 'Bullet 2',        key: 'amazon_bullet_2' },
    { label: 'Bullet 3',        key: 'amazon_bullet_3' },
    { label: 'Bullet 4',        key: 'amazon_bullet_4' },
    { label: 'Bullet 5',        key: 'amazon_bullet_5' },
    { label: 'Description',     key: 'amazon_description' },
    { label: 'Search Terms',    key: 'amazon_search_terms' },
    { label: 'Price',           key: 'amazon_price',   format: v => v ? `₹${v}` : '—' },
  ],
  flipkart: [
    { label: 'SKU',             key: 'sku' },
    { label: 'Name',            key: 'name' },
    { label: 'Brand',           key: 'brand' },
    { label: 'Title',           key: 'flipkart_title' },
    { label: 'Feature 1',       key: 'flipkart_key_feature_1' },
    { label: 'Feature 2',       key: 'flipkart_key_feature_2' },
    { label: 'Feature 3',       key: 'flipkart_key_feature_3' },
    { label: 'Feature 4',       key: 'flipkart_key_feature_4' },
    { label: 'Feature 5',       key: 'flipkart_key_feature_5' },
    { label: 'Feature 6',       key: 'flipkart_key_feature_6' },
    { label: 'Description',     key: 'flipkart_description' },
    { label: 'Keywords',        key: 'flipkart_keywords' },
    { label: 'Price',           key: 'flipkart_price', format: v => v ? `₹${v}` : '—' },
  ],
  meesho: [
    { label: 'SKU',             key: 'sku' },
    { label: 'Name',            key: 'name' },
    { label: 'Brand',           key: 'brand' },
    { label: 'Title',           key: 'meesho_title' },
    { label: 'Description',     key: 'meesho_description' },
    { label: 'Price',           key: 'meesho_price',   format: v => v ? `₹${v}` : '—' },
  ],
};

function switchPreviewTab(marketplace) {
  activePreviewMarketplace = marketplace;
  ['all', 'amazon', 'flipkart', 'meesho'].forEach(mp => {
    const btn = document.getElementById(`w-ptab-${mp}`);
    if (btn) btn.classList.toggle('active', mp === marketplace);
  });
  loadWizardStep5Preview();
}

async function loadWizardStep5Preview() {
  if (!wizardProduct) return;

  const thead = document.querySelector('#w-preview-table thead');
  const tbody = document.querySelector('#w-preview-table tbody');
  if (!thead || !tbody) return;

  const colCount = (PREVIEW_COLUMNS[activePreviewMarketplace] || PREVIEW_COLUMNS.all).length;
  thead.innerHTML = `<tr><th colspan="${colCount}">Loading template preview...</th></tr>`;
  tbody.innerHTML = '';

  try {
    const res = await api('/templates/preview', 'POST', {
      product_ids: [wizardProduct.id],
      marketplace: activePreviewMarketplace,
    });

    const rows = Array.isArray(res?.data) ? res.data : null;
    if (!rows || rows.length === 0) {
      thead.innerHTML = `<tr><th colspan="${colCount}">No listing data found. Please complete Steps 1–4 before previewing.</th></tr>`;
      return;
    }

    const columns = PREVIEW_COLUMNS[activePreviewMarketplace] || PREVIEW_COLUMNS.all;

    thead.innerHTML = `<tr>${columns.map(col => `<th>${escapeHtml(col.label)}</th>`).join('')}</tr>`;
    tbody.innerHTML = rows.map(row => `
      <tr>
        ${columns.map(col => {
          let val = row[col.key];
          if (col.format) val = col.format(val);
          return `<td>${escapeHtml(val != null ? String(val) : '—')}</td>`;
        }).join('')}
      </tr>
    `).join('');

  } catch (err) {
    thead.innerHTML = `<tr><th colspan="${colCount}" class="text-danger">Failed to load preview: ${escapeHtml(err.message)}</th></tr>`;
    tbody.innerHTML = '';
    showToast(err.message, 'error');
  }
}

/**
 * Export workbook sheets and close the wizard.
 */
async function finishWizard() {
  if (!wizardProduct) {
    closeWizard();
    return;
  }
  
  showToast("Generating styled spreadsheet workbook...", "info");
  
  try {
    const response = await fetch('/api/templates/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_ids: [wizardProduct.id], marketplace: 'all' })
    });
    
    if (!response.ok) throw new Error('Excel generation failed');
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    const disposition = response.headers.get('content-disposition');
    let filename = `onboard_listing_${wizardProduct.sku}.xlsx`;
    if (disposition && disposition.includes('attachment')) {
      const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
      if (matches && matches[1]) {
        filename = matches[1].replace(/['"]/g, '');
      }
    }
    
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    
    showToast('Spreadsheet downloaded successfully!', 'success');

    // Build status update from "Mark as Published" checkboxes
    const listedAmazon   = document.getElementById('w-listed-amazon')?.checked;
    const listedFlipkart = document.getElementById('w-listed-flipkart')?.checked;
    const listedMeesho   = document.getElementById('w-listed-meesho')?.checked;
    const allListed = listedAmazon && listedFlipkart && listedMeesho;

    const statusUpdate = {
      listing_status: allListed ? 'listed' : 'exported',
    };
    if (listedAmazon)   statusUpdate.amazon_status   = 'listed';
    if (listedFlipkart) statusUpdate.flipkart_status = 'listed';
    if (listedMeesho)   statusUpdate.meesho_status   = 'listed';

    await api(`/products/${wizardProduct.id}`, 'PUT', statusUpdate);

  } catch (err) {
    showToast('Export failed: ' + err.message, 'error');
  }

  closeWizard();
}

// =============================================================
// Kanban Board Drag-and-Drop Pipeline (Phase 5)
// =============================================================

/**
 * Render the Kanban Board component for pipeline layout.
 * @param {Array} allProducts - List of all products
 * @returns {string} HTML markup string
 */
function renderKanbanBoard(allProducts) {
  const columns = [
    { title: 'New', status: 'new', color: 'accent-primary' },
    { title: 'Keywords', status: 'keywords_done', color: 'accent-secondary' },
    { title: 'Content', status: 'content_ready', color: 'accent-warning' },
    { title: 'Priced', status: 'priced', color: 'accent-success' },
    { title: 'Exported', status: 'exported', color: 'accent-amazon' },
    { title: 'Listed', status: 'listed', color: 'accent-success' }
  ];
  
  const groups = {
    new: [],
    keywords_done: [],
    content_ready: [],
    priced: [],
    exported: [],
    listed: []
  };
  
  allProducts.forEach(p => {
    const status = p.listing_status || 'new';
    if (groups[status]) {
      groups[status].push(p);
    } else {
      groups.new.push(p);
    }
  });
  
  const colsHtml = columns.map(col => {
    const prods = groups[col.status] || [];
    const count = prods.length;
    
    const cardsHtml = prods.map(p => {
      const costHtml = p.cost_price != null ? `₹${Number(p.cost_price).toLocaleString('en-IN')}` : '—';
      return `
        <div class="kanban-card" draggable="true" data-pid="${p.id}" ondragstart="handleKanbanDragStart(event)">
          <div class="kanban-card-sku">${escapeHtml(p.sku)}</div>
          <div class="kanban-card-title">${escapeHtml(p.name)}</div>
          <div class="kanban-card-category">${formatCategory(p.category)}</div>
          <div class="kanban-card-footer">
            <span class="kanban-card-price">Cost: ${costHtml}</span>
            <span style="cursor:pointer;" onclick="editProductFromKanban(${p.id})">🧙‍♂️</span>
          </div>
        </div>
      `;
    }).join('');
    
    return `
      <div class="kanban-column" data-status="${col.status}" ondragover="handleKanbanDragOver(event)" ondragleave="handleKanbanDragLeave(event)" ondrop="handleKanbanDrop(event)">
        <div class="kanban-column-header">
          <span>${col.title}</span>
          <span class="kanban-column-count">${count}</span>
        </div>
        <div class="kanban-cards">
          ${cardsHtml || '<div class="text-muted" style="text-align:center;font-size:12px;padding:20px 0;">Drop here</div>'}
        </div>
      </div>
    `;
  }).join('');
  
  return `
    <div class="section-title" style="margin-top:28px">Listing Onboarding Pipeline</div>
    <div class="kanban-board">
      ${colsHtml}
    </div>
  `;
}

/**
 * Handle card drag start.
 */
function handleKanbanDragStart(e) {
  e.dataTransfer.setData('text/plain', e.target.dataset.pid);
  e.target.style.opacity = '0.5';
}

/**
 * Handle drag over column.
 */
function handleKanbanDragOver(e) {
  e.preventDefault();
  const col = e.currentTarget;
  const isListed = col.dataset.status === 'listed';
  col.style.background = isListed ? 'rgba(16, 185, 129, 0.08)' : 'rgba(99, 102, 241, 0.08)';
  col.style.borderColor = isListed ? 'var(--accent-success)' : 'var(--accent-primary)';
}

/**
 * Handle drag leaving column.
 */
function handleKanbanDragLeave(e) {
  const col = e.currentTarget;
  col.style.background = '';
  col.style.borderColor = '';
}

/**
 * Handle card drop.
 */
async function handleKanbanDrop(e) {
  e.preventDefault();
  const col = e.currentTarget;
  col.style.background = '';
  col.style.borderColor = '';
  
  const pid = e.dataTransfer.getData('text/plain');
  const targetStatus = col.dataset.status;
  
  if (!pid || !targetStatus) return;
  
  const card = document.querySelector(`.kanban-card[data-pid="${pid}"]`);
  if (card) card.style.opacity = '1';
  
  try {
    await api(`/products/${pid}`, 'PUT', { listing_status: targetStatus });
    showToast(`Pipeline updated! Product set to ${targetStatus}.`, "success");
    renderDashboard();
  } catch (err) {
    showToast("Failed to update status: " + err.message, "error");
  }
}

/**
 * Kanban action to open wizard for specific product.
 */
function editProductFromKanban(productId) {
  openProductWizard(productId);
}

// Reset opacity of any cards dragged but not dropped on valid columns
document.addEventListener('dragend', (e) => {
  if (e.target.classList && e.target.classList.contains('kanban-card')) {
    e.target.style.opacity = '1';
  }
});
