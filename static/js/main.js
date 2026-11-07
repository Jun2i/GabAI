/**
 * GabAI: An AI-Driven Platform for Mental Health Monitoring and Personalized Recommendation System
 * Healthcare Application Client Logic
 */

document.addEventListener('DOMContentLoaded', function () {
  // Initialize Bootstrap Tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Auto-dismiss standard alerts after 6 seconds
  setTimeout(function () {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 6000);

  // Questionnaire Category Tab Switching & Progress Calculation
  const questionnaireForm = document.getElementById('assessmentForm');
  if (questionnaireForm) {
    initQuestionnaireProgress();
  }
});

function initQuestionnaireProgress() {
  const questionnaireForm = document.getElementById('assessmentForm');
  if (!questionnaireForm) return;
  const allRadios = document.querySelectorAll('.assessment-input');
  const progressBar = document.getElementById('formProgressBar');
  const progressText = document.getElementById('formProgressText');
  const questionCount = parseInt(questionnaireForm.getAttribute('data-total-questions') || '0', 10);

  function updateCount() {
    const answeredNames = new Set();
    allRadios.forEach(input => {
      if ((input.type === 'radio' && input.checked) || (input.type === 'select-one' && input.value)) {
        answeredNames.add(input.name);
      }
    });

    const answeredCount = answeredNames.size;
    const pct = questionCount > 0 ? Math.round((answeredCount / questionCount) * 100) : 0;

    if (progressBar) {
      progressBar.style.width = pct + '%';
      progressBar.setAttribute('aria-valuenow', pct);
    }
    if (progressText) {
      progressText.textContent = `${answeredCount} of ${questionCount} answered (${pct}%)`;
    }
  }

  allRadios.forEach(input => {
    input.addEventListener('change', updateCount);
  });

  updateCount();
}

/**
 * Render Radar Chart for Assessment 13 Screening Categories
 */
function renderCategoryRadarChart(canvasId, labels, dataValues) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'radar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Symptom Burden (%)',
        data: dataValues,
        fill: true,
        backgroundColor: 'rgba(45, 122, 94, 0.2)',
        borderColor: '#2D7A5E',
        pointBackgroundColor: '#2D7A5E',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: '#2D7A5E'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          angleLines: { color: '#E2E8F0' },
          grid: { color: '#E2E8F0' },
          suggestedMin: 0,
          suggestedMax: 100,
          ticks: { stepSize: 25, backdropColor: 'transparent' }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

/**
 * Render Doughnut Chart for Activity Tracker
 */
function renderActivityDoughnut(canvasId, completed, remaining) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Completed', 'Pending / Skipped'],
      datasets: [{
        data: [completed, remaining],
        backgroundColor: ['#2D7A5E', '#E2E8F0'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '75%',
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  });
}

/**
 * ==========================================================================
 * GabAI Assistant - Floating Chatbot Client Logic
 * ==========================================================================
 */
document.addEventListener('DOMContentLoaded', function () {
  initGabAIChatbot();
});

function initGabAIChatbot() {
  const fab = document.getElementById('chatbotFab');
  const windowEl = document.getElementById('chatbotWindow');
  const closeBtn = document.getElementById('chatbotCloseBtn');
  const minimizeBtn = document.getElementById('chatbotMinimizeBtn');
  const clearBtn = document.getElementById('chatbotClearBtn');
  const inputEl = document.getElementById('chatbotInput');
  const sendBtn = document.getElementById('chatbotSendBtn');
  const messagesEl = document.getElementById('chatbotMessages');

  if (!fab || !windowEl) return;

  function toggleChatbot() {
    const isVisible = windowEl.style.display === 'flex';
    if (isVisible) {
      windowEl.style.display = 'none';
    } else {
      windowEl.style.display = 'flex';
      scrollChatToBottom();
      if (inputEl) inputEl.focus();
    }
  }

  fab.addEventListener('click', toggleChatbot);

  if (closeBtn) {
    closeBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      windowEl.style.display = 'none';
    });
  }

  if (minimizeBtn) {
    minimizeBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      windowEl.style.display = 'none';
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      if (confirm('Clear chat history?')) {
        const welcomeMsg = messagesEl.querySelector('.mc-chat-msg:first-child');
        messagesEl.innerHTML = '';
        if (welcomeMsg) messagesEl.appendChild(welcomeMsg);
      }
    });
  }

  // Handle suggested prompt chips
  document.addEventListener('click', function (e) {
    const chip = e.target.closest('.mc-chip-btn');
    if (chip) {
      const prompt = chip.getAttribute('data-prompt') || chip.textContent.trim();
      if (inputEl) {
        inputEl.value = prompt;
        sendMessage();
      }
    }
  });

  if (sendBtn && inputEl) {
    sendBtn.addEventListener('click', sendMessage);

    inputEl.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  function scrollChatToBottom() {
    if (messagesEl) {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
  }

  function formatMarkdown(text) {
    if (!text) return '';
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Markdown bold **text**
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Markdown italic *text*
    escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Markdown links [text](url)
    escaped = escaped.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" class="fw-semibold text-primary">$1</a>');
    // Bullet points
    escaped = escaped.replace(/^[•\-]\s+(.*)$/gm, '<li class="ms-3">$1</li>');
    // Line breaks
    escaped = escaped.replace(/\n\n/g, '<br><br>');
    escaped = escaped.replace(/\n/g, '<br>');

    return escaped;
  }

  function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue || '';
  }

  function appendMessage(sender, text, isCrisis = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `mc-chat-msg ${sender} ${isCrisis ? 'crisis' : ''}`;

    if (sender === 'bot') {
      const avatar = document.createElement('div');
      avatar.className = 'mc-chat-avatar-sm';
      avatar.innerHTML = isCrisis ? '<i class="fa-solid fa-triangle-exclamation text-danger"></i>' : '<i class="fa-solid fa-robot"></i>';
      msgDiv.appendChild(avatar);
    }

    const bubble = document.createElement('div');
    bubble.className = 'mc-chat-bubble';
    bubble.innerHTML = formatMarkdown(text);
    msgDiv.appendChild(bubble);

    messagesEl.appendChild(msgDiv);
    scrollChatToBottom();
  }

  function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.id = 'chatbotTypingIndicator';
    typingDiv.className = 'mc-chat-msg bot';
    typingDiv.innerHTML = `
      <div class="mc-chat-avatar-sm"><i class="fa-solid fa-robot"></i></div>
      <div class="mc-typing-indicator">
        <div class="mc-typing-dot"></div>
        <div class="mc-typing-dot"></div>
        <div class="mc-typing-dot"></div>
      </div>
    `;
    messagesEl.appendChild(typingDiv);
    scrollChatToBottom();
  }

  function removeTyping() {
    const typingDiv = document.getElementById('chatbotTypingIndicator');
    if (typingDiv) typingDiv.remove();
  }

  function sendMessage() {
    if (!inputEl) return;
    const text = inputEl.value.trim();
    if (!text) return;

    // Display user message
    appendMessage('user', text);
    inputEl.value = '';
    if (sendBtn) sendBtn.disabled = true;

    showTyping();

    fetch('/ai/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({ message: text })
    })
      .then(res => res.json())
      .then(data => {
        removeTyping();
        if (sendBtn) sendBtn.disabled = false;
        if (data.status === 'success') {
          appendMessage('bot', data.reply, data.is_crisis);
        } else {
          appendMessage('bot', '⚠️ Sorry, I encountered an issue processing your request. Please try again.');
        }
      })
      .catch(err => {
        console.error('Chatbot request error:', err);
        removeTyping();
        if (sendBtn) sendBtn.disabled = false;
        appendMessage('bot', '⚠️ Network connection error. Please verify your connection.');
      });
  }
}


