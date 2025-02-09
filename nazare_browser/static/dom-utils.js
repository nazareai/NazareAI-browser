// DOM Utilities for NazareAI Browser
(function() {
    // Only initialize if not already present
    if (window.NazareDOM) return;

    window.NazareDOM = {
        config: {
            overlayId: 'nazare-overlay-container',
            styleId: 'nazare-styles',
            elementCounter: 0
        },

        init() {
            // Create overlay container
            let overlay = document.getElementById(this.config.overlayId);
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = this.config.overlayId;
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    pointer-events: none;
                    z-index: 2147483647;
                `;
                document.body.appendChild(overlay);
            }

            // Add minimal styles for overlays
            const style = document.createElement('style');
            style.id = this.config.styleId;
            style.textContent = `
                .nazare-overlay-highlight {
                    position: absolute;
                    pointer-events: none;
                    border-radius: 4px;
                    z-index: 2147483647;
                    transition: opacity 0.2s;
                    overflow: visible;
                }
                .nazare-number {
                    position: absolute;
                    top: 4px;
                    right: 4px;
                    color: white;
                    padding: 1px 5px;
                    border-radius: 10px;
                    font-size: 11px;
                    font-weight: bold;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                    pointer-events: none;
                    z-index: 2147483648;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                    min-width: 15px;
                    text-align: center;
                }
                .nazare-number.nazare-number-button {
                    background: rgba(255, 64, 129, 0.9);
                }
                .nazare-number.nazare-number-link {
                    background: rgba(33, 150, 243, 0.9);
                }
                .nazare-number.nazare-number-searchbox {
                    background: rgba(76, 175, 80, 0.9);
                }
                .nazare-number.nazare-number-video {
                    background: rgba(255, 193, 7, 0.9);
                }
                .nazare-number.nazare-number-player {
                    background: rgba(156, 39, 176, 0.9);
                }
                .nazare-number.nazare-number-menu {
                    background: rgba(255, 152, 0, 0.9);
                }
                .nazare-number.nazare-number-navigation {
                    background: rgba(0, 188, 212, 0.9);
                }
                .nazare-number.nazare-number-tab {
                    background: rgba(139, 195, 74, 0.9);
                }
                .nazare-overlay-button {
                    box-shadow: 0 0 0 2px rgba(255, 64, 129, 0.5);
                }
                .nazare-overlay-link {
                    box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.5);
                }
                .nazare-overlay-searchbox {
                    box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.5);
                }
                .nazare-overlay-video {
                    box-shadow: 0 0 0 2px rgba(255, 193, 7, 0.5);
                }
                .nazare-overlay-player {
                    box-shadow: 0 0 0 2px rgba(156, 39, 176, 0.5);
                }
                .nazare-overlay-menu {
                    box-shadow: 0 0 0 2px rgba(255, 152, 0, 0.5);
                }
                .nazare-overlay-navigation {
                    box-shadow: 0 0 0 2px rgba(0, 188, 212, 0.5);
                }
                .nazare-overlay-tab {
                    box-shadow: 0 0 0 2px rgba(139, 195, 74, 0.5);
                }
                .nazare-overlay-label {
                    position: absolute;
                    top: -18px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(0, 0, 0, 0.8);
                    color: white;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 10px;
                    white-space: nowrap;
                    opacity: 0;
                    transition: opacity 0.2s;
                    pointer-events: none;
                }
                .nazare-overlay-highlight:hover .nazare-overlay-label {
                    opacity: 1;
                }
                .nazare-overlay-highlight[data-nazare-action]:after {
                    content: attr(data-nazare-action);
                    position: absolute;
                    bottom: -16px;
                    right: 0;
                    background: rgba(0, 0, 0, 0.6);
                    color: white;
                    padding: 1px 4px;
                    border-radius: 2px;
                    font-size: 9px;
                    opacity: 0;
                    transition: opacity 0.2s;
                }
                .nazare-overlay-highlight:hover[data-nazare-action]:after {
                    opacity: 1;
                }
                .nazare-id {
                    position: absolute;
                    top: 2px;
                    left: 2px;
                    background: rgba(33, 150, 243, 0.9);
                    color: white;
                    padding: 1px 4px;
                    border-radius: 2px;
                    font-size: 8px;
                    opacity: 0;
                    transition: opacity 0.2s;
                }
                .nazare-overlay-highlight:hover .nazare-id {
                    opacity: 1;
                }
                .nazare-context {
                    position: absolute;
                    bottom: -24px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(0, 0, 0, 0.7);
                    color: #4CAF50;
                    padding: 2px 6px;
                    border-radius: 2px;
                    font-size: 9px;
                    white-space: nowrap;
                    opacity: 0;
                    transition: opacity 0.2s;
                }
                .nazare-overlay-highlight:hover .nazare-context {
                    opacity: 1;
                }
            `;
            document.head.appendChild(style);

            // Initialize
            this.scanForInteractiveElements();
            this.setupObservers();
        },

        scanForInteractiveElements() {
            // Reset counter when scanning starts
            this.config.elementCounter = 0;
            
            // Clear existing overlays
            const overlay = document.getElementById(this.config.overlayId);
            if (overlay) {
                overlay.innerHTML = '';
            }

            // Scan for elements
            this.findInteractiveElements().forEach(el => {
                this.createOverlay(el);
            });
        },

        findInteractiveElements() {
            const elements = [];
            
            // Define selectors for different types of elements
            const selectors = {
                // Search elements
                search: `
                    input#search,
                    input[name="search_query"],
                    input[aria-label="Search"],
                    button#search-icon-legacy,
                    button[aria-label="Search"]
                `,
                // Video elements
                video: `
                    a#video-title-link,
                    ytd-video-renderer a#thumbnail,
                    ytd-compact-video-renderer a#thumbnail,
                    ytd-grid-video-renderer a#thumbnail,
                    ytd-rich-item-renderer a#thumbnail,
                    ytd-video-renderer h3,
                    ytd-compact-video-renderer h3,
                    ytd-grid-video-renderer h3,
                    ytd-rich-item-renderer h3
                `,
                // Player controls
                player: `
                    .ytp-play-button,
                    .ytp-mute-button,
                    .ytp-settings-button,
                    .ytp-fullscreen-button,
                    .ytp-volume-panel,
                    .ytp-prev-button,
                    .ytp-next-button,
                    .ytp-subtitles-button,
                    .ytp-size-button,
                    .ytp-chapter-container
                `,
                // Navigation elements
                navigation: `
                    ytd-guide-entry-renderer a,
                    ytd-mini-guide-entry-renderer a,
                    #guide-button,
                    ytd-topbar-menu-button-renderer button,
                    ytd-guide-section-renderer h3,
                    ytd-guide-section-renderer ytd-guide-entry-renderer,
                    #sections > ytd-guide-section-renderer
                `,
                // Interactive buttons
                buttons: `
                    ytd-button-renderer button,
                    ytd-toggle-button-renderer button,
                    button[aria-label],
                    yt-button-renderer button,
                    ytd-menu-renderer button,
                    ytd-menu-service-item-renderer button,
                    ytd-subscribe-button-renderer button
                `,
                // Menu items
                menu: `
                    ytd-menu-renderer,
                    ytd-menu-service-item-renderer,
                    tp-yt-paper-item,
                    ytd-menu-popup-renderer,
                    ytd-multi-page-menu-renderer
                `,
                // Tabs and filters
                tabs: `
                    yt-chip-cloud-chip-renderer,
                    ytd-feed-filter-chip-bar-renderer,
                    ytd-video-primary-info-renderer ytd-expander,
                    ytd-comments-header-renderer,
                    ytd-watch-metadata
                `,
                // Channel elements
                channel: `
                    ytd-channel-name,
                    #owner-container,
                    #channel-header,
                    #avatar-link,
                    ytd-video-owner-renderer
                `
            };

            // Find elements for each type
            Object.entries(selectors).forEach(([type, selector]) => {
                document.querySelectorAll(selector).forEach(el => {
                    if (this.isElementVisible(el)) {
                        elements.push(el);
                    }
                });
            });

            return elements;
        },

        createOverlay(element) {
            const type = this.getElementType(element);
            if (!type) return;

            const rect = element.getBoundingClientRect();
            if (!rect.width || !rect.height) return;

            const overlay = document.getElementById(this.config.overlayId);
            if (!overlay) return;

            // Increment counter
            this.config.elementCounter++;
            const elementNumber = this.config.elementCounter;

            const highlight = document.createElement('div');
            highlight.className = `nazare-overlay-highlight nazare-overlay-${type}`;
            
            // Position the highlight
            highlight.style.cssText = `
                left: ${rect.left + window.scrollX}px;
                top: ${rect.top + window.scrollY}px;
                width: ${rect.width}px;
                height: ${rect.height}px;
            `;

            // Add number indicator
            const number = document.createElement('div');
            number.className = `nazare-number nazare-number-${type}`;
            number.textContent = elementNumber;
            highlight.appendChild(number);

            // Add Nazare-specific metadata
            const metadata = this.getNazareMetadata(element, type);
            if (metadata.action) {
                highlight.setAttribute('data-nazare-action', metadata.action);
            }

            // Store the number reference
            highlight.setAttribute('data-nazare-number', elementNumber);
            element.setAttribute('data-nazare-number', elementNumber);

            // Add other metadata
            highlight.setAttribute('data-nazare-type', type);
            highlight.setAttribute('data-nazare-text', metadata.label);
            highlight.setAttribute('data-nazare-rect', JSON.stringify(rect));
            if (metadata.context) {
                highlight.setAttribute('data-nazare-context', metadata.context);
            }

            overlay.appendChild(highlight);
        },

        getElementType(element) {
            // Search elements
            if (element.matches('input#search') || 
                element.matches('input[name="search_query"]') ||
                element.matches('input[aria-label="Search"]')) {
                return 'searchbox';
            }
            if (element.matches('button#search-icon-legacy') ||
                element.matches('button[aria-label="Search"]')) {
                return 'button';
            }

            // Video elements
            if (element.matches('a#video-title-link, ytd-video-renderer a#thumbnail, ytd-compact-video-renderer a#thumbnail, ytd-grid-video-renderer a#thumbnail, ytd-rich-item-renderer a#thumbnail')) {
                return 'video';
            }

            // Player controls
            if (element.matches('.ytp-play-button, .ytp-mute-button, .ytp-settings-button, .ytp-fullscreen-button, .ytp-volume-panel, .ytp-prev-button, .ytp-next-button')) {
                return 'player';
            }

            // Navigation elements
            if (element.matches('ytd-guide-entry-renderer a, ytd-mini-guide-entry-renderer a, #guide-button')) {
                return 'navigation';
            }

            // Menu items
            if (element.matches('ytd-menu-renderer, ytd-menu-service-item-renderer, tp-yt-paper-item')) {
                return 'menu';
            }

            // Tabs and filters
            if (element.matches('yt-chip-cloud-chip-renderer, ytd-feed-filter-chip-bar-renderer')) {
                return 'tab';
            }

            // Channel elements
            if (element.matches('ytd-channel-name, #owner-container, #channel-header, #avatar-link')) {
                return 'link';
            }

            // Generic buttons
            if (element.matches('button, ytd-button-renderer button, yt-button-renderer button')) {
                return 'button';
            }

            return null;
        },

        getNazareMetadata(element, type) {
            const metadata = {
                label: '',
                action: null,
                context: null
            };

            // Get basic text content
            const ariaLabel = element.getAttribute('aria-label');
            const title = element.getAttribute('title');
            const text = element.textContent.trim();
            
            // Set the label
            metadata.label = ariaLabel || title || text || type;

            // Determine action based on element type and context
            if (type === 'searchbox') {
                metadata.action = 'type';
                metadata.context = 'search';
            } else if (type === 'video') {
                metadata.action = 'click to watch';
                metadata.context = 'content';
            } else if (type === 'player') {
                const controls = {
                    'ytp-play-button': 'play/pause',
                    'ytp-mute-button': 'toggle mute',
                    'ytp-settings-button': 'settings',
                    'ytp-fullscreen-button': 'fullscreen'
                };
                for (const [className, action] of Object.entries(controls)) {
                    if (element.classList.contains(className)) {
                        metadata.action = action;
                        metadata.context = 'player';
                        break;
                    }
                }
            } else if (type === 'navigation') {
                metadata.action = 'navigate';
                metadata.context = 'navigation';
            } else if (type === 'menu') {
                metadata.action = 'open menu';
                metadata.context = 'actions';
            } else if (type === 'tab') {
                metadata.action = 'filter';
                metadata.context = 'filters';
            }

            return metadata;
        },

        isElementVisible(element) {
            if (!element) return false;

            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            
            return !!(
                rect.width &&
                rect.height &&
                rect.top < window.innerHeight &&
                rect.bottom > 0 &&
                rect.left < window.innerWidth &&
                rect.right > 0 &&
                style.display !== 'none' &&
                style.visibility !== 'hidden' &&
                parseFloat(style.opacity) > 0 &&
                !element.closest('[hidden]') // Check if any parent is hidden
            );
        },

        setupObservers() {
            // Update on scroll and resize
            window.addEventListener('scroll', () => this.updateOverlays(), { passive: true });
            window.addEventListener('resize', () => this.updateOverlays(), { passive: true });

            // Watch for DOM changes
            const observer = new MutationObserver(() => {
                if (this._updateTimeout) {
                    clearTimeout(this._updateTimeout);
                }
                this._updateTimeout = setTimeout(() => {
                    this.scanForInteractiveElements();
                }, 100);
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['style', 'class', 'hidden', 'aria-hidden']
            });
        },

        updateOverlays() {
            if (this._updateTimeout) {
                clearTimeout(this._updateTimeout);
            }
            this._updateTimeout = setTimeout(() => {
                this.scanForInteractiveElements();
            }, 100);
        },

        findElement(selector) {
            // Direct element finding without modifying the element
            return document.querySelector(selector);
        },

        generateNazareId(element, type) {
            // Generate a unique, readable ID for the element
            const baseId = element.id || element.getAttribute('aria-label') || 
                          element.getAttribute('title') || element.textContent.trim();
            const shortId = baseId ? baseId.slice(0, 10).replace(/[^a-zA-Z0-9]/g, '') : '';
            return `nz-${type}-${shortId || Math.random().toString(36).substr(2, 6)}`;
        },

        getNazareContext(element, type) {
            // Get contextual information about the element
            const contexts = [];

            // Add parent context
            const parent = element.closest('ytd-rich-item-renderer, ytd-compact-video-renderer, ytd-video-renderer');
            if (parent) {
                const parentType = parent.tagName.toLowerCase();
                contexts.push(`in: ${parentType}`);
            }

            // Add position context
            const position = this.getElementPosition(element);
            if (position) {
                contexts.push(position);
            }

            // Add semantic context
            const semantic = this.getSemanticContext(element, type);
            if (semantic) {
                contexts.push(semantic);
            }

            return contexts.join(' | ');
        },

        getElementPosition(element) {
            // Get position information (e.g., "top-right", "main-content")
            const rect = element.getBoundingClientRect();
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;

            const horizontal = rect.left < viewportWidth / 3 ? 'left' :
                             rect.left < (viewportWidth * 2/3) ? 'center' : 'right';
            const vertical = rect.top < viewportHeight / 3 ? 'top' :
                           rect.top < (viewportHeight * 2/3) ? 'middle' : 'bottom';

            return `pos: ${vertical}-${horizontal}`;
        },

        getSemanticContext(element, type) {
            // Get semantic context based on element type and location
            const contexts = {
                video: 'content',
                searchbox: 'header',
                navigation: 'sidebar',
                player: 'media-controls',
                menu: 'actions',
                tab: 'filters'
            };

            // Add role-specific context
            const role = element.getAttribute('role');
            if (role) {
                return `role: ${role}`;
            }

            return contexts[type] ? `ctx: ${contexts[type]}` : '';
        },

        findElementByNumber(number) {
            return document.querySelector(`[data-nazare-number="${number}"]`);
        }
    };

    // Initialize
    window.NazareDOM.init();
})(); 