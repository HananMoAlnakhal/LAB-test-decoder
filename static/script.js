// ===== GLOBAL STATE =====
let currentResults = null;
let explanations = null;

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    // Navigation is now handled via onclick="showSection", but we init other listeners
    initFileUpload();
    initScrollAnimations();
    initEnterKey();
});

// ===== NAVIGATION (Compatible with Tailwind HTML) =====
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.remove('active');
        sec.style.display = 'none';
    });

    // Show target section
    const target = document.getElementById(sectionId);
    if (target) {
        target.style.display = 'block';
        // Small timeout to allow display:block to apply before adding active class for animation
        setTimeout(() => {
            target.classList.add('active');
        }, 10);
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// ===== SCROLL ANIMATIONS =====
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.remove('opacity-0', 'translate-y-4');
                entry.target.classList.add('opacity-100', 'translate-y-0');
            }
        });
    }, { threshold: 0.1 });
    
    // Add animation classes to cards
    document.querySelectorAll('.feature-card, .upload-card').forEach(card => {
        card.classList.add('transition-all', 'duration-700', 'opacity-0', 'translate-y-4');
        observer.observe(card);
    });
}

// ===== FILE UPLOAD =====
function initFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    
    if (!fileInput || !uploadArea) return;
    
    // Click to upload (handled by onclick in HTML, but keeping listener just in case)
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop Visuals
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        // Add Tailwind classes for drag state
        uploadArea.classList.add('border-secondary', 'bg-blue-50', 'scale-[1.02]');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        // Remove Tailwind classes
        uploadArea.classList.remove('border-secondary', 'bg-blue-50', 'scale-[1.02]');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('border-secondary', 'bg-blue-50', 'scale-[1.02]');
        
        const file = e.dataTransfer.files[0];
        if (file && file.type === 'application/pdf') {
            uploadFile(file);
        } else {
            showToast('Please upload a PDF file', 'error');
        }
    });
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        uploadFile(file);
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    // Show progress
    document.getElementById('uploadArea').classList.add('hidden');
    document.getElementById('uploadProgress').classList.remove('hidden');
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }
        
        currentResults = data.results;
        showToast(`✓ Found ${data.count} lab results!`, 'success');
        
        // Generate explanations
        await generateExplanations();
        
        // Display results
        displayResults();
        
        // Switch to results tab automatically
        showSection('results-section');
        
    } catch (error) {
        showToast(error.message, 'error');
        resetUploadArea();
    }
}

async function generateExplanations() {
    // Optional: show a mini toast or loading indicator
    try {
        const response = await fetch('/api/explain', { method: 'POST' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        explanations = data.explanations;
    } catch (error) {
        console.warn('Auto-explanation generation failed:', error);
        // We continue anyway, results will just say "Loading..." or show basic info
    }
}

function displayResults() {
    const container = document.getElementById('resultsContainer');
    
    if (!currentResults || currentResults.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-10">No results found</div>';
        return;
    }
    
    // Update summary stats in the Summary tab
    updateSummaryStats();
    
    // Clear container
    container.innerHTML = '';
    
    // Create result cards with Tailwind Styling
    currentResults.forEach((result, index) => {
        const card = createResultCard(result, index);
        container.appendChild(card);
    });
    
    // Reset upload area for next time
    resetUploadArea();
}

function updateSummaryStats() {
    const stats = { normal: 0, high: 0, low: 0 };
    
    currentResults.forEach(result => {
        // Normalize status string
        const status = result.status ? result.status.toLowerCase() : 'normal';
        if (status.includes('high')) stats.high++;
        else if (status.includes('low')) stats.low++;
        else stats.normal++;
    });
    
    // Update the DOM elements in the Summary Section
    document.getElementById('normalCount').textContent = stats.normal;
    document.getElementById('highCount').textContent = stats.high;
    document.getElementById('lowCount').textContent = stats.low;
    
    // Reveal the stats container
    const statsContainer = document.getElementById('summaryStats');
    if(statsContainer) statsContainer.classList.remove('hidden');
    
    const generateBtn = document.getElementById('generateSummaryBtn');
    if(generateBtn) generateBtn.classList.remove('hidden');
}

function createResultCard(result, index) {
    const card = document.createElement('div');
    // TAILWIND STYLING: Card container
    card.className = 'bg-white rounded-xl shadow-sm border border-slate-100 p-5 mb-4 hover:shadow-md transition-shadow';
    
    // Status colors
    let statusColors = 'bg-green-100 text-green-700'; // Default normal
    let borderClass = 'border-l-4 border-green-500';
    
    const statusLower = result.status ? result.status.toLowerCase() : '';
    if (statusLower.includes('high')) {
        statusColors = 'bg-red-100 text-red-700';
        borderClass = 'border-l-4 border-red-500';
    } else if (statusLower.includes('low')) {
        statusColors = 'bg-yellow-100 text-yellow-800';
        borderClass = 'border-l-4 border-yellow-500';
    }

    const explanation = explanations && explanations[result.test_name] 
        ? explanations[result.test_name] 
        : 'Analysis available in Chat or Summary.';
    
    // HTML Structure using Tailwind
    card.innerHTML = `
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 ${borderClass} pl-4">
            <div class="flex-grow">
                <h3 class="text-lg font-bold text-slate-800">${escapeHtml(result.test_name)}</h3>
                <p class="text-sm text-slate-500">Ref Range: ${escapeHtml(result.reference_range || 'N/A')}</p>
            </div>
            
            <div class="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
                <span class="text-xl font-bold text-slate-700">${escapeHtml(result.value)} <span class="text-sm font-normal text-slate-500">${escapeHtml(result.unit)}</span></span>
                <span class="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide ${statusColors}">
                    ${escapeHtml(result.status)}
                </span>
            </div>
        </div>
        
        <div class="mt-4 pt-3 border-t border-slate-50">
            <p class="text-sm text-slate-600 leading-relaxed">
                <span class="font-semibold text-primary">Insight:</span> ${escapeHtml(explanation)}
            </p>
        </div>
    `;
    
    return card;
}

function resetUploadArea() {
    document.getElementById('uploadArea').classList.remove('hidden');
    document.getElementById('uploadProgress').classList.add('hidden');
    document.getElementById('fileInput').value = '';
}

// ===== SUMMARY GENERATION =====
async function generateSummary() {
    if (!currentResults) {
        showToast('Please upload a lab report first', 'error');
        return;
    }
    
    const contentDiv = document.getElementById('summaryContent');
    contentDiv.innerHTML = '<div class="flex justify-center p-8"><div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>';
    
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.error);
        
        // Render summary with Markdown-like paragraphs
        contentDiv.innerHTML = `
            <div class="prose prose-slate max-w-none">
                <h3 class="text-xl font-semibold mb-4 text-primary">Analysis Report</h3>
                <div class="text-slate-700 leading-relaxed whitespace-pre-line">
                    ${escapeHtml(data.summary).replace(/\n/g, '<br>')}
                </div>
            </div>
        `;
        
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
        contentDiv.innerHTML = '<p class="text-red-500 text-center">Failed to generate summary.</p>';
    }
}

