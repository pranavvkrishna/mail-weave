console.log("MailWeave: Background script running");

// Listen for messages from content.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    
    if (request.action === "classifyEmail") {
        console.log("MailWeave Background: Received email data", request.data);
        
        fetch('http://localhost:8000/classify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                subject: request.data.subject,
                snippet: request.data.snippet,
                body: request.data.body,
                date: request.data.date
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log("MailWeave Background: Classification result:", data);
            sendResponse({ success: true, data: data });
        })
        .catch(error => {
            console.error("MailWeave Background: Error:", error);
            sendResponse({ success: false, error: error.message });
        });
        
        return true;
    }
});