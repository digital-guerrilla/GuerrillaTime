/**
 * Guerrilla T API Documentation JavaScript
 * Provides interactive functionality for the API docs page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Add copy functionality to code blocks
    addCopyButtons();
    
    // Add smooth scrolling to anchor links
    addSmoothScrolling();
    
    // Add collapsible sections
    addCollapsibleSections();
});

/**
 * Add copy buttons to code examples
 */
function addCopyButtons() {
    const codeBlocks = document.querySelectorAll('.response-example');
    
    codeBlocks.forEach(function(block) {
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-btn';
        copyButton.innerHTML = '📋 Copy';
        copyButton.title = 'Copy to clipboard';
        
        copyButton.addEventListener('click', function() {
            const text = block.textContent || block.innerText;
            navigator.clipboard.writeText(text).then(function() {
                copyButton.innerHTML = '✅ Copied!';
                copyButton.style.background = '#28a745';
                
                setTimeout(function() {
                    copyButton.innerHTML = '📋 Copy';
                    copyButton.style.background = '';
                }, 2000);
            }).catch(function(err) {
                console.error('Failed to copy text: ', err);
                copyButton.innerHTML = '❌ Failed';
                setTimeout(function() {
                    copyButton.innerHTML = '📋 Copy';
                }, 2000);
            });
        });
        
        block.style.position = 'relative';
        block.appendChild(copyButton);
    });
}

/**
 * Add smooth scrolling to anchor links
 */
function addSmoothScrolling() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Add collapsible functionality to endpoint sections
 */
function addCollapsibleSections() {
    const endpoints = document.querySelectorAll('.endpoint h3');
    
    endpoints.forEach(function(header) {
        header.style.cursor = 'pointer';
        header.style.userSelect = 'none';
        
        // Add collapse indicator
        const indicator = document.createElement('span');
        indicator.className = 'collapse-indicator';
        indicator.innerHTML = ' ▼';
        indicator.style.float = 'right';
        indicator.style.fontSize = '0.8em';
        indicator.style.color = '#666';
        header.appendChild(indicator);
        
        header.addEventListener('click', function() {
            const endpoint = this.parentElement;
            const content = Array.from(endpoint.children).slice(1); // Skip the header
            
            content.forEach(function(element) {
                if (element.style.display === 'none') {
                    element.style.display = '';
                    indicator.innerHTML = ' ▼';
                } else {
                    element.style.display = 'none';
                    indicator.innerHTML = ' ▶';
                }
            });
        });
    });
}

/**
 * Format JSON in response examples
 */
function formatJSON() {
    const jsonBlocks = document.querySelectorAll('.response-example');
    
    jsonBlocks.forEach(function(block) {
        const content = block.textContent || block.innerText;
        
        try {
            // Check if it's JSON
            if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
                const parsed = JSON.parse(content);
                const formatted = JSON.stringify(parsed, null, 2);
                block.textContent = formatted;
            }
        } catch (e) {
            // Not JSON, leave as is
        }
    });
}
