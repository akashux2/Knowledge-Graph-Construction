// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // Handle tab switching to ensure form data is preserved
    const tabs = document.querySelectorAll('button[data-bs-toggle="tab"]');
    
    if (tabs.length > 0) {
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function (event) {
                // Clear validation errors when switching tabs
                const forms = document.querySelectorAll('form');
                forms.forEach(form => {
                    const inputs = form.querySelectorAll('.is-invalid');
                    inputs.forEach(input => {
                        input.classList.remove('is-invalid');
                    });
                });
            });
        });
    }
    
    // Enable tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Handle graph iframe messaging
    window.addEventListener('message', function(event) {
        if (event.data && event.data.type === 'graphReady') {
            console.log('Graph is ready for interaction');
        }
    });
    
    // Add animation to elements that come into view
    const animateOnScroll = function() {
        const elements = document.querySelectorAll('.animate-on-scroll');
        
        elements.forEach(element => {
            const position = element.getBoundingClientRect();
            
            // Check if element is in viewport
            if(position.top < window.innerHeight && position.bottom >= 0) {
                element.classList.add('animated');
            }
        });
    };
    
    // Activate animations
    window.addEventListener('scroll', animateOnScroll);
    animateOnScroll(); // Initial check
});

// Add a small enhancement to pyvis graphs when loaded in iframes
function enhancePyvisGraph() {
    // This function should be called from within the generated pyvis HTML
    
    // Add zoom controls
    window.zoomLevel = 1.0;
    
    window.addEventListener('message', function(event) {
        if (event.data.action === 'zoomIn') {
            window.zoomLevel *= 1.2;
            document.getElementById('mynetwork').style.transform = `scale(${window.zoomLevel})`;
        } else if (event.data.action === 'zoomOut') {
            window.zoomLevel /= 1.2;
            document.getElementById('mynetwork').style.transform = `scale(${window.zoomLevel})`;
        } else if (event.data.action === 'resetView') {
            window.zoomLevel = 1.0;
            document.getElementById('mynetwork').style.transform = 'scale(1)';
            if (window.network) {
                window.network.fit();
            }
        }
    });
    
    // Notify parent that graph is ready
    if (window.parent !== window) {
        window.parent.postMessage({type: 'graphReady'}, '*');
    }
}

// For graph_builder.py modification (To be inserted into pyvis graph output)
function injectPyvisEnhancement(html_content) {
    // This function would be called from the create_graph function
    // to inject our custom zoom control enhancements
    
    const scriptToInject = `
    <script>
    // Add event listener for when the network is ready
    window.addEventListener('load', function() {
        // Wait for network to be defined
        setTimeout(function() {
            if (window.network) {
                // Store initial viewport
                window.initialViewport = {
                    scale: network.getScale(),
                    position: network.getViewPosition()
                };
                
                // Setup messaging with parent frame
                ${enhancePyvisGraph.toString()}
                enhancePyvisGraph();
            }
        }, 500);
    });
    </script>
    `;
    
    // Insert before the closing body tag
    return html_content.replace('</body>', scriptToInject + '</body>');
}