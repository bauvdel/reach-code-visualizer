/**
 * Path Highlighting System for REACH Code Visualizer
 * Visualizes paths between nodes with animated edges
 */

class PathHighlighter {
    constructor(graphRenderer, apiClient) {
        this.graphRenderer = graphRenderer;
        this.apiClient = apiClient;
        this.isPathMode = false;
        this.sourceNode = null;
        this.targetNode = null;
        this.currentPath = [];
        this.highlightedNodes = new Set();
        this.highlightedEdges = new Set();
        this.originalColors = new Map();

        this.init();
    }

    init() {
        this.cacheElements();
        this.bindEvents();
    }

    cacheElements() {
        this.pathModeBtn = document.getElementById('find-path-btn');
        this.pathBanner = document.getElementById('path-banner');
        this.pathStatusSpan = document.getElementById('path-status');
        this.cancelPathBtn = document.getElementById('cancel-path');
        this.clearAllBtn = document.getElementById('clear-highlights-btn');
    }

    bindEvents() {
        this.pathModeBtn?.addEventListener('click', () => this.togglePathMode());
        this.cancelPathBtn?.addEventListener('click', () => this.clearAll());
        this.clearAllBtn?.addEventListener('click', () => this.clearPath());
    }

    /**
     * Toggle path selection mode
     */
    togglePathMode() {
        this.isPathMode = !this.isPathMode;

        if (this.pathModeBtn) {
            this.pathModeBtn.classList.toggle('active', this.isPathMode);
        }

        if (this.isPathMode) {
            this.showBanner();
            this.sourceNode = null;
            this.targetNode = null;
            this.updateBannerText();
            window.showToast?.('Click a node to set path source', 'info');
        } else {
            this.hideBanner();
            this.clearPath();
        }
    }

    /**
     * Enable path mode programmatically
     */
    enablePathMode() {
        if (!this.isPathMode) {
            this.togglePathMode();
        }
    }

    /**
     * Disable path mode
     */
    disablePathMode() {
        if (this.isPathMode) {
            this.isPathMode = false;
            this.pathModeBtn?.classList.remove('active');
            this.hideBanner();
        }
    }

    showBanner() {
        this.pathBanner?.classList.remove('hidden');
    }

    hideBanner() {
        this.pathBanner?.classList.add('hidden');
    }

    updateBannerText() {
        if (this.pathStatusSpan) {
            if (!this.sourceNode) {
                this.pathStatusSpan.textContent = 'Click first node';
            } else if (!this.targetNode) {
                this.pathStatusSpan.textContent = `From: ${this.sourceNode.label || this.sourceNode.id} → Click target`;
            } else {
                this.pathStatusSpan.textContent = `${this.sourceNode.label || this.sourceNode.id} → ${this.targetNode.label || this.targetNode.id}`;
            }
        }
    }

    /**
     * Handle node click in path mode
     */
    handleNodeClick(nodeId, nodeData) {
        if (!this.isPathMode) return false;

        if (!this.sourceNode) {
            // Set source node
            this.sourceNode = { id: nodeId, label: nodeData?.label || nodeId };
            this.highlightSourceNode(nodeId);
            this.updateBannerText();
            window.showToast?.('Source set. Click another node for target', 'info');
            return true;
        } else if (!this.targetNode && nodeId !== this.sourceNode.id) {
            // Set target node
            this.targetNode = { id: nodeId, label: nodeData?.label || nodeId };
            this.highlightTargetNode(nodeId);
            this.updateBannerText();
            this.findAndHighlightPath();
            return true;
        }

        return false;
    }

    /**
     * Find path between source and target
     */
    async findAndHighlightPath() {
        if (!this.sourceNode || !this.targetNode) return;

        window.showToast?.('Finding path...', 'info');

        try {
            // Call API to find path
            const response = await this.apiClient.query(
                `path from "${this.sourceNode.id}" to "${this.targetNode.id}"`
            );

            if (response.success && response.path && response.path.length > 0) {
                this.currentPath = response.path;
                this.highlightPath(response.path);
                window.showToast?.(`Found path with ${response.path.length} nodes`, 'success');
            } else {
                window.showToast?.('No path found between nodes', 'warning');
            }
        } catch (error) {
            console.error('Path finding error:', error);
            window.showToast?.('Error finding path', 'error');
        }
    }

    /**
     * Highlight source node
     */
    highlightSourceNode(nodeId) {
        if (!this.graphRenderer?.network) return;

        const network = this.graphRenderer.network;
        const nodes = this.graphRenderer.nodes;

        // Store original color
        const nodeData = nodes.get(nodeId);
        if (nodeData) {
            this.originalColors.set(nodeId, {
                color: nodeData.color,
                borderWidth: nodeData.borderWidth
            });

            // Update node appearance
            nodes.update({
                id: nodeId,
                color: {
                    background: '#28a745',
                    border: '#155724',
                    highlight: { background: '#34ce57', border: '#1a7431 ' }
                },
                borderWidth: 4
            });

            this.highlightedNodes.add(nodeId);
        }
    }

