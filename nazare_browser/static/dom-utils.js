// DOM Utilities for NazareAI Browser
(function() {
    // Only initialize if not already present
    if (window.NazareDOM) {
        // If already exists, just rescan
        window.NazareDOM.scanForInteractiveElements();
        return;
    }

    window.NazareDOM = {
        config: {
            overlayId: 'nazare-overlay-container',
            styleId: 'nazare-styles',
            elementCounter: 0,
            // Add minimum dimensions for elements
            minElementSize: {
                width: 5,
                height: 5
            },
            // Add common interactive class patterns
            interactiveClassPatterns: [
                'button', 'menu', 'menuitem', 'link', 'checkbox', 'radio',
                'slider', 'tab', 'tabpanel', 'textbox', 'combobox', 'grid',
                'listbox', 'option', 'progressbar', 'scrollbar', 'searchbox',
                'switch', 'tree', 'treeitem', 'spinbutton', 'tooltip', 'a-button-inner', 'a-dropdown-button', 'click', 
                'menuitemcheckbox', 'menuitemradio', 'a-button-text', 'button-text', 'button-icon', 'button-icon-only', 
                'button-text-icon-only', 'dropdown', 'combobox', 'expendable'
            ],
            // New configuration options
            shadowDOMEnabled: true,
            iframeSupport: true,
            coordinateTracking: true,
            xpathGeneration: true,
            viewportExpansion: 0
        },

        // Add data storage for DOM tree representation
        domTree: null,

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
                    background-color: rgba(29, 155, 240, 0.1);
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
                    background-color: rgba(255, 64, 129, 0.1);
                    box-shadow: 0 0 0 1px rgba(255, 64, 129, 0.2);
                }
                .nazare-overlay-link {
                    background-color: rgba(33, 150, 243, 0.1);
                    box-shadow: 0 0 0 1px rgba(33, 150, 243, 0.2);
                }
                .nazare-overlay-searchbox {
                    background-color: rgba(76, 175, 80, 0.1);
                    box-shadow: 0 0 0 1px rgba(76, 175, 80, 0.2);
                }
                .nazare-overlay-video {
                    background-color: rgba(255, 193, 7, 0.1);
                    box-shadow: 0 0 0 1px rgba(255, 193, 7, 0.2);
                }
                .nazare-overlay-player {
                    background-color: rgba(156, 39, 176, 0.1);
                    box-shadow: 0 0 0 1px rgba(156, 39, 176, 0.2);
                }
                .nazare-overlay-menu {
                    background-color: rgba(255, 152, 0, 0.1);
                    box-shadow: 0 0 0 1px rgba(255, 152, 0, 0.2);
                }
                .nazare-overlay-navigation {
                    background-color: rgba(0, 188, 212, 0.1);
                    box-shadow: 0 0 0 1px rgba(0, 188, 212, 0.2);
                }
                .nazare-overlay-tab {
                    background-color: rgba(139, 195, 74, 0.1);
                    box-shadow: 0 0 0 1px rgba(139, 195, 74, 0.2);
                }
                .nazare-overlay-highlight:hover {
                    background-color: rgba(29, 155, 240, 0.15);
                }
                .nazare-overlay-button:hover {
                    background-color: rgba(255, 64, 129, 0.15);
                }
                .nazare-overlay-link:hover {
                    background-color: rgba(33, 150, 243, 0.15);
                }
                .nazare-overlay-searchbox:hover {
                    background-color: rgba(76, 175, 80, 0.15);
                }
                .nazare-overlay-video:hover {
                    background-color: rgba(255, 193, 7, 0.15);
                }
                .nazare-overlay-player:hover {
                    background-color: rgba(156, 39, 176, 0.15);
                }
                .nazare-overlay-menu:hover {
                    background-color: rgba(255, 152, 0, 0.15);
                }
                .nazare-overlay-navigation:hover {
                    background-color: rgba(0, 188, 212, 0.15);
                }
                .nazare-overlay-tab:hover {
                    background-color: rgba(139, 195, 74, 0.15);
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
            this.setupShadowDOMObserver();
            this.setupIframeObserver();
            this.initializeCoordinateTracking();
        },

        scanForInteractiveElements(root = document) {
            this.config.elementCounter = 0;
            
            const overlay = document.getElementById(this.config.overlayId);
            if (overlay) {
                overlay.innerHTML = '';
            }

            // Reset DOM tree
            this.domTree = {};

            // Get all elements including shadow DOM and iframes
            const allElements = this.getAllElements(root);
            
            // Filter and sort elements
            const interactiveElements = allElements
                .filter(el => {
                    if (!this.isElementVisible(el)) return false;

                    const rect = el.getBoundingClientRect();
                    if (rect.width < this.config.minElementSize.width || 
                        rect.height < this.config.minElementSize.height) {
                        return false;
                    }

                    return (
                        this.isSemanticInteractive(el) ||
                        this.hasInteractiveRole(el) ||
                        this.hasInteractiveStyle(el) ||
                        this.hasInteractiveClass(el) ||
                        this.hasInteractiveText(el)
                    );
                })
                .sort((a, b) => this.getElementDepth(b) - this.getElementDepth(a));

            interactiveElements.forEach(el => this.createOverlay(el));
        },

        getAllElements(root) {
            // Handle different types of roots
            let elements = [];
            
            try {
                // For shadow roots, use querySelectorAll instead of getElementsByTagName
                if (root instanceof ShadowRoot) {
                    elements = Array.from(root.querySelectorAll('*'));
                } else if (root instanceof Document || root instanceof Element) {
                    // For regular document/elements, use getElementsByTagName
                    elements = Array.from(root.getElementsByTagName('*'));
                } else {
                    console.warn('Invalid root element type:', root);
                    return [];
                }

                if (this.config.shadowDOMEnabled) {
                    elements = elements.reduce((acc, el) => {
                        acc.push(el);
                        if (el.shadowRoot) {
                            acc.push(...this.getAllElements(el.shadowRoot));
                        }
                        return acc;
                    }, []);
                }

                if (this.config.iframeSupport) {
                    let iframes;
                    if (root instanceof ShadowRoot) {
                        iframes = root.querySelectorAll('iframe');
                    } else {
                        iframes = root.getElementsByTagName('iframe');
                    }
                    
                    for (const iframe of iframes) {
                        try {
                            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                            if (iframeDoc) {
                                elements.push(...this.getAllElements(iframeDoc));
                            }
                        } catch (e) {
                            console.warn('Unable to access iframe:', e);
                        }
                    }
                }
            } catch (e) {
                console.warn('Error in getAllElements:', e);
                return [];
            }

            return elements;
        },

        isSemanticInteractive(el) {
            // Core interactive elements that should always be included
            const coreInteractive = [
                'A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'
            ];
            
            // Heading elements that should be meaningful
            const headings = ['H1', 'H2', 'H3', 'H4', 'H5', 'H6'];
            
            // Other potentially interactive elements that need additional checks
            const otherInteractive = [
                'ARTICLE', 'NAV', 'HEADER', 'FOOTER'
            ];
            
            // Always include core interactive elements with additional checks
            if (coreInteractive.includes(el.tagName)) {
                // For links, only include if they have href or role
                if (el.tagName === 'A') {
                    return el.hasAttribute('href') || el.hasAttribute('role');
                }
                return true;
            }
            
            // Include headings only if they are main content headings
            if (headings.includes(el.tagName)) {
                const text = el.textContent.trim();
                return text.length > 0 && text.length < 200 && !el.closest('footer');
            }
            
            // For other elements, require strong interactive signals
            if (otherInteractive.includes(el.tagName)) {
                return (
                    el.hasAttribute('onclick') ||
                    el.getAttribute('tabindex') === '0' ||
                    el.getAttribute('role') === 'button' ||
                    el.getAttribute('role') === 'link' ||
                    el.getAttribute('role') === 'menuitem'
                );
            }
            
            return false;
        },

        hasInteractiveRole(el) {
            // More focused set of interactive roles
            const interactiveRoles = [
                'button', 'link', 'menuitem', 'tab',
                'searchbox', 'textbox', 'menu'
            ];
            
            const role = el.getAttribute('role');
            return role && interactiveRoles.includes(role.toLowerCase());
        },

        hasInteractiveStyle(el) {
            const style = window.getComputedStyle(el);
            
            // Only consider pointer cursor if element has other interactive traits
            if (style.cursor === 'pointer') {
                return (
                    el.hasAttribute('onclick') ||
                    el.hasAttribute('role') ||
                    el.tagName === 'BUTTON' ||
                    el.tagName === 'A' ||
                    el.querySelector('a, button') !== null
                );
            }
            
            // Include elements with tabindex=0
            if (el.getAttribute('tabindex') === '0') {
                return true;
            }
            
            return false;
        },

        hasInteractiveClass(el) {
            let classNames = '';
            try {
                // Handle different types of className (SVG vs HTML elements)
                if (typeof el.className === 'string') {
                    classNames = el.className;
                } else if (el.className && typeof el.className.baseVal === 'string') {
                    classNames = el.className.baseVal;
                } else if (el.getAttribute('class')) {
                    classNames = el.getAttribute('class');
                }
                
                classNames = (classNames || '').toLowerCase();
                
                // Very focused set of interactive class patterns
                const patterns = [
                    'btn', 'button',
                    'nav-item',
                    'menu-item',
                    'search-box',
                    'article-title'
                ];
                
                // Only include if the element also has other interactive traits
                if (patterns.some(pattern => classNames.includes(pattern))) {
                    return (
                        el.hasAttribute('onclick') ||
                        el.hasAttribute('role') ||
                        el.tagName === 'A' ||
                        el.tagName === 'BUTTON' ||
                        window.getComputedStyle(el).cursor === 'pointer'
                    );
                }
                
                return false;
            } catch (e) {
                console.debug('Error checking className:', e);
                return false;
            }
        },

        hasInteractiveText(el) {
            // Only process elements that directly contain text
            const hasDirectText = Array.from(el.childNodes)
                .some(node => node.nodeType === Node.TEXT_NODE && 
                            node.textContent.trim().length > 0);
            
            if (!hasDirectText) return false;
            
            const text = el.textContent.trim();
            
            // Skip if text is too long or too short
            if (text.length < 2 || text.length > 150) return false;
            
            // Only consider text content for elements that are likely interactive
            if (
                el.tagName === 'A' ||
                el.tagName === 'BUTTON' ||
                el.hasAttribute('role') ||
                el.hasAttribute('onclick') ||
                window.getComputedStyle(el).cursor === 'pointer'
            ) {
                // Common interactive text patterns
                const patterns = [
                    'sign in', 'login', 'subscribe',
                    'search', 'menu', 'more', 'view all'
                ];
                
                return patterns.some(pattern => text.toLowerCase().includes(pattern));
            }
            
            // For article titles, require specific structure
            if (el.closest('article')) {
                return (
                    text.length > 10 &&
                    text.length < 150 &&
                    /^[A-Z]/.test(text) &&
                    (el.tagName.match(/^H[1-6]$/) || el.classList.contains('title'))
                );
            }
            
            return false;
        },

        // Helper function to get element's depth in DOM tree
        getElementDepth(element) {
            let depth = 0;
            let current = element;
            while (current.parentElement) {
                depth++;
                current = current.parentElement;
            }
            return depth;
        },

        createOverlay(el) {
            const rect = el.getBoundingClientRect();
            if (!rect.width || !rect.height) return;

            const overlay = document.getElementById(this.config.overlayId);
            if (!overlay) return;

            // Increment counter
            this.config.elementCounter++;
            const elementNumber = this.config.elementCounter;

            const highlight = document.createElement('div');
            highlight.className = `nazare-overlay-highlight nazare-overlay-${this.getElementType(el)}`;
            
            // Position the highlight with absolute coordinates
            highlight.style.cssText = `
                left: ${rect.left + window.scrollX}px;
                top: ${rect.top + window.scrollY}px;
                width: ${rect.width}px;
                height: ${rect.height}px;
                pointer-events: none;
                position: absolute;
                z-index: ${2147483647 - this.getElementDepth(el)}; // Ensure proper stacking
            `;

            // Add number indicator
            const number = document.createElement('div');
            number.className = `nazare-number nazare-number-${this.getElementType(el)}`;
            number.textContent = elementNumber;
            highlight.appendChild(number);

            // Store references
            highlight.setAttribute('data-nazare-number', elementNumber);
            el.setAttribute('data-nazare-number', elementNumber);

            // Add element info for debugging
            highlight.setAttribute('data-nazare-tag', el.tagName.toLowerCase());
            highlight.setAttribute('data-nazare-depth', this.getElementDepth(el));

            overlay.appendChild(highlight);
        },

        getElementType(el) {
            // Simplified type detection to ensure we don't miss anything
            if (el.tagName === 'A' || el.hasAttribute('href')) return 'link';
            if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') return 'button';
            if (el.tagName === 'INPUT' && el.type === 'search') return 'searchbox';
            if (el.tagName === 'VIDEO') return 'video';
            if (el.classList.contains('player')) return 'player';
            if (el.classList.contains('menu')) return 'menu';
            if (el.tagName === 'NAV' || el.getAttribute('role') === 'navigation') return 'navigation';
            if (el.classList.contains('tab')) return 'tab';
            return 'link'; // Default to link type for better visibility
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
        },

        setupShadowDOMObserver() {
            if (!this.config.shadowDOMEnabled) return;

            const observeShadowDOM = (node) => {
                if (node.shadowRoot) {
                    this.setupObservers(node.shadowRoot);
                    this.scanForInteractiveElements(node.shadowRoot);
                }
            };

            const shadowObserver = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            observeShadowDOM(node);
                        }
                    });
                });
            });

            shadowObserver.observe(document.body, {
                childList: true,
                subtree: true
            });
        },

        setupIframeObserver() {
            if (!this.config.iframeSupport) return;

            const iframeObserver = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.tagName === 'IFRAME') {
                            this.handleIframe(node);
                        }
                    });
                });
            });

            iframeObserver.observe(document.body, {
                childList: true,
                subtree: true
            });
        },

        handleIframe(iframe) {
            try {
                iframe.addEventListener('load', () => {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (iframeDoc) {
                        this.setupObservers(iframeDoc);
                        this.scanForInteractiveElements(iframeDoc);
                    }
                });
            } catch (e) {
                console.warn('Unable to access iframe:', e);
            }
        },

        getXPathForElement(element) {
            if (!this.config.xpathGeneration) return '';

            const segments = [];
            let currentElement = element;

            while (currentElement && currentElement.nodeType === Node.ELEMENT_NODE) {
                if (currentElement.parentNode instanceof ShadowRoot || 
                    currentElement.parentNode instanceof HTMLIFrameElement) {
                    break;
                }

                let index = 0;
                let sibling = currentElement.previousSibling;
                while (sibling) {
                    if (sibling.nodeType === Node.ELEMENT_NODE &&
                        sibling.nodeName === currentElement.nodeName) {
                        index++;
                    }
                    sibling = sibling.previousSibling;
                }

                const tagName = currentElement.nodeName.toLowerCase();
                const xpathIndex = index > 0 ? `[${index + 1}]` : '';
                segments.unshift(`${tagName}${xpathIndex}`);

                currentElement = currentElement.parentNode;
            }

            return segments.join('/');
        },

        getElementCoordinates(element) {
            if (!this.config.coordinateTracking) return null;

            const rect = element.getBoundingClientRect();
            const scrollX = window.scrollX;
            const scrollY = window.scrollY;

            return {
                viewport: {
                    topLeft: {
                        x: Math.round(rect.left),
                        y: Math.round(rect.top)
                    },
                    bottomRight: {
                        x: Math.round(rect.right),
                        y: Math.round(rect.bottom)
                    },
                    center: {
                        x: Math.round(rect.left + rect.width/2),
                        y: Math.round(rect.top + rect.height/2)
                    }
                },
                page: {
                    topLeft: {
                        x: Math.round(rect.left + scrollX),
                        y: Math.round(rect.top + scrollY)
                    },
                    bottomRight: {
                        x: Math.round(rect.right + scrollX),
                        y: Math.round(rect.bottom + scrollY)
                    },
                    center: {
                        x: Math.round(rect.left + rect.width/2 + scrollX),
                        y: Math.round(rect.top + rect.height/2 + scrollY)
                    }
                },
                dimensions: {
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                }
            };
        },

        initializeCoordinateTracking() {
            // Implementation of initializeCoordinateTracking method
        },

        exportDOMTree() {
            return {
                tree: this.domTree,
                metadata: {
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight,
                        scrollX: window.scrollX,
                        scrollY: window.scrollY
                    }
                }
            };
        }
    };

    // Initialize when script loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.NazareDOM.init();
        });
    } else {
        window.NazareDOM.init();
    }
})();
