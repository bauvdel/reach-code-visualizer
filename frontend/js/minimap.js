/**
 * Mini-map Overview for REACH Code Visualizer
 * Shows bird's-eye view of the graph with viewport indicator
 */

class Minimap {
    constructor(graphRenderer) {
        this.graphRenderer = graphRenderer;
        this.isVisible = true;
        this.canvas = null;
        this.ctx = null;
        this.viewport = { x: 0, y: 0, width: 0, height: 0 };
        this.graphBounds = { minX: 0, maxX: 0, minY: 0, maxY: 0 };
        this.scale = 1;
        this.isDragging = false;
        this.nodePositions = new Map();

        this.init();
    }

    init() {
        this.createCanvas();
        this.bindEvents();
    }

    createCanvas() {
        this.container = document.getElementById('minimap');
        if (!this.container) return;

        // Use existing canvas container or create new one
        const canvasContainer = document.getElementById('minimap-canvas');

        // Create canvas element
        this.canvas = document.createElement('canvas');
        this.canvas.width = 200;
        this.canvas.height = 150;
        this.canvas.style.cursor = 'move';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';

        if (canvasContainer) {
            canvasContainer.appendChild(this.canvas);
        } else {
            this.container.appendChild(this.canvas);
        }

        this.ctx = this.canvas.getContext('2d');
    }

    bindEvents() {
        if (!this.canvas) return;

        // Mouse events for viewport panning
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', () => this.onMouseUp());
        this.canvas.addEventListener('mouseleave', () => this.onMouseUp());

        // Touch events
        this.canvas.addEventListener('touchstart', (e) => this.onTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.onTouchMove(e));
        this.canvas.addEventListener('touchend', () => this.onMouseUp());

        // Toggle visibility
        const toggleBtn = document.getElementById('toggle-minimap');
        toggleBtn?.addEventListener('click', () => this.toggle());

        // Update on graph changes
        if (this.graphRenderer?.network) {
            this.graphRenderer.network.on('afterDrawing', () => this.update());
            this.graphRenderer.network.on('zoom', () => this.updateViewport());
            this.graphRenderer.network.on('dragEnd', () => this.updateViewport());
        }
    }

    /**
     * Connect to the graph renderer's network
     */
    setNetwork(network) {
        if (network) {
            network.on('afterDrawing', () => this.update());
            network.on('zoom', () => this.updateViewport());
            network.on('dragEnd', () => this.updateViewport());
        }
    }

    /**
     * Toggle minimap visibility
     */
    toggle() {
        this.isVisible = !this.isVisible;
        if (this.container) {
            this.container.style.display = this.isVisible ? 'block' : 'none';
        }
    }

    /**
     * Show minimap
     */
    show() {
        this.isVisible = true;
        if (this.container) {
            this.container.style.display = 'block';
        }
        this.update();
    }

    /**
     * Hide minimap
     */
    hide() {
        this.isVisible = false;
        if (this.container) {
            this.container.style.display = 'none';
        }
    }

    /**
     * Update minimap display
     */
    update() {
        if (!this.isVisible || !this.ctx || !this.graphRenderer?.network) return;

        this.updateNodePositions();
        this.calculateBounds();
        this.calculateScale();
        this.draw();
    }

    /**
     * Update cached node positions from network
     */
    updateNodePositions() {
        if (!this.graphRenderer?.network) return;

        this.nodePositions.clear();
        const positions = this.graphRenderer.network.getPositions();

        for (const [id, pos] of Object.entries(positions)) {
            this.nodePositions.set(id, pos);
        }
    }

    /**
     * Calculate graph bounds
     */
    calculateBounds() {
        if (this.nodePositions.size === 0) {
            this.graphBounds = { minX: -100, maxX: 100, minY: -100, maxY: 100 };
            return;
        }

        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;

        this.nodePositions.forEach(pos => {
            minX = Math.min(minX, pos.x);
            maxX = Math.max(maxX, pos.x);
            minY = Math.min(minY, pos.y);
            maxY = Math.max(maxY, pos.y);
        });

        // Add padding
        const padding = 50;
        this.graphBounds = {
            minX: minX - padding,
            maxX: maxX + padding,
            minY: minY - padding,
            maxY: maxY + padding
        };
    }

    /**
     * Calculate scale to fit graph in minimap
     */
    calculateScale() {
        const graphWidth = this.graphBounds.maxX - this.graphBounds.minX;
        const graphHeight = this.graphBounds.maxY - this.graphBounds.minY;

        const scaleX = this.canvas.width / graphWidth;
        const scaleY = this.canvas.height / graphHeight;

        this.scale = Math.min(scaleX, scaleY, 1);
    }

    /**
     * Update viewport rectangle based on current view
     */
    updateViewport() {
        if (!this.graphRenderer?.network) return;

        const viewPosition = this.graphRenderer.network.getViewPosition();
        const scale = this.graphRenderer.network.getScale();
        const canvas = this.graphRenderer.network.canvas.frame.canvas;

        const viewWidth = canvas.width / scale;
        const viewHeight = canvas.height / scale;

        this.viewport = {
            x: viewPosition.x - viewWidth / 2,
            y: viewPosition.y - viewHeight / 2,
            width: viewWidth,
            height: viewHeight
        };

        this.draw();
    }

