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
        this.currentLayout = 'forceAtlas2Based';

        // Event callbacks
        this.onNodeSelect = null;
        this.onNodeHover = null;
        this.onNodeDoubleClick = null;
        this.onClusterClick = null;
        this.onDataLoaded = null;

        // Node color mapping
        this.nodeColors = {
            'FUNCTION': { background: '#61afef', border: '#4080a8', font: '#ffffff' },
            'VARIABLE': { background: '#e5c07b', border: '#b8993e', font: '#1e1e1e' },
            'SIGNAL': { background: '#98c379', border: '#6b9a4b', font: '#1e1e1e' },
            'CLASS': { background: '#c678dd', border: '#9d5ab3', font: '#ffffff' },
            'SCENE': { background: '#e06c75', border: '#b35359', font: '#ffffff' },
            'SIGNAL_CONNECTION': { background: '#98c379', border: '#6b9a4b', font: '#1e1e1e' },
            'NODE_REFERENCE': { background: '#56b6c2', border: '#3d8a93', font: '#1e1e1e' },
            'RESOURCE': { background: '#d19a66', border: '#a67840', font: '#1e1e1e' },
            'UNKNOWN': { background: '#5c6370', border: '#3e4451', font: '#ffffff' }
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
            'CALLS': '#61afef',
            'READS': '#98c379',
            'WRITES': '#e5c07b',
            'EMITS': '#c678dd',
            'CONNECTS_TO': '#e06c75',
            'INSTANTIATES': '#56b6c2',
            'INHERITS': '#c678dd',
            'REFERENCES': '#5c6370',
            'CONTAINS': '#3e4451',
            'ATTACHES_TO': '#d19a66'
        };

        // Layout options
        this.layoutOptions = {
            forceAtlas2Based: {
                physics: {
                    enabled: true,
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {
                        gravitationalConstant: -50,
                        centralGravity: 0.01,
                        springLength: 100,
                        springConstant: 0.08,
                        damping: 0.4
                    },
                    stabilization: {
                        enabled: true,
                        iterations: 200,
                        updateInterval: 25
                    }
                },
                layout: { improvedLayout: true }
            },
            hierarchical: {
                physics: { enabled: false },
                layout: {
                    hierarchical: {
                        enabled: true,
                        direction: 'UD',
                        sortMethod: 'hubsize',
                        nodeSpacing: 150,
                        levelSeparation: 150,
                        treeSpacing: 200
                    }
                }
            },
            radial: {
                physics: {
                    enabled: true,
                    solver: 'repulsion',
                    repulsion: {
                        centralGravity: 0.2,
                        springLength: 200,
                        springConstant: 0.05,
                        nodeDistance: 100,
                        damping: 0.09
                    },
                    stabilization: { enabled: true, iterations: 150 }
                },
                layout: { improvedLayout: true }
            },
            circular: {
                physics: { enabled: false },
                layout: { improvedLayout: false }
            }
        };

        this.init();
    }

    /**
     * Initialize the vis.js network.
     */
    init() {
        const options = this.getDefaultOptions();

        this.network = new vis.Network(
            this.container,
            { nodes: this.nodes, edges: this.edges },
            options
        );

        this.setupEventListeners();
    }

    /**
     * Get default network options.
     */
    getDefaultOptions() {
        return {
            nodes: {
                font: {
                    size: 12,
                    face: 'Consolas, Monaco, monospace'
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
                    color: '#8b8b8b'
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
    }

    /**
     * Set up network event listeners.
     */
    setupEventListeners() {
        // Node click
        this.network.on('click', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];

                // Check if it's a cluster
                if (this.network.isCluster(nodeId)) {
                    if (this.onClusterClick) {
                        this.onClusterClick(nodeId);
                    }
                    return;
                }

                this.selectedNode = nodeId;
                this.highlightNode(nodeId);

                const nodeData = this.nodes.get(nodeId);
                if (this.onNodeSelect) {
                    this.onNodeSelect(nodeId, nodeData);
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

        // Double-click for focus mode
        this.network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];

                // Don't focus on clusters
                if (this.network.isCluster(nodeId)) {
                    return;
                }

                if (this.onNodeDoubleClick) {
                    this.onNodeDoubleClick(nodeId);
                } else {
                    this.focusOnNode(nodeId);
                }
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

        // Notify listeners
        if (this.onDataLoaded) {
            this.onDataLoaded(visNodes, visEdges);
        }

        // Start physics simulation
        this.network.stabilize();
    }

    /**
     * Update graph data (used by filters, focus mode, etc.)
     */
    updateData(nodes, edges) {
        this.nodes.clear();
        this.edges.clear();

        this.nodes.add(nodes);
        this.edges.add(edges);

        // Fit to view
        setTimeout(() => this.fit(), 100);
    }

    /**
     * Set layout type.
     */
    setLayout(layoutType) {
        this.currentLayout = layoutType;
        const layoutConfig = this.layoutOptions[layoutType];

        if (!layoutConfig) {
            console.warn(`Unknown layout type: ${layoutType}`);
            return;
        }

        // Handle circular layout specially
        if (layoutType === 'circular') {
            this.applyCircularLayout();
            return;
        }

        // Apply layout options
        this.network.setOptions(layoutConfig);

        // Re-stabilize if physics is enabled
        if (layoutConfig.physics?.enabled) {
            this.network.stabilize();
        }
    }

    /**
     * Apply circular layout manually.
     */
    applyCircularLayout() {
        const nodeIds = this.nodes.getIds();
        const nodeCount = nodeIds.length;
        const centerX = 0;
        const centerY = 0;
        const radius = Math.max(200, nodeCount * 10);

        const positions = {};
        nodeIds.forEach((id, index) => {
            const angle = (2 * Math.PI * index) / nodeCount;
            positions[id] = {
                x: centerX + radius * Math.cos(angle),
                y: centerY + radius * Math.sin(angle)
            };
        });

        // Disable physics and set positions
        this.network.setOptions({ physics: { enabled: false } });
        this.network.setData({ nodes: this.nodes, edges: this.edges });

        nodeIds.forEach(id => {
            this.network.moveNode(id, positions[id].x, positions[id].y);
        });

        this.fit();
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
            label: this.truncateLabel(node.name || node.label || node.id),
            title: this.createTooltip(node),
            shape: shape,
            group: type.toLowerCase(),
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
            file: node.file,
            line: node.line,
            // Store original data for reference
            data: node
        };
    }

    /**
     * Create a vis.js edge from API data.
     */
    createVisEdge(edge, index) {
        const relationship = edge.relationship || edge.type || 'UNKNOWN';
        const color = this.edgeColors[relationship] || '#5c6370';
        const confidence = edge.confidence || 'HIGH';

        // Determine dash style based on confidence
        let dashes = false;
        if (confidence === 'MEDIUM') {
            dashes = [5, 5];
        } else if (confidence === 'LOW') {
            dashes = [2, 2];
        }

        return {
            id: edge.id || `edge-${index}`,
            from: edge.from,
            to: edge.to,
            type: relationship,
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
        if (!label) return '';
        if (label.length <= maxLength) return label;
        return label.substring(0, maxLength - 3) + '...';
    }

    /**
     * Create tooltip HTML for a node.
     */
    createTooltip(node) {
        const lines = [
            `<strong>${node.name || node.label || node.id}</strong>`,
            `Type: ${node.type || 'Unknown'}`,
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

        // Notify listeners
        if (this.onDataLoaded) {
            this.onDataLoaded(visNodes, visEdges);
        }

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
        if (overlay) {
            const loadingText = overlay.querySelector('.loading-text');
            if (loadingText) {
                loadingText.textContent = text;
            }
            overlay.classList.remove('hidden');
        }
    }

    /**
     * Update loading progress.
     */
    updateLoadingProgress(progress) {
        const loadingText = document.querySelector('.loading-text');
        if (loadingText) {
            loadingText.textContent = `Stabilizing layout... ${progress}%`;
        }
    }

    /**
     * Hide loading overlay.
     */
    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
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

            const nodeData = this.nodes.get(nodeId);
            if (this.onNodeSelect) {
                this.onNodeSelect(nodeId, nodeData);
            }
        }
    }

    /**
     * Get all node data.
     */
    getAllNodes() {
        return this.nodes.get();
    }

    /**
     * Get all edge data.
     */
    getAllEdges() {
        return this.edges.get();
    }

    /**
     * Get current layout type.
     */
    getCurrentLayout() {
        return this.currentLayout;
    }
}
