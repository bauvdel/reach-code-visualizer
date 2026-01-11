/**
 * Keyboard Shortcuts for REACH Code Visualizer
 * Provides keyboard navigation and quick actions
 */

class KeyboardShortcuts {
    constructor(managers) {
        this.graphRenderer = managers.graphRenderer;
        this.filterManager = managers.filterManager;
        this.focusMode = managers.focusMode;
        this.pathHighlighter = managers.pathHighlighter;
        this.bookmarksManager = managers.bookmarksManager;
        this.exportManager = managers.exportManager;
        this.clusterManager = managers.clusterManager;

        this.shortcuts = this.defineShortcuts();
        this.isEnabled = true;

        this.init();
    }

    init() {
        this.bindEvents();
        this.setupHelpModal();
    }

    /**
     * Define all keyboard shortcuts
     */
    defineShortcuts() {
        return [
            // Navigation
            {
                key: 'f',
                ctrl: true,
                description: 'Open search / Focus search box',
                action: () => this.focusSearch()
            },
            {
                key: 'Escape',
                description: 'Clear selection / Exit modes',
                action: () => this.clearAll()
            },
            {
                key: 'Home',
                description: 'Fit graph to view',
                action: () => this.fitToView()
            },
            {
                key: '+',
                description: 'Zoom in',
                action: () => this.zoom(1.2)
            },
            {
                key: '-',
                description: 'Zoom out',
                action: () => this.zoom(0.8)
            },
            {
                key: '0',
                ctrl: true,
                description: 'Reset zoom to 100%',
                action: () => this.resetZoom()
            },

            // Modes
            {
                key: 'f',
                shift: true,
                description: 'Toggle focus mode',
                action: () => this.focusMode?.toggleFocusMode()
            },
            {
                key: 'p',
                shift: true,
                description: 'Toggle path mode',
                action: () => this.pathHighlighter?.togglePathMode()
            },

            // Panels
            {
                key: 'f',
                alt: true,
                description: 'Toggle filter panel',
                action: () => this.filterManager?.togglePanel()
            },
            {
                key: 'b',
                ctrl: true,
                description: 'Toggle bookmarks panel',
                action: () => this.bookmarksManager?.togglePanel()
            },
            {
                key: 'b',
                ctrl: true,
                shift: true,
                description: 'Add bookmark',
                action: () => this.bookmarksManager?.showAddModal()
            },

            // Focus depth (when in focus mode)
            {
                key: 'ArrowUp',
                shift: true,
                description: 'Increase focus depth',
                action: () => this.adjustFocusDepth(1)
            },
            {
                key: 'ArrowDown',
                shift: true,
                description: 'Decrease focus depth',
                action: () => this.adjustFocusDepth(-1)
            },

            // Export
            {
                key: 'e',
                ctrl: true,
                description: 'Export as PNG',
                action: () => this.exportManager?.exportPng()
            },
            {
                key: 's',
                ctrl: true,
                description: 'Export as JSON',
                action: (e) => {
                    e.preventDefault();
                    this.exportManager?.exportJson();
                }
            },

            // Layout
            {
                key: '1',
                alt: true,
                description: 'Force-directed layout',
                action: () => this.setLayout('forceAtlas2Based')
            },
            {
                key: '2',
                alt: true,
                description: 'Hierarchical layout',
                action: () => this.setLayout('hierarchical')
            },

            // Selection
            {
                key: 'a',
                ctrl: true,
                description: 'Select all nodes',
                action: (e) => {
                    e.preventDefault();
                    this.selectAll();
                }
            },

            // Help
            {
                key: '?',
                shift: true,
                description: 'Show keyboard shortcuts',
                action: () => this.showHelp()
            },
            {
                key: 'F1',
                description: 'Show keyboard shortcuts',
                action: (e) => {
                    e.preventDefault();
                    this.showHelp();
                }
            }
        ];
    }

    bindEvents() {
        document.addEventListener('keydown', (e) => this.handleKeyDown(e));
    }

    /**
     * Handle keydown event
     */
    handleKeyDown(e) {
        if (!this.isEnabled) return;

        // Don't trigger shortcuts when typing in inputs
        if (this.isTypingInInput(e)) {
            // Allow Escape even when in input
            if (e.key === 'Escape') {
                e.target.blur();
            }
            return;
        }

        // Find matching shortcut
        const shortcut = this.shortcuts.find(s => this.matchesShortcut(e, s));

        if (shortcut) {
            shortcut.action(e);
        }
    }

    /**
     * Check if user is typing in an input field
     */
    isTypingInInput(e) {
        const target = e.target;
        const tagName = target.tagName.toLowerCase();

        return tagName === 'input' ||
               tagName === 'textarea' ||
               target.isContentEditable;
    }

