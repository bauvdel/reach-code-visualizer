/**
 * Advanced Filtering System for REACH Code Visualizer
 * Handles node filtering by type, language, directory, and custom expressions
 */

class FilterManager {
    constructor(graphRenderer) {
        this.graphRenderer = graphRenderer;
        this.activeFilters = {
            types: new Set(['FUNCTION', 'VARIABLE', 'SIGNAL', 'CLASS', 'SCENE', 'SIGNAL_CONNECTION']),
            languages: new Set(['gdscript', 'scene']),
            confidence: new Set(['high', 'medium', 'low', 'ambiguous']),
            directory: '',
            customExpression: ''
        };
        this.allNodes = [];
        this.allEdges = [];
        this.isVisible = false;

        this.init();
    }

    init() {
        this.cacheElements();
        this.bindEvents();
    }

    cacheElements() {
        // Panel elements
        this.filterPanel = document.getElementById('filter-panel');
        this.toggleBtn = document.getElementById('toggle-filter-panel');
        this.closeBtn = document.getElementById('close-filter-panel');
        this.applyBtn = document.getElementById('apply-filters');
        this.resetBtn = document.getElementById('reset-filters');

        // Type checkboxes (by class)
        this.typeCheckboxes = document.querySelectorAll('.type-filter');

        // Language checkboxes (by class)
        this.langCheckboxes = document.querySelectorAll('.lang-filter');

        // Confidence checkboxes (by class)
        this.confCheckboxes = document.querySelectorAll('.conf-filter');

        // Other inputs
        this.directoryInput = document.getElementById('dir-filter');
        this.customFilterInput = document.getElementById('custom-filter');

        // Cluster controls
        this.clusterBySelect = document.getElementById('cluster-by');
        this.clusterThreshold = document.getElementById('cluster-threshold');
        this.clusterThresholdValue = document.getElementById('cluster-threshold-value');
    }

