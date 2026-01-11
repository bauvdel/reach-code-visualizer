/**
 * Main Application for REACH Code Visualizer
 * Coordinates all components and initializes the application.
 */

console.log('main.js loaded - checking dependencies...');
console.log('vis available:', typeof vis !== 'undefined');
console.log('api available:', typeof api !== 'undefined');

class App {
    constructor() {
        // Core components
        this.graphRenderer = null;
        this.nodeInspector = null;
        this.queryInterface = null;

        // Phase 4 components
        this.filterManager = null;
        this.pathHighlighter = null;
        this.clusterManager = null;
        this.focusMode = null;
        this.minimap = null;
        this.bookmarksManager = null;
        this.exportManager = null;
        this.keyboardShortcuts = null;

        this.stats = null;
        this.updateInterval = null;
        this.allNodes = [];
        this.allEdges = [];
    }

    /**
     * Initialize the application.
     */
    async init() {
        console.log('Initializing REACH Code Visualizer...');

        try {
            // Initialize core components
            console.log('Creating GraphRenderer...');
            this.graphRenderer = new GraphRenderer('graph-container');

            console.log('Creating NodeInspector...');
            this.nodeInspector = new NodeInspector('inspector-panel', 'inspector-content');

            console.log('Creating QueryInterface...');
            this.queryInterface = new QueryInterface();
        } catch (e) {
            console.error('Core component initialization failed:', e);
            return;
        }

        // Initialize Phase 4 components
        this.initPhase4Components();

        // Set up event handlers
        try {
            console.log('Setting up event handlers...');
            this.setupEventHandlers();
        } catch (e) { console.error('Event handlers failed:', e); }

        // Set up control buttons
        try {
            console.log('Setting up controls...');
            this.setupControls();
        } catch (e) { console.error('Controls setup failed:', e); }

        // Set up toast notification system
        try {
            console.log('Setting up toast system...');
            this.setupToastSystem();
        } catch (e) { console.error('Toast system failed:', e); }

        // Load initial data
        console.log('Loading graph data...');
        await this.loadGraph();

        // Start status update interval
        this.startStatusUpdates();

        // Expose managers globally for debugging and component access
        this.exposeGlobally();

        console.log('Application initialized');
    }

    /**
     * Initialize Phase 4 components.
     */
    initPhase4Components() {
        try {
            console.log('Initializing FilterManager...');
            this.filterManager = new FilterManager(this.graphRenderer);
        } catch (e) { console.error('FilterManager failed:', e); }

        try {
            console.log('Initializing PathHighlighter...');
            this.pathHighlighter = new PathHighlighter(this.graphRenderer, api);
        } catch (e) { console.error('PathHighlighter failed:', e); }

        try {
            console.log('Initializing ClusterManager...');
            this.clusterManager = new ClusterManager(this.graphRenderer);
        } catch (e) { console.error('ClusterManager failed:', e); }

        try {
            console.log('Initializing FocusMode...');
            this.focusMode = new FocusMode(this.graphRenderer);
        } catch (e) { console.error('FocusMode failed:', e); }

        try {
            console.log('Initializing Minimap...');
            this.minimap = new Minimap(this.graphRenderer);
        } catch (e) { console.error('Minimap failed:', e); }

        try {
            console.log('Initializing BookmarksManager...');
            this.bookmarksManager = new BookmarksManager(
                this.graphRenderer,
                this.filterManager,
                this.focusMode
            );
        } catch (e) { console.error('BookmarksManager failed:', e); }

        try {
            console.log('Initializing ExportManager...');
            this.exportManager = new ExportManager(this.graphRenderer);
        } catch (e) { console.error('ExportManager failed:', e); }

        try {
            console.log('Initializing KeyboardShortcuts...');
            this.keyboardShortcuts = new KeyboardShortcuts({
                graphRenderer: this.graphRenderer,
                filterManager: this.filterManager,
                focusMode: this.focusMode,
                pathHighlighter: this.pathHighlighter,
                bookmarksManager: this.bookmarksManager,
                exportManager: this.exportManager,
                clusterManager: this.clusterManager
            });
        } catch (e) { console.error('KeyboardShortcuts failed:', e); }

        console.log('Phase 4 components initialized');
    }

