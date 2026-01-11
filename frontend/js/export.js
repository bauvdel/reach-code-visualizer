/**
 * Export Functionality for REACH Code Visualizer
 * Supports PNG, SVG, and JSON export
 */

class ExportManager {
    constructor(graphRenderer) {
        this.graphRenderer = graphRenderer;

        this.init();
    }

    init() {
        this.cacheElements();
        this.bindEvents();
    }

    cacheElements() {
        this.exportPngBtn = document.getElementById('export-png');
        this.exportSvgBtn = document.getElementById('export-svg');
        this.exportJsonBtn = document.getElementById('export-json');
    }

    bindEvents() {
        this.exportPngBtn?.addEventListener('click', () => this.exportPng());
        this.exportSvgBtn?.addEventListener('click', () => this.exportSvg());
        this.exportJsonBtn?.addEventListener('click', () => this.exportJson());
    }

    /**
     * Export graph as PNG using html2canvas
     */
    async exportPng() {
        if (!this.graphRenderer?.network) {
            window.showToast?.('No graph to export', 'warning');
            return;
        }

        window.showToast?.('Generating PNG...', 'info');

        try {
            // Get the canvas from vis.js
            const canvas = this.graphRenderer.network.canvas.frame.canvas;

            // Create a new canvas with white/dark background
            const exportCanvas = document.createElement('canvas');
            const ctx = exportCanvas.getContext('2d');

            // Set dimensions with some padding
            const padding = 40;
            exportCanvas.width = canvas.width + padding * 2;
            exportCanvas.height = canvas.height + padding * 2;

            // Fill background
            ctx.fillStyle = '#1e1e2e'; // Dark background
            ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);

            // Draw the graph canvas
            ctx.drawImage(canvas, padding, padding);

            // Add title/watermark
            ctx.fillStyle = '#8b8b8b';
            ctx.font = '12px monospace';
            ctx.fillText('REACH Code Visualizer', padding, exportCanvas.height - 15);
            ctx.fillText(new Date().toLocaleString(), exportCanvas.width - 180, exportCanvas.height - 15);

            // Convert to blob and download
            exportCanvas.toBlob((blob) => {
                this.downloadBlob(blob, 'reach-graph.png');
                window.showToast?.('PNG exported successfully', 'success');
            }, 'image/png');

        } catch (error) {
            console.error('PNG export error:', error);
            window.showToast?.('Failed to export PNG', 'error');
        }
    }

    /**
     * Export graph as SVG
     */
    exportSvg() {
        if (!this.graphRenderer?.network) {
            window.showToast?.('No graph to export', 'warning');
            return;
        }

        window.showToast?.('Generating SVG...', 'info');

        try {
            const nodes = this.graphRenderer.nodes.get();
            const edges = this.graphRenderer.edges.get();
            const positions = this.graphRenderer.network.getPositions();

            // Calculate bounds
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;

            Object.values(positions).forEach(pos => {
                minX = Math.min(minX, pos.x);
                maxX = Math.max(maxX, pos.x);
                minY = Math.min(minY, pos.y);
                maxY = Math.max(maxY, pos.y);
            });

            const padding = 100;
            const width = maxX - minX + padding * 2;
            const height = maxY - minY + padding * 2;
            const offsetX = -minX + padding;
            const offsetY = -minY + padding;

            // Build SVG
            let svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <style>
    .node-label { font-family: monospace; font-size: 12px; fill: #e0e0e0; }
    .edge { stroke: #666; stroke-width: 1; fill: none; }
    .node-function { fill: #61afef; }
    .node-class { fill: #c678dd; }
    .node-signal { fill: #98c379; }
    .node-variable { fill: #e5c07b; }
    .node-scene { fill: #e06c75; }
    .node-default { fill: #56b6c2; }
  </style>
  <rect width="100%" height="100%" fill="#1e1e2e"/>

  <!-- Edges -->
  <g class="edges">`;

            // Draw edges
            edges.forEach(edge => {
                const fromPos = positions[edge.from];
                const toPos = positions[edge.to];

                if (fromPos && toPos) {
                    const x1 = fromPos.x + offsetX;
                    const y1 = fromPos.y + offsetY;
                    const x2 = toPos.x + offsetX;
                    const y2 = toPos.y + offsetY;

                    svg += `
    <line class="edge" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
                }
            });

            svg += `
  </g>

  <!-- Nodes -->
  <g class="nodes">`;

            // Draw nodes
            nodes.forEach(node => {
                const pos = positions[node.id];
                if (!pos) return;

                const x = pos.x + offsetX;
                const y = pos.y + offsetY;
                const radius = 8;
                const nodeClass = `node-${node.group || 'default'}`;
                const label = node.label || node.id;

                svg += `
    <g class="node" data-id="${this.escapeXml(node.id)}">
      <circle class="${nodeClass}" cx="${x}" cy="${y}" r="${radius}"/>
      <text class="node-label" x="${x}" y="${y + 20}" text-anchor="middle">${this.escapeXml(label)}</text>
    </g>`;
            });

            svg += `
  </g>

  <!-- Watermark -->
  <text x="20" y="${height - 20}" fill="#666" font-family="monospace" font-size="10">
    REACH Code Visualizer - ${new Date().toLocaleDateString()}
  </text>
</svg>`;

            // Download
            const blob = new Blob([svg], { type: 'image/svg+xml' });
            this.downloadBlob(blob, 'reach-graph.svg');
            window.showToast?.('SVG exported successfully', 'success');

        } catch (error) {
            console.error('SVG export error:', error);
            window.showToast?.('Failed to export SVG', 'error');
        }
    }

    /**
     * Export graph data as JSON
     */
    exportJson() {
        if (!this.graphRenderer?.network) {
            window.showToast?.('No graph to export', 'warning');
            return;
        }

        window.showToast?.('Generating JSON...', 'info');

        try {
            const nodes = this.graphRenderer.nodes.get();
            const edges = this.graphRenderer.edges.get();
            const positions = this.graphRenderer.network.getPositions();

            // Build export data
            const exportData = {
                metadata: {
                    exportedAt: new Date().toISOString(),
                    tool: 'REACH Code Visualizer',
                    version: '1.0.0',
                    nodeCount: nodes.length,
                    edgeCount: edges.length
                },
                nodes: nodes.map(node => ({
                    id: node.id,
                    label: node.label,
                    type: node.group || 'unknown',
                    file: node.file || null,
                    line: node.line || null,
                    position: positions[node.id] || null,
                    metadata: node.metadata || {}
                })),
                edges: edges.map(edge => ({
                    id: edge.id,
                    from: edge.from,
                    to: edge.to,
                    type: edge.type || 'unknown',
                    label: edge.label || null
                })),
                statistics: this.calculateStatistics(nodes, edges)
            };

            // Download
            const json = JSON.stringify(exportData, null, 2);
            const blob = new Blob([json], { type: 'application/json' });
            this.downloadBlob(blob, 'reach-graph.json');
            window.showToast?.('JSON exported successfully', 'success');

        } catch (error) {
            console.error('JSON export error:', error);
            window.showToast?.('Failed to export JSON', 'error');
        }
    }

    /**
     * Calculate graph statistics for export
     */
    calculateStatistics(nodes, edges) {
        const nodesByType = {};
        nodes.forEach(node => {
            const type = node.group || 'unknown';
            nodesByType[type] = (nodesByType[type] || 0) + 1;
        });

        const edgesByType = {};
        edges.forEach(edge => {
            const type = edge.type || 'unknown';
            edgesByType[type] = (edgesByType[type] || 0) + 1;
        });

        // Calculate degree distribution
        const inDegree = {};
        const outDegree = {};
        nodes.forEach(node => {
            inDegree[node.id] = 0;
            outDegree[node.id] = 0;
        });

        edges.forEach(edge => {
            if (outDegree[edge.from] !== undefined) outDegree[edge.from]++;
            if (inDegree[edge.to] !== undefined) inDegree[edge.to]++;
        });

        const avgInDegree = Object.values(inDegree).reduce((a, b) => a + b, 0) / nodes.length || 0;
        const avgOutDegree = Object.values(outDegree).reduce((a, b) => a + b, 0) / nodes.length || 0;
        const maxInDegree = Math.max(...Object.values(inDegree), 0);
        const maxOutDegree = Math.max(...Object.values(outDegree), 0);

        return {
            nodesByType,
            edgesByType,
            connectivity: {
                averageInDegree: avgInDegree.toFixed(2),
                averageOutDegree: avgOutDegree.toFixed(2),
                maxInDegree,
                maxOutDegree
            }
        };
    }

    /**
     * Download a blob as a file
     */
    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Escape XML special characters
     */
    escapeXml(str) {
        if (!str) return '';
        return str.toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&apos;');
    }

    /**
     * Export visible graph only (respecting filters)
     */
    exportVisibleJson() {
        if (!this.graphRenderer?.network) {
            window.showToast?.('No graph to export', 'warning');
            return;
        }

        const visibleNodes = this.graphRenderer.nodes.get();
        const visibleEdges = this.graphRenderer.edges.get();

        const exportData = {
            metadata: {
                exportedAt: new Date().toISOString(),
                tool: 'REACH Code Visualizer',
                version: '1.0.0',
                type: 'filtered-view',
                nodeCount: visibleNodes.length,
                edgeCount: visibleEdges.length
            },
            nodes: visibleNodes,
            edges: visibleEdges
        };

        const json = JSON.stringify(exportData, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        this.downloadBlob(blob, 'reach-graph-filtered.json');
        window.showToast?.('Filtered JSON exported successfully', 'success');
    }

    /**
     * Copy graph data to clipboard
     */
    async copyToClipboard() {
        if (!this.graphRenderer?.network) {
            window.showToast?.('No graph to copy', 'warning');
            return;
        }

        try {
            const nodes = this.graphRenderer.nodes.get();
            const edges = this.graphRenderer.edges.get();

            const data = {
                nodes: nodes.map(n => ({ id: n.id, label: n.label, type: n.group })),
                edges: edges.map(e => ({ from: e.from, to: e.to, type: e.type }))
            };

            await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
            window.showToast?.('Graph data copied to clipboard', 'success');
        } catch (error) {
            console.error('Clipboard error:', error);
            window.showToast?.('Failed to copy to clipboard', 'error');
        }
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ExportManager;
}
