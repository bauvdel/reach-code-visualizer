/**
 * Bookmarks System for REACH Code Visualizer
 * Save and restore view states with localStorage persistence
 */

class BookmarksManager {
    constructor(graphRenderer, filterManager, focusMode) {
        this.graphRenderer = graphRenderer;
        this.filterManager = filterManager;
        this.focusMode = focusMode;
        this.bookmarks = [];
        this.storageKey = 'reach-visualizer-bookmarks';
        this.isPanelVisible = false;

        this.init();
    }

    init() {
        this.cacheElements();
        this.bindEvents();
        this.loadBookmarks();
        this.renderBookmarksList();
    }

    cacheElements() {
        this.bookmarksPanel = document.getElementById('bookmarks-panel');
        this.toggleBookmarksBtn = document.getElementById('toggle-bookmarks');
        this.closeBookmarksBtn = document.getElementById('close-bookmarks');
        this.addBookmarkBtn = document.getElementById('save-bookmark');
        this.bookmarksList = document.getElementById('bookmarks-list');
        this.exportBookmarksBtn = document.getElementById('export-bookmarks');
        this.importBookmarksBtn = document.getElementById('import-bookmarks');
    }

    bindEvents() {
        this.toggleBookmarksBtn?.addEventListener('click', () => this.togglePanel());
        this.closeBookmarksBtn?.addEventListener('click', () => this.hidePanel());
        this.addBookmarkBtn?.addEventListener('click', () => this.saveCurrentView());
        this.exportBookmarksBtn?.addEventListener('click', () => this.exportBookmarks());
        this.importBookmarksBtn?.addEventListener('click', () => this.promptImport());
    }

    hidePanel() {
        this.isPanelVisible = false;
        this.bookmarksPanel?.classList.add('collapsed');
        this.toggleBookmarksBtn?.classList.remove('active');
    }

    /**
     * Toggle bookmarks panel visibility
     */
    togglePanel() {
        this.isPanelVisible = !this.isPanelVisible;
        this.bookmarksPanel?.classList.toggle('collapsed', !this.isPanelVisible);
        this.toggleBookmarksBtn?.classList.toggle('active', this.isPanelVisible);
    }

    /**
     * Save current view as a bookmark
     */
    saveCurrentView() {
        const name = this.generateBookmarkName();
        const bookmark = this.captureCurrentState(name, '');
        this.bookmarks.push(bookmark);
        this.persistBookmarks();
        this.renderBookmarksList();
        window.showToast?.(`Bookmark "${name}" saved`, 'success');
    }

