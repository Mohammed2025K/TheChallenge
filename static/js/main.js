function getCsrfToken() {
    const el = document.querySelector('meta[name="csrf-token"]');
    return el ? el.getAttribute('content') : '';
}

function getTasksData() {
    const el = document.getElementById('tasks-data');
    if (!el) return null;
    try {
        return JSON.parse(el.textContent);
    } catch (e) {
        console.error('Invalid tasks-data JSON', e);
        return null;
    }
}

function setTasksData(data) {
    const el = document.getElementById('tasks-data');
    if (el) el.textContent = JSON.stringify(data);
}

function updateChartProgress(dayNumber, percent) {
    if (window.progressChart) {
        window.progressChart.data.datasets[0].data[dayNumber - 1] = percent;
        window.progressChart.update();
    }
}

function updateDayProgressUI(dayNumber) {
    const data = getTasksData();
    if (!data) return;

    const dayTasks = data.days[dayNumber] || [];
    if (dayTasks.length === 0) return;

    const total = dayTasks.length;
    const completed = dayTasks.filter(t => t.is_completed).length;
    const percent = Math.round((completed / total) * 100);

    const bar = document.getElementById(`progress-bar-${dayNumber}`);
    const text = document.getElementById(`progress-text-${dayNumber}`);
    if (bar) bar.style.width = `${percent}%`;
    if (text) text.innerText = `${percent}%`;

    updateChartProgress(dayNumber, percent);
}

async function toggleTask(taskId, dayNumber) {
    try {
        const response = await fetch(`/toggle_task/${taskId}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken(),
            },
        });
        const data = await response.json();
        if (!data.success) return;

        const row = document.getElementById(`task-row-${taskId}`);
        if (!row) return;
        const textSpan = row.querySelector('.task-name');
        if (data.is_completed) {
            textSpan.classList.add('completed');
        } else {
            textSpan.classList.remove('completed');
        }

        const allData = getTasksData();
        if (!allData || !allData.days[dayNumber]) return;
        const task = allData.days[dayNumber].find(t => t.id === taskId);
        if (task) {
            task.is_completed = data.is_completed;
            setTasksData(allData);
        }
        updateDayProgressUI(dayNumber);
    } catch (err) {
        console.error(err);
    }
}

async function deleteTask(taskId, dayNumber) {
    try {
        const response = await fetch(`/delete_task/${taskId}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken(),
            },
        });
        const data = await response.json();
        if (!data.success) return;

        const row = document.getElementById(`task-row-${taskId}`);
        if (row) row.remove();

        const allData = getTasksData();
        if (!allData || !allData.days[dayNumber]) return;
        allData.days[dayNumber] = allData.days[dayNumber].filter(t => t.id !== taskId);
        setTasksData(allData);
        updateDayProgressUI(dayNumber);

        const tasksList = document.getElementById('day-tasks-list');
        if (tasksList && tasksList.children.length === 0) {
            tasksList.innerHTML = '<p class="no-tasks">لا توجد مهام لهذا اليوم.</p>';
        }
    } catch (err) {
        console.error(err);
    }
}

async function submitAddTask(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);

    try {
        const response = await fetch('/add_daily_task', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: formData,
        });
        const data = await response.json();
        if (!data.success) return;

        const task = data.task;
        const dayNumber = document.getElementById('modal-day-number').value;
        const tasksList = document.getElementById('day-tasks-list');
        if (!tasksList) return;

        const noTasksMsg = tasksList.querySelector('.no-tasks');
        if (noTasksMsg) noTasksMsg.remove();

        const taskItem = document.createElement('div');
        taskItem.className = 'task-item daily';
        taskItem.id = `task-row-${task.id}`;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = task.is_completed;
        checkbox.className = 'task-checkbox';
        checkbox.onchange = () => toggleTask(task.id, dayNumber);

        const spanName = document.createElement('span');
        spanName.className = 'task-name';
        spanName.textContent = task.name;

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn-delete';
        deleteBtn.innerHTML = '&times;';
        deleteBtn.onclick = () => deleteTask(task.id, dayNumber);

        const leftDiv = document.createElement('div');
        leftDiv.className = 'task-left';
        leftDiv.appendChild(checkbox);
        leftDiv.appendChild(spanName);

        const rightDiv = document.createElement('div');
        rightDiv.className = 'task-right';
        const badge = document.createElement('span');
        badge.className = 'task-type badge-daily';
        badge.textContent = 'يومية';
        rightDiv.appendChild(badge);
        rightDiv.appendChild(deleteBtn);

        taskItem.appendChild(leftDiv);
        taskItem.appendChild(rightDiv);
        tasksList.appendChild(taskItem);

        const input = document.getElementById('new-task-input');
        if (input) input.value = '';

        const allData = getTasksData();
        if (!allData) return;
        if (!allData.days[dayNumber]) allData.days[dayNumber] = [];
        allData.days[dayNumber].push(task);
        setTasksData(allData);
        updateDayProgressUI(dayNumber);
    } catch (err) {
        console.error(err);
    }
}