// ===== CHAT FUNCTIONALITY =====
function initEnterKey() {
    const input = document.getElementById('chatInput');
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') askQuestion();
        });
    }
}

async function askQuestion() {
    if (!currentResults) {
        showToast('Please upload a lab report first', 'error');
        return;
    }

    const input = document.getElementById('chatInput');
    const question = input.value.trim();
    
    if (!question) return;
    
    // Clear input
    input.value = '';
    
    // Add user message
    addChatMessage(question, 'user');
    
    // Show loading
    const loadingId = addChatMessage('Analyzing...', 'assistant', true);
    
    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);
        
        // Remove loading
        const loadingEl = document.getElementById(loadingId);
        if(loadingEl) loadingEl.remove();
        
        // Add response
        addChatMessage(data.answer, 'assistant');
        
    } catch (error) {
        const loadingEl = document.getElementById(loadingId);
        if(loadingEl) loadingEl.remove();
        showToast(error.message, 'error');
    }
}

function addChatMessage(text, sender, isLoading = false) {
    const container = document.getElementById('chatMessages');
    
    const wrapper = document.createElement('div');
    // Flex alignment based on sender
    wrapper.className = `flex w-full mb-4 ${sender === 'user' ? 'justify-end' : 'justify-start'}`;
    
    const bubble = document.createElement('div');
    // Bubble Styling
    const baseStyle = "max-w-[85%] rounded-2xl px-5 py-3 shadow-sm text-sm leading-relaxed";
    const userStyle = "bg-secondary text-white rounded-br-none"; // Blue bubble
    const aiStyle = "bg-slate-100 text-slate-800 rounded-tl-none border border-slate-200"; // Grey bubble
    
    bubble.className = `${baseStyle} ${sender === 'user' ? userStyle : aiStyle} ${isLoading ? 'animate-pulse' : ''}`;
    
    bubble.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');
    if (isLoading) bubble.id = `loading-${Date.now()}`;
    
    wrapper.appendChild(bubble);
    container.appendChild(wrapper);
    
    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
    
    return bubble.id;
}

// ===== TOAST NOTIFICATIONS =====
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    
    // Tailwind classes for toast
    toast.className = `fixed bottom-5 right-5 px-6 py-3 rounded-lg shadow-2xl transform transition-all duration-300 z-50 text-white font-medium translate-y-0 opacity-100`;
    
    if (type === 'error') toast.classList.add('bg-red-600');
    else if (type === 'success') toast.classList.add('bg-green-600');
    else toast.classList.add('bg-slate-800');
    
    setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('translate-y-20', 'opacity-0');
    }, 4000);
}

// ===== UTILS =====
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}