// Collapsible Helper Methods for Test Documentation
document.addEventListener('DOMContentLoaded', function() {
    // Helper method names to group into collapsible section
    const helperMethods = [
        'setUp', 'tearDown', 'delete_on_finish',
        'setUpClass', 'tearDownClass', 'setUpModule', 'tearDownModule'
    ];
    
    function createCollapsibleSection() {
        // Find all sections that contain test documentation
        const testSections = document.querySelectorAll('div.doc-contents');
        
        testSections.forEach(function(section) {
            let helperElements = [];
            
            // Find helper method elements in this section
            helperMethods.forEach(function(methodName) {
                const elements = section.querySelectorAll('[id*="' + methodName + '"]');
                elements.forEach(function(element) {
                    // Find the parent element that contains the full method documentation
                    let parentDoc = element.closest('.doc-object-name') || 
                                   element.closest('div[class*="doc-"]') ||
                                   element.parentElement;
                    
                    // Look for the full method documentation block
                    while (parentDoc && !parentDoc.querySelector('.doc-object-name, h3, h4')) {
                        parentDoc = parentDoc.parentElement;
                    }
                    
                    if (parentDoc && !helperElements.includes(parentDoc)) {
                        helperElements.push(parentDoc);
                    }
                });
            });
            
            // If we found helper methods, create collapsible section
            if (helperElements.length > 0) {
                const collapsibleSection = document.createElement('details');
                collapsibleSection.className = 'helper-methods-section';
                
                const summary = document.createElement('summary');
                summary.innerHTML = '🔧 Helper Methods (' + helperElements.length + ')';
                
                const content = document.createElement('div');
                content.className = 'helper-methods-content';
                
                // Move helper method elements into the collapsible section
                helperElements.forEach(function(element) {
                    content.appendChild(element.cloneNode(true));
                    element.style.display = 'none'; // Hide original
                });
                
                collapsibleSection.appendChild(summary);
                collapsibleSection.appendChild(content);
                
                // Insert after the first section or at the beginning
                const insertAfter = section.querySelector('h2, h3, p') || section.firstElementChild;
                if (insertAfter && insertAfter.nextSibling) {
                    section.insertBefore(collapsibleSection, insertAfter.nextSibling);
                } else {
                    section.appendChild(collapsibleSection);
                }
            }
        });
    }
    
    // Alternative approach: Target specific test class documentation
    function createCollapsibleForTestClasses() {
        // Look for test class headings and their content
        const testClassHeaders = document.querySelectorAll('h2, h3, h4');
        
        testClassHeaders.forEach(function(header) {
            const headerText = header.textContent;
            
            // Skip if not a test class header
            if (!headerText.includes('TestCase') && !headerText.includes('Tester')) {
                return;
            }
            
            let nextElement = header.nextElementSibling;
            let helperElements = [];
            
            // Scan following elements for helper methods
            while (nextElement && !nextElement.matches('h2, h3, h4')) {
                helperMethods.forEach(function(methodName) {
                    if (nextElement.textContent && nextElement.textContent.includes(methodName)) {
                        helperElements.push(nextElement);
                    }
                });
                nextElement = nextElement.nextElementSibling;
            }
            
            // Create collapsible section if helper methods found
            if (helperElements.length > 0) {
                const collapsibleSection = document.createElement('details');
                collapsibleSection.className = 'helper-methods-section';
                
                const summary = document.createElement('summary');
                summary.innerHTML = '🔧 Test Helper Methods (' + helperElements.length + ')';
                
                const content = document.createElement('div');
                content.className = 'helper-methods-content';
                
                helperElements.forEach(function(element) {
                    content.appendChild(element.cloneNode(true));
                    element.style.display = 'none';
                });
                
                collapsibleSection.appendChild(summary);
                collapsibleSection.appendChild(content);
                
                // Insert after the header
                if (header.nextElementSibling) {
                    header.parentNode.insertBefore(collapsibleSection, header.nextElementSibling);
                }
            }
        });
    }
    
    // Try both approaches
    setTimeout(function() {
        createCollapsibleSection();
        createCollapsibleForTestClasses();
    }, 500); // Delay to ensure mkdocstrings content is loaded
    
    // Also run when navigating between pages
    if (typeof instantNavigation !== 'undefined') {
        document.addEventListener('nav', function() {
            setTimeout(function() {
                createCollapsibleSection();
                createCollapsibleForTestClasses();
            }, 500);
        });
    }
});
