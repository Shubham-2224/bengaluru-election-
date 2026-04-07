/**
 * Main Application Module
 * Coordinates all components and handles user interactions
 */

// Application state
const AppState = {
    pdfFile: null,
    fileId: null,
    configId: null,
    excelId: null,
    totalPages: 0,
    extractedData: null  // Store extracted data for preview
};

// Initialize components
const pdfViewer = new PDFViewer('pdfCanvas');
const gridOverlay = new GridOverlay('overlayCanvas');
const azureVisionIntegration = new AzureVisionIntegration(gridOverlay);

// DOM Elements
const elements = {
    // Upload
    pdfInput: document.getElementById('pdfInput'),
    uploadArea: document.getElementById('uploadArea'),
    fileInfo: document.getElementById('fileInfo'),

    // Page settings
    skipPagesStart: document.getElementById('skipPagesStart'),
    skipPagesEnd: document.getElementById('skipPagesEnd'),
    skipHeaderHeight: document.getElementById('skipHeaderHeight'),
    skipFooterHeight: document.getElementById('skipFooterHeight'),
    prabhag: document.getElementById('prabhag'),
    boothNo: document.getElementById('boothNo'),
    btnShowSkipZones: document.getElementById('btnShowSkipZones'),

    // Grid
    gridRows: document.getElementById('gridRows'),
    gridColumns: document.getElementById('gridColumns'),
    btnDrawGrid: document.getElementById('btnDrawGrid'),
    btnClearGrid: document.getElementById('btnClearGrid'),

    // Template
    btnTemplateMode: document.getElementById('btnTemplateMode'),
    btnApplyTemplate: document.getElementById('btnApplyTemplate'),
    templateStatus: document.getElementById('templateStatus'),
    templateSelect: document.getElementById('templateSelect'), // NEW DROPDOWN

    // Extraction
    btnExtract: document.getElementById('btnExtract'),
    btnDownload: document.getElementById('btnDownload'),
    extractPhotos: document.getElementById('extractPhotos'),
    performanceMode: document.getElementById('performanceMode'),
    extractionStatus: document.getElementById('extractionStatus'),

    // Preview
    previewSection: document.getElementById('previewSection'),
    extractionSummary: document.getElementById('extractionSummary'),
    btnPreview: document.getElementById('btnPreview'),
    previewModal: document.getElementById('previewModal'),
    btnClosePreview: document.getElementById('btnClosePreview'),
    btnClosePreviewFooter: document.getElementById('btnClosePreviewFooter'),
    btnDownloadFromPreview: document.getElementById('btnDownloadFromPreview'),
    previewStats: document.getElementById('previewStats'),
    previewTableBody: document.getElementById('previewTableBody'),

    // Viewer controls
    btnPrevPage: document.getElementById('btnPrevPage'),
    btnNextPage: document.getElementById('btnNextPage'),
    btnZoomIn: document.getElementById('btnZoomIn'),
    btnZoomOut: document.getElementById('btnZoomOut'),
    currentPage: document.getElementById('currentPage'),
    totalPages: document.getElementById('totalPages'),
    zoomLevel: document.getElementById('zoomLevel'),

    // Overlay
    loadingOverlay: document.getElementById('loadingOverlay'),
    viewerPlaceholder: document.getElementById('viewerPlaceholder'),
    canvasWrapper: document.getElementById('canvasWrapper'),

    // Toast
    toastContainer: document.getElementById('toastContainer')
};

