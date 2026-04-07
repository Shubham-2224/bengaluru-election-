/**
 * Grid Overlay Module
 * Handles grid drawing, cell selection, and template definition
 */

class GridOverlay {
    static FIELD_CONFIG = {
        voterID: { label: 'Voter ID', key: 'v', color: '#3b82f6' },      // Blue
        photo: { label: 'Photo', key: 'i', color: '#10b981' },           // Green
        name: { label: 'Name', key: 'n', color: '#f59e0b' },             // Amber
        relativeName: { label: 'Relative Name', key: 'r', color: '#ef4444' }, // Red
        houseNo: { label: 'House No', key: 'h', color: '#8b5cf6' },      // Purple
        gender: { label: 'Gender', key: 'g', color: '#ec4899' },         // Pink
        age: { label: 'Age', key: 'a', color: '#06b6d4' },               // Cyan
        serialNo: { label: 'Serial No', key: 's', color: '#6366f1' },    // Indigo
        assemblyNo: { label: 'Assembly No', key: 'm', color: '#14b8a6' }, // Teal
        relationType: { label: 'Relation Type', key: 't', color: '#10b981' }, // Emerald
        boothCenter: { label: 'Booth Center', key: 'c', color: '#db2777', scope: 'page' }, // Pink-Red
        boothAddress: { label: 'Booth Address', key: 'b', color: '#7c3aed', scope: 'page' } // Violet
    };

    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.context = this.canvas.getContext('2d');

        // Grid state
        this.grid = null;
        this.isDrawing = false;
        this.isDragging = false;
        this.isResizing = false;
        this.isDraggingLine = false;
        this.resizeHandle = null; // 'topLeft', 'topRight', 'bottomLeft', 'bottomRight'
        this.draggedLine = null; // {type: 'row'|'col', index: number}
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.gridStartX = 0;
        this.gridStartY = 0;
        this.gridStartWidth = 0;
        this.gridStartHeight = 0;

        // Custom line positions (for non-uniform grids)
        this.customRowPositions = []; // Array of y positions
        this.customColPositions = []; // Array of x positions

        // Template state
        this.templateMode = false;
        this.templateType = null; // Key from FIELD_CONFIG
        this.boxes = {}; // Stores CELL boxes keyed by templateType
        this.pageBoxes = {}; // Stores PAGE boxes keyed by templateType

        // Drawing state
        this.drawStart = null;
        this.currentRect = null;

        // Skip zones
        this.showSkipZones = false;
        this.headerHeight = 0;
        this.footerHeight = 0;

        // PDF scale (CRITICAL: must match pdfViewer scale for coordinate conversion)
        this.pdfScale = 1.5;  // Default scale from PDFViewer

