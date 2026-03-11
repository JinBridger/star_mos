// Experiment page JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    const scoringForm = document.getElementById('scoringForm');
    const submitBtn = document.getElementById('submitBtn');
    const prevBtn = document.getElementById('prevBtn');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    
    // Initialize sliders
    initializeSliders();
    
    // Handle form submission
    scoringForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Collect form data
        const formData = new FormData(scoringForm);
        const scores = {};
        
        // Extract scores from form data and organize by system
        for (let [key, value] of formData.entries()) {
            if (key.startsWith('score_')) {
                const parts = key.replace('score_', '').split('_');
                if (parts.length >= 2) {
                    const metricName = parts[0];
                    const systemId = parts.slice(1).join('_'); // Handle system IDs with underscores
                    
                    if (!scores[systemId]) {
                        scores[systemId] = {};
                    }
                    scores[systemId][metricName] = parseInt(value);
                }
            }
        }
        
        // Calculate response time
        const responseTime = Date.now() - questionStartTime;
        
        // Prepare submission data
        const submissionData = {
            scores: scores,
            response_time_ms: responseTime
        };
        
        // Show loading modal
        loadingModal.show();
        submitBtn.disabled = true;
        
        // Submit via AJAX
        fetch(`/experiment/${experimentName}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(submissionData)
        })
        .then(response => response.json())
        .then(data => {
            loadingModal.hide();
            
            if (data.success) {
                if (data.is_last_question) {
                    // For the last question, we need to reload the page to trigger the save logic
                    // The server will detect completion and save data before redirecting
                    window.location.reload();
                } else {
                    // Reload page for next question
                    window.location.reload();
                }
            } else {
                alert('提交失败：' + (data.error || '未知错误'));
                submitBtn.disabled = false;
            }
        })
        .catch(error => {
            loadingModal.hide();
            console.error('Error:', error);
            alert('提交失败，请检查网络连接');
            submitBtn.disabled = false;
        });
    });
    
    // Handle previous button click
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            if (canGoBack) {
                // Go to previous question
                fetch(`/experiment/${experimentName}/previous`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.reload();
                    } else {
                        alert('返回上一题失败：' + (data.error || '未知错误'));
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('返回上一题失败，请检查网络连接');
                });
            }
        });
    }
    
    // Initialize sliders functionality
    function initializeSliders() {
        const sliders = document.querySelectorAll('input[type="range"]');
        
        sliders.forEach(slider => {
            const valueDisplay = document.getElementById(slider.id.replace('slider_', 'value_'));
            
            // Update value display when slider changes
            slider.addEventListener('input', function() {
                if (valueDisplay) {
                    valueDisplay.textContent = this.value;
                }
            });
            
            // Set initial value display
            if (valueDisplay) {
                valueDisplay.textContent = slider.value;
            }
        });
    }
    

    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Submit with Ctrl+Enter
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            if (isFormValid()) {
                scoringForm.dispatchEvent(new Event('submit'));
            }
        }
        
        // Go back with Ctrl+Left Arrow
        if (e.ctrlKey && e.key === 'ArrowLeft' && canGoBack) {
            e.preventDefault();
            prevBtn.click();
        }
        
        // Number keys for quick rating (1-5)
        if (e.key >= '1' && e.key <= '5') {
            const visibleSliders = document.querySelectorAll('input[type="range"]:not([disabled])');
            if (visibleSliders.length === 1) {
                // If only one slider, use number keys for quick rating
                const slider = visibleSliders[0];
                slider.value = e.key;
                slider.dispatchEvent(new Event('input'));
            }
        }
    });
    
    // Form validation
    function isFormValid() {
        const requiredSliders = document.querySelectorAll('input[type="range"][required]');
        
        for (let slider of requiredSliders) {
            if (!slider.value || slider.value < slider.min || slider.value > slider.max) {
                return false;
            }
        }
        
        return true;
    }
    

    
    // Update submit button state based on form validity
    function updateSubmitButton() {
        if (isFormValid()) {
            submitBtn.disabled = false;
            submitBtn.textContent = '下一题';
        } else {
            submitBtn.disabled = true;
            submitBtn.textContent = '请完成所有评分';
        }
    }
    
    // Listen for changes to update submit button
    const sliders = document.querySelectorAll('input[type="range"]');
    sliders.forEach(slider => {
        slider.addEventListener('change', updateSubmitButton);
        slider.addEventListener('input', updateSubmitButton);
    });
    
    // Initial button state
    updateSubmitButton();
    
    // Audio playback controls
    const audioElements = document.querySelectorAll('audio');
    audioElements.forEach(audio => {
        // Pause other audios when one starts playing
        audio.addEventListener('play', function() {
            audioElements.forEach(otherAudio => {
                if (otherAudio !== audio) {
                    otherAudio.pause();
                }
            });
        });
    });
});