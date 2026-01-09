/**
 * Query Interface for REACH Code Visualizer
 * Handles search, filtering, and query execution.
 */

class QueryInterface {
    constructor() {
        this.searchInput = document.getElementById('search-input');
        this.searchBtn = document.getElementById('search-btn');
        this.searchResults = document.getElementById('search-results');
        this.filterType = document.getElementById('filter-type');
        this.filterLanguage = document.getElementById('filter-language');

        this.searchTimeout = null;
        this.isQueryMode = false;

        // Event callbacks
        this.onSearch = null;
        this.onFilter = null;
        this.onQuery = null;
        this.onSelectResult = null;

        this.setupEventListeners();
    }

    /**
     * Set up event listeners.
     */
    setupEventListeners() {
        // Search input - debounced
        this.searchInput.addEventListener('input', () => {
            clearTimeout(this.searchTimeout);
            const query = this.searchInput.value.trim();

            // Check if this is a query (contains special keywords)
            this.isQueryMode = this.isQuery(query);

            if (query.length >= 2 && !this.isQueryMode) {
                this.searchTimeout = setTimeout(() => {
                    this.performSearch(query);
                }, 300);
            } else {
                this.hideResults();
            }
        });

        // Search button click - execute query
        this.searchBtn.addEventListener('click', () => {
            this.executeCurrentQuery();
        });

        // Enter key
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (this.isQueryMode) {
                    this.executeCurrentQuery();
                } else {
                    // Select first result if available
                    const firstResult = this.searchResults.querySelector('.search-result-item');
                    if (firstResult) {
                        firstResult.click();
                    }
                }
            } else if (e.key === 'Escape') {
                this.hideResults();
                this.searchInput.blur();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateResults(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateResults(-1);
            }
        });

        // Click outside to close results
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.searchResults.contains(e.target)) {
                this.hideResults();
            }
        });

        // Filter changes
        this.filterType.addEventListener('change', () => {
            if (this.onFilter) {
                this.onFilter({
                    type: this.filterType.value,
                    language: this.filterLanguage.value
                });
            }
        });

        this.filterLanguage.addEventListener('change', () => {
            if (this.onFilter) {
                this.onFilter({
                    type: this.filterType.value,
                    language: this.filterLanguage.value
                });
            }
        });
    }

    /**
     * Check if input is a query (vs. simple search).
     */
    isQuery(text) {
        const queryPatterns = [
            /path\s+from/i,
            /path\s+\w+\s+to/i,
            /what\s+calls/i,
            /what\s+does.*call/i,
            /where\s+is.*used/i,
            /what\s+uses/i,
            /trace\s+signal/i,
            /show\s+path/i,
            /signal\s+\w+/i
        ];

        return queryPatterns.some(pattern => pattern.test(text));
    }

    /**
     * Perform a search.
     */
    async performSearch(query) {
        try {
            const type = this.filterType.value;
            const results = await api.search(query, { type, limit: 20 });
            this.displayResults(results.results);
        } catch (error) {
            console.error('Search failed:', error);
            this.displayResults([]);
        }
    }

    /**
     * Display search results.
     */
    displayResults(results) {
        if (results.length === 0) {
            this.searchResults.innerHTML = `
                <div class="search-result-item">
                    <span class="search-result-name text-muted">No results found</span>
                </div>
            `;
        } else {
            const html = results.map(result => `
                <div class="search-result-item" data-node-id="${this.escapeHtml(result.id)}">
                    <span class="search-result-type ${result.type}">${result.type}</span>
                    <span class="search-result-name">${this.escapeHtml(result.name)}</span>
                    <span class="search-result-file">${this.escapeHtml(result.file || '')}</span>
                </div>
            `).join('');
            this.searchResults.innerHTML = html;

            // Add click handlers
            this.searchResults.querySelectorAll('.search-result-item[data-node-id]').forEach(item => {
                item.addEventListener('click', () => {
                    const nodeId = item.dataset.nodeId;
                    if (nodeId && this.onSelectResult) {
                        this.onSelectResult(nodeId);
                        this.hideResults();
                        this.searchInput.value = item.querySelector('.search-result-name').textContent;
                    }
                });
            });
        }

        this.showResults();
    }

    /**
     * Navigate through search results with arrow keys.
     */
    navigateResults(direction) {
        const items = this.searchResults.querySelectorAll('.search-result-item[data-node-id]');
        if (items.length === 0) return;

        const focused = this.searchResults.querySelector('.search-result-item.focused');
        let index = -1;

        if (focused) {
            focused.classList.remove('focused');
            index = Array.from(items).indexOf(focused);
        }

        index += direction;
        if (index < 0) index = items.length - 1;
        if (index >= items.length) index = 0;

        items[index].classList.add('focused');
        items[index].scrollIntoView({ block: 'nearest' });
    }

    /**
     * Execute the current query.
     */
    async executeCurrentQuery() {
        const query = this.searchInput.value.trim();
        if (!query) return;

        this.hideResults();
        this.setLoading(true);

        try {
            const result = await api.executeQuery(query);

            if (this.onQuery) {
                this.onQuery(result);
            }

            // Update status message
            this.updateStatusMessage(result.message);
        } catch (error) {
            console.error('Query failed:', error);
            this.updateStatusMessage('Query failed: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }

    /**
     * Show search results dropdown.
     */
    showResults() {
        this.searchResults.classList.add('active');
    }

    /**
     * Hide search results dropdown.
     */
    hideResults() {
        this.searchResults.classList.remove('active');
    }

    /**
     * Set loading state.
     */
    setLoading(loading) {
        this.searchBtn.disabled = loading;
        if (loading) {
            this.searchBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        } else {
            this.searchBtn.innerHTML = '<i class="bi bi-arrow-right-circle"></i>';
        }
    }

    /**
     * Update the status bar message.
     */
    updateStatusMessage(message) {
        const statusMessage = document.getElementById('status-message');
        if (statusMessage) {
            statusMessage.textContent = message;
            // Clear after 5 seconds
            setTimeout(() => {
                statusMessage.textContent = '';
            }, 5000);
        }
    }

    /**
     * Get current filters.
     */
    getFilters() {
        return {
            type: this.filterType.value,
            language: this.filterLanguage.value
        };
    }

    /**
     * Clear the search input.
     */
    clear() {
        this.searchInput.value = '';
        this.hideResults();
    }

    /**
     * Escape HTML special characters.
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
