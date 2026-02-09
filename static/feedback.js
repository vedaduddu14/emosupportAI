const sliderValues = {};

function updateSlider(sliderName, slideAmount) {
    // Store the slider value in the dictionary
    sliderValues[sliderName] = slideAmount;
}

async function updateClientQueue() {
    console.log('[DEBUG] ============ updateClientQueue() CALLED ============');
    const sessionId = window.location.pathname.split('/')[2];

    console.log('[DEBUG] updateClientQueue called from:', window.location.pathname);
    console.log('[DEBUG] Session ID:', sessionId);

    // Save mouse tracking before moving to next round - WAIT for it to complete
    console.log('[DEBUG] Checking if saveMouseTracking exists:', typeof saveMouseTracking);
    if (typeof saveMouseTracking === 'function') {
        try {
            console.log('[DEBUG] saveMouseTracking is a function - calling it now...');
            await saveMouseTracking();
            console.log('[DEBUG] Mouse tracking saved successfully!');
        } catch (error) {
            console.error('[DEBUG] Error saving mouse tracking:', error);
        }
    } else {
        console.error('[DEBUG] saveMouseTracking is NOT a function! Type:', typeof saveMouseTracking);
    }

    fetch(`/update-clientQueue/${sessionId}/`)
    .then(response => response.json())
    .then(data => {
        console.log('[DEBUG] updateClientQueue response:', data);

        if (data.url) {
            console.log('[DEBUG] Redirecting to:', data.url);
            // Don't reset tracker here - page is unloading anyway
            // Next chat page will initialize a fresh tracker
            window.location.href = data.url;
        }
    })
    .catch(error => console.error('Error updating client queue:', error));
}

function completeSurvey() {
    const session_id = window.location.pathname.split('/')[2];
    // Redirect to demographics survey instead of complete page
    window.location.href = `/demographics-survey/${session_id}/`;
}

// ===== Pagination =====
const TOTAL_PAGES = 4;
let currentPage = 1;

// Questions required on each page
const pageRequiredKeys = {
    1: ["advice_helpful", "advice_supportive", "advice_informative", "advice_compassionate",
        "surface_act", "surface_mask", "surface_fake"],
    2: ["deep_experience", "deep_effort", "deep_work",
        "genuine_emotions", "natural_emotions", "match_emotions"],
    3: ["burnout_frustrating", "burnout_drain", "burnout_tired",
        "job_satisfaction", "recovery"],
    4: ["useful_quickly", "useful_performance", "useful_find",
        "trust_guidance", "trust_rely", "trust_dependable",
        "literacy_evaluate", "literacy_choose_solution", "literacy_choose_assistant"]
};

function changeSurveyPage(direction) {
    // Validate current page before moving forward
    if (direction === 1) {
        const formData = new FormData(document.getElementById('feedbackForm'));
        const formValues = {};
        formData.forEach((value, key) => { formValues[key] = value; });

        const requiredKeys = pageRequiredKeys[currentPage];
        const allAnswered = requiredKeys.every(key => Object.keys(formValues).includes(key));
        if (!allAnswered) {
            alert("Please respond to all questions on this page.");
            return;
        }
    }

    // Hide current page, show next
    document.querySelector(`.survey-page[data-page="${currentPage}"]`).classList.remove('active');
    currentPage += direction;
    document.querySelector(`.survey-page[data-page="${currentPage}"]`).classList.add('active');

    // Scroll modal content to top
    document.querySelector('.modal-content').scrollTop = 0;

    // Update buttons (no back button - participants cannot go backwards)
    document.getElementById('nextBtn').style.display = currentPage < TOTAL_PAGES ? '' : 'none';
    document.getElementById('completeButton').style.display = currentPage === TOTAL_PAGES ? '' : 'none';
    document.getElementById('pageIndicator').textContent = `Page ${currentPage} of ${TOTAL_PAGES}`;
}

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('feedbackForm');

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const submitterButton = e.submitter.id;

        const formData = new FormData(this);
        const formValues = {};
        formData.forEach((value, key) => { formValues[key] = value; });

        // Validate last page
        const requiredKeys = pageRequiredKeys[TOTAL_PAGES];
        const allAnswered = requiredKeys.every(key => Object.keys(formValues).includes(key));
        if (!allAnswered) {
            alert("Please respond to all questions on this page.");
            return;
        }

        const sessionId = window.location.pathname.split('/')[2];
        const clientId = sessionStorage.getItem('client_id');

        data = formValues
        data['client_id'] = clientId

        // Save mouse tracking data before submitting survey
        if (typeof saveMouseTracking === 'function') {
            saveMouseTracking();
        }

        fetch(`/store-survey/${sessionId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Success:', data);
            alert('Feedback submitted successfully!');

            if (submitterButton == "completeButton") {
                completeSurvey();
            }
            else {
                updateClientQueue();
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('Error submitting feedback');
        });
    });
});
