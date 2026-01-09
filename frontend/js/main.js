/**
 * Main Application for REACH Code Visualizer
 * Coordinates all components and initializes the application.
 */

class App {
    constructor() {
        this.graphRenderer = null;
        this.nodeInspector = null;
        this.queryInterface = null;

        this.stats = null;
        this.updateInterval = null;
    }

    /**
     * Initialize the application.
     */
    async init() {
        console.log('Initializing REACH Code Visualizer...');

        // Initialize components
        this.graphRenderer = new GraphRenderer('graph-container');
        this.nodeInspector = new NodeInspector('inspector-panel', 'inspector-content');
        this.queryInterface = new QueryInterface();

        // Set up event handlers
        this.setupEventHandlers();

        // Set up control buttons
        this.setupControls();

        // Load initial data
        await this.loadGraph();

        // Start status update interval
        this.startStatusUpdates();

        console.log('Application initialized');
    }

    /**
     * Set up event handlers between components.
     */
    setupEventHandlers() {
        // Graph node selection
        this.graphRenderer.onNodeSelect = (nodeId) => {
            this.nodeInspector.displayNode(nodeId);
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

        // Filter changes
        this.queryInterface.onFilter = async (filters) => {
            await this.loadGraph(filters);
        };
    }

    /**
     * Set up control buttons.
     */
    setupControls() {
        // Zoom controls
        document.getElementById('zoom-in').addEventListener('click', () => {
            this.graphRenderer.zoomIn();
        });

        document.getElementById('zoom-out').addEventListener('click', () => {
            this.graphRenderer.zoomOut();
        });

        document.getElementById('center-btn').addEventListener('click', () => {
            this.graphRenderer.center();
        });

        // Header controls
        document.getElementById('fit-btn').addEventListener('click', () => {
            this.graphRenderer.fit();
        });

        document.getElementById('refresh-btn').addEventListener('click', async () => {
            await this.loadGraph(this.queryInterface.getFilters());
        });
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
                limit: 500
            });

            // Load stats
            this.stats = await api.getStats();

            // Render graph
            this.graphRenderer.loadGraph(graphData);

            // Update status bar
            this.updateStatusBar();

        } catch (error) {
            console.error('Failed to load graph:', error);
            this.graphRenderer.hideLoading();
            this.setConnectionStatus(false);
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
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
    app.init().catch(error => {
        console.error('Failed to initialize application:', error);
    });

    // Expose app globally for debugging
    window.app = app;
});
