document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('demographicsForm');

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = new FormData(this);
        const formValues = {};
        formData.forEach((value, key) => { formValues[key] = value; });

        // Validate all fields are filled
        const requiredFields = ['age', 'gender', 'education', 'occupation', 'years_experience', 'genai_familiarity', 'genai_attitude'];
        const allFieldsFilled = requiredFields.every(field => formValues[field] && formValues[field].trim() !== '');

        if (!allFieldsFilled) {
            alert("Please answer all questions.");
            return;
        }

        const sessionId = window.location.pathname.split('/')[2];

        fetch(`/store-demographics-survey/${sessionId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formValues)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.redirect_url) {
                window.location.href = data.redirect_url;
            } else {
                alert('Survey submitted successfully!');
                window.location.href = `/complete/?session_id=${sessionId}`;
            }
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('Error submitting survey. Please try again.');
        });
    });
});