    /**
     * Highlight target node
     */
    highlightTargetNode(nodeId) {
        if (!this.graphRenderer?.network) return;

        const nodes = this.graphRenderer.nodes;
        const nodeData = nodes.get(nodeId);

        if (nodeData) {
            this.originalColors.set(nodeId, {
                color: nodeData.color,
                borderWidth: nodeData.borderWidth
            });

            nodes.update({
                id: nodeId,
                color: {
                    background: '#dc3545',
                    border: '#721c24',
                    highlight: { background: '#e4606d', border: '#8b2131 ' }
                },
                borderWidth: 4
            });

            this.highlightedNodes.add(nodeId);
        }
    }

    /**
     * Highlight the entire path
     */
    highlightPath(path) {
        if (!this.graphRenderer?.network) return;

        const nodes = this.graphRenderer.nodes;
        const edges = this.graphRenderer.edges;

        // Highlight intermediate nodes
        for (let i = 1; i < path.length - 1; i++) {
            const nodeId = path[i];
            const nodeData = nodes.get(nodeId);

            if (nodeData && !this.highlightedNodes.has(nodeId)) {
                this.originalColors.set(nodeId, {
                    color: nodeData.color,
                    borderWidth: nodeData.borderWidth
                });

                nodes.update({
                    id: nodeId,
                    color: {
                        background: '#ffc107',
                        border: '#d39e00',
                        highlight: { background: '#ffcd39', border: '#e0a800' }
                    },
                    borderWidth: 3
                });

                this.highlightedNodes.add(nodeId);
            }
        }

        // Highlight edges along the path
        for (let i = 0; i < path.length - 1; i++) {
            const fromId = path[i];
            const toId = path[i + 1];

            // Find edge between these nodes
            const allEdges = edges.get();
            for (const edge of allEdges) {
                if ((edge.from === fromId && edge.to === toId) ||
                    (edge.from === toId && edge.to === fromId)) {

                    this.originalColors.set(`edge_${edge.id}`, {
                        color: edge.color,
                        width: edge.width
                    });

                    edges.update({
                        id: edge.id,
                        color: { color: '#ff6b35', highlight: '#ff8c5a' },
                        width: 4,
                        dashes: false
                    });

                    this.highlightedEdges.add(edge.id);
                }
            }
        }

        // Focus on the path
        this.graphRenderer.network.fit({
            nodes: path,
            animation: { duration: 500, easingFunction: 'easeInOutQuad' }
        });
    }

    /**
     * Clear current path highlighting
     */
    clearPath() {
        if (!this.graphRenderer?.network) return;

        const nodes = this.graphRenderer.nodes;
        const edges = this.graphRenderer.edges;

        // Restore original node colors
        for (const nodeId of this.highlightedNodes) {
            const original = this.originalColors.get(nodeId);
            if (original) {
                nodes.update({
                    id: nodeId,
                    color: original.color,
                    borderWidth: original.borderWidth || 1
                });
            }
        }

        // Restore original edge colors
        for (const edgeId of this.highlightedEdges) {
            const original = this.originalColors.get(`edge_${edgeId}`);
            if (original) {
                edges.update({
                    id: edgeId,
                    color: original.color,
                    width: original.width || 1
                });
            }
        }

        // Clear tracking
        this.highlightedNodes.clear();
        this.highlightedEdges.clear();
        this.originalColors.clear();
        this.currentPath = [];
        this.sourceNode = null;
        this.targetNode = null;

        this.updateBannerText();
    }

    /**
     * Clear all and exit path mode
     */
    clearAll() {
        this.clearPath();
        this.disablePathMode();
    }

    /**
     * Set path programmatically (without clicks)
     */
    async setPath(sourceId, targetId) {
        this.sourceNode = { id: sourceId, label: sourceId };
        this.targetNode = { id: targetId, label: targetId };

        this.highlightSourceNode(sourceId);
        this.highlightTargetNode(targetId);
        this.showBanner();
        this.updateBannerText();

        await this.findAndHighlightPath();
    }

    /**
     * Get current path info
     */
    getPathInfo() {
        return {
            source: this.sourceNode,
            target: this.targetNode,
            path: this.currentPath,
            length: this.currentPath.length
        };
    }

    /**
     * Check if in path mode
     */
    isActive() {
        return this.isPathMode;
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PathHighlighter;
}