    /**
     * Check if event matches shortcut definition
     */
    matchesShortcut(e, shortcut) {
        // Check key
        if (e.key.toLowerCase() !== shortcut.key.toLowerCase() &&
            e.key !== shortcut.key) {
            return false;
        }

        // Check modifiers
        const ctrlMatch = !!shortcut.ctrl === (e.ctrlKey || e.metaKey);
        const shiftMatch = !!shortcut.shift === e.shiftKey;
        const altMatch = !!shortcut.alt === e.altKey;

        return ctrlMatch && shiftMatch && altMatch;
    }

    // Action implementations

    focusSearch() {
        const searchInput = document.getElementById('search-input') ||
                           document.querySelector('input[type="search"]');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }

    clearAll() {
        // Clear selection
        this.graphRenderer?.network?.unselectAll();

        // Exit focus mode
        if (this.focusMode?.isActive) {
            this.focusMode.exitFocusMode();
            return;
        }

        // Clear path mode
        if (this.pathHighlighter?.isActive()) {
            this.pathHighlighter.clearAll();
            return;
        }

        // Close modals
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });

        // Close panels
        this.filterManager?.hidePanel();
        this.bookmarksManager?.hidePanel();
    }

    fitToView() {
        this.graphRenderer?.network?.fit({
            animation: {
                duration: 500,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    zoom(factor) {
        if (!this.graphRenderer?.network) return;

        const currentScale = this.graphRenderer.network.getScale();
        const newScale = currentScale * factor;

        this.graphRenderer.network.moveTo({
            scale: Math.max(0.1, Math.min(5, newScale)),
            animation: {
                duration: 200,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    resetZoom() {
        this.graphRenderer?.network?.moveTo({
            scale: 1,
            animation: {
                duration: 300,
                easingFunction: 'easeInOutQuad'
            }
        });
    }

    adjustFocusDepth(delta) {
        if (!this.focusMode?.isActive) return;

        const newDepth = Math.max(1, Math.min(5, this.focusMode.focusDepth + delta));
        const depthSlider = document.getElementById('focus-depth');
        const depthValue = document.getElementById('focus-depth-value');

        if (depthSlider) {
            depthSlider.value = newDepth;
        }
        if (depthValue) {
            depthValue.textContent = newDepth;
        }

        this.focusMode.focusDepth = newDepth;
        if (this.focusMode.focusedNodeId) {
            this.focusMode.applyFocus(this.focusMode.focusedNodeId);
        }
    }

    setLayout(layoutType) {
        // Trigger layout change in graph renderer
        if (window.graphRenderer?.setLayout) {
            window.graphRenderer.setLayout(layoutType);
        }
    }

    selectAll() {
        if (!this.graphRenderer?.network) return;

        const nodeIds = this.graphRenderer.nodes.getIds();
        this.graphRenderer.network.selectNodes(nodeIds);
    }

    showHelp() {
        const modal = document.getElementById('shortcuts-modal');
        if (modal) {
            // Use Bootstrap modal API if available, otherwise toggle class
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const bsModal = new bootstrap.Modal(modal);
                bsModal.show();
            } else {
                modal.classList.add('show');
                modal.style.display = 'block';
            }
        }
    }

    setupHelpModal() {
        const modal = document.getElementById('shortcuts-modal');
        if (!modal) return;

        // Close on background click (for non-Bootstrap fallback)
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
                modal.style.display = 'none';
            }
        });

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('show')) {
                modal.classList.remove('show');
                modal.style.display = 'none';
            }
        });
    }

    /**
     * Format shortcut for display
     */
    formatShortcut(shortcut) {
        const parts = [];

        if (shortcut.ctrl) parts.push('Ctrl');
        if (shortcut.alt) parts.push('Alt');
        if (shortcut.shift) parts.push('Shift');

        // Format special keys
        let key = shortcut.key;
        if (key === ' ') key = 'Space';
        if (key === 'ArrowUp') key = '↑';
        if (key === 'ArrowDown') key = '↓';
        if (key === 'ArrowLeft') key = '←';
        if (key === 'ArrowRight') key = '→';

        parts.push(key.toUpperCase());

        return parts.join(' + ');
    }

    /**
     * Enable shortcuts
     */
    enable() {
        this.isEnabled = true;
    }

    /**
     * Disable shortcuts (e.g., when modal is open)
     */
    disable() {
        this.isEnabled = false;
    }

    /**
     * Get all shortcuts for external use
     */
    getShortcuts() {
        return this.shortcuts.map(s => ({
            keys: this.formatShortcut(s),
            description: s.description
        }));
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KeyboardShortcuts;
}
