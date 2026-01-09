/**
 * API Client for REACH Code Visualizer
 * Handles all communication with the backend server.
 */

class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.lastUpdate = null;
    }

    /**
     * Make a GET request to the API.
     */
    async get(endpoint, params = {}) {
        const url = new URL(this.baseUrl + endpoint, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                url.searchParams.append(key, value);
            }
        });

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API GET ${endpoint} failed:`, error);
            throw error;
        }
    }

    /**
     * Make a POST request to the API.
     */
    async post(endpoint, data) {
        try {
            const response = await fetch(this.baseUrl + endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API POST ${endpoint} failed:`, error);
            throw error;
        }
    }

    /**
     * Get full graph data with optional filters.
     */
    async getGraph(filters = {}) {
        const data = await this.get('/api/graph', filters);
        this.lastUpdate = new Date();
        return data;
    }

    /**
     * Get detailed node information.
     */
    async getNode(nodeId) {
        return await this.get(`/api/node/${encodeURIComponent(nodeId)}`);
    }

    /**
     * Get graph statistics.
     */
    async getStats() {
        return await this.get('/api/stats');
    }

    /**
     * Search for nodes by name.
     */
    async search(query, options = {}) {
        return await this.get('/api/search', {
            q: query,
            limit: options.limit || 50,
            type: options.type || ''
        });
    }

    /**
     * Execute a query.
     */
    async executeQuery(query, type = 'auto') {
        return await this.post('/api/query', { query, type });
    }

    /**
     * Get neighboring nodes for a given node.
     */
    async getNeighbors(nodeId, depth = 1) {
        return await this.get(`/api/neighbors/${encodeURIComponent(nodeId)}`, { depth });
    }

    /**
     * Get last update time formatted.
     */
    getLastUpdateFormatted() {
        if (!this.lastUpdate) return '--';
        const now = new Date();
        const diff = Math.floor((now - this.lastUpdate) / 1000);
        if (diff < 60) return `${diff}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        return this.lastUpdate.toLocaleTimeString();
    }
}

// Global API client instance
const api = new ApiClient();