    /**
     * Set up event handlers between components.
     */
    setupEventHandlers() {
        // Graph node selection - coordinate with Phase 4 modes
        this.graphRenderer.onNodeSelect = (nodeId, nodeData) => {
            // Check if path mode is active
            if (this.pathHighlighter?.handleNodeClick(nodeId, nodeData)) {
                return; // Path highlighter handled the click
            }

            // Check if focus mode is waiting for selection
            if (this.focusMode?.handleNodeClick(nodeId, nodeData)) {
                return; // Focus mode handled the click
            }

            // Default: show in inspector
            this.nodeInspector.displayNode(nodeId);
        };

        // Graph node double-click - focus on node
        this.graphRenderer.onNodeDoubleClick = (nodeId) => {
            this.focusMode?.focusOnNode(nodeId);
        };

        // Handle cluster clicks
        this.graphRenderer.onClusterClick = (clusterId) => {
            this.clusterManager?.handleClusterClick(clusterId);
        };

        // Inspector navigation
        this.nodeInspector.onNavigate = (nodeId) => {
            this.graphRenderer.selectNode(nodeId);
        };

        // Search result selection
        this.queryInterface.onSelectResult = (nodeId) => {
            this.graphRenderer.selectNode(nodeId);
        };

        // Query execution
        this.queryInterface.onQuery = (result) => {
            if (result.nodes && result.nodes.length > 0) {
                this.graphRenderer.loadQueryResults(result);
            }
        };

        // Filter changes from query interface
        this.queryInterface.onFilter = async (filters) => {
            await this.loadGraph(filters);
        };

        // Listen for graph data updates to sync with Phase 4 components
        this.graphRenderer.onDataLoaded = (nodes, edges) => {
            this.allNodes = nodes;
            this.allEdges = edges;

            // Update Phase 4 components with new data
            this.filterManager?.setGraphData(nodes, edges);
            this.focusMode?.setGraphData(nodes, edges);
            this.minimap?.update();

            // Check if auto-clustering should be enabled
            if (this.clusterManager?.shouldAutoCluster(nodes.length)) {
                window.showToast?.(`Large graph detected (${nodes.length} nodes). Consider enabling clustering.`, 'info');
            }
        };
    }

    /**
     * Set up control buttons.
     */
    setupControls() {
        // Zoom controls
        document.getElementById('zoom-in')?.addEventListener('click', () => {
            this.graphRenderer.zoomIn();
        });

        document.getElementById('zoom-out')?.addEventListener('click', () => {
            this.graphRenderer.zoomOut();
        });

        document.getElementById('center-btn')?.addEventListener('click', () => {
            this.graphRenderer.center();
        });

        // Header controls
        document.getElementById('fit-btn')?.addEventListener('click', () => {
            this.graphRenderer.fit();
        });

        document.getElementById('refresh-btn')?.addEventListener('click', async () => {
            await this.loadGraph(this.queryInterface?.getFilters());
        });

        // Clear all button
        document.getElementById('clear-all')?.addEventListener('click', () => {
            this.clearAllModes();
        });

        // Layout dropdown
        this.setupLayoutControls();

        // Settings modal
        this.setupSettingsModal();
    }