// Event Listeners
function setupEventListeners() {
    // File upload
    elements.pdfInput.addEventListener('change', handleFileSelect);
    elements.uploadArea.addEventListener('dragover', handleDragOver);
    elements.uploadArea.addEventListener('drop', handleFileDrop);

    // Skip zones
    elements.btnShowSkipZones.addEventListener('click', handleShowSkipZones);

    // Grid
    elements.btnDrawGrid.addEventListener('click', handleDrawGrid);
    elements.btnClearGrid.addEventListener('click', handleClearGrid);

    // Template
    elements.btnTemplateMode.addEventListener('click', handleTemplateMode);
    elements.btnApplyTemplate.addEventListener('click', handleApplyTemplate);

    if (elements.templateSelect) {
        elements.templateSelect.addEventListener('change', (e) => {
            if (gridOverlay.templateMode) {
                gridOverlay.setTemplateType(e.target.value);
            }
        });
    }

    // Extraction
    elements.btnExtract.addEventListener('click', handleExtract);
    elements.btnDownload.addEventListener('click', handleDownload);

    // Preview
    elements.btnPreview.addEventListener('click', handlePreview);
    elements.btnClosePreview.addEventListener('click', closePreviewModal);
    elements.btnClosePreviewFooter.addEventListener('click', closePreviewModal);
    elements.btnDownloadFromPreview.addEventListener('click', handleDownload);
    elements.previewModal.addEventListener('click', (e) => {
        if (e.target === elements.previewModal) closePreviewModal();
    });

    // Viewer controls
    elements.btnPrevPage.addEventListener('click', handlePrevPage);
    elements.btnNextPage.addEventListener('click', handleNextPage);
    elements.btnZoomIn.addEventListener('click', handleZoomIn);
    elements.btnZoomOut.addEventListener('click', handleZoomOut);

    // Custom events
    window.addEventListener('showToast', (e) => {
        showToast(e.detail.message, e.detail.type);
    });

    window.addEventListener('gridConfigRestored', handleGridRestored);
}

// === NEW HANDLERS ===

function handleGridRestored() {
    // Enable relevant buttons since grid exists
    elements.btnTemplateMode.disabled = false;

    // Check if template is fully defined
    if (gridOverlay.isTemplateComplete()) {
        elements.btnExtract.disabled = false;
        elements.templateStatus.textContent = '✓ Template restored from storage';
        elements.templateStatus.classList.remove('hidden');
        elements.templateStatus.classList.add('success');
        elements.btnTemplateMode.textContent = 'Template Defined ✓';
    } else {
        // Grid exists but template incomplete
        elements.templateStatus.classList.remove('hidden');
        elements.templateStatus.textContent = 'Grid restored. Please define template boxes.';
        elements.templateStatus.classList.add('info');
    }

    // Restore skip inputs if available
    elements.skipHeaderHeight.value = Math.round(gridOverlay.headerHeight || 0);
    elements.skipFooterHeight.value = Math.round(gridOverlay.footerHeight || 0);

    console.log('UI updated from restored grid config');
}

// File Upload Handlers
async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        await loadPDFFile(file);
    }
}

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    elements.uploadArea.classList.add('drag-over');
}

async function handleFileDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    elements.uploadArea.classList.remove('drag-over');

    const file = event.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
        await loadPDFFile(file);
    } else {
        showToast('Please drop a PDF file', 'error');
    }
}

async function loadPDFFile(file) {
    try {
        showLoading(true, 'Loading PDF...');

        // Load PDF in viewer first
        const result = await pdfViewer.loadPDF(file);
        AppState.pdfFile = file;
        AppState.totalPages = result.totalPages;

        // Update UI
        elements.viewerPlaceholder.classList.add('hidden');
        elements.canvasWrapper.classList.remove('hidden');
        elements.currentPage.textContent = '1';
        elements.totalPages.textContent = result.totalPages;
        elements.fileInfo.textContent = `📄 ${file.name} (${result.totalPages} pages)`;
        elements.fileInfo.classList.remove('hidden');

        // Enable controls
        elements.btnPrevPage.disabled = false;
        elements.btnNextPage.disabled = false;

        // Upload to server (non-blocking, can work offline for preview)
        showLoading(true, 'Uploading to server...');
        try {
            const uploadResult = await API.uploadPDF(file);
            AppState.fileId = uploadResult.fileId;
            console.log('File uploaded successfully:', uploadResult);
            showToast('PDF loaded and uploaded successfully!', 'success');
        } catch (uploadError) {
            console.warn('Server upload failed, but PDF loaded in viewer:', uploadError);
            showToast('PDF loaded in viewer. Upload failed: ' + uploadError.message + ' (You can still adjust grid, but extraction needs server)', 'error');
            // Set fileId to null so extraction knows to fail early
            AppState.fileId = null;
        }

        showLoading(false);

    } catch (error) {
        console.error('Load PDF error:', error);
        showToast('Failed to load PDF: ' + error.message, 'error');
        showLoading(false);
    }
}

// Skip Zones Handler
function handleShowSkipZones() {
    const headerHeight = parseInt(elements.skipHeaderHeight.value) || 0;
    const footerHeight = parseInt(elements.skipFooterHeight.value) || 0;
    gridOverlay.toggleSkipZones(headerHeight, footerHeight);
}

