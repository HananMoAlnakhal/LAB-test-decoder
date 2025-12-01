// ===== GLOBAL STATE =====
let currentResults = null;
let explanations = null;

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initFileUpload();
    initScrollAnimations();
});

// ===== NAVIGATION =====
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const target = link.getAttribute('href');
            
            // Update active state
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // Smooth scroll
            document.querySelector(target).scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        });
    });
    
    // Mobile menu toggle
    const mobileToggle = document.querySelector('.mobile-menu-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (mobileToggle) {
        mobileToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
        });
    }
}

// ===== SCROLL ANIMATIONS =====
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });
    
    document.querySelectorAll('.about-card, .feature-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.6s ease-out';
        observer.observe(card);
    });
}

// ===== FILE UPLOAD =====
function initFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    
    if (!fileInput || !uploadArea) return;
    
    // Click to upload
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
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
        
        // Scroll to results
        setTimeout(() => {
            document.getElementById('results').scrollIntoView({ 
                behavior: 'smooth' 
            });
        }, 500);
        
    } catch (error) {
        showToast(error.message, 'error');
        resetUploadArea();
    }
}

async function generateExplanations() {
    showLoading('Generating explanations...');
    
    try {
        const response = await fetch('/api/explain', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to generate explanations');
        }
        
        explanations = data.explanations;
        
    } catch (error) {
        showToast('Error generating explanations: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function displayResults() {
    const resultsSection = document.getElementById('results');
    const container = document.getElementById('resultsContainer');
    
    if (!currentResults || currentResults.length === 0) {
        container.innerHTML = '<p class="empty-message">No results found</p>';
        return;
    }
    
    // Show results section
    resultsSection.classList.remove('hidden');
    
    // Update summary stats
    updateSummaryStats();
    
    // Clear container
    container.innerHTML = '';
    
    // Create result cards
    currentResults.forEach((result, index) => {
        const card = createResultCard(result, index);
        container.appendChild(card);
    });
    
    // Reset upload area
    resetUploadArea();
}

function updateSummaryStats() {
    const stats = {
        normal: 0,
        high: 0,
        low: 0
    };
    
    currentResults.forEach(result => {
        if (result.status in stats) {
            stats[result.status]++;
        }
    });
    
    document.getElementById('normalCount').textContent = stats.normal;
    document.getElementById('highCount').textContent = stats.high;
    document.getElementById('lowCount').textContent = stats.low;
}

function createResultCard(result, index) {
    const card = document.createElement('div');
    card.className = 'result-card';
    card.style.setProperty('--i', index + 1);
    
    const statusClass = `status-${result.status}`;
    const explanation = explanations && explanations[result.test_name] 
        ? explanations[result.test_name] 
        : 'Loading explanation...';
    
    card.innerHTML = `
        <div class="result-header">
            <div>
                <h3 class="result-name">${escapeHtml(result.test_name)}</h3>
                <p class="result-range">Reference: ${escapeHtml(result.reference_range || 'N/A')}</p>
            </div>
            <div class="result-value-container">
                <div class="result-value">${escapeHtml(result.value)} ${escapeHtml(result.unit)}</div>
                <span class="result-status ${statusClass}">${result.status}</span>
            </div>
        </div>
        <div class="result-explanation">
            <strong>What does this mean?</strong>
            <p>${escapeHtml(explanation)}</p>
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
    
    showLoading('Generating summary...');
    
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to generate summary');
        }
        
        // Show summary modal or section
        showSummaryModal(data.summary, data.stats);
        
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function showSummaryModal(summary, stats) {
    const modal = document.createElement('div');
    modal.className = 'chat-modal';
    modal.innerHTML = `
        <div class="chat-modal-content">
            <div class="chat-header">
                <h3>📊 Complete Summary</h3>
                <button class="chat-close" onclick="this.closest('.chat-modal').remove()">&times;</button>
            </div>
            <div class="chat-messages">
                <div class="chat-bubble">
                    <p>${escapeHtml(summary).replace(/\n/g, '<br><br>')}</p>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

// ===== CHAT FUNCTIONALITY =====
function openChat() {
    if (!currentResults) {
        showToast('Please upload a lab report first', 'error');
        return;
    }
    
    const modal = document.getElementById('chatModal');
    modal.classList.remove('hidden');
    document.getElementById('chatInput').focus();
}

function closeChat() {
    document.getElementById('chatModal').classList.add('hidden');
}

function handleChatKeypress(event) {
    if (event.key === 'Enter') {
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const question = input.value.trim();
    
    if (!question) return;
    
    // Clear input
    input.value = '';
    
    // Add user message
    addChatMessage(question, 'user');
    
    // Show loading message
    const loadingId = addChatMessage('Thinking...', 'assistant', true);
    
    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to get answer');
        }
        
        // Remove loading message
        document.getElementById(loadingId).remove();
        
        // Add assistant response
        addChatMessage(data.answer, 'assistant');
        
    } catch (error) {
        document.getElementById(loadingId).remove();
        addChatMessage(`Sorry, I encountered an error: ${error.message}`, 'assistant');
        showToast(error.message, 'error');
    }
}

function addChatMessage(text, sender, isLoading = false) {
    const messagesContainer = document.getElementById('chatMessages');
    
    // Remove welcome message if exists
    const welcome = messagesContainer.querySelector('.chat-welcome');
    if (welcome) {
        welcome.remove();
    }
    
    const messageId = `msg-${Date.now()}`;
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `chat-message ${sender}`;
    
    const bubbleClass = isLoading ? 'chat-bubble loading' : 'chat-bubble';
    messageDiv.innerHTML = `<div class="${bubbleClass}">${escapeHtml(text)}</div>`;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageId;
}

// ===== LOADING OVERLAY =====
function showLoading(message = 'Processing...') {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.querySelector('p').textContent = message;
        overlay.classList.remove('hidden');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

// ===== TOAST NOTIFICATIONS =====
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

// ===== UTILITY FUNCTIONS =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== SMOOTH SCROLL FOR ALL LINKS =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// ===== CLOSE MODALS ON ESC =====
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const chatModal = document.getElementById('chatModal');
        if (chatModal && !chatModal.classList.contains('hidden')) {
            closeChat();
        }
    }
});

// ===== CLOSE MODALS ON OUTSIDE CLICK =====
document.addEventListener('click', (e) => {
    const chatModal = document.getElementById('chatModal');
    if (e.target === chatModal) {
        closeChat();
    }
});