    /**
     * Set up layout controls.
     */
    setupLayoutControls() {
        const layoutItems = document.querySelectorAll('[data-layout]');
        layoutItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const layout = item.dataset.layout;
                this.graphRenderer.setLayout(layout);
                window.showToast?.(`Layout changed to ${layout}`, 'info');
            });
        });
    }

    /**
     * Set up settings modal.
     */
    setupSettingsModal() {
        const settingsBtn = document.getElementById('settings-btn');
        const settingsModal = document.getElementById('settings-modal');
        const closeSettings = document.getElementById('close-settings');

        settingsBtn?.addEventListener('click', () => {
            settingsModal.style.display = 'flex';
        });

        closeSettings?.addEventListener('click', () => {
            settingsModal.style.display = 'none';
        });

        settingsModal?.addEventListener('click', (e) => {
            if (e.target === settingsModal) {
                settingsModal.style.display = 'none';
            }
        });
    }

    /**
     * Set up toast notification system.
     */
    setupToastSystem() {
        // Create global showToast function
        window.showToast = (message, type = 'info', duration = 3000) => {
            const container = document.getElementById('toast-container');
            if (!container) return;

            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;

            const icon = this.getToastIcon(type);
            toast.innerHTML = `
                <span class="toast-icon">${icon}</span>
                <span class="toast-message">${message}</span>
            `;

            container.appendChild(toast);

            // Animate in
            setTimeout(() => toast.classList.add('show'), 10);

            // Remove after duration
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        };
    }

    /**
     * Get icon for toast type.
     */
    getToastIcon(type) {
        switch (type) {
            case 'success': return '<i class="bi bi-check-circle"></i>';
            case 'error': return '<i class="bi bi-x-circle"></i>';
            case 'warning': return '<i class="bi bi-exclamation-triangle"></i>';
            default: return '<i class="bi bi-info-circle"></i>';
        }
    }

    /**
     * Clear all active modes.
     */
    clearAllModes() {
        this.focusMode?.exitFocusMode();
        this.pathHighlighter?.clearAll();
        this.graphRenderer?.network?.unselectAll();
        window.showToast?.('All modes cleared', 'info');
    }

    /**
     * Load graph data from API.
     */
    async loadGraph(filters = {}) {
        this.graphRenderer.showLoading('Loading graph data...');

        try {
            // Load graph data
            const graphData = await api.getGraph({
                type: filters.type || '',
                language: filters.language || '',
                limit: 1000
            });

            // Load stats
            this.stats = await api.getStats();

            // Render graph
            this.graphRenderer.loadGraph(graphData);

            // Update status bar
            this.updateStatusBar();

            // Sync minimap
            setTimeout(() => {
                this.minimap?.refresh();
            }, 500);

        } catch (error) {
            console.error('Failed to load graph:', error);
            this.graphRenderer.hideLoading();
            this.setConnectionStatus(false);
            window.showToast?.('Failed to load graph data', 'error');
        }
    }

    /**
     * Update the status bar.
     */
    updateStatusBar() {
        if (!this.stats) return;

        // Update node count
        const nodesEl = document.querySelector('#status-nodes .status-value');
        if (nodesEl) {
            nodesEl.textContent = this.stats.total_nodes.toLocaleString();
        }

        // Update edge count
        const edgesEl = document.querySelector('#status-edges .status-value');
        if (edgesEl) {
            edgesEl.textContent = this.stats.total_edges.toLocaleString();
        }

        // Update visible count
        const visibleEl = document.querySelector('#status-visible .status-value');
        if (visibleEl) {
            visibleEl.textContent = this.graphRenderer.getVisibleCount().toLocaleString();
        }

        // Update last update time
        const updatedEl = document.querySelector('#status-updated .status-value');
        if (updatedEl) {
            updatedEl.textContent = api.getLastUpdateFormatted();
        }

        // Set connection status
        this.setConnectionStatus(true);
    }

    /**
     * Set connection status indicator.
     */
    setConnectionStatus(connected) {
        const statusEl = document.getElementById('status-connection');
        if (statusEl) {
            if (connected) {
                statusEl.className = 'status-connected';
                statusEl.innerHTML = '<i class="bi bi-wifi"></i> Connected';
            } else {
                statusEl.className = 'status-disconnected';
                statusEl.innerHTML = '<i class="bi bi-wifi-off"></i> Disconnected';
            }
        }
    }

    /**
     * Start status update interval.
     */
    startStatusUpdates() {
        // Update status bar every 5 seconds
        this.updateInterval = setInterval(() => {
            const updatedEl = document.querySelector('#status-updated .status-value');
            if (updatedEl) {
                updatedEl.textContent = api.getLastUpdateFormatted();
            }
        }, 5000);
    }

    /**
     * Stop status update interval.
     */
    stopStatusUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Expose managers globally for debugging and cross-component access.
     */
    exposeGlobally() {
        window.app = this;
        window.graphRenderer = this.graphRenderer;
        window.filterManager = this.filterManager;
        window.focusMode = this.focusMode;
        window.pathHighlighter = this.pathHighlighter;
        window.bookmarksManager = this.bookmarksManager;
        window.clusterManager = this.clusterManager;
        window.exportManager = this.exportManager;
        window.minimap = this.minimap;
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
    app.init().catch(error => {
        console.error('Failed to initialize application:', error);
        window.showToast?.('Failed to initialize application', 'error');
    });
});
