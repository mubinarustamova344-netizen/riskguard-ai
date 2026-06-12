'use strict';

var messagesEl  = document.getElementById('chatMessages');
var chatInputEl = document.getElementById('chatInput');
var sendBtnEl   = document.getElementById('sendBtn');

function scrollToBottom() {
  if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendUserBubble(text) {
  if (!messagesEl) return;
  var now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
  wrap.innerHTML =
    '<div class="bot-avatar-sm"><i class="bi bi-robot"></i></div>' +
    '<div>' +
      '<div class="chat-bubble bot-bubble">' + mdToHtml(text) + '</div>' +
      '<div class="chat-time bot-time">' + (time || '') + '</div>' +
    '</div>';
  messagesEl.appendChild(wrap);
  scrollToBottom();
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

// ── Streaming send ────────────────────────────────────────────────────────────
function sendMessage() {
  if (!chatInputEl) return;
  var text = chatInputEl.value.trim();
  if (!text) return;

  chatInputEl.value = '';
  if (sendBtnEl) sendBtnEl.disabled = true;
  removeQuickReplies();
  appendUserBubble(text);
  showTypingIndicator();
  streamResponse(text);
}

function streamResponse(text) {
  fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: text }),
  })
  .then(function(resp) {
    if (!resp.ok) throw new Error('Server error ' + resp.status);

    removeTypingIndicator();
    var now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    var bubbleId = 'bubble_' + Date.now();
    var wrap = document.createElement('div');
    wrap.className = 'chat-bubble-wrap bot';
    wrap.innerHTML =
      '<div class="bot-avatar-sm"><i class="bi bi-robot"></i></div>' +
      '<div>' +
        '<div class="chat-bubble bot-bubble" id="' + bubbleId + '"><span class="cursor-blink">▋</span></div>' +
        '<div class="chat-time bot-time">' + now + '</div>' +
      '</div>';
    messagesEl.appendChild(wrap);
    scrollToBottom();

    var bubbleEl = document.getElementById(bubbleId);
    var fullText = '';
    var reader   = resp.body.getReader();
    var decoder  = new TextDecoder();
    var buffer   = '';

    function processChunk(done, value) {
      if (done) {
        if (bubbleEl) bubbleEl.innerHTML = mdToHtml(fullText);
        enableInput();
        return;
      }
      buffer += decoder.decode(value, { stream: true });
      var lines = buffer.split('\n');
      buffer = lines.pop();
      lines.forEach(function(line) {
        if (!line.startsWith('data: ')) return;
        var raw = line.slice(6).trim();
        if (raw === '[DONE]') return;
        try {
          var parsed = JSON.parse(raw);
          if (parsed.delta) {
            fullText += parsed.delta;
            if (bubbleEl) {
              bubbleEl.innerHTML = mdToHtml(fullText) + '<span class="cursor-blink">▋</span>';
              scrollToBottom();
            }
          }
        } catch (e) {}
      });
      reader.read().then(function(r) { processChunk(r.done, r.value); }).catch(enableInput);
    }

    reader.read().then(function(r) { processChunk(r.done, r.value); }).catch(enableInput);
  })
  .catch(function(err) {
    removeTypingIndicator();
    appendBotBubble('Connection error. Please try again.', '');
    enableInput();
  });
}

function enableInput() {
  if (sendBtnEl)   sendBtnEl.disabled = false;
  if (chatInputEl) chatInputEl.focus();
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

// ── Helpers ───────────────────────────────────────────────────────────────────
function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Markdown → HTML renderer ──────────────────────────────────────────────────
function mdToHtml(md) {
  if (!md) return '';
  var s = String(md);

  // 1. Protect fenced code blocks
  var saved = [];
  s = s.replace(/```[\w]*\n?([\s\S]*?)```/g, function(_, code) {
    saved.push('<pre class="md-pre"><code>' + escapeHtml(code.replace(/\n$/, '')) + '</code></pre>');
    return '\x01' + (saved.length - 1) + '\x01';
  });

  // 2. Render markdown tables (| header | ... \n | --- | ... \n | rows |)
  s = s.replace(/(\|[^\n]+\|\n\|[-| :]+\|\n(?:\|[^\n]+\|\n?)+)/g, function(tbl) {
    var rows = tbl.trim().split('\n');
    var hCells = rows[0].split('|').filter(function(c,i,a){ return i>0 && i<a.length-1; });
    var bRows  = rows.slice(2).filter(Boolean);
    var thead  = '<thead><tr>' + hCells.map(function(c){
      return '<th>' + inlineMd(c.trim()) + '</th>';
    }).join('') + '</tr></thead>';
    var tbody  = '<tbody>' + bRows.map(function(r){
      var cells = r.split('|').filter(function(c,i,a){ return i>0 && i<a.length-1; });
      return '<tr>' + cells.map(function(c){
        return '<td>' + inlineMd(c.trim()) + '</td>';
      }).join('') + '</tr>';
    }).join('') + '</tbody>';
    return '<div class="table-responsive my-1"><table class="table table-sm table-bordered mb-0 md-table">' + thead + tbody + '</table></div>';
  });

  // 3. Inline formatting on remaining text
  s = inlineMd(s);

  // 4. Line breaks
  s = s.replace(/\n\n+/g, '<br><br>').replace(/\n/g, '<br>');

  // 5. Restore code blocks
  s = s.replace(/\x01(\d+)\x01/g, function(_, i){ return saved[+i]; });

  return s;
}

function inlineMd(t) {
  return String(t)
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,     '<em>$1</em>')
    .replace(/`([^`]+)`/g,     '<code>$1</code>');
}

// ── Voice Input ───────────────────────────────────────────────────────────────
var recognition = null;
function startVoice() {
  var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) { showToast('Browser does not support voice input', 'warning', 2000); return; }
  if (recognition) { recognition.stop(); recognition = null; setVoiceBtn(false); return; }
  recognition = new SpeechRec();
  recognition.continuous     = false;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
  setVoiceBtn(true);
  recognition.onresult = function(e) {
    var t = Array.from(e.results).map(function(r) { return r[0].transcript; }).join('');
    if (chatInputEl) chatInputEl.value = t;
  };
  recognition.onend   = function() { setVoiceBtn(false); recognition = null; };
  recognition.onerror = function() { setVoiceBtn(false); recognition = null; };
  recognition.start();
}

function setVoiceBtn(active) {
  var btn = document.getElementById('voiceBtn');
  if (!btn) return;
  if (active) {
    btn.innerHTML  = '<i class="bi bi-mic-fill"></i>';
    btn.style.color     = '#ef4444';
    btn.style.animation = 'voicePulse 1s infinite';
  } else {
    btn.innerHTML  = '<i class="bi bi-mic"></i>';
    btn.style.color     = '';
    btn.style.animation = '';
  }
}

document.addEventListener('DOMContentLoaded', function() {
  if (chatInputEl) {
    chatInputEl.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    chatInputEl.focus();
  }
});
