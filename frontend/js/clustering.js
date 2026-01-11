/**
 * Graph Clustering System for REACH Code Visualizer
 * Auto-clusters large graphs by directory, type, or modularity
 */

class ClusterManager {
    constructor(graphRenderer) {
        this.graphRenderer = graphRenderer;
        this.clusteringEnabled = false;
        this.clusterMethod = 'directory'; // directory, type, modularity
        this.clusterThreshold = 100; // Auto-cluster above this node count
        this.clusters = new Map();
        this.clusterColors = [
            '#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f',
            '#edc949', '#af7aa1', '#ff9da7', '#9c755f', '#bab0ab'
        ];

        this.init();
    }

    init() {
        this.cacheElements();
        this.bindEvents();
    }

    cacheElements() {
        this.enableClusteringCheck = document.getElementById('enable-clustering');
        this.clusterMethodSelect = document.getElementById('cluster-method');
        this.clusterThresholdInput = document.getElementById('cluster-threshold');
        this.applyClusterBtn = document.getElementById('apply-clustering');
        this.expandAllBtn = document.getElementById('expand-all-clusters');
    }

    bindEvents() {
        this.enableClusteringCheck?.addEventListener('change', (e) => {
            this.clusteringEnabled = e.target.checked;
            if (this.clusteringEnabled) {
                this.applyClustering();
            } else {
                this.expandAllClusters();
            }
        });

        this.clusterMethodSelect?.addEventListener('change', (e) => {
            this.clusterMethod = e.target.value;
            if (this.clusteringEnabled) {
                this.applyClustering();
            }
        });

        this.applyClusterBtn?.addEventListener('click', () => this.applyClustering());
        this.expandAllBtn?.addEventListener('click', () => this.expandAllClusters());
    }

    /**
     * Apply clustering based on current method
     */
    applyClustering() {
        if (!this.graphRenderer?.network) return;

        const nodes = this.graphRenderer.nodes.get();

        // Check if we should auto-cluster
        if (nodes.length < this.clusterThreshold && !this.clusteringEnabled) {
            return;
        }

        // Clear existing clusters first
        this.expandAllClusters();

        switch (this.clusterMethod) {
            case 'directory':
                this.clusterByDirectory();
                break;
            case 'type':
                this.clusterByType();
                break;
            case 'modularity':
                this.clusterByModularity();
                break;
        }

        window.showToast?.(`Clustered graph using ${this.clusterMethod} method`, 'success');
    }

    /**
     * Cluster nodes by directory/folder structure
     */
    clusterByDirectory() {
        if (!this.graphRenderer?.network) return;

        const nodes = this.graphRenderer.nodes.get();
        const directories = new Map();

        // Group nodes by directory
        nodes.forEach(node => {
            const path = node.file || node.path || '';
            const dir = this.extractDirectory(path);

            if (!directories.has(dir)) {
                directories.set(dir, []);
            }
            directories.get(dir).push(node.id);
        });

        // Create clusters for directories with multiple nodes
        let colorIndex = 0;
        directories.forEach((nodeIds, dir) => {
            if (nodeIds.length >= 3 && dir !== 'root') {
                const clusterColor = this.clusterColors[colorIndex % this.clusterColors.length];
                colorIndex++;

                const clusterOptionsByData = {
                    joinCondition: (nodeOptions) => {
                        return nodeIds.includes(nodeOptions.id);
                    },
                    clusterNodeProperties: {
                        id: `cluster_${dir}`,
                        label: `${dir} (${nodeIds.length})`,
                        shape: 'box',
                        color: {
                            background: clusterColor,
                            border: this.darkenColor(clusterColor, 20)
                        },
                        font: { color: '#ffffff', size: 14 },
                        borderWidth: 2
                    }
                };

                this.graphRenderer.network.cluster(clusterOptionsByData);
                this.clusters.set(`cluster_${dir}`, { dir, nodeIds, color: clusterColor });
            }
        });
    }

    /**
     * Cluster nodes by type (function, class, signal, etc.)
     */
    clusterByType() {
        if (!this.graphRenderer?.network) return;

        const nodes = this.graphRenderer.nodes.get();
        const types = new Map();

        // Group nodes by type
        nodes.forEach(node => {
            const type = this.getNodeType(node);

            if (!types.has(type)) {
                types.set(type, []);
            }
            types.get(type).push(node.id);
        });

        // Create clusters for types with multiple nodes
        let colorIndex = 0;
        types.forEach((nodeIds, type) => {
            if (nodeIds.length >= 5) {
                const clusterColor = this.clusterColors[colorIndex % this.clusterColors.length];
                colorIndex++;

                const clusterOptionsByData = {
                    joinCondition: (nodeOptions) => {
                        return nodeIds.includes(nodeOptions.id);
                    },
                    clusterNodeProperties: {
                        id: `cluster_${type}`,
                        label: `${type}s (${nodeIds.length})`,
                        shape: 'diamond',
                        color: {
                            background: clusterColor,
                            border: this.darkenColor(clusterColor, 20)
                        },
                        font: { color: '#ffffff', size: 14 },
                        borderWidth: 2
                    }
                };

                this.graphRenderer.network.cluster(clusterOptionsByData);
                this.clusters.set(`cluster_${type}`, { type, nodeIds, color: clusterColor });
            }
        });
    }