    /**
     * Draw the minimap
     */
    draw() {
        if (!this.ctx) return;

        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;

        // Clear canvas
        ctx.fillStyle = '#1e1e2e';
        ctx.fillRect(0, 0, width, height);

        // Draw border
        ctx.strokeStyle = '#3d3d5c';
        ctx.lineWidth = 1;
        ctx.strokeRect(0, 0, width, height);

        // Draw nodes
        this.drawNodes();

        // Draw edges (simplified)
        this.drawEdges();

        // Draw viewport rectangle
        this.drawViewport();
    }

    /**
     * Draw nodes on minimap
     */
    drawNodes() {
        const ctx = this.ctx;

        // Group nodes by type for color coding
        const typeColors = {
            function: '#61afef',
            class: '#c678dd',
            signal: '#98c379',
            variable: '#e5c07b',
            scene: '#e06c75',
            resource: '#56b6c2'
        };

        this.nodePositions.forEach((pos, id) => {
            const x = this.graphToMinimapX(pos.x);
            const y = this.graphToMinimapY(pos.y);

            // Get node type from graph renderer
            const nodeData = this.graphRenderer?.nodes?.get(id);
            const type = nodeData?.group || 'function';
            const color = typeColors[type] || '#61afef';

            ctx.beginPath();
            ctx.arc(x, y, 2, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
        });
    }

    /**
     * Draw edges on minimap (simplified)
     */
    drawEdges() {
        if (!this.graphRenderer?.edges) return;

        const ctx = this.ctx;
        ctx.strokeStyle = 'rgba(100, 100, 150, 0.3)';
        ctx.lineWidth = 0.5;

        const edges = this.graphRenderer.edges.get();

        edges.forEach(edge => {
            const fromPos = this.nodePositions.get(edge.from);
            const toPos = this.nodePositions.get(edge.to);

            if (fromPos && toPos) {
                ctx.beginPath();
                ctx.moveTo(
                    this.graphToMinimapX(fromPos.x),
                    this.graphToMinimapY(fromPos.y)
                );
                ctx.lineTo(
                    this.graphToMinimapX(toPos.x),
                    this.graphToMinimapY(toPos.y)
                );
                ctx.stroke();
            }
        });
    }

    /**
     * Draw viewport rectangle
     */
    drawViewport() {
        const ctx = this.ctx;

        const x = this.graphToMinimapX(this.viewport.x);
        const y = this.graphToMinimapY(this.viewport.y);
        const width = this.viewport.width * this.scale;
        const height = this.viewport.height * this.scale;

        // Draw viewport rectangle
        ctx.strokeStyle = '#ff6b35';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);

        // Draw semi-transparent fill
        ctx.fillStyle = 'rgba(255, 107, 53, 0.1)';
        ctx.fillRect(x, y, width, height);
    }

    /**
     * Convert graph X coordinate to minimap X
     */
    graphToMinimapX(graphX) {
        return (graphX - this.graphBounds.minX) * this.scale;
    }

    /**
     * Convert graph Y coordinate to minimap Y
     */
    graphToMinimapY(graphY) {
        return (graphY - this.graphBounds.minY) * this.scale;
    }

    /**
     * Convert minimap X to graph X
     */
    minimapToGraphX(minimapX) {
        return minimapX / this.scale + this.graphBounds.minX;
    }

    /**
     * Convert minimap Y to graph Y
     */
    minimapToGraphY(minimapY) {
        return minimapY / this.scale + this.graphBounds.minY;
    }

    /**
     * Handle mouse down on minimap
     */
    onMouseDown(e) {
        this.isDragging = true;
        this.panToPosition(e);
    }

    /**
     * Handle mouse move on minimap
     */
    onMouseMove(e) {
        if (this.isDragging) {
            this.panToPosition(e);
        }
    }

    /**
     * Handle mouse up
     */
    onMouseUp() {
        this.isDragging = false;
    }

    /**
     * Handle touch start
     */
    onTouchStart(e) {
        e.preventDefault();
        this.isDragging = true;
        if (e.touches.length > 0) {
            this.panToPosition(e.touches[0]);
        }
    }

    /**
     * Handle touch move
     */
    onTouchMove(e) {
        e.preventDefault();
        if (this.isDragging && e.touches.length > 0) {
            this.panToPosition(e.touches[0]);
        }
    }

    /**
     * Pan graph to position clicked on minimap
     */
    panToPosition(e) {
        if (!this.graphRenderer?.network) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const graphX = this.minimapToGraphX(x);
        const graphY = this.minimapToGraphY(y);

        this.graphRenderer.network.moveTo({
            position: { x: graphX, y: graphY },
            animation: {
                duration: 200,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    /**
     * Refresh minimap data
     */
    refresh() {
        this.update();
        this.updateViewport();
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Minimap;
}
