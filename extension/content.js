console.log("MailWeave is running");
let currentEmailId = null;

function classifyEmail(emailData) {
    console.log("MailWeave: Sending to background script for classification")

    chrome.runtime.sendMessage(
        {
            action: "classifyEmail",
            data: {
                subject: emailData.subject,
                snippet: emailData.body
            }
        },
        (response) => {
            if (response.success) {
                console.log("MailWeave: Classification result:", response.data);
                console.log("MailWeave: Category:", response.data.category);
                console.log("MailWeave: Confidence:", response.data.confidence);
                console.log("MailWeave: Deadline:", response.data.deadline);

                addCategoryBadge(response.data.category, response.data.confidence);

                if (response.data.deadline) {
                    addToChecklist(emailData.subject, response.data.deadline, response.data.category);
                }
            } else {
                console.error("MailWeave: Classification failed:", response.error);
            }
        }
    );
}


function addToChecklist(subject, deadline, category) {
    const emailId = window.location.hash;

    chrome.storage.local.get(['checklist'], function(result) {
        const checklist = result.checklist || [];

        const alreadyExists = checklist.some(item => item.emailId === emailId);
        if (alreadyExists) {
            console.log("MailWeave: Task already in checklist, skipping");
            return;
        }

        const newTask = {
            id: Date.now().toString(),
            text: subject,
            deadline: deadline,
            category: category,
            source: "email",
            done: false,
            emailId: emailId
        };

        checklist.push(newTask);

        chrome.storage.local.set({ checklist: checklist }, function() {
            console.log("MailWeave: Added to checklist:", newTask);
        });
    });
}


function addCategoryBadge(category, confidence) {
    const subjectElement = document.querySelector("h2.hP");
    
    if (!subjectElement) {
        console.log("MailWeave: Subject element not found, can't add badge");
        return;
    }

    const existingBadge = subjectElement.querySelector(".mailweave-badge");
    if (existingBadge) {
        existingBadge.remove();
    }

    const badge = document.createElement("span");
    badge.className = "mailweave-badge";
    badge.textContent = category;

    const colors = {
        "Assignment": "#4285f4",
        "Exam": "#fbbc04",
        "Clubs & Orgs": "#00acc1",
        "Social": "#34a853",
        "Career": "#ff7043",
        "Academic-Admin": "#5c6bc0",
        "Subscription": "#ea4335",
        "Promotions": "#9c27b0",
        "Other": "#9e9e9e"
    };

    badge.style.backgroundColor = colors[category] || "#9e9e9e";
    badge.style.color = "white";
    badge.style.padding = "2px 8px";
    badge.style.borderRadius = "12px";
    badge.style.fontSize = "12px";
    badge.style.fontWeight = "600";
    badge.style.marginLeft = "10px";
    badge.style.display = "inline-block";
    badge.style.verticalAlign = "middle";

    subjectElement.appendChild(badge);
    
    console.log("MailWeave: Badge added -", category);
}


function readEmail() {
    console.log("MailWeave: Attempting to read Emails");

    const emailSubject = document.querySelector("h2.hP");
    const subject = emailSubject ? emailSubject.textContent : "Subject not found";

    const emailId = window.location.hash;
    
    if (emailId === currentEmailId) {
        console.log("MailWeave: Already processed this email, skipping");
        return;
    }
    
    currentEmailId = emailId;

    const emailBody = document.querySelector("div.a3s.aiL");
    const body = emailBody ? emailBody.textContent : "Body not found";

    const emailSender = document.querySelector("span.gD");
    const sender = emailSender ? emailSender.getAttribute("email") : "Sender not found";

    const emailDate = document.querySelector("span.g3");
    const date = emailDate ? emailDate.getAttribute("title") : "Date not found";

    const emailData = {
        subject: subject,
        sender: sender,
        date: date,
        body: body.substring(0, 250) + "..."
    };

    console.log("MailWeave: Extracted email data: ", emailData);

    chrome.storage.local.set({currentEmail: emailData},
        function() {
            console.log("MailWeave: Email data saved");
        }
    );

    classifyEmail(emailData);

    return emailData
}


function watchEmail() {
    let prevUrl = location.href;

    const observer = new MutationObserver(function(){
        const currentUrl = location.href;
        const urlUpdate = currentUrl !== prevUrl;

        if (urlUpdate) {
            prevUrl = currentUrl;
            const emailView = document.querySelector("h2.hP");
            
            if (emailView) {
                console.log("MailWeave: URL updated, reading new email");
                setTimeout(readEmail, 500);
            }
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    console.log("MailWeave: Watching for email changes")
}

setTimeout(watchEmail, 2000);
setTimeout(readEmail, 3000);