        // Bind event listeners
        this.setupEventListeners();
    }

    /**
     * Set PDF scale for coordinate conversion
     * Must be called when PDF scale changes
     */
    setPDFScale(scale) {
        this.pdfScale = scale;
        console.log(`Grid overlay scale updated to: ${scale}`);
    }

    setupEventListeners() {
        this.canvas.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.handleMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.handleMouseUp.bind(this));

        // Listen for PDF page rendered events
        window.addEventListener('pdfPageRendered', this.handlePDFPageRendered.bind(this));

        // Listen for keyboard events
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    }

    handlePDFPageRendered(event) {
        const { width, height, scale } = event.detail;
        this.canvas.width = width;
        this.canvas.height = height;

        // CRITICAL: Update PDF scale for coordinate conversion
        if (scale !== undefined) {
            this.setPDFScale(scale);
        }

        // Try to restore grid from localStorage if available
        this.loadConfig();

        this.redraw();
    }

    handleMouseDown(event) {
        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        if (this.templateMode && this.grid) {
            // Template mode - draw sub-regions in first cell
            this.isDrawing = true;
            this.drawStart = { x, y };
        } else if (this.grid && !this.templateMode) {
            // Check if clicking on resize handle
            const handle = this.getResizeHandle(x, y);
            if (handle) {
                this.isResizing = true;
                this.resizeHandle = handle;
                this.dragStartX = x;
                this.dragStartY = y;
                this.gridStartX = this.grid.x;
                this.gridStartY = this.grid.y;
                this.gridStartWidth = this.grid.width;
                this.gridStartHeight = this.grid.height;
                return;
            }

            // Check if clicking on a grid line
            const line = this.getGridLineAtPoint(x, y);
            if (line) {
                this.isDraggingLine = true;
                this.draggedLine = line;
                this.dragStartX = x;
                this.dragStartY = y;
                return;
            }

            // Check if clicking on grid for dragging
            if (this.isPointInGrid(x, y)) {
                this.isDragging = true;
                this.dragStartX = x - this.grid.x;
                this.dragStartY = y - this.grid.y;
            }
        }
    }

    handleMouseMove(event) {
        const rect = this.canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        if (this.isDrawing && this.drawStart) {
            // Drawing template boxes
            this.currentRect = {
                x: Math.min(this.drawStart.x, x),
                y: Math.min(this.drawStart.y, y),
                width: Math.abs(x - this.drawStart.x),
                height: Math.abs(y - this.drawStart.y)
            };
            this.redraw();
        } else if (this.isDraggingLine && this.draggedLine) {
            // Dragging individual grid line
            if (this.draggedLine.type === 'row') {
                const newY = y;
                // Constrain within grid bounds
                if (newY > this.grid.y && newY < this.grid.y + this.grid.height) {
                    this.customRowPositions[this.draggedLine.index] = newY;
                }
            } else if (this.draggedLine.type === 'col') {
                const newX = x;
                // Constrain within grid bounds
                if (newX > this.grid.x && newX < this.grid.x + this.grid.width) {
                    this.customColPositions[this.draggedLine.index] = newX;
                }
            }
            this.redraw();
        } else if (this.isResizing && this.grid) {
            // Resizing grid from corner
            const deltaX = x - this.dragStartX;
            const deltaY = y - this.dragStartY;

            switch (this.resizeHandle) {
                case 'topLeft':
                    this.grid.x = this.gridStartX + deltaX;
                    this.grid.y = this.gridStartY + deltaY;
                    this.grid.width = this.gridStartWidth - deltaX;
                    this.grid.height = this.gridStartHeight - deltaY;
                    break;
                case 'topRight':
                    this.grid.y = this.gridStartY + deltaY;
                    this.grid.width = this.gridStartWidth + deltaX;
                    this.grid.height = this.gridStartHeight - deltaY;
                    break;
                case 'bottomLeft':
                    this.grid.x = this.gridStartX + deltaX;
                    this.grid.width = this.gridStartWidth - deltaX;
                    this.grid.height = this.gridStartHeight + deltaY;
                    break;
                case 'bottomRight':
                    this.grid.width = this.gridStartWidth + deltaX;
                    this.grid.height = this.gridStartHeight + deltaY;
                    break;
            }

            // Ensure minimum size
            if (this.grid.width < 100) this.grid.width = 100;
            if (this.grid.height < 100) this.grid.height = 100;

            // Reset custom positions when resizing
            this.initializeCustomPositions();
            this.redraw();
        } else if (this.isDragging && this.grid) {
            // Dragging grid
            this.grid.x = x - this.dragStartX;
            this.grid.y = y - this.dragStartY;
            this.redraw();
        } else if (this.grid && !this.templateMode) {
            // Update cursor based on hover position
            const handle = this.getResizeHandle(x, y);
            if (handle) {
                this.updateCursor(handle);
            } else {
                const line = this.getGridLineAtPoint(x, y);
                if (line) {
                    this.canvas.style.cursor = line.type === 'row' ? 'ns-resize' : 'ew-resize';
                } else if (this.isPointInGrid(x, y)) {
                    this.canvas.style.cursor = 'move';
                } else {
                    this.canvas.style.cursor = 'default';
                }
            }
        }
    }

    handleMouseUp(event) {
        if (this.isDrawing && this.currentRect) {
            // Save the drawn rectangle
            if (this.templateType && GridOverlay.FIELD_CONFIG[this.templateType]) {
                const config = GridOverlay.FIELD_CONFIG[this.templateType];
                const box = { ...this.currentRect };

                if (config.scope === 'page') {
                    // Page-level box: Store absolute coordinates
                    this.pageBoxes[this.templateType] = box;
                    console.log(`Page box ${config.label} defined:`, box);
                    this.showToast(`${config.label} box defined (Page Header)`, 'success');
                } else {
                    // Cell-level box: Convert to relative coordinates (relative to first cell)
                    const firstCell = this.getFirstCell();
                    if (firstCell) {
                        box.x -= firstCell.x;
                        box.y -= firstCell.y;
                        this.boxes[this.templateType] = box;
                        console.log(`${config.label} box defined:`, box);
                        this.showToast(`${config.label} box defined`, 'success');
                    }
                }
            }
            this.currentRect = null;
        }

        this.isDrawing = false;
        this.isDragging = false;
        this.isResizing = false;
        this.isDraggingLine = false;
        this.resizeHandle = null;
        this.draggedLine = null;
        this.canvas.style.cursor = 'default';
        this.redraw();

        // Save state after any interaction
        this.saveConfig();
    }

    handleKeyDown(event) {
        if (this.templateMode) {
            // check against FIELD_CONFIG
            for (const [type, config] of Object.entries(GridOverlay.FIELD_CONFIG)) {
                if (event.key.toLowerCase() === config.key) {
                    this.templateType = type;
                    this.showToast(`Draw ${config.label} box`, 'info');
                    this.redraw(); // to update cursor color if implemented or UI
                    return;
                }
            }
        } else if (this.grid && !this.templateMode) {
            // Grid adjustment with arrow keys
            const step = event.shiftKey ? 10 : 1; // Hold Shift for larger steps
            let changed = false;

            switch (event.key) {
                case 'ArrowUp':
                    this.grid.y -= step;
                    changed = true;
                    break;
                case 'ArrowDown':
                    this.grid.y += step;
                    changed = true;
                    break;
                case 'ArrowLeft':
                    this.grid.x -= step;
                    changed = true;
                    break;
                case 'ArrowRight':
                    this.grid.x += step;
                    changed = true;
                    break;
                case '+':
                case '=':
                    // Increase grid size
                    this.grid.width += step * 2;
                    this.grid.height += step * 2;
                    changed = true;
                    break;
                case '-':
                case '_':
                    // Decrease grid size
                    this.grid.width -= step * 2;
                    this.grid.height -= step * 2;
                    changed = true;
                    break;
            }

            if (changed) {
                event.preventDefault();
                this.redraw();
                this.saveConfig();
            }
        }
    }

    /**
     * Draw grid on canvas
     */
    drawGrid(rows, columns, x = null, y = null, width = null, height = null) {
        if (!this.canvas.width || !this.canvas.height) {
            console.error('Canvas not initialized');
            return;
        }

        // Auto-calculate dimensions if not provided
        // Better defaults for voter card documents
        if (x === null) {
            x = Math.round(this.canvas.width * 0.05); // 5% margin from left
        }
        if (y === null) {
            y = Math.round(this.canvas.height * 0.10); // 10% margin from top
        }
        if (!width) {
            width = Math.round(this.canvas.width * 0.90); // 90% of canvas width
        }
        if (!height) {
            height = Math.round(this.canvas.height * 0.82); // 82% of canvas height (leaving space for header/footer)
        }

        this.grid = {
            rows,
            columns,
            x,
            y,
            width,
            height
        };

        // Initialize custom line positions
        this.initializeCustomPositions();

        this.redraw();
        this.saveConfig();
    }

    /**
     * Initialize custom line positions with equal spacing
     */
    initializeCustomPositions() {
        if (!this.grid) return;

        const cellWidth = this.grid.width / this.grid.columns;
        const cellHeight = this.grid.height / this.grid.rows;

        // Initialize column positions (vertical lines)
        this.customColPositions = [];
        for (let i = 1; i < this.grid.columns; i++) {
            this.customColPositions.push(this.grid.x + i * cellWidth);
        }

        // Initialize row positions (horizontal lines)
        this.customRowPositions = [];
        for (let i = 1; i < this.grid.rows; i++) {
            this.customRowPositions.push(this.grid.y + i * cellHeight);
        }
    }

    /**
     * Get grid line at point (for dragging)
     */
    getGridLineAtPoint(x, y) {
        if (!this.grid) return null;

        const threshold = 8; // Pixels from line to detect

        // Check vertical lines (columns)
        for (let i = 0; i < this.customColPositions.length; i++) {
            const lineX = this.customColPositions[i];
            if (Math.abs(x - lineX) <= threshold &&
                y >= this.grid.y &&
                y <= this.grid.y + this.grid.height) {
                return { type: 'col', index: i };
            }
        }

        // Check horizontal lines (rows)
        for (let i = 0; i < this.customRowPositions.length; i++) {
            const lineY = this.customRowPositions[i];
            if (Math.abs(y - lineY) <= threshold &&
                x >= this.grid.x &&
                x <= this.grid.x + this.grid.width) {
                return { type: 'row', index: i };
            }
        }

        return null;
    }

    /**
     * Clear grid
     */
    clearGrid() {
        this.grid = null;
        this.boxes = {};
        this.templateMode = false;
        this.customRowPositions = [];
        this.customColPositions = [];
        this.redraw();
        this.saveConfig(); // effectively clears it from storage
    }

    /**
     * Toggle skip zones display
     */
    toggleSkipZones(headerHeight, footerHeight) {
        this.showSkipZones = !this.showSkipZones;
        this.headerHeight = headerHeight;
        this.footerHeight = footerHeight;
        this.redraw();
        this.saveConfig();
    }

    /**
     * Enable template mode
     */
    enableTemplateMode() {
        if (!this.grid) {
            alert('Please draw a grid first');
            return false;
        }
        this.templateMode = true;
        this.templateType = 'voterID';
        this.redraw();
        return true;
    }

    /**
     * Disable template mode
     */
    disableTemplateMode() {
        this.templateMode = false;
        this.templateType = null;
        this.redraw();
    }

    /**
     * Check if template is complete
     */
    isTemplateComplete() {
        // At minimum require Voter ID
        return !!this.boxes.voterID;
    }

    /**
     * Apply quick template for voter cards with photo on RIGHT
     * Creates standard boxes: voter ID on left, photo on right
     */
    applyQuickTemplate() {
        if (!this.grid) {
            console.error('Grid must be created first');
            return false;
        }

        const firstCell = this.getFirstCell();
        if (!firstCell) {
            console.error('Cannot get first cell');
            return false;
        }

        // Standard voter card layout:
        // - Voter ID text on LEFT (60% of width)
        // - Photo on RIGHT (35% of width with 5% margin)

        const cellWidth = firstCell.width;
        const cellHeight = firstCell.height;

        // Voter ID box: Left side, 60% width
        this.boxes.voterID = {
            x: cellWidth * 0.05,      // 5% margin from left
            y: cellHeight * 0.15,     // 15% from top
            width: cellWidth * 0.55,  // 55% width
            height: cellHeight * 0.35 // 35% height (enough for ID text)
        };

        // Photo box: Right side, 35% width
        this.boxes.photo = {
            x: cellWidth * 0.62,      // 62% from left (right side)
            y: cellHeight * 0.10,     // 10% from top
            width: cellWidth * 0.33,  // 33% width
            height: cellHeight * 0.70 // 70% height (vertical photo)
        };

        console.log('✓ Quick template applied (photo on RIGHT)');
        console.log('  Boxes:', this.boxes);

        this.redraw();
        this.saveConfig();
        return true;
    }

    /**
     * Get grid configuration (CONVERTED to PDF coordinates)
     * 
     * CRITICAL: Coordinates are drawn on canvas at pdfScale (default 1.5x),
     * but backend needs actual PDF coordinates (scale 1.0).
     * We must divide by pdfScale to convert canvas → PDF coordinates!
     */
    getGridConfig() {
        if (!this.grid) {
            return null;
        }

        // COORDINATE CONVERSION: Canvas → PDF
        // Canvas shows PDF at 1.5x scale, so divide by scale to get actual PDF coordinates
        const scale = this.pdfScale;

        // Calculate cell boundaries based on custom positions
        const colPositions = [this.grid.x, ...this.customColPositions, this.grid.x + this.grid.width];
        const rowPositions = [this.grid.y, ...this.customRowPositions, this.grid.y + this.grid.height];

        // Convert ALL coordinates from canvas to PDF scale
        const convertedColPositions = colPositions.map(pos => pos / scale);
        const convertedRowPositions = rowPositions.map(pos => pos / scale);
        const convertedCustomColPositions = this.customColPositions.map(pos => pos / scale);
        const convertedCustomRowPositions = this.customRowPositions.map(pos => pos / scale);

        const config = {
            rows: this.grid.rows,
            columns: this.grid.columns,
            x: this.grid.x / scale,
            y: this.grid.y / scale,
            width: this.grid.width / scale,
            height: this.grid.height / scale,
            customColPositions: convertedCustomColPositions,
            customRowPositions: convertedCustomRowPositions,
            colPositions: convertedColPositions,
            rowPositions: convertedRowPositions
        };

        console.log('Grid config (canvas):', {
            x: this.grid.x,
            y: this.grid.y,
            width: this.grid.width,
            height: this.grid.height,
            scale: scale
        });
        console.log('Grid config (PDF):', {
            x: config.x,
            y: config.y,
            width: config.width,
            height: config.height
        });

        return config;
    }

    /**
     * Get cell template (CONVERTED to PDF coordinates)
     * 
     * CRITICAL: Template boxes are relative to first cell, but still need
     * to be scaled because they're drawn on the canvas at pdfScale.
     */
    getCellTemplate() {
        if (!this.boxes.voterID) { // Minimum requirement
            return null;
        }

        const scale = this.pdfScale;
        const scaledBoxes = {};

        for (const [type, box] of Object.entries(this.boxes)) {
            if (box) {
                scaledBoxes[type] = {
                    x: box.x / scale,
                    y: box.y / scale,
                    width: box.width / scale,
                    height: box.height / scale
                };
            }
        }

        return {
            fields: scaledBoxes // New structure
        };
    }

    /**
     * Set the current template type for drawing
     */
    setTemplateType(type) {
        if (GridOverlay.FIELD_CONFIG[type]) {
            this.templateType = type;
            console.log(`Template type set to: ${type}`);
            return true;
        }
        return false;
    }

    /**
     * Get page template (boxes that appear once per page)
     * Converted to PDF coordinates
     */
    getPageTemplate() {
        if (Object.keys(this.pageBoxes).length === 0) {
            return null;
        }

        const scale = this.pdfScale;
        const scaledPageBoxes = {};

        for (const [type, box] of Object.entries(this.pageBoxes)) {
            if (box) {
                scaledPageBoxes[type] = {
                    x: box.x / scale,
                    y: box.y / scale,
                    width: box.width / scale,
                    height: box.height / scale
                };
            }
        }

        return scaledPageBoxes;
    }

    /**
     * Draw template boxes (Cell and Page level)
     */
    drawTemplateBoxes() {
        const firstCell = this.getFirstCell();

        // Draw CELL boxes (only if grid/firstCell exists)
        if (firstCell) {
            for (const [type, box] of Object.entries(this.boxes)) {
                const config = GridOverlay.FIELD_CONFIG[type];
                if (!config) continue;

                const absX = firstCell.x + box.x;
                const absY = firstCell.y + box.y;

                this.context.fillStyle = this.hexToRgba(config.color, 0.3);
                this.context.strokeStyle = config.color;
                this.context.lineWidth = 2;

                this.context.fillRect(absX, absY, box.width, box.height);
                this.context.strokeRect(absX, absY, box.width, box.height);

                // Label
                this.context.fillStyle = config.color;
                this.context.font = 'bold 12px Inter';
                this.context.fillText(config.label, absX, absY - 5);
            }
        }

        // Draw PAGE boxes (Absolute positions) - Indepedent of grid cells
        for (const [type, box] of Object.entries(this.pageBoxes)) {
            const config = GridOverlay.FIELD_CONFIG[type];
            if (!config) continue;

            this.context.fillStyle = this.hexToRgba(config.color, 0.2);
            this.context.strokeStyle = config.color;
            this.context.lineWidth = 2;
            this.context.setLineDash([5, 3]); // Dashed line for page elements

            this.context.fillRect(box.x, box.y, box.width, box.height);
            this.context.strokeRect(box.x, box.y, box.width, box.height);

            this.context.setLineDash([]); // Reset dash

            // Label
            this.context.fillStyle = config.color;
            this.context.font = 'bold 12px Inter';
            this.context.fillText(config.label + ' (Page)', box.x, box.y - 5);
        }
    }

    // Helper to get first cell for relative calculations
    getFirstCell() {
        if (!this.grid) return null;
        const width = this.grid.width / this.grid.columns;
        const height = this.grid.height / this.grid.rows;

        // Use custom positions if available
        let x = this.grid.x;
        let y = this.grid.y;
        let w = width;
        let h = height;

        if (this.customColPositions.length > 0) {
            w = this.customColPositions[0] - this.grid.x;
        }
        if (this.customRowPositions.length > 0) {
            h = this.customRowPositions[0] - this.grid.y;
        }

        return { x, y, width: w, height: h };
    }

    hexToRgba(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    /**
     * Redraw canvas
     */
    redraw() {
        // Clear canvas
        this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw skip zones
        if (this.showSkipZones) {
            this.drawSkipZones();
        }

        // Draw grid
        if (this.grid) {
            this.drawGridLines();
        }

        // Draw template boxes
        // Allow drawing if grid exists OR if we have Page Boxes (which don't need a grid)
        const hasBoxes = Object.keys(this.boxes).length > 0;
        const hasPageBoxes = Object.keys(this.pageBoxes).length > 0;

        if (this.templateMode || this.grid || hasBoxes || hasPageBoxes) {
            this.drawTemplateBoxes();
        }

        // Draw current rectangle being drawn
        if (this.currentRect) {
            const config = GridOverlay.FIELD_CONFIG[this.templateType];
            this.context.strokeStyle = config ? config.color : '#3b82f6';
            this.context.lineWidth = 3;
            this.context.strokeRect(
                this.currentRect.x,
                this.currentRect.y,
                this.currentRect.width,
                this.currentRect.height
            );
        }
    }

    /**
     * Draw skip zones (header and footer)
     */
    drawSkipZones() {
        // Header zone
        if (this.headerHeight > 0) {
            this.context.fillStyle = 'rgba(239, 68, 68, 0.3)';
            this.context.fillRect(0, 0, this.canvas.width, this.headerHeight);
            this.context.strokeStyle = '#ef4444';
            this.context.lineWidth = 2;
            this.context.strokeRect(0, 0, this.canvas.width, this.headerHeight);

            // Label
            this.context.fillStyle = '#ef4444';
            this.context.font = 'bold 16px Inter';
            this.context.fillText('SKIP HEADER', 10, this.headerHeight - 10);
        }

        // Footer zone
        if (this.footerHeight > 0) {
            const footerY = this.canvas.height - this.footerHeight;
            this.context.fillStyle = 'rgba(239, 68, 68, 0.3)';
            this.context.fillRect(0, footerY, this.canvas.width, this.footerHeight);
            this.context.strokeStyle = '#ef4444';
            this.context.lineWidth = 2;
            this.context.strokeRect(0, footerY, this.canvas.width, this.footerHeight);

            // Label
            this.context.fillStyle = '#ef4444';
            this.context.font = 'bold 16px Inter';
            this.context.fillText('SKIP FOOTER', 10, footerY + 25);
        }
    }

    /**
     * Draw grid lines
     */
    drawGridLines() {
        // Draw outer border
        this.context.strokeStyle = '#4f46e5';
        this.context.lineWidth = 3;
        this.context.strokeRect(this.grid.x, this.grid.y, this.grid.width, this.grid.height);

        // Draw grid lines
        this.context.strokeStyle = '#818cf8';
        this.context.lineWidth = 2;

        // Vertical lines (using custom positions)
        for (let i = 0; i < this.customColPositions.length; i++) {
            const x = this.customColPositions[i];
            this.context.beginPath();
            this.context.moveTo(x, this.grid.y);
            this.context.lineTo(x, this.grid.y + this.grid.height);
            this.context.stroke();
        }

        // Horizontal lines (using custom positions)
        for (let i = 0; i < this.customRowPositions.length; i++) {
            const y = this.customRowPositions[i];
            this.context.beginPath();
            this.context.moveTo(this.grid.x, y);
            this.context.lineTo(this.grid.x + this.grid.width, y);
            this.context.stroke();
        }

        // Draw cell numbers
        this.drawCellNumbers();

        // Draw resize handles at corners (only when not in template mode)
        if (!this.templateMode) {
            this.drawResizeHandles();
            this.drawLineHandles();
        }
    }

    /**
     * Draw cell numbers based on current grid divisions
     */
    drawCellNumbers() {
        this.context.fillStyle = '#4f46e5';
        this.context.font = 'bold 14px Inter';

        // Calculate all column X positions
        const colPositions = [this.grid.x, ...this.customColPositions, this.grid.x + this.grid.width];

        // Calculate all row Y positions
        const rowPositions = [this.grid.y, ...this.customRowPositions, this.grid.y + this.grid.height];

        let cellNum = 1;
        for (let row = 0; row < this.grid.rows; row++) {
            for (let col = 0; col < this.grid.columns; col++) {
                const cellX = colPositions[col] + 5;
                const cellY = rowPositions[row] + 20;
                this.context.fillText(`${cellNum}`, cellX, cellY);
                cellNum++;
            }
        }
    }

    /**
     * Draw visual indicators on draggable lines
     */
    drawLineHandles() {
        const handleSize = 6;

        // Draw handles on vertical lines
        this.customColPositions.forEach(x => {
            const y = this.grid.y + this.grid.height / 2;

            // Outer circle
            this.context.fillStyle = '#ffffff';
            this.context.beginPath();
            this.context.arc(x, y, handleSize + 1, 0, 2 * Math.PI);
            this.context.fill();

            // Inner circle
            this.context.fillStyle = '#818cf8';
            this.context.beginPath();
            this.context.arc(x, y, handleSize, 0, 2 * Math.PI);
            this.context.fill();
        });

        // Draw handles on horizontal lines
        this.customRowPositions.forEach(y => {
            const x = this.grid.x + this.grid.width / 2;

            // Outer circle
            this.context.fillStyle = '#ffffff';
            this.context.beginPath();
            this.context.arc(x, y, handleSize + 1, 0, 2 * Math.PI);
            this.context.fill();

            // Inner circle
            this.context.fillStyle = '#818cf8';
            this.context.beginPath();
            this.context.arc(x, y, handleSize, 0, 2 * Math.PI);
            this.context.fill();
        });
    }

    /**
     * Draw resize handles at grid corners
     */
    drawResizeHandles() {
        const handleSize = 12;
        const corners = [
            { x: this.grid.x, y: this.grid.y }, // topLeft
            { x: this.grid.x + this.grid.width, y: this.grid.y }, // topRight
            { x: this.grid.x, y: this.grid.y + this.grid.height }, // bottomLeft
            { x: this.grid.x + this.grid.width, y: this.grid.y + this.grid.height } // bottomRight
        ];

        corners.forEach(corner => {
            // Outer circle (white)
            this.context.fillStyle = '#ffffff';
            this.context.beginPath();
            this.context.arc(corner.x, corner.y, handleSize / 2 + 2, 0, 2 * Math.PI);
            this.context.fill();

            // Inner circle (primary color)
            this.context.fillStyle = '#4f46e5';
            this.context.beginPath();
            this.context.arc(corner.x, corner.y, handleSize / 2, 0, 2 * Math.PI);
            this.context.fill();

            // Border
            this.context.strokeStyle = '#ffffff';
            this.context.lineWidth = 2;
            this.context.stroke();
        });
    }

    /**
     * Draw template boxes
     */
    drawTemplateBoxes() {
        // Always draw PAGE boxes (Absolute positions) - Independent of grid cells and template mode
        for (const [type, box] of Object.entries(this.pageBoxes)) {
            const config = GridOverlay.FIELD_CONFIG[type];
            if (!config) continue;

            this.context.fillStyle = this.hexToRgba(config.color, 0.2);
            this.context.strokeStyle = config.color;
            this.context.lineWidth = 2;
            this.context.setLineDash([5, 3]); // Dashed line for page elements

            this.context.fillRect(box.x, box.y, box.width, box.height);
            this.context.strokeRect(box.x, box.y, box.width, box.height);

            this.context.setLineDash([]); // Reset dash

            // Label
            this.context.fillStyle = config.color;
            this.context.font = 'bold 12px Inter';
            this.context.fillText(config.label + ' (Page)', box.x, box.y - 5);
        }

        // If not in template mode, draw on all cells
        if (!this.templateMode && Object.keys(this.boxes).length > 0) {
            this.drawTemplateOnAllCells();
            return;
        }

        const firstCell = this.getFirstCell();
        if (!firstCell) return;

        // Draw each defined box on first cell
        for (const [type, box] of Object.entries(this.boxes)) {
            if (!box) continue;

            const x = firstCell.x + box.x;
            const y = firstCell.y + box.y;

            const config = GridOverlay.FIELD_CONFIG[type];
            const color = config ? config.color : '#999';
            const label = config ? config.label : type;

            this.context.strokeStyle = color;
            this.context.lineWidth = 2;
            this.context.strokeRect(x, y, box.width, box.height);

            this.context.fillStyle = color;
            const textWidth = this.context.measureText(label).width;
            this.context.fillRect(x, y - 20, textWidth + 10, 20);

            this.context.fillStyle = 'white';
            this.context.font = 'bold 12px Inter';
            this.context.fillText(label, x + 5, y - 5);
        }

        // Highlight first cell (only in template mode)
        if (this.templateMode) {
            this.context.strokeStyle = '#f59e0b';
            this.context.lineWidth = 3;
            this.context.setLineDash([10, 5]);
            this.context.strokeRect(firstCell.x, firstCell.y, firstCell.width, firstCell.height);
            this.context.setLineDash([]);
        }
    }

    /**
     * Draw template boxes on all grid cells (after template is applied)
     */
    drawTemplateOnAllCells() {
        const colPositions = [this.grid.x, ...this.customColPositions, this.grid.x + this.grid.width];
        const rowPositions = [this.grid.y, ...this.customRowPositions, this.grid.y + this.grid.height];

        // Draw template on each cell
        for (let row = 0; row < this.grid.rows; row++) {
            for (let col = 0; col < this.grid.columns; col++) {
                const cellX = colPositions[col];
                const cellY = rowPositions[row];
                const cellWidth = colPositions[col + 1] - colPositions[col];
                const cellHeight = rowPositions[row + 1] - rowPositions[row];

                // Scale the template boxes to fit the cell
                const scaleX = cellWidth / this.getFirstCell().width;
                const scaleY = cellHeight / this.getFirstCell().height;

                // Draw each box
                for (const [type, box] of Object.entries(this.boxes)) {
                    if (!box) continue;

                    const config = GridOverlay.FIELD_CONFIG[type];
                    const color = config ? config.color : '#999';

                    this.context.strokeStyle = color;
                    this.context.lineWidth = 2;
                    this.context.strokeRect(
                        cellX + box.x * scaleX,
                        cellY + box.y * scaleY,
                        box.width * scaleX,
                        box.height * scaleY
                    );

                    // Light fill
                    this.context.fillStyle = color + '1A'; // 10% opacity (hex approx)
                    this.context.fillRect(
                        cellX + box.x * scaleX,
                        cellY + box.y * scaleY,
                        box.width * scaleX,
                        box.height * scaleY
                    );
                }
            }
        }
    }

    /**
     * Get first cell coordinates
     */
    getFirstCell() {
        if (!this.grid) {
            return null;
        }

        const colPositions = [this.grid.x, ...this.customColPositions, this.grid.x + this.grid.width];
        const rowPositions = [this.grid.y, ...this.customRowPositions, this.grid.y + this.grid.height];

        return {
            x: colPositions[0],
            y: rowPositions[0],
            width: colPositions[1] - colPositions[0],
            height: rowPositions[1] - rowPositions[0]
        };
    }

    /**
     * Check if point is in grid
     */
    isPointInGrid(x, y) {
        if (!this.grid) {
            return false;
        }

        return x >= this.grid.x &&
            x <= this.grid.x + this.grid.width &&
            y >= this.grid.y &&
            y <= this.grid.y + this.grid.height;
    }

    /**
     * Get resize handle at point
     */
    getResizeHandle(x, y) {
        if (!this.grid) {
            return null;
        }

        const handleSize = 20; // Size of the clickable corner area
        const corners = {
            topLeft: {
                x: this.grid.x,
                y: this.grid.y
            },
            topRight: {
                x: this.grid.x + this.grid.width,
                y: this.grid.y
            },
            bottomLeft: {
                x: this.grid.x,
                y: this.grid.y + this.grid.height
            },
            bottomRight: {
                x: this.grid.x + this.grid.width,
                y: this.grid.y + this.grid.height
            }
        };

        for (const [handle, corner] of Object.entries(corners)) {
            if (Math.abs(x - corner.x) <= handleSize && Math.abs(y - corner.y) <= handleSize) {
                return handle;
            }
        }

        return null;
    }

    /**
     * Update cursor based on resize handle
     */
    updateCursor(handle) {
        const cursors = {
            topLeft: 'nwse-resize',
            topRight: 'nesw-resize',
            bottomLeft: 'nesw-resize',
            bottomRight: 'nwse-resize'
        };
        this.canvas.style.cursor = cursors[handle] || 'default';
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        // This will be handled by app.js
        window.dispatchEvent(new CustomEvent('showToast', {
            detail: { message, type }
        }));
    }
    /**
     * Save configuration to LocalStorage
     * Saves essentially the "PDF Coordinate" version so it's scale-independent
     */
    saveConfig() {
        if (!this.grid) {
            localStorage.removeItem('voter_grid_config');
            return;
        }

        const scale = this.pdfScale;

        // Normalize everything to Scale 1.0 (PDF Coordinates)
        const config = {
            grid: {
                rows: this.grid.rows,
                columns: this.grid.columns,
                x: this.grid.x / scale,
                y: this.grid.y / scale,
                width: this.grid.width / scale,
                height: this.grid.height / scale
            },
            customColPositions: this.customColPositions.map(p => p / scale),
            customRowPositions: this.customRowPositions.map(p => p / scale),
            boxes: {},
            pageBoxes: {},
            headerHeight: this.headerHeight / scale,
            footerHeight: this.footerHeight / scale,
            showSkipZones: this.showSkipZones,
            timestamp: Date.now()
        };

        // Normalize boxes
        for (const [key, box] of Object.entries(this.boxes)) {
            if (box) {
                config.boxes[key] = {
                    x: box.x / scale,
                    y: box.y / scale,
                    width: box.width / scale,
                    height: box.height / scale
                };
            }
        }

        // Normalize PAGE boxes
        for (const [key, box] of Object.entries(this.pageBoxes)) {
            if (box) {
                config.pageBoxes[key] = {
                    x: box.x / scale,
                    y: box.y / scale,
                    width: box.width / scale,
                    height: box.height / scale
                };
            }
        }

        localStorage.setItem('voter_grid_config', JSON.stringify(config));
        // console.log("Grid configuration saved to LocalStorage");
    }

    /**
     * Load configuration from external JSON (Server)
     */
    loadConfigFromJSON(config) {
        if (!config) return;

        console.log("Loading Config from JSON:", config);

        // Restore Grid
        if (config.grid) {
            this.grid = config.grid;

            // Restore Custom Positions if valid
            if (config.customColPositions && Array.isArray(config.customColPositions)) {
                this.customColPositions = config.customColPositions;
            }
            if (config.customRowPositions && Array.isArray(config.customRowPositions)) {
                this.customRowPositions = config.customRowPositions;
            }
        }

        // Restore Boxes
        if (config.cellTemplate) {
            // Convert template format back to internal boxes format
            // Template: { voterIdBox: {x,y,w,h}, ... }
            // Internal: { voterID: {x,y,w,h}, ... }

            // Clear existing
            this.boxes = {};

            // Reverse mapping from FIELD_CONFIG key to template key
            const reverseMap = {};
            for (const [key, val] of Object.entries(GridOverlay.FIELD_CONFIG)) {
                // Assume standard mapping logic or check config structure
                // In getGridConfig/getCellTemplate, we mapped 'voterID' -> 'voterIdBox'
                // Here we need to map back 'voterID' -> 'voterIdBox' (Wait, logic is mapped in getCellTemplate)
            }

            // Mapping based on standard expectations from getCellTemplate
            if (config.cellTemplate.voterIdBox) this.boxes['voterID'] = config.cellTemplate.voterIdBox;
            if (config.cellTemplate.photoBox) this.boxes['photo'] = config.cellTemplate.photoBox;

            if (config.cellTemplate.fields) {
                for (const [key, box] of Object.entries(config.cellTemplate.fields)) {
                    this.boxes[key] = box;
                }
            }
        }

        // Restore Page Boxes
        if (config.pageTemplate) {
            this.pageBoxes = config.pageTemplate;
        }

        this.redraw();
    }

    /**
     * Load configuration from LocalStorage
     */
    loadConfig() {
        // We ALWAYS try to load from storage on render/init to ensure
        // the grid is scaled correctly to the current PDF scale (zooming).
        // Since saveConfig() is called on every interaction, storage is the source of truth.

        const saved = localStorage.getItem('voter_grid_config');
        if (!saved) return;

        try {
            const config = JSON.parse(saved);
            const scale = this.pdfScale;

            // Restore Grid
            this.grid = {
                rows: config.grid.rows,
                columns: config.grid.columns,
                x: config.grid.x * scale,
                y: config.grid.y * scale,
                width: config.grid.width * scale,
                height: config.grid.height * scale
            };

            // Restore Custom Positions
            if (config.customColPositions) {
                this.customColPositions = config.customColPositions.map(p => p * scale);
            }
            if (config.customRowPositions) {
                this.customRowPositions = config.customRowPositions.map(p => p * scale);
            }

            // Restore Boxes
            this.boxes = {};
            if (config.boxes) {
                for (const [key, box] of Object.entries(config.boxes)) {
                    this.boxes[key] = {
                        x: box.x * scale,
                        y: box.y * scale,
                        width: box.width * scale,
                        height: box.height * scale
                    };
                }
            }

            // Restore Page Boxes
            this.pageBoxes = {};
            if (config.pageBoxes) {
                for (const [key, box] of Object.entries(config.pageBoxes)) {
                    this.pageBoxes[key] = {
                        x: box.x * scale,
                        y: box.y * scale,
                        width: box.width * scale,
                        height: box.height * scale
                    };
                }
            }

            // Restore Skip Zones
            if (typeof config.headerHeight === 'number') {
                this.headerHeight = config.headerHeight * scale;
                this.footerHeight = config.footerHeight * scale;
                this.showSkipZones = config.showSkipZones || false;
            }

            console.log("Grid configuration restored from LocalStorage");
            this.redraw();

            // Notify app that config is restored (to update UI buttons)
            window.dispatchEvent(new CustomEvent('gridConfigRestored'));

        } catch (e) {
            console.error("Failed to load grid config:", e);
        }
    }
}


