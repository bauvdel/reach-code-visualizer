/**
 * Graph Renderer for REACH Code Visualizer
 * Uses vis.js for interactive graph visualization.
 */

class GraphRenderer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.network = null;
        this.nodes = new vis.DataSet([]);
        this.edges = new vis.DataSet([]);
        this.selectedNode = null;

        // Event callbacks
        this.onNodeSelect = null;
        this.onNodeHover = null;

        // Node color mapping
        this.nodeColors = {
            'FUNCTION': { background: '#569cd6', border: '#4080a8', font: '#ffffff' },
            'VARIABLE': { background: '#4ec9b0', border: '#3da38d', font: '#1e1e1e' },
            'SIGNAL': { background: '#ce9178', border: '#a87360', font: '#1e1e1e' },
            'CLASS': { background: '#c586c0', border: '#9d6a99', font: '#ffffff' },
            'SCENE': { background: '#9cdcfe', border: '#7ab0cc', font: '#1e1e1e' },
            'SIGNAL_CONNECTION': { background: '#ce9178', border: '#a87360', font: '#1e1e1e' },
            'NODE_REFERENCE': { background: '#dcdcaa', border: '#b0b088', font: '#1e1e1e' },
            'RESOURCE': { background: '#b5cea8', border: '#91a686', font: '#1e1e1e' },
            'UNKNOWN': { background: '#808080', border: '#606060', font: '#ffffff' }
        };

        // Node shape mapping
        this.nodeShapes = {
            'FUNCTION': 'box',
            'VARIABLE': 'ellipse',
            'SIGNAL': 'diamond',
            'CLASS': 'box',
            'SCENE': 'hexagon',
            'SIGNAL_CONNECTION': 'triangle',
            'NODE_REFERENCE': 'dot',
            'RESOURCE': 'square',
            'UNKNOWN': 'dot'
        };

        // Edge color mapping
        this.edgeColors = {
            'CALLS': '#569cd6',
            'READS': '#4ec9b0',
            'WRITES': '#dcdcaa',
            'EMITS': '#ce9178',
            'CONNECTS_TO': '#c586c0',
            'INSTANTIATES': '#9cdcfe',
            'INHERITS': '#c586c0',
            'REFERENCES': '#808080',
            'CONTAINS': '#6d6d6d',
            'ATTACHES_TO': '#b5cea8'
        };

        this.init();
    }

    /**
     * Initialize the vis.js network.
     */
    init() {
        const options = {
            nodes: {
                font: {
                    size: 12,
                    face: 'Segoe UI, sans-serif'
                },
                borderWidth: 2,
                shadow: {
                    enabled: true,
                    size: 5,
                    x: 2,
                    y: 2
                }
            },
            edges: {
                arrows: {
                    to: { enabled: true, scaleFactor: 0.5 }
                },
                smooth: {
                    type: 'continuous',
                    roundness: 0.2
                },
                font: {
                    size: 10,
                    align: 'middle',
                    color: '#9d9d9d'
                },
                width: 1.5
            },
            physics: {
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08
                },
                stabilization: {
                    enabled: true,
                    iterations: 200,
                    updateInterval: 25
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: true,
                multiselect: true,
                navigationButtons: false,
                keyboard: {
                    enabled: true,
                    speed: { x: 10, y: 10, zoom: 0.05 }
                }
            },
            layout: {
                improvedLayout: true
            }
        };

        this.network = new vis.Network(
            this.container,
            { nodes: this.nodes, edges: this.edges },
            options
        );

        this.setupEventListeners();
    }

    /**
     * Set up network event listeners.
     */
    setupEventListeners() {
        // Node click
        this.network.on('click', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                this.selectedNode = nodeId;
                this.highlightNode(nodeId);
                if (this.onNodeSelect) {
                    this.onNodeSelect(nodeId);
                }
            } else {
                this.clearHighlight();
                this.selectedNode = null;
            }
        });

        // Node hover
        this.network.on('hoverNode', (params) => {
            this.container.style.cursor = 'pointer';
            if (this.onNodeHover) {
                this.onNodeHover(params.node);
            }
        });

        this.network.on('blurNode', () => {
            this.container.style.cursor = 'default';
        });

        // Double-click to focus on node
        this.network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                this.focusOnNode(params.nodes[0]);
            }
        });

        // Stabilization progress
        this.network.on('stabilizationProgress', (params) => {
            const progress = Math.round((params.iterations / params.total) * 100);
            this.updateLoadingProgress(progress);
        });

        this.network.on('stabilizationIterationsDone', () => {
            this.hideLoading();
        });
    }

    /**
     * Load graph data from API response.
     */
    loadGraph(data) {
        this.showLoading('Loading graph...');

        // Clear existing data
        this.nodes.clear();
        this.edges.clear();

        // Add nodes
        const visNodes = data.nodes.map(node => this.createVisNode(node));
        this.nodes.add(visNodes);

        // Add edges
        const visEdges = data.edges.map((edge, index) => this.createVisEdge(edge, index));
        this.edges.add(visEdges);

        // Start physics simulation
        this.network.stabilize();
    }

    /**
     * Create a vis.js node from API data.
     */
    createVisNode(node) {
        const type = node.type || 'UNKNOWN';
        const colors = this.nodeColors[type] || this.nodeColors['UNKNOWN'];
        const shape = this.nodeShapes[type] || 'dot';

        return {
            id: node.id,
            label: this.truncateLabel(node.name),
            title: this.createTooltip(node),
            shape: shape,
            color: {
                background: colors.background,
                border: colors.border,
                highlight: {
                    background: colors.background,
                    border: '#ffffff'
                },
                hover: {
                    background: colors.background,
                    border: '#ffffff'
                }
            },
            font: {
                color: colors.font
            },
            // Store original data for reference
            data: node
        };
    }

    /**
     * Create a vis.js edge from API data.
     */
    createVisEdge(edge, index) {
        const relationship = edge.relationship || 'UNKNOWN';
        const color = this.edgeColors[relationship] || '#808080';
        const confidence = edge.confidence || 'HIGH';

        // Determine dash style based on confidence
        let dashes = false;
        if (confidence === 'MEDIUM') {
            dashes = [5, 5];
        } else if (confidence === 'LOW') {
            dashes = [2, 2];
        }

        return {
            id: `edge-${index}`,
            from: edge.from,
            to: edge.to,
            label: relationship,
            color: {
                color: color,
                highlight: '#ffffff',
                hover: color
            },
            dashes: dashes,
            data: edge
        };
    }

    /**
     * Truncate long labels.
     */
    truncateLabel(label, maxLength = 25) {
        if (label.length <= maxLength) return label;
        return label.substring(0, maxLength - 3) + '...';
    }

    /**
     * Create tooltip HTML for a node.
     */
    createTooltip(node) {
        const lines = [
            `<strong>${node.name}</strong>`,
            `Type: ${node.type}`,
        ];
        if (node.file) {
            lines.push(`File: ${node.file}`);
        }
        if (node.line) {
            lines.push(`Line: ${node.line}`);
        }
        return lines.join('\n');
    }

    /**
     * Highlight a node and its connections.
     */
    highlightNode(nodeId) {
        const connectedNodes = this.network.getConnectedNodes(nodeId);
        const connectedEdges = this.network.getConnectedEdges(nodeId);

        // Dim all nodes
        this.nodes.forEach(node => {
            if (node.id !== nodeId && !connectedNodes.includes(node.id)) {
                this.nodes.update({
                    id: node.id,
                    opacity: 0.3
                });
            } else {
                this.nodes.update({
                    id: node.id,
                    opacity: 1
                });
            }
        });

        // Dim all edges
        this.edges.forEach(edge => {
            if (!connectedEdges.includes(edge.id)) {
                this.edges.update({
                    id: edge.id,
                    hidden: true
                });
            } else {
                this.edges.update({
                    id: edge.id,
                    hidden: false,
                    width: 3
                });
            }
        });
    }

    /**
     * Clear all highlights.
     */
    clearHighlight() {
        this.nodes.forEach(node => {
            this.nodes.update({
                id: node.id,
                opacity: 1
            });
        });

        this.edges.forEach(edge => {
            this.edges.update({
                id: edge.id,
                hidden: false,
                width: 1.5
            });
        });
    }

    /**
     * Focus on a specific node.
     */
    focusOnNode(nodeId) {
        this.network.focus(nodeId, {
            scale: 1.5,
            animation: {
                duration: 500,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    /**
     * Fit all nodes in view.
     */
    fit() {
        this.network.fit({
            animation: {
                duration: 500,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    /**
     * Zoom in.
     */
    zoomIn() {
        const scale = this.network.getScale();
        this.network.moveTo({
            scale: scale * 1.3,
            animation: { duration: 300 }
        });
    }

    /**
     * Zoom out.
     */
    zoomOut() {
        const scale = this.network.getScale();
        this.network.moveTo({
            scale: scale / 1.3,
            animation: { duration: 300 }
        });
    }

    /**
     * Center the view.
     */
    center() {
        if (this.selectedNode) {
            this.focusOnNode(this.selectedNode);
        } else {
            this.fit();
        }
    }

    /**
     * Add nodes from query results.
     */
    loadQueryResults(data) {
        // Clear existing
        this.nodes.clear();
        this.edges.clear();

        // Add nodes with highlight
        const visNodes = data.nodes.map(node => {
            const visNode = this.createVisNode(node);
            if (node.highlight) {
                visNode.borderWidth = 4;
                visNode.color.border = '#ffffff';
            }
            return visNode;
        });
        this.nodes.add(visNodes);

        // Add edges with highlight
        const visEdges = data.edges.map((edge, index) => {
            const visEdge = this.createVisEdge(edge, index);
            if (edge.highlight) {
                visEdge.width = 4;
                visEdge.color.color = '#ffffff';
            }
            return visEdge;
        });
        this.edges.add(visEdges);

        // Fit to view
        setTimeout(() => this.fit(), 100);
    }

    /**
     * Get visible node count.
     */
    getVisibleCount() {
        return this.nodes.length;
    }

    /**
     * Show loading overlay.
     */
    showLoading(text = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        const loadingText = overlay.querySelector('.loading-text');
        loadingText.textContent = text;
        overlay.classList.remove('hidden');
    }

    /**
     * Update loading progress.
     */
    updateLoadingProgress(progress) {
        const loadingText = document.querySelector('.loading-text');
        loadingText.textContent = `Stabilizing layout... ${progress}%`;
    }

    /**
     * Hide loading overlay.
     */
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        overlay.classList.add('hidden');
    }

    /**
     * Select a node programmatically.
     */
    selectNode(nodeId) {
        if (this.nodes.get(nodeId)) {
            this.network.selectNodes([nodeId]);
            this.selectedNode = nodeId;
            this.highlightNode(nodeId);
            this.focusOnNode(nodeId);
            if (this.onNodeSelect) {
                this.onNodeSelect(nodeId);
            }
        }
    }
}