// Grid Handlers
function handleDrawGrid() {
    const rows = parseInt(elements.gridRows.value) || 9;
    const columns = parseInt(elements.gridColumns.value) || 3;

    if (!AppState.pdfFile) {
        showToast('Please upload a PDF first', 'error');
        return;
    }

    gridOverlay.drawGrid(rows, columns);
    showToast('Grid drawn! Drag any line to adjust spacing, drag corners to resize, or drag center to move.', 'success');

    // Enable template mode button
    elements.btnTemplateMode.disabled = false;
}

function handleClearGrid() {
    gridOverlay.clearGrid();
    elements.btnTemplateMode.disabled = true;
    elements.btnApplyTemplate.disabled = true;
    elements.btnExtract.disabled = true;
    elements.templateStatus.classList.add('hidden');
    showToast('Grid cleared', 'info');
}

// Template Handlers
function handleTemplateMode() {
    const enabled = gridOverlay.enableTemplateMode();
    if (enabled) {
        elements.btnTemplateMode.textContent = '✓ Template Mode Active';
        elements.btnTemplateMode.classList.remove('btn-primary');
        elements.btnTemplateMode.classList.add('btn-success');
        elements.templateStatus.textContent = 'Select type from dropdown and draw box.';
        elements.templateStatus.classList.remove('hidden');
        elements.templateStatus.classList.add('info');

        // Sync dropdown with grid overlay (default voterID)
        const currentType = elements.templateSelect.value || 'voterID';
        gridOverlay.setTemplateType(currentType);

        showToast('Template mode active. Select field type and draw box.', 'info');
    }
}

function handleApplyTemplate() {
    if (!gridOverlay.isTemplateComplete()) {
        showToast('Please define both Voter ID and Photo boxes', 'error');
        return;
    }

    gridOverlay.disableTemplateMode();
    elements.btnTemplateMode.textContent = 'Template Defined ✓';
    elements.btnApplyTemplate.disabled = true;
    elements.templateStatus.textContent = '✓ Template applied to all cells';
    elements.templateStatus.classList.remove('info');
    elements.templateStatus.classList.add('success');
    elements.btnExtract.disabled = false;

    showToast('Template applied successfully!', 'success');
}

// Watch for template completion
setInterval(() => {
    if (gridOverlay.templateMode && gridOverlay.isTemplateComplete()) {
        elements.btnApplyTemplate.disabled = false;
    }
}, 500);

