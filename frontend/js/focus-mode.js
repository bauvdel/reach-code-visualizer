/**
 * Focus Mode for REACH Code Visualizer
 * Shows only a node and its neighbors within configurable depth
 */

class FocusMode {
    constructor(graphRenderer) {
        this.graphRenderer = graphRenderer;
        this.isActive = false;
        this.focusedNodeId = null;
        this.focusDepth = 2;
        this.allNodes = [];
        this.allEdges = [];
        this.visibleNodes = new Set();
        this.visibleEdges = new Set();

        this.init();
    }

    init() {
        this.cacheElements();
        this.bindEvents();
    }

    cacheElements() {
        this.focusModeBtn = document.getElementById('toggle-focus-mode');
        this.focusBanner = document.getElementById('focus-banner');
        this.focusNodeSpan = document.getElementById('focus-node-name');
        this.depthSlider = document.getElementById('focus-depth');
        this.depthValue = document.getElementById('focus-depth-value');
        this.exitFocusBtn = document.getElementById('exit-focus');
    }

    bindEvents() {
        this.focusModeBtn?.addEventListener('click', () => this.toggleFocusMode());
        this.exitFocusBtn?.addEventListener('click', () => this.exitFocusMode());

        this.depthSlider?.addEventListener('input', (e) => {
            this.focusDepth = parseInt(e.target.value);
            if (this.depthValue) {
                this.depthValue.textContent = this.focusDepth;
            }
            if (this.isActive && this.focusedNodeId) {
                this.applyFocus(this.focusedNodeId);
            }
        });
    }

    /**
     * Cache all graph data for focus filtering
     */
    setGraphData(nodes, edges) {
        this.allNodes = nodes;
        this.allEdges = edges;
        this.buildAdjacencyMap();
    }

    /**
     * Build adjacency map for efficient neighbor lookup
     */
    buildAdjacencyMap() {
        this.adjacency = new Map();

        this.allNodes.forEach(node => {
            this.adjacency.set(node.id, { incoming: [], outgoing: [] });
        });

        this.allEdges.forEach(edge => {
            if (this.adjacency.has(edge.from)) {
                this.adjacency.get(edge.from).outgoing.push({
                    nodeId: edge.to,
                    edgeId: edge.id
                });
            }
            if (this.adjacency.has(edge.to)) {
                this.adjacency.get(edge.to).incoming.push({
                    nodeId: edge.from,
                    edgeId: edge.id
                });
            }
        });
    }

    /**
     * Toggle focus mode on/off
     */
    toggleFocusMode() {
        if (this.isActive) {
            this.exitFocusMode();
        } else {
            this.enableFocusMode();
        }
    }

    /**
     * Enable focus mode (waiting for node selection)
     */
    enableFocusMode() {
        this.isActive = true;
        this.focusModeBtn?.classList.add('active');
        window.showToast?.('Click a node to focus on it', 'info');
    }

    /**
     * Exit focus mode and restore full graph
     */
    exitFocusMode() {
        this.isActive = false;
        this.focusedNodeId = null;
        this.focusModeBtn?.classList.remove('active');
        this.hideBanner();

        // Restore full graph
        if (this.graphRenderer) {
            this.graphRenderer.updateData(this.allNodes, this.allEdges);
        }

        window.showToast?.('Focus mode exited', 'info');
    }

    /**
     * Handle node click in focus mode
     */
    handleNodeClick(nodeId, nodeData) {
        if (!this.isActive) return false;

        this.focusedNodeId = nodeId;
        this.applyFocus(nodeId);
        this.showBanner(nodeData?.label || nodeId);

        return true;
    }

    /**
     * Focus on a specific node programmatically
     */
    focusOnNode(nodeId, depth = null) {
        if (depth !== null) {
            this.focusDepth = depth;
            if (this.depthSlider) {
                this.depthSlider.value = depth;
                this.depthValue.textContent = depth;
            }
        }

        this.isActive = true;
        this.focusedNodeId = nodeId;
        this.applyFocus(nodeId);

        const nodeData = this.allNodes.find(n => n.id === nodeId);
        this.showBanner(nodeData?.label || nodeId);
    }

    /**
     * Apply focus filter to show only nodes within depth
     */
    applyFocus(centerNodeId) {
        // Find all nodes within depth using BFS
        const nodesAtDepth = this.getNodesWithinDepth(centerNodeId, this.focusDepth);
        this.visibleNodes = nodesAtDepth;

        // Get edges connecting visible nodes
        this.visibleEdges = new Set();
        const edgesToShow = this.allEdges.filter(edge => {
            const isVisible = nodesAtDepth.has(edge.from) && nodesAtDepth.has(edge.to);
            if (isVisible) {
                this.visibleEdges.add(edge.id);
            }
            return isVisible;
        });

        // Get visible nodes
        const nodesToShow = this.allNodes.filter(node => nodesAtDepth.has(node.id));

        // Add depth information to nodes for coloring
        const nodesWithDepth = nodesToShow.map(node => {
            const depth = this.getDepthFromCenter(centerNodeId, node.id);
            return {
                ...node,
                _focusDepth: depth,
                color: this.getDepthColor(depth, node.color)
            };
        });

        // Update graph
        if (this.graphRenderer) {
            this.graphRenderer.updateData(nodesWithDepth, edgesToShow);

            // Focus on the center node
            setTimeout(() => {
                this.graphRenderer.network?.focus(centerNodeId, {
                    scale: 1.2,
                    animation: { duration: 500, easingFunction: 'easeInOutQuad' }
                });
            }, 100);
        }

        const hiddenCount = this.allNodes.length - nodesToShow.length;
        window.showToast?.(`Showing ${nodesToShow.length} nodes (${hiddenCount} hidden)`, 'info');
    }

