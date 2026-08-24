document.addEventListener("DOMContentLoaded", function() {
    console.log("MailWeave: Popup loaded");

    const container = document.getElementById('checklist-container');
    const form = document.getElementById('add-task-form');
    const input = document.getElementById('new-task-input');
    const deadlineInput = document.getElementById('new-deadline-input');

    loadChecklist();

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        const deadline = deadlineInput.value.trim() || null;
        addManualTask(text, deadline);
        input.value = '';
        deadlineInput.value = '';
    });

    function loadChecklist() {
        chrome.storage.local.get(['checklist'], function(result) {
            const checklist = result.checklist || [];
            renderChecklist(checklist);
        });
    }

    function renderChecklist(checklist) {
        if (checklist.length === 0) {
            container.innerHTML = '<div class="empty-state">No tasks yet. Open an email with a deadline, or add one manually below.</div>';
            return;
        }

        // unchecked first, then within each group tasks with a deadline come before ones without
        const sorted = [...checklist].sort((a, b) => {
            if (a.done !== b.done) return a.done - b.done;
            if (a.deadline && !b.deadline) return -1;
            if (!a.deadline && b.deadline) return 1;
            return 0;
        });

        container.innerHTML = sorted.map(task => `
            <div class="task-item ${task.done ? 'task-done' : ''}" data-id="${task.id}">
                <input type="checkbox" class="task-checkbox" ${task.done ? 'checked' : ''}>
                <div class="task-content">
                    <div class="task-text">${escapeHtml(task.text)}</div>
                    ${task.deadline ? `<div class="task-deadline">Due: ${escapeHtml(task.deadline)}</div>` : ''}
                    ${task.category ? `<span class="task-category">${escapeHtml(task.category)}</span>` : ''}
                </div>
                <button class="delete-btn" title="Delete">✕</button>
            </div>
        `).join('');

        container.querySelectorAll('.task-item').forEach(item => {
            const id = item.dataset.id;

            item.querySelector('.task-checkbox').addEventListener('change', function() {
                toggleTask(id);
            });

            item.querySelector('.delete-btn').addEventListener('click', function() {
                deleteTask(id);
            });
        });
    }

    function toggleTask(id) {
        chrome.storage.local.get(['checklist'], function(result) {
            const checklist = result.checklist || [];
            const updated = checklist.map(task =>
                task.id === id ? { ...task, done: !task.done } : task
            );
            chrome.storage.local.set({ checklist: updated }, function() {
                renderChecklist(updated);
            });
        });
    }

    function deleteTask(id) {
        chrome.storage.local.get(['checklist'], function(result) {
            const checklist = result.checklist || [];
            const updated = checklist.filter(task => task.id !== id);
            chrome.storage.local.set({ checklist: updated }, function() {
                renderChecklist(updated);
            });
        });
    }

    function addManualTask(text, deadline) {
        chrome.storage.local.get(['checklist'], function(result) {
            const checklist = result.checklist || [];

            const newTask = {
                id: Date.now().toString(),
                text: text,
                deadline: deadline || null,
                category: 'Manual',
                source: 'manual',
                done: false,
                emailId: null
            };

            checklist.push(newTask);
            chrome.storage.local.set({ checklist: checklist }, function() {
                renderChecklist(checklist);
            });
        });
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
});