    /**
     * Cluster by modularity (connected components)
     */
    clusterByModularity() {
        if (!this.graphRenderer?.network) return;

        const nodes = this.graphRenderer.nodes.get();
        const edges = this.graphRenderer.edges.get();

        // Build adjacency list
        const adjacency = new Map();
        nodes.forEach(node => adjacency.set(node.id, []));

        edges.forEach(edge => {
            if (adjacency.has(edge.from)) {
                adjacency.get(edge.from).push(edge.to);
            }
            if (adjacency.has(edge.to)) {
                adjacency.get(edge.to).push(edge.from);
            }
        });

        // Find connected components using BFS
        const visited = new Set();
        const components = [];

        nodes.forEach(node => {
            if (!visited.has(node.id)) {
                const component = this.bfs(node.id, adjacency, visited);
                if (component.length >= 3) {
                    components.push(component);
                }
            }
        });

        // Create clusters for each component
        components.forEach((component, index) => {
            if (component.length >= 5) {
                const clusterColor = this.clusterColors[index % this.clusterColors.length];

                const clusterOptionsByData = {
                    joinCondition: (nodeOptions) => {
                        return component.includes(nodeOptions.id);
                    },
                    clusterNodeProperties: {
                        id: `cluster_component_${index}`,
                        label: `Module ${index + 1} (${component.length})`,
                        shape: 'hexagon',
                        color: {
                            background: clusterColor,
                            border: this.darkenColor(clusterColor, 20)
                        },
                        font: { color: '#ffffff', size: 14 },
                        borderWidth: 2
                    }
                };

                this.graphRenderer.network.cluster(clusterOptionsByData);
                this.clusters.set(`cluster_component_${index}`, {
                    index,
                    nodeIds: component,
                    color: clusterColor
                });
            }
        });
    }

    /**
     * BFS for finding connected components
     */
    bfs(startId, adjacency, visited) {
        const component = [];
        const queue = [startId];

        while (queue.length > 0) {
            const nodeId = queue.shift();

            if (visited.has(nodeId)) continue;
            visited.add(nodeId);
            component.push(nodeId);

            const neighbors = adjacency.get(nodeId) || [];
            neighbors.forEach(neighbor => {
                if (!visited.has(neighbor)) {
                    queue.push(neighbor);
                }
            });
        }

        return component;
    }

    /**
     * Expand all clusters
     */
    expandAllClusters() {
        if (!this.graphRenderer?.network) return;

        this.clusters.forEach((data, clusterId) => {
            if (this.graphRenderer.network.isCluster(clusterId)) {
                this.graphRenderer.network.openCluster(clusterId);
            }
        });

        this.clusters.clear();
    }

    /**
     * Expand a specific cluster
     */
    expandCluster(clusterId) {
        if (!this.graphRenderer?.network) return;

        if (this.graphRenderer.network.isCluster(clusterId)) {
            this.graphRenderer.network.openCluster(clusterId);
            this.clusters.delete(clusterId);
        }
    }

    /**
     * Handle click on cluster - expand it
     */
    handleClusterClick(clusterId) {
        if (this.clusters.has(clusterId)) {
            this.expandCluster(clusterId);
            return true;
        }
        return false;
    }

    /**
     * Extract directory from file path
     */
    extractDirectory(path) {
        if (!path) return 'root';

        // Normalize path separators
        const normalized = path.replace(/\\/g, '/');

        // Get parent directory
        const parts = normalized.split('/');
        if (parts.length <= 1) return 'root';

        // Return second-to-last part (immediate parent dir)
        return parts[parts.length - 2] || 'root';
    }

    /**
     * Get node type for clustering
     */
    getNodeType(node) {
        const type = (node.type || node.group || '').toLowerCase();

        if (type.includes('function') || type.includes('method')) return 'function';
        if (type.includes('class')) return 'class';
        if (type.includes('signal')) return 'signal';
        if (type.includes('variable') || type.includes('property')) return 'variable';
        if (type.includes('scene')) return 'scene';
        if (type.includes('resource')) return 'resource';

        return 'other';
    }

    /**
     * Darken a hex color by a percentage
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
     * Check if clustering should auto-enable
     */
    shouldAutoCluster(nodeCount) {
        return nodeCount > this.clusterThreshold;
    }

    /**
     * Get cluster info
     */
    getClusterInfo() {
        return {
            enabled: this.clusteringEnabled,
            method: this.clusterMethod,
            clusterCount: this.clusters.size,
            clusters: Array.from(this.clusters.entries()).map(([id, data]) => ({
                id,
                nodeCount: data.nodeIds?.length || 0,
                ...data
            }))
        };
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ClusterManager;
}
