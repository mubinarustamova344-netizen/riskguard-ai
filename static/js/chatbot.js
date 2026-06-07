'use strict';
// Chatbot JS

var messagesEl = document.getElementById('chatMessages');
var chatInputEl = document.getElementById('chatInput');
var sendBtnEl   = document.getElementById('sendBtn');

function scrollToBottom() {
  if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendUserBubble(text) {
  if (!messagesEl) return;
  var now = new Date().toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
  var wrap = document.createElement('div');
  wrap.className = 'chat-bubble-wrap user';
  wrap.innerHTML =
    '<div>' +
      '<div class="chat-bubble user-bubble">' + escapeHtml(text) + '</div>' +
      '<div class="chat-time">' + now + '</div>' +
    '</div>';
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

function appendBotBubble(text, time) {
  removeTypingIndicator();
  if (!messagesEl) return;
  var wrap = document.createElement('div');
  wrap.className = 'chat-bubble-wrap bot';
  var bubbleId = 'bubble_' + Date.now();
  wrap.innerHTML =
    '<div class="bot-avatar-sm"><i class="bi bi-robot"></i></div>' +
    '<div>' +
      '<div class="chat-bubble bot-bubble" id="' + bubbleId + '"></div>' +
      '<div class="chat-time bot-time">' + (time || '') + '</div>' +
    '</div>';
  messagesEl.appendChild(wrap);
  scrollToBottom();
  // Typewriter effect
  typeWriter(document.getElementById(bubbleId), text, 0);
}

function typeWriter(el, fullText, i) {
  if (!el) return;
  var html = mdToHtml(fullText.substring(0, i));
  el.innerHTML = html + (i < fullText.length ? '<span class="cursor-blink">▋</span>' : '');
  if (i < fullText.length) {
    var speed = fullText[i] === '\n' ? 30 : (i % 3 === 0 ? 22 : 18);
    setTimeout(function() { typeWriter(el, fullText, i + 1); scrollToBottom(); }, speed);
  }
}

function showTypingIndicator() {
  if (!messagesEl) return;
  var el = document.createElement('div');
  el.className = 'chat-bubble-wrap bot';
  el.id = 'typingIndicator';
  el.innerHTML =
    '<div class="bot-avatar-sm"><i class="bi bi-robot"></i></div>' +
    '<div class="chat-bubble bot-bubble py-2">' +
      '<div class="typing-indicator">' +
        '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>' +
      '</div>' +
    '</div>';
  messagesEl.appendChild(el);
  scrollToBottom();
}

function removeTypingIndicator() {
  var el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function removeQuickReplies() {
  var qr = document.getElementById('quickReplies');
  if (qr) qr.remove();
}

function sendMessage() {
  if (!chatInputEl) return;
  var text = chatInputEl.value.trim();
  if (!text) return;

  chatInputEl.value = '';
  if (sendBtnEl) sendBtnEl.disabled = true;
  removeQuickReplies();
  appendUserBubble(text);
  showTypingIndicator();

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text })
  })
  .then(function(resp) { return resp.json(); })
  .then(function(data) {
    setTimeout(function() {
      appendBotBubble(data.response, data.timestamp);
    }, 400 + Math.random() * 300);
  })
  .catch(function(err) {
    removeTypingIndicator();
    appendBotBubble('Sorry, an error occurred: ' + err.message, '');
  })
  .finally(function() {
    if (sendBtnEl) sendBtnEl.disabled = false;
    if (chatInputEl) chatInputEl.focus();
  });
}

function sendQuick(text) {
  if (chatInputEl) chatInputEl.value = text;
  sendMessage();
}

function resetChat() {
  fetch('/api/chat/reset', { method: 'POST' })
    .then(function() {
      if (!messagesEl) return;
      messagesEl.innerHTML = '';
      var wrap = document.createElement('div');
      wrap.className = 'chat-bubble-wrap bot';
      wrap.innerHTML =
        '<div class="bot-avatar-sm"><i class="bi bi-robot"></i></div>' +
        '<div class="chat-bubble bot-bubble">Conversation reset. How can I help you?</div>';
      messagesEl.appendChild(wrap);
    })
    .catch(function() {});
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function mdToHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');
}

// ── Voice Input ───────────────────────────────────────────────
var recognition = null;
function startVoice() {
  var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) { showToast('Browser does not support voice input', 'warning', 2000); return; }
  if (recognition) { recognition.stop(); recognition = null; setVoiceBtn(false); return; }
  recognition = new SpeechRec();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
  setVoiceBtn(true);
  recognition.onresult = function(e) {
    var t = Array.from(e.results).map(r => r[0].transcript).join('');
    if (chatInputEl) chatInputEl.value = t;
  };
  recognition.onend = function() { setVoiceBtn(false); recognition = null; };
  recognition.onerror = function() { setVoiceBtn(false); recognition = null; };
  recognition.start();
}
function setVoiceBtn(active) {
  var btn = document.getElementById('voiceBtn');
  if (!btn) return;
  if (active) {
    btn.innerHTML = '<i class="bi bi-mic-fill"></i>';
    btn.style.color = '#ef4444';
    btn.style.animation = 'voicePulse 1s infinite';
  } else {
    btn.innerHTML = '<i class="bi bi-mic"></i>';
    btn.style.color = '';
    btn.style.animation = '';
  }
}

// Enter key
document.addEventListener('DOMContentLoaded', function() {
  if (chatInputEl) {
    chatInputEl.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    chatInputEl.focus();
  }
});
