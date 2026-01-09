/**
 * Node Inspector for REACH Code Visualizer
 * Displays detailed information about selected nodes.
 */

class NodeInspector {
    constructor(panelId, contentId) {
        this.panel = document.getElementById(panelId);
        this.content = document.getElementById(contentId);
        this.currentNodeId = null;

        // Event callbacks
        this.onNavigate = null;

        this.setupCloseButton();
    }

    /**
     * Set up the close button handler.
     */
    setupCloseButton() {
        const closeBtn = document.getElementById('close-inspector');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }
    }

    /**
     * Show the inspector panel.
     */
    show() {
        this.panel.classList.remove('collapsed');
    }

    /**
     * Hide the inspector panel.
     */
    hide() {
        this.panel.classList.add('collapsed');
        this.currentNodeId = null;
    }

    /**
     * Display node details.
     */
    async displayNode(nodeId) {
        this.show();
        this.currentNodeId = nodeId;

        // Show loading state
        this.content.innerHTML = `
            <div class="inspector-placeholder">
                <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                <p>Loading node details...</p>
            </div>
        `;

        try {
            const nodeData = await api.getNode(nodeId);
            this.renderNodeDetails(nodeData);
        } catch (error) {
            this.content.innerHTML = `
                <div class="inspector-placeholder">
                    <i class="bi bi-exclamation-triangle text-warning"></i>
                    <p>Failed to load node details</p>
                </div>
            `;
        }
    }

    /**
     * Render node details HTML.
     */
    renderNodeDetails(data) {
        const html = `
            <div class="node-header">
                <div class="node-name">${this.escapeHtml(data.name)}</div>
                <span class="node-type ${data.type}">${data.type}</span>
            </div>

            <div class="node-meta">
                <div class="meta-item">
                    <span class="meta-label">File</span>
                    <span class="meta-value">
                        <a href="#" class="file-link" data-path="${this.escapeHtml(data.full_path || data.file)}" data-line="${data.line}">
                            ${this.escapeHtml(data.file || 'N/A')}
                        </a>
                    </span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Line</span>
                    <span class="meta-value">${data.line || 'N/A'}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Language</span>
                    <span class="meta-value">${data.language || 'N/A'}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Confidence</span>
                    <span class="meta-value">${data.confidence || 'HIGH'}</span>
                </div>
            </div>

            ${this.renderCodeSnippet(data.code_snippet)}
            ${this.renderRelationships(data.outgoing, data.incoming)}
        `;

        this.content.innerHTML = html;
        this.setupNavigationLinks();
    }

    /**
     * Render code snippet section.
     */
    renderCodeSnippet(snippet) {
        if (!snippet) return '';

        // Highlight the target line
        const lines = snippet.split('\n');
        const highlightedLines = lines.map(line => {
            if (line.startsWith('→')) {
                return `<span class="highlight-line">${this.escapeHtml(line)}</span>`;
            }
            return this.escapeHtml(line);
        }).join('\n');

        return `
            <div class="code-section">
                <div class="section-header">
                    <i class="bi bi-code-slash"></i>
                    Code Preview
                </div>
                <pre class="code-snippet">${highlightedLines}</pre>
            </div>
        `;
    }

    /**
     * Render relationships section.
     */
    renderRelationships(outgoing, incoming) {
        if ((!outgoing || outgoing.length === 0) && (!incoming || incoming.length === 0)) {
            return '';
        }

        // Group by relationship type
        const outgoingGroups = this.groupByRelationship(outgoing || []);
        const incomingGroups = this.groupByRelationship(incoming || []);

        let html = '<div class="relationships-section">';
        html += '<div class="section-header"><i class="bi bi-diagram-3"></i> Relationships</div>';

        // Outgoing relationships
        for (const [rel, items] of Object.entries(outgoingGroups)) {
            html += this.renderRelationshipGroup(rel, items, 'out');
        }

        // Incoming relationships
        for (const [rel, items] of Object.entries(incomingGroups)) {
            html += this.renderRelationshipGroup(rel + ' (by)', items, 'in');
        }

        html += '</div>';
        return html;
    }

    /**
     * Group relationships by type.
     */
    groupByRelationship(items) {
        const groups = {};
        for (const item of items) {
            const rel = item.relationship || 'RELATED';
            if (!groups[rel]) {
                groups[rel] = [];
            }
            groups[rel].push(item);
        }
        return groups;
    }

    /**
     * Render a relationship group.
     */
    renderRelationshipGroup(label, items, direction) {
        const icon = direction === 'out' ? 'bi-arrow-right' : 'bi-arrow-left';
        const nameKey = direction === 'out' ? 'target_name' : 'source_name';
        const idKey = direction === 'out' ? 'target_id' : 'source_id';
        const typeKey = direction === 'out' ? 'target_type' : 'source_type';

        let html = `
            <div class="relationship-group">
                <div class="relationship-label">${label}</div>
                <div class="relationship-items">
        `;

        for (const item of items.slice(0, 10)) { // Limit to 10
            html += `
                <div class="relationship-item" data-node-id="${this.escapeHtml(item[idKey])}">
                    <i class="rel-icon bi ${icon}"></i>
                    <span class="rel-name">${this.escapeHtml(item[nameKey])}</span>
                    <span class="rel-type">${item[typeKey]}</span>
                </div>
            `;
        }

        if (items.length > 10) {
            html += `<div class="relationship-item text-muted">... and ${items.length - 10} more</div>`;
        }

        html += '</div></div>';
        return html;
    }

    /**
     * Set up navigation links in the inspector.
     */
    setupNavigationLinks() {
        // Relationship item clicks
        const items = this.content.querySelectorAll('.relationship-item[data-node-id]');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const nodeId = item.dataset.nodeId;
                if (nodeId && this.onNavigate) {
                    this.onNavigate(nodeId);
                }
            });
        });

        // File links
        const fileLinks = this.content.querySelectorAll('.file-link');
        fileLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                // Could open in external editor if configured
                const path = link.dataset.path;
                const line = link.dataset.line;
                console.log(`Would open: ${path}:${line}`);
            });
        });
    }

    /**
     * Escape HTML special characters.
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Clear the inspector content.
     */
    clear() {
        this.content.innerHTML = `
            <div class="inspector-placeholder">
                <i class="bi bi-cursor-fill"></i>
                <p>Click a node to inspect</p>
            </div>
        `;
        this.currentNodeId = null;
    }
}