// Extraction Handlers
async function handleExtract() {
    try {
        // Check if PDF file exists
        if (!AppState.pdfFile) {
            showToast('Please upload a PDF file first', 'error');
            return;
        }

        // Check if file was uploaded to server
        if (!AppState.fileId) {
            showToast('PDF upload to server failed. Please ensure the backend server is running and try uploading the PDF again.', 'error');
            return;
        }

        showLoading(true, 'Configuring extraction...');

        // Get PDF scale for coordinate conversion
        const pdfScale = gridOverlay.pdfScale || 1.5;

        const gridConfig = gridOverlay.getGridConfig();
        const cellTemplate = gridOverlay.getCellTemplate();

        if (!gridConfig) {
            showToast('Please draw a grid first', 'error');
            showLoading(false);
            return;
        }

        // Configure extraction
        // IMPORTANT: skipHeaderHeight and skipFooterHeight are in CANVAS coordinates,
        // so we need to convert them to PDF coordinates too!
        const config = {
            fileId: AppState.fileId,
            skipPagesStart: parseInt(elements.skipPagesStart.value) || 0,
            skipPagesEnd: parseInt(elements.skipPagesEnd.value) || 0,
            skipHeaderHeight: (parseInt(elements.skipHeaderHeight.value) || 0) / pdfScale,
            skipFooterHeight: (parseInt(elements.skipFooterHeight.value) || 0) / pdfScale,
            prabhag: elements.prabhag.value.trim(),
            boothNo: elements.boothNo.value.trim(),
            grid: gridConfig,
            cellTemplate: cellTemplate,
            pageTemplate: gridOverlay.getPageTemplate(), // Include page template
            extractPhotos: elements.extractPhotos.checked, // Photo extraction control
            performanceMode: elements.performanceMode.value // Performance mode control
        };

        console.log('Extraction Configuration (converted to PDF coordinates):', config);
        console.log(`PDF Scale used for conversion: ${pdfScale}`);

        const configResult = await API.configureExtraction(config);
        AppState.configId = configResult.configId;

        showLoading(true, 'Extracting data... This may take a few minutes.');

        // Start extraction
        const extractResult = await API.extractGrid(AppState.configId);
        AppState.excelId = extractResult.excelId;
        AppState.extractedData = extractResult.extractedData || [];  // Store extracted data

        console.log('Extraction completed. Records:', extractResult.recordsExtracted);
        console.log('Extracted data available:', extractResult.extractedData ? extractResult.extractedData.length : 0, 'records');
        console.log('Excel ID:', AppState.excelId);

        showLoading(false);

        // Get stats from result
        const stats = extractResult.stats || {};
        const extractionTime = stats.extraction_time_seconds || 0;
        const cellsSkipped = stats.cells_skipped || 0;

        // Format time
        const timeFormatted = extractionTime > 60
            ? `${Math.floor(extractionTime / 60)}m ${Math.round(extractionTime % 60)}s`
            : `${Math.round(extractionTime)}s`;

        // Update UI
        elements.extractionStatus.textContent = `✓ Extracted ${extractResult.recordsExtracted} records successfully!`;
        elements.extractionStatus.classList.remove('hidden');
        elements.extractionStatus.classList.add('success');

        // Show preview section with stats
        let summaryHtml = `
            <div style="margin-bottom: 12px;">
                <strong style="font-size: 18px; color: #10b981;">${extractResult.recordsExtracted}</strong> records extracted successfully!
            </div>
        `;

        if (extractionTime > 0 || cellsSkipped > 0) {
            summaryHtml += `<div style="margin-top: 12px; padding: 12px; background: #f3f4f6; border-radius: 8px; font-size: 13px;">`;

            if (extractionTime > 0) {
                summaryHtml += `
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                        <span>⏱️</span>
                        <span><strong>Time:</strong> ${timeFormatted}</span>
                    </div>
                `;
            }

            if (cellsSkipped > 0) {
                summaryHtml += `
                    <div style="display: flex; align-items: center; gap: 8px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e7eb;">
                        <span>⊘</span>
                        <span style="color: #f59e0b;"><strong>Skipped:</strong> ${cellsSkipped} cells (no voter ID found)</span>
                    </div>
                `;
            }

            summaryHtml += `</div>`;
        }

        summaryHtml += `<div style="margin-top: 12px; font-size: 13px; color: #6b7280;">Click "Preview Data" to see results before downloading.</div>`;

        // Show preview section with data
        console.log('Showing preview section. Hidden class:', elements.previewSection.classList.contains('hidden'));
        elements.previewSection.classList.remove('hidden');
        console.log('After removal. Hidden class:', elements.previewSection.classList.contains('hidden'));
        elements.extractionSummary.innerHTML = summaryHtml;
        elements.btnDownload.disabled = false;
        elements.btnPreview.disabled = false;  // Ensure preview button is enabled

        console.log('Preview section shown. Data ready:', AppState.extractedData ? AppState.extractedData.length : 0, 'records');

        // Show toast with stats
        let toastMsg = `Extraction complete! ${extractResult.recordsExtracted} records extracted.`;
        if (extractionTime > 0) toastMsg += ` Time: ${timeFormatted}`;
        showToast(toastMsg, 'success');

    } catch (error) {
        console.error('Extraction error:', error);
        showLoading(false);
        if (error.message.includes('Failed to fetch') || error.message.includes('Cannot connect')) {
            showToast('Cannot connect to server. Please ensure both Node.js and Python servers are running (START_SERVERS.bat)', 'error');
        } else {
            showToast('Extraction failed: ' + error.message, 'error');
        }
    }
}

function handleDownload() {
    if (!AppState.excelId) {
        showToast('No file to download', 'error');
        return;
    }

    API.downloadExcel(AppState.excelId);
    showToast('Downloading Excel file...', 'success');
}

// Viewer Control Handlers
async function handlePrevPage() {
    await pdfViewer.prevPage();
    updatePageDisplay();
    gridOverlay.redraw();
}

async function handleNextPage() {
    await pdfViewer.nextPage();
    updatePageDisplay();
    gridOverlay.redraw();
}

async function handleZoomIn() {
    await pdfViewer.zoomIn();
    updateZoomDisplay();
    gridOverlay.redraw();
}

async function handleZoomOut() {
    await pdfViewer.zoomOut();
    updateZoomDisplay();
    gridOverlay.redraw();
}

function updatePageDisplay() {
    elements.currentPage.textContent = pdfViewer.currentPage;
}