    bindEvents() {
        // Toggle panel visibility
        this.toggleBtn?.addEventListener('click', () => this.togglePanel());
        this.closeBtn?.addEventListener('click', () => this.hidePanel());

        // Apply and reset buttons
        this.applyBtn?.addEventListener('click', () => this.applyFilters());
        this.resetBtn?.addEventListener('click', () => this.resetFilters());

        // Cluster threshold slider
        this.clusterThreshold?.addEventListener('input', (e) => {
            if (this.clusterThresholdValue) {
                this.clusterThresholdValue.textContent = e.target.value;
            }
        });

        // Directory input with debounce
        let directoryTimeout;
        this.directoryInput?.addEventListener('input', () => {
            clearTimeout(directoryTimeout);
            directoryTimeout = setTimeout(() => this.applyFilters(), 500);
        });

        // Custom filter with Enter key
        this.customFilterInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.applyFilters();
            }
        });
    }

    togglePanel() {
        this.isVisible = !this.isVisible;
        if (this.filterPanel) {
            this.filterPanel.classList.toggle('collapsed', !this.isVisible);
        }
        if (this.toggleBtn) {
            this.toggleBtn.classList.toggle('active', this.isVisible);
        }
    }

    showPanel() {
        this.isVisible = true;
        this.filterPanel?.classList.remove('collapsed');
        this.toggleBtn?.classList.add('active');
    }

    hidePanel() {
        this.isVisible = false;
        this.filterPanel?.classList.add('collapsed');
        this.toggleBtn?.classList.remove('active');
    }

    /**
     * Cache all nodes and edges for filtering
     */
    setGraphData(nodes, edges) {
        this.allNodes = nodes;
        this.allEdges = edges;
    }

    /**
     * Read current filter state from UI
     */
    readFiltersFromUI() {
        // Types
        this.activeFilters.types.clear();
        this.typeCheckboxes.forEach(cb => {
            if (cb.checked) {
                this.activeFilters.types.add(cb.value);
            }
        });

        // Languages
        this.activeFilters.languages.clear();
        this.langCheckboxes.forEach(cb => {
            if (cb.checked) {
                this.activeFilters.languages.add(cb.value);
            }
        });

        // Confidence
        this.activeFilters.confidence.clear();
        this.confCheckboxes.forEach(cb => {
            if (cb.checked) {
                this.activeFilters.confidence.add(cb.value);
            }
        });

        // Directory
        this.activeFilters.directory = this.directoryInput?.value?.trim() || '';

        // Custom expression
        this.activeFilters.customExpression = this.customFilterInput?.value?.trim() || '';
    }

    /**
     * Apply filters to the graph
     */
    applyFilters() {
        this.readFiltersFromUI();

        const filteredNodes = this.filterNodes(this.allNodes);
        const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
        const filteredEdges = this.filterEdges(this.allEdges, filteredNodeIds);

        // Update graph
        if (this.graphRenderer) {
            this.graphRenderer.updateData(filteredNodes, filteredEdges);
        }

        // Show notification
        this.showFilterNotification(filteredNodes.length, this.allNodes.length);

        return { nodes: filteredNodes, edges: filteredEdges };
    }

    /**
     * Filter nodes based on active filters
     */
    filterNodes(nodes) {
        if (!nodes || nodes.length === 0) return [];

        return nodes.filter(node => {
            // Type filter
            const nodeType = (node.group || node.type || 'UNKNOWN').toUpperCase();
            if (!this.activeFilters.types.has(nodeType)) {
                return false;
            }

            // Language filter
            const nodeLang = this.getNodeLanguage(node);
            if (nodeLang && !this.activeFilters.languages.has(nodeLang)) {
                return false;
            }

            // Directory filter
            if (this.activeFilters.directory) {
                const nodePath = node.file || node.path || '';
                if (!nodePath.toLowerCase().includes(this.activeFilters.directory.toLowerCase())) {
                    return false;
                }
            }

            // Custom expression filter
            if (this.activeFilters.customExpression) {
                if (!this.matchesCustomExpression(node, this.activeFilters.customExpression)) {
                    return false;
                }
            }

            return true;
        });
    }

    /**
     * Filter edges to only include those connecting visible nodes
     */
    filterEdges(edges, visibleNodeIds) {
        if (!edges || edges.length === 0) return [];

        return edges.filter(edge => {
            return visibleNodeIds.has(edge.from) && visibleNodeIds.has(edge.to);
        });
    }

    /**
     * Get the language of a node
     */
    getNodeLanguage(node) {
        const file = node.file || node.path || '';

        if (file.endsWith('.gd')) return 'gdscript';
        if (file.endsWith('.tscn') || file.endsWith('.tres')) return 'scene';

        return null;
    }

    /**
     * Match node against custom expression
     * Supports: name contains 'text', type:pattern, file:pattern
     */
    matchesCustomExpression(node, expression) {
        const lowerExpr = expression.toLowerCase();
        const nodeName = (node.label || node.id || '').toLowerCase();
        const nodeType = (node.group || node.type || '').toLowerCase();
        const nodeFile = (node.file || node.path || '').toLowerCase();

        // Simple "contains" check
        if (lowerExpr.includes('contains')) {
            const match = lowerExpr.match(/contains\s+['"](.+)['"]/);
            if (match) {
                return nodeName.includes(match[1].toLowerCase());
            }
        }

        // Type prefix
        if (lowerExpr.startsWith('type:')) {
            return nodeType.includes(lowerExpr.slice(5));
        }

        // File prefix
        if (lowerExpr.startsWith('file:')) {
            return nodeFile.includes(lowerExpr.slice(5));
        }

        // Default: search in name
        return nodeName.includes(lowerExpr);
    }

    /**
     * Reset all filters to defaults
     */
    resetFilters() {
        // Reset types
        this.typeCheckboxes.forEach(cb => {
            cb.checked = true;
        });

        // Reset languages
        this.langCheckboxes.forEach(cb => {
            cb.checked = true;
        });

        // Reset confidence
        this.confCheckboxes.forEach(cb => {
            cb.checked = true;
        });

        // Reset directory
        if (this.directoryInput) {
            this.directoryInput.value = '';
        }

        // Reset custom filter
        if (this.customFilterInput) {
            this.customFilterInput.value = '';
        }

        // Reset cluster controls
        if (this.clusterBySelect) {
            this.clusterBySelect.value = 'none';
        }

        // Apply reset - show all nodes
        if (this.graphRenderer) {
            this.graphRenderer.updateData(this.allNodes, this.allEdges);
        }

        window.showToast?.('Filters reset', 'info');
    }

    /**
     * Show notification about filter results
     */
    showFilterNotification(visibleCount, totalCount) {
        if (window.showToast) {
            const hidden = totalCount - visibleCount;
            if (hidden > 0) {
                window.showToast(`Showing ${visibleCount} of ${totalCount} nodes (${hidden} filtered)`, 'info');
            } else {
                window.showToast(`Showing all ${visibleCount} nodes`, 'info');
            }
        }
    }

    /**
     * Get current filter summary
     */
    getFilterSummary() {
        const activeTypes = Array.from(this.activeFilters.types);
        const activeLangs = Array.from(this.activeFilters.languages);

        const parts = [];

        if (activeTypes.length < 6) {
            parts.push(`Types: ${activeTypes.join(', ')}`);
        }

        if (activeLangs.length < 2) {
            parts.push(`Languages: ${activeLangs.join(', ')}`);
        }

        if (this.activeFilters.directory) {
            parts.push(`Directory: ${this.activeFilters.directory}`);
        }

        if (this.activeFilters.customExpression) {
            parts.push(`Custom: ${this.activeFilters.customExpression}`);
        }

        return parts.length > 0 ? parts.join(' | ') : 'All nodes visible';
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FilterManager;
}
