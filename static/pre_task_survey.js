const sliderValues = {};

function updateSlider(sliderName, slideAmount) {
    // Store the slider value in the dictionary
    sliderValues[sliderName] = slideAmount;
}

// function updateClientQueue() {
//     const sessionId = window.location.pathname.split('/')[1];

//     fetch(`/${sessionId}/update-clientQueue`)
//     .then(response => response.json())
//     .then(data => {
//         if (data.url) {
//             window.location.href = data.url;
//         }
//     })
//     .catch(error => console.error('Error updating client queue:', error));
// }

document.addEventListener('DOMContentLoaded', function() {
    // Modal is already active via HTML is-active class
    const form = document.getElementById('preFeedbackForm');
    form.addEventListener('submit', function(e) {
        e.preventDefault(); 
        const formData = new FormData(this);
        const formValues = {};
        formData.forEach((value, key) => { formValues[key] = value; });

        // Check if all 3 emotion regulation questions were answered
        radioKeysValidation = ["emotion_q1", "emotion_q2", "emotion_q3"]
        allKeysExist = radioKeysValidation.every(key => Object.keys(formValues).includes(key));
        if (!allKeysExist){
            alert("Please respond to all questions.");
            return;
        }

        // Calculate SuppScore
        const q1 = parseFloat(formValues['emotion_q1']);
        const q2 = parseFloat(formValues['emotion_q2']);
        const q3 = parseFloat(formValues['emotion_q3']);
        const suppScore = (q1 + q2 + q3) / 3;

        // Classify EmotionRegulation_Type
        const emotionRegulationType = suppScore >= 4.5 ? "Suppressor" : "NonSuppressor";

        // Add to data being sent
        formValues['supp_score'] = suppScore;
        formValues['emotion_regulation_type'] = emotionRegulationType;
        const sessionId = window.location.pathname.split('/')[2];
        const clientParam = window.location.href.split('?')[1];

        data = formValues
        data['client_param'] = clientParam

        fetch(`/store-pre-task-survey/${sessionId}/`, {
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
            alert('Feedback submitted successfully!');
            window.location.href = response.url
            // return response.json();
        })
        // .then(data => {
        //     console.log('Success:', data);
        //     alert('Feedback submitted successfully!');
        //     // updateClientQueue();
        // })
        .catch((error) => {
            console.error('Error:', error);
            alert('Error submitting feedback');
        });
    });
});