window.openDayModal = function (dayNumber) {
    const allData = getTasksData();
    if (!allData) return;

    const dayTasks = allData.days[dayNumber] || [];
    const currentDay = allData.current_day;

    const modalTitle = document.getElementById('day-modal-title');
    if (modalTitle) modalTitle.textContent = `تفاصيل اليوم ${dayNumber}`;

    const mChallengeId = document.getElementById('modal-challenge-id');
    const mDayNumber = document.getElementById('modal-day-number');
    if (mChallengeId) mChallengeId.value = allData.challenge_id;
    if (mDayNumber) mDayNumber.value = dayNumber;

    const addForm = document.getElementById('add-daily-task-form');
    if (addForm) {
        addForm.style.display = dayNumber == currentDay && !allData.is_finished ? 'flex' : 'none';
    }

    const tasksList = document.getElementById('day-tasks-list');
    if (!tasksList) return;
    tasksList.innerHTML = '';

    if (dayTasks.length === 0) {
        tasksList.innerHTML = '<p class="no-tasks">لا توجد مهام لهذا اليوم.</p>';
    } else {
        dayTasks.forEach(task => {
            const taskItem = document.createElement('div');
            taskItem.className = `task-item ${task.is_fixed ? 'fixed' : 'daily'}`;
            taskItem.id = `task-row-${task.id}`;

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = task.is_completed;
            checkbox.className = 'task-checkbox';
            checkbox.onchange = () => toggleTask(task.id, dayNumber);
            if (dayNumber != currentDay || allData.is_finished) checkbox.disabled = true;

            const spanName = document.createElement('span');
            spanName.className = 'task-name';
            spanName.textContent = task.name;
            if (task.is_completed) spanName.classList.add('completed');

            const leftDiv = document.createElement('div');
            leftDiv.className = 'task-left';
            leftDiv.appendChild(checkbox);
            leftDiv.appendChild(spanName);

            const rightDiv = document.createElement('div');
            rightDiv.className = 'task-right';
            const badge = document.createElement('span');
            badge.className = `task-type ${task.is_fixed ? 'badge-fixed' : 'badge-daily'}`;
            badge.textContent = task.is_fixed ? 'ثابتة' : 'يومية';
            rightDiv.appendChild(badge);

            if (!task.is_fixed && dayNumber == currentDay && !allData.is_finished) {
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn-delete';
                deleteBtn.innerHTML = '&times;';
                deleteBtn.onclick = () => deleteTask(task.id, dayNumber);
                rightDiv.appendChild(deleteBtn);
            }

            taskItem.appendChild(leftDiv);
            taskItem.appendChild(rightDiv);
            tasksList.appendChild(taskItem);
        });
    }

    const dayModal = document.getElementById('day-modal');
    if (dayModal) dayModal.style.display = 'block';
};

window.closeDayModal = function () {
    const dayModal = document.getElementById('day-modal');
    if (dayModal) dayModal.style.display = 'none';
};

document.addEventListener('DOMContentLoaded', () => {
    const flashMessages = document.querySelectorAll('.flash-messages li');
    if (flashMessages.length > 0) {
        setTimeout(() => {
            flashMessages.forEach(msg => {
                msg.style.transition = 'opacity 0.5s ease';
                msg.style.opacity = '0';
                setTimeout(() => msg.remove(), 500);
            });
        }, 3000);
    }

    const createModal = document.getElementById('challenge-modal');
    const btnStart = document.getElementById('btn-start-challenge');
    const spanCloseCreate = document.querySelector('#challenge-modal .close-modal');
    const addTaskBtn = document.getElementById('add-task-btn');
    const fixedTasksContainer = document.getElementById('fixed-tasks-container');
    const startDateInput = document.getElementById('start-date-input');
    const dayModal = document.getElementById('day-modal');

    if (btnStart && createModal) {
        btnStart.onclick = function () {
            createModal.style.display = 'block';
            if (startDateInput) {
                const today = new Date().toISOString().split('T')[0];
                startDateInput.min = today;
                if (!startDateInput.value) startDateInput.value = today;
            }
        };
    }

    if (spanCloseCreate) {
        spanCloseCreate.onclick = function () {
            createModal.style.display = 'none';
        };
    }

    if (addTaskBtn && fixedTasksContainer) {
        addTaskBtn.onclick = function () {
            const div = document.createElement('div');
            div.className = 'task-input-row';

            const input = document.createElement('input');
            input.type = 'text';
            input.name = 'fixed_tasks[]';
            input.required = true;
            input.placeholder = 'مهمة ثابتة جديدة...';

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn-remove-task';
            removeBtn.setAttribute('aria-label', 'حذف المهمة');
            removeBtn.innerHTML = '&times;';
            removeBtn.onclick = function () {
                div.remove();
            };

            div.appendChild(input);
            div.appendChild(removeBtn);
            fixedTasksContainer.appendChild(div);
            input.focus();
        };
    }

    window.onclick = function (event) {
        if (event.target == createModal) createModal.style.display = 'none';
        if (event.target == dayModal) dayModal.style.display = 'none';
    };

    const chartCanvas = document.getElementById('progressChart');
    const tasksData = getTasksData();
    if (chartCanvas && tasksData && window.Chart) {
        const totalDays = Number(document.querySelector('.chart-container')?.dataset.totalDays || 0);
        const labels = Array.from({ length: totalDays }, (_, i) => `اليوم ${i + 1}`);
        const progressData = tasksData.progress_data || [];

        const container = document.querySelector('.chart-container');
        if (container && totalDays > 10) {
            container.style.width = `${totalDays * 50}px`;
        }

        window.progressChart = new Chart(chartCanvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'مستوى التقدم (%)',
                        data: progressData,
                        borderColor: '#ffd700',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#ffd700',
                        pointRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        position: 'right',
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { color: '#aaa' },
                    },
                    x: { reverse: true, grid: { display: false }, ticks: { color: '#aaa' } },
                },
                plugins: { legend: { display: false } },
            },
        });
    }
});