function updateZoomDisplay() {
    elements.zoomLevel.textContent = pdfViewer.getZoomLevel() + '%';
}

// UI Helpers
function showLoading(show, message = 'Processing...') {
    if (show) {
        elements.loadingOverlay.classList.remove('hidden');
        const loadingText = elements.loadingOverlay.querySelector('.loading-text');
        if (loadingText) {
            loadingText.textContent = message;
        }
    } else {
        elements.loadingOverlay.classList.add('hidden');
    }
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
        error: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
        info: '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
    };

    toast.innerHTML = `
        ${icons[type] || icons.info}
        <div class="toast-message">${message}</div>
    `;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getConfidenceClass(confidence) {
    if (confidence >= 0.8) return 'confidence-high';
    if (confidence >= 0.5) return 'confidence-medium';
    return 'confidence-low';
}

// Preview Modal Handlers
function handlePreview() {
    console.log('Preview button clicked. Data available:', AppState.extractedData ? AppState.extractedData.length : 0);

    if (!AppState.extractedData || AppState.extractedData.length === 0) {
        console.error('No data to preview');
        showToast('No data to preview', 'error');
        return;
    }

    console.log('Opening preview modal...');
    // Show modal
    elements.previewModal.classList.remove('hidden');

    // Populate stats
    const totalRecords = AppState.extractedData.length;
    const withVoterIds = AppState.extractedData.filter(r => r.voterID && r.voterID.trim()).length;
    const withPhotos = AppState.extractedData.filter(r => r.image_base64 && r.image_base64.trim()).length;

    elements.previewStats.innerHTML = `
        <div class="stat-item">
            <span class="stat-value">${totalRecords}</span>
            <span class="stat-label">Total Records</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">${withVoterIds}</span>
            <span class="stat-label">Voter IDs Found</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">${withPhotos}</span>
            <span class="stat-label">Photos Extracted</span>
        </div>
    `;

    // Populate table
    elements.previewTableBody.innerHTML = AppState.extractedData.map((record, index) => {
        const confidence = record.metadata?.voter_id_confidence || 0;
        const confidenceClass = getConfidenceClass(confidence);
        const confidencePercent = (confidence * 100).toFixed(0);

        return `
            <tr>
                <td>${index + 1}</td>
                <td>${record.page || '-'}</td>
                <td>${record.row || '-'}</td>
                <td>${record.column || '-'}</td>
                <td>${record.prabhag || '-'}</td>
                <td>${record.boothNo || '-'}</td>
                <td>${record.serialNo || '-'}</td>
                <td class="voter-id-cell">${record.voterID || '<span class="no-data">No ID</span>'}</td>
                <td>${record.name || '-'}</td>
                <td>${record.nameKannada || '-'}</td>
                <td>${record.relationType || '-'}</td>
                <td>${record.relativeName || '-'}</td>
                <td>${record.relativeNameKannada || '-'}</td>
                <td>${record.houseNo || '-'}</td>
                <td>${record.gender || '-'}</td>
                <td>${record.age || '-'}</td>
                <td>${record.assemblyNo || '-'}</td>
                <td>${record.boothCenter || '-'}</td>
                <td>${record.boothCenterKannada || '-'}</td>
                <td>${record.boothAddress || '-'}</td>
                <td>${record.boothAddressKannada || '-'}</td>
                <td class="photo-cell">
                    ${record.image_base64
                ? `<img src="data:image/jpeg;base64,${record.image_base64}" 
                             alt="Voter Photo" 
                             class="preview-photo" 
                             title="Click to zoom">`
                : '<span class="no-data">No Photo</span>'}
                </td>
                <td>
                    <span class="confidence-badge ${confidenceClass}">
                        ${confidencePercent}%
                    </span>
                </td>
            </tr>
        `;
    }).join('');

    showToast(`Previewing ${totalRecords} records`, 'info');
}

function closePreviewModal() {
    elements.previewModal.classList.add('hidden');
}

// Check server health on load
async function checkServerHealth() {
    const isHealthy = await API.checkHealth();
    if (!isHealthy) {
        showToast('Warning: Cannot connect to backend server. Please ensure it is running.', 'error');
    }
}

// Initialize application
function init() {
    console.log('Initializing Grid-Based PDF Voter Data Extraction Tool');
    setupEventListeners();
    checkServerHealth();

    // Initial state
    elements.canvasWrapper.classList.add('hidden');

    console.log('Application initialized successfully');
}

// Start application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}