    /**
     * Get all nodes within specified depth from center
     */
    getNodesWithinDepth(centerId, maxDepth) {
        const visited = new Set([centerId]);
        const queue = [{ nodeId: centerId, depth: 0 }];

        while (queue.length > 0) {
            const { nodeId, depth } = queue.shift();

            if (depth >= maxDepth) continue;

            const neighbors = this.adjacency.get(nodeId);
            if (!neighbors) continue;

            // Add incoming neighbors
            for (const { nodeId: neighborId } of neighbors.incoming) {
                if (!visited.has(neighborId)) {
                    visited.add(neighborId);
                    queue.push({ nodeId: neighborId, depth: depth + 1 });
                }
            }

            // Add outgoing neighbors
            for (const { nodeId: neighborId } of neighbors.outgoing) {
                if (!visited.has(neighborId)) {
                    visited.add(neighborId);
                    queue.push({ nodeId: neighborId, depth: depth + 1 });
                }
            }
        }

        return visited;
    }

    /**
     * Get depth of a node from center using BFS
     */
    getDepthFromCenter(centerId, nodeId) {
        if (centerId === nodeId) return 0;

        const visited = new Set([centerId]);
        const queue = [{ nodeId: centerId, depth: 0 }];

        while (queue.length > 0) {
            const { nodeId: currentId, depth } = queue.shift();

            const neighbors = this.adjacency.get(currentId);
            if (!neighbors) continue;

            const allNeighbors = [
                ...neighbors.incoming.map(n => n.nodeId),
                ...neighbors.outgoing.map(n => n.nodeId)
            ];

            for (const neighborId of allNeighbors) {
                if (neighborId === nodeId) {
                    return depth + 1;
                }
                if (!visited.has(neighborId)) {
                    visited.add(neighborId);
                    queue.push({ nodeId: neighborId, depth: depth + 1 });
                }
            }
        }

        return -1; // Not connected
    }

    /**
     * Get color based on depth from center
     */
    getDepthColor(depth, originalColor) {
        const depthColors = [
            '#ff6b35', // Center - bright orange
            '#f7c548', // Depth 1 - yellow
            '#45b7aa', // Depth 2 - teal
            '#5d8aa8', // Depth 3 - blue
            '#8b7da8', // Depth 4 - purple
            '#a87d8b'  // Depth 5+ - muted pink
        ];

        const color = depthColors[Math.min(depth, depthColors.length - 1)];

        return {
            background: color,
            border: this.darkenColor(color, 20),
            highlight: {
                background: this.lightenColor(color, 10),
                border: this.darkenColor(color, 10)
            }
        };
    }

    /**
     * Show focus mode banner
     */
    showBanner(nodeName) {
        this.focusBanner?.classList.remove('hidden');
        if (this.focusNodeSpan) {
            this.focusNodeSpan.textContent = nodeName;
        }
    }

    /**
     * Hide focus mode banner
     */
    hideBanner() {
        this.focusBanner?.classList.add('hidden');
    }

    /**
     * Check if focus mode is active
     */
    isFocusModeActive() {
        return this.isActive;
    }

    /**
     * Get current focus info
     */
    getFocusInfo() {
        return {
            active: this.isActive,
            focusedNode: this.focusedNodeId,
            depth: this.focusDepth,
            visibleNodeCount: this.visibleNodes.size,
            hiddenNodeCount: this.allNodes.length - this.visibleNodes.size
        };
    }

    /**
     * Darken a hex color
     */
    darkenColor(hex, percent) {
        const num = parseInt(hex.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.max((num >> 16) - amt, 0);
        const G = Math.max((num >> 8 & 0x00FF) - amt, 0);
        const B = Math.max((num & 0x0000FF) - amt, 0);
        return `#${(1 << 24 | R << 16 | G << 8 | B).toString(16).slice(1)}`;
    }

    /**
     * Lighten a hex color
     */
    lightenColor(hex, percent) {
        const num = parseInt(hex.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = Math.min((num >> 16) + amt, 255);
        const G = Math.min((num >> 8 & 0x00FF) + amt, 255);
        const B = Math.min((num & 0x0000FF) + amt, 255);
        return `#${(1 << 24 | R << 16 | G << 8 | B).toString(16).slice(1)}`;
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FocusMode;
}