    /**
     * Prompt for import file
     */
    promptImport() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    this.importBookmarks(event.target.result);
                };
                reader.readAsText(file);
            }
        };
        input.click();
    }

    /**
     * Generate a suggested bookmark name
     */
    generateBookmarkName() {
        const now = new Date();
        const timestamp = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        if (this.focusMode?.isActive && this.focusMode?.focusedNodeId) {
            return `Focus: ${this.focusMode.focusedNodeId}`;
        }

        const selectedNodes = this.graphRenderer?.network?.getSelectedNodes() || [];
        if (selectedNodes.length === 1) {
            return `Node: ${selectedNodes[0]}`;
        }

        return `View ${timestamp}`;
    }

    /**
     * Save new bookmark from modal
     */
    saveNewBookmark() {
        const name = this.bookmarkNameInput?.value?.trim();
        if (!name) {
            window.showToast?.('Please enter a bookmark name', 'warning');
            return;
        }

        const bookmark = this.captureCurrentState(name, this.bookmarkDescInput?.value?.trim());
        this.bookmarks.push(bookmark);
        this.persistBookmarks();
        this.renderBookmarksList();
        this.hideModal();

        window.showToast?.(`Bookmark "${name}" saved`, 'success');
    }

    /**
     * Capture current view state
     */
    captureCurrentState(name, description = '') {
        const network = this.graphRenderer?.network;

        // Get view position and scale
        const viewPosition = network?.getViewPosition() || { x: 0, y: 0 };
        const scale = network?.getScale() || 1;

        // Get selected nodes
        const selectedNodes = network?.getSelectedNodes() || [];

        // Get filter state
        const filterState = this.filterManager?.activeFilters || {};

        // Get focus state
        const focusState = this.focusMode?.getFocusInfo() || {};

        return {
            id: this.generateId(),
            name,
            description,
            createdAt: new Date().toISOString(),
            viewState: {
                position: viewPosition,
                scale,
                selectedNodes
            },
            filterState: {
                types: Array.from(filterState.types || []),
                languages: Array.from(filterState.languages || []),
                directory: filterState.directory || '',
                customExpression: filterState.customExpression || ''
            },
            focusState: {
                active: focusState.active || false,
                focusedNode: focusState.focusedNode || null,
                depth: focusState.depth || 2
            }
        };
    }

    /**
     * Generate unique bookmark ID
     */
    generateId() {
        return `bm_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Restore a bookmark
     */
    restoreBookmark(bookmarkId) {
        const bookmark = this.bookmarks.find(b => b.id === bookmarkId);
        if (!bookmark) {
            window.showToast?.('Bookmark not found', 'error');
            return;
        }

        // Restore focus state first (if applicable)
        if (bookmark.focusState?.active && bookmark.focusState?.focusedNode) {
            this.focusMode?.focusOnNode(
                bookmark.focusState.focusedNode,
                bookmark.focusState.depth
            );
        } else {
            this.focusMode?.exitFocusMode();
        }

        // Restore filter state
        if (this.filterManager) {
            // Update filter UI
            Object.entries(this.filterManager.typeCheckboxes).forEach(([type, cb]) => {
                if (cb) cb.checked = bookmark.filterState.types.includes(type);
            });

            Object.entries(this.filterManager.langCheckboxes).forEach(([lang, cb]) => {
                if (cb) cb.checked = bookmark.filterState.languages.includes(lang);
            });

            if (this.filterManager.directoryInput) {
                this.filterManager.directoryInput.value = bookmark.filterState.directory || '';
            }

            if (this.filterManager.customFilterInput) {
                this.filterManager.customFilterInput.value = bookmark.filterState.customExpression || '';
            }

            // Apply filters
            this.filterManager.applyFilters();
        }

        // Restore view position and scale
        if (this.graphRenderer?.network) {
            setTimeout(() => {
                this.graphRenderer.network.moveTo({
                    position: bookmark.viewState.position,
                    scale: bookmark.viewState.scale,
                    animation: {
                        duration: 500,
                        easingFunction: 'easeInOutQuad'
                    }
                });

                // Restore selection
                if (bookmark.viewState.selectedNodes?.length > 0) {
                    this.graphRenderer.network.selectNodes(bookmark.viewState.selectedNodes);
                }
            }, 100);
        }

        window.showToast?.(`Restored bookmark "${bookmark.name}"`, 'success');
    }

    /**
     * Delete a bookmark
     */
    deleteBookmark(bookmarkId) {
        const index = this.bookmarks.findIndex(b => b.id === bookmarkId);
        if (index === -1) return;

        const bookmark = this.bookmarks[index];
        this.bookmarks.splice(index, 1);
        this.persistBookmarks();
        this.renderBookmarksList();

        window.showToast?.(`Deleted bookmark "${bookmark.name}"`, 'info');
    }

    /**
     * Rename a bookmark
     */
    renameBookmark(bookmarkId, newName) {
        const bookmark = this.bookmarks.find(b => b.id === bookmarkId);
        if (bookmark) {
            bookmark.name = newName;
            this.persistBookmarks();
            this.renderBookmarksList();
        }
    }

    /**
     * Render bookmarks list in panel
     */
    renderBookmarksList() {
        if (!this.bookmarksList) return;

        if (this.bookmarks.length === 0) {
            this.bookmarksList.innerHTML = `
                <div class="text-muted small text-center py-3">
                    No bookmarks yet.<br>
                    Click "Add Bookmark" to save current view.
                </div>
            `;
            return;
        }

        this.bookmarksList.innerHTML = this.bookmarks.map(bookmark => `
            <div class="bookmark-item" data-id="${bookmark.id}">
                <div class="bookmark-info" onclick="window.bookmarksManager?.restoreBookmark('${bookmark.id}')">
                    <div class="bookmark-name">${this.escapeHtml(bookmark.name)}</div>
                    ${bookmark.description ? `<div class="bookmark-desc">${this.escapeHtml(bookmark.description)}</div>` : ''}
                    <div class="bookmark-meta">
                        ${this.formatDate(bookmark.createdAt)}
                        ${bookmark.focusState?.active ? ' · Focus mode' : ''}
                    </div>
                </div>
                <div class="bookmark-actions">
                    <button class="btn btn-sm btn-outline-danger"
                            onclick="event.stopPropagation(); window.bookmarksManager?.deleteBookmark('${bookmark.id}')"
                            title="Delete bookmark">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }

    /**
     * Format date for display
     */
    formatDate(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }

    /**
     * Escape HTML for safe rendering
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Load bookmarks from localStorage
     */
    loadBookmarks() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                this.bookmarks = JSON.parse(saved);
            }
        } catch (e) {
            console.warn('Failed to load bookmarks:', e);
            this.bookmarks = [];
        }
    }

    /**
     * Persist bookmarks to localStorage
     */
    persistBookmarks() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.bookmarks));
        } catch (e) {
            console.warn('Failed to save bookmarks:', e);
        }
    }

    /**
     * Export bookmarks as JSON
     */
    exportBookmarks() {
        const data = JSON.stringify(this.bookmarks, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = 'reach-visualizer-bookmarks.json';
        a.click();

        URL.revokeObjectURL(url);
    }

    /**
     * Import bookmarks from JSON
     */
    importBookmarks(jsonString) {
        try {
            const imported = JSON.parse(jsonString);
            if (Array.isArray(imported)) {
                // Merge with existing, avoiding duplicates by ID
                const existingIds = new Set(this.bookmarks.map(b => b.id));
                const newBookmarks = imported.filter(b => !existingIds.has(b.id));

                this.bookmarks.push(...newBookmarks);
                this.persistBookmarks();
                this.renderBookmarksList();

                window.showToast?.(`Imported ${newBookmarks.length} bookmarks`, 'success');
            }
        } catch (e) {
            console.error('Failed to import bookmarks:', e);
            window.showToast?.('Failed to import bookmarks', 'error');
        }
    }

    /**
     * Clear all bookmarks
     */
    clearAllBookmarks() {
        if (confirm('Delete all bookmarks? This cannot be undone.')) {
            this.bookmarks = [];
            this.persistBookmarks();
            this.renderBookmarksList();
            window.showToast?.('All bookmarks cleared', 'info');
        }
    }

    /**
     * Get bookmark count
     */
    getBookmarkCount() {
        return this.bookmarks.length;
    }

    /**
     * Get all bookmarks
     */
    getAllBookmarks() {
        return [...this.bookmarks];
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BookmarksManager;
}
