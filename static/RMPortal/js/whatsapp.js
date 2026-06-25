// ===== DATA =====
const chatUsers = {
    1: { phone: '9876543210', ip: '223.237.188.8', status: 'Active', online: true },
    2: { phone: '9876543211', ip: '42.109.144.227', status: 'Offline', online: false },
    3: { phone: '9876543212', ip: '223.181.240.64', status: 'Online', online: true },
    4: { phone: '9876543213', ip: '122.178.83.180', status: 'Online', online: true },
    5: { phone: '9876543214', ip: '106.192.79.153', status: 'Visitor', online: false }
};

const visitorUsers = {
    1: { ip: '223.237.188.8', location: 'India, Tamil Nadu', status: 'Quickly Left' },
    2: { ip: '42.109.144.227', location: 'USA, New York', status: 'Active' },
    3: { ip: '223.181.240.64', location: 'UK, London', status: 'Reassigned' },
    4: { ip: '122.178.83.180', location: 'Canada, Toronto', status: 'Quickly Left' }
};

const chatMeMessages = {
    1: [
        { text: 'Hey! How are you doing today?', time: '10:30 AM', type: 'received', read: true },
        { text: "I'm doing great! Just finished working on the new project.", time: '10:32 AM', type: 'sent', status: 'delivered', read: true },
        { text: "That's awesome! Can't wait to see it. Are you free this weekend?", time: '10:33 AM', type: 'received', read: true },
        { voiceMessage: true, audioBlobUrl: null, duration: 15, time: '10:35 AM', type: 'sent', status: 'delivered' },
        { voiceMessage: true, audioBlobUrl: null, duration: 8, time: '10:36 AM', type: 'received', read: true },
        { text: 'Yes! Lets catch up. Maybe grab coffee on Saturday?', time: '10:37 AM', type: 'sent', status: 'delivered' }
    ],
    2: [{ text: 'would u like to ...', time: '02:26 PM', type: 'received', read: true }],
    3: [{ text: 'h sit', time: '01:00 PM', type: 'received', read: true }],
    4: [],
    5: []
};

// Preload demo voice audio for sample messages.
chatMeMessages[1][3].audioBlobUrl = createSampleVoiceUrl(15, 420);
chatMeMessages[1][4].audioBlobUrl = createSampleVoiceUrl(8, 520);

const visitorMessages = {
    1: [{ text: 'New visitor from India', time: '02:39 PM', type: 'received', read: true }],
    2: [{ text: 'Hello from USA', time: '02:26 PM', type: 'received', read: true }],
    3: [{ text: 'UK visitor here', time: '01:00 PM', type: 'received', read: true }],
    4: [{ text: 'Canada visitor', time: '12:54 PM', type: 'received', read: true }]
};

// ===== STATE =====
let currentChat = null;
let currentTab = 'chats';
let currentMessages = chatMeMessages;
let replyTarget = null;          // { text, type, index }
let mediaRecorder = null;
let audioChunks = [];
let recordingTimer = null;
let recordingSeconds = 0;
let currentUploadType = 'image';
let currentImageIndex = 0;
let chatImages = {};             // chatId -> [blobUrl]
let confirmCallback = null;
let activeAudioEl = null;        // currently playing <audio>

// ===== DOM =====
const tabs = document.querySelectorAll('.tab');
const chatList = document.getElementById('chatList');
const visitorsPanel = document.getElementById('visitorsPanel');
const visitorsList = document.getElementById('visitorsList');
const chatMessagesEl = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('recordBtn');
const endChatBtn = document.getElementById('endChatBtn');
const websiteBtn = document.getElementById('websiteBtn');
const chatName = document.getElementById('chatName');
const chatStatus = document.getElementById('chatStatus');
const fileInput = document.getElementById('fileInput');
const fileMenuToggle = document.getElementById('fileMenuToggle');
const fileMenuDropdown = document.getElementById('fileMenuDropdown');
const uploadImageBtn = document.getElementById('uploadImageBtn');
const uploadDocumentBtn = document.getElementById('uploadDocumentBtn');
const emojiBtn = document.getElementById('emojiBtn');
const emojiPicker = document.getElementById('emojiPicker');
const imageViewerModal = document.getElementById('imageViewerModal');
const imageViewerImg = document.getElementById('imageViewerImg');
const imageViewerClose = document.getElementById('imageViewerClose');
const imageDownloadBtn = document.getElementById('imageDownloadBtn');
const imageCountText = document.getElementById('imageCountText');
const confirmModal = document.getElementById('confirmModal');
const confirmTitle = document.getElementById('confirmTitle');
const confirmBody = document.getElementById('confirmBody');
const confirmOk = document.getElementById('confirmOk');
const confirmCancel = document.getElementById('confirmCancel');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const onlineBtn = document.getElementById('onlineBtn');
const chatSidebar = document.getElementById('chatSidebar');
const chatMain = document.getElementById('chatMain');
const backBtn = document.getElementById('backBtn');
const offlineBanner = document.getElementById('offlineBanner');
const closeBannerBtn = document.getElementById('closeBanner');
const todayStats = document.getElementById('todayStats');
const statsDropdown = document.getElementById('statsDropdown');
const replyBar = document.getElementById('replyBar');
const replyBarText = document.getElementById('replyBarText');
const replyBarClose = document.getElementById('replyBarClose');
const voiceRecordBar = document.getElementById('voiceRecordBar');
const voiceRecTime = document.getElementById('voiceRecTime');
const voiceCancelBtn = document.getElementById('voiceCancelBtn');
const voiceSendBtn = document.getElementById('voiceSendBtn');
const chatInput = document.getElementById('chatInput');

const emojis = ['😀','😂','❤️','😍','🎉','👍','🔥','😎','✨','🌟','💯','😘','🙌','😅','💪','🤔','😌','😳','🥳','😱'];

// ===== INIT =====
function init() {
    setupEventListeners();
    loadEmojis();
    selectChat(1);
}

// ===== EVENT LISTENERS =====
function setupEventListeners() {
    // Tabs
    tabs.forEach(tab => tab.addEventListener('click', (e) => switchTab(tab.dataset.tab, e)));

    // Chat / Visitor selection
    chatList.addEventListener('click', (e) => {
        const item = e.target.closest('.chat-item');
        if (item) selectChat(parseInt(item.dataset.chat));
    });
    visitorsList.addEventListener('click', (e) => {
        const item = e.target.closest('.visitor-item');
        if (item) selectVisitor(parseInt(item.dataset.visitor));
    });

    // Message input → toggle mic/send button
    messageInput.addEventListener('input', toggleInputButtons);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });

    sendBtn.addEventListener('click', sendMessage);

    // Mic / recording
    micBtn.addEventListener('click', startRecording);
    voiceCancelBtn.addEventListener('click', cancelRecording);
    voiceSendBtn.addEventListener('click', stopAndSendRecording);

    // File upload
    fileMenuToggle.addEventListener('click', (e) => { e.stopPropagation(); fileMenuDropdown.classList.toggle('show'); });
    uploadImageBtn.addEventListener('click', () => { currentUploadType = 'image'; fileInput.accept = 'image/*'; fileInput.click(); fileMenuDropdown.classList.remove('show'); });
    uploadDocumentBtn.addEventListener('click', () => { currentUploadType = 'document'; fileInput.accept = '*'; fileInput.click(); fileMenuDropdown.classList.remove('show'); });
    fileInput.addEventListener('change', handleFileUpload);

    // Emoji
    emojiBtn.addEventListener('click', (e) => { e.stopPropagation(); emojiPicker.classList.toggle('open'); });
    document.addEventListener('click', (e) => {
        if (!e.target.closest('#emojiBtn') && !e.target.closest('.emoji-picker')) emojiPicker.classList.remove('open');
        if (!e.target.closest('.file-menu')) fileMenuDropdown.classList.remove('show');
    });

    // Reply bar close
    replyBarClose.addEventListener('click', clearReply);

    // Modal
    confirmCancel.addEventListener('click', closeConfirmModal);
    confirmOk.addEventListener('click', handleConfirmOk);
    document.addEventListener('click', (e) => { if (e.target === confirmModal) closeConfirmModal(); });

    // Image viewer
    imageViewerClose.addEventListener('click', closeImageViewer);
    imageDownloadBtn.addEventListener('click', downloadImage);
    document.addEventListener('click', (e) => { if (e.target === imageViewerModal) closeImageViewer(); });

    // Header actions
    onlineBtn.addEventListener('click', toggleOnlineStatus);
    backBtn.addEventListener('click', goBack);
    closeBannerBtn.addEventListener('click', () => offlineBanner.remove());
    todayStats.addEventListener('click', toggleStats);
    endChatBtn.addEventListener('click', endChat);
    websiteBtn.addEventListener('click', () => window.open('https://example.com', '_blank'));
}

// ===== TOGGLE SEND / MIC =====
function toggleInputButtons() {
    const hasText = messageInput.value.trim().length > 0;
    sendBtn.style.display = hasText ? 'flex' : 'none';
    micBtn.style.display = hasText ? 'none' : 'flex';
}

// ===== TABS =====
function switchTab(tabName, e) {
    currentTab = tabName;
    tabs.forEach(t => t.classList.remove('active'));
    if (e) e.target.closest('.tab').classList.add('active');

    if (tabName === 'chats') {
        chatList.classList.remove('hidden');
        visitorsPanel.classList.remove('active');
        todayStats.classList.remove('show');
        micBtn.style.display = 'flex';
        selectChat(1);
    } else {
        chatList.classList.add('hidden');
        visitorsPanel.classList.add('active');
        todayStats.classList.add('show');
        micBtn.style.display = 'none';
        sendBtn.style.display = 'none';
        selectVisitor(1);
    }
}

// ===== SELECT CHAT =====
function selectChat(chatId) {
    currentChat = chatId;
    currentMessages = chatMeMessages;
    document.querySelectorAll('.chat-item').forEach(i => i.classList.remove('active'));
    document.querySelector(`[data-chat="${chatId}"]`)?.classList.add('active');
    const user = chatUsers[chatId];
    chatName.textContent = user.phone;
    chatStatus.textContent = user.online ? 'Online' : 'Offline';
    chatStatus.style.color = user.online ? '#10b981' : '#ef4444';
    clearReply();
    renderMessages(chatId);
    hideOnMobile();
}

// ===== SELECT VISITOR =====
function selectVisitor(visitorId) {
    currentChat = visitorId;
    currentMessages = visitorMessages;
    document.querySelectorAll('.visitor-item').forEach(i => i.classList.remove('active'));
    document.querySelector(`[data-visitor="${visitorId}"]`)?.classList.add('active');
    const v = visitorUsers[visitorId];
    chatName.textContent = v.ip;
    chatStatus.textContent = v.location;
    chatStatus.style.color = '#666';
    clearReply();
    renderMessages(visitorId);
    hideOnMobile();
}

// ===== RENDER MESSAGES =====
function renderMessages(chatId) {
    chatMessagesEl.innerHTML = '<div class="date-divider"><span>Today</span></div>';
    const messages = currentMessages[chatId] || [];
    if (messages.length === 0) {
        chatMessagesEl.innerHTML += `<div class="empty-chat"><div class="empty-icon"><i class="fas fa-comments"></i></div><p>No messages yet</p></div>`;
        return;
    }
    messages.forEach((msg, index) => {
        const el = createMessageElement(msg, index);
        chatMessagesEl.appendChild(el);
    });
    scrollToBottom();
}

// ===== CREATE MESSAGE ELEMENT =====
function createMessageElement(msg, index) {
    const div = document.createElement('div');
    div.className = `message ${msg.type}`;

    // Reply quote HTML (FB style)
    let replyQuoteHtml = '';
    if (msg.reply) {
        const replyContent = msg.reply.voiceMessage
            ? `<div class="msg-reply-quote-voice"><i class="fas fa-microphone"></i> Voice message</div>`
            : `<div class="msg-reply-quote-text">${escapeHtml(msg.reply.text || '')}</div>`;
        replyQuoteHtml = `
            <div class="msg-reply-quote" data-scroll="${msg.reply.index}">
                <div class="msg-reply-quote-name">${msg.reply.senderName || 'Message'}</div>
                ${replyContent}
            </div>
        `;
    }

    let contentHtml = '';

    if (msg.voiceMessage) {
        // === VOICE MESSAGE ===
        if (currentTab === 'visitors') {
            // In Visitors tab: show plain text placeholder (no playback)
            contentHtml = `
                <div class="message-content">
                    ${replyQuoteHtml}
                    <p><i class="fas fa-microphone" style="margin-right:5px;color:var(--primary)"></i>Voice message</p>
                    <div class="message-time">${msg.time}${msg.status ? `<span class="message-status ${msg.status}"></span>` : ''}</div>
                </div>
            `;
        } else {
            const durationStr = formatDuration(msg.duration || 0);
            contentHtml = `
                <div class="message-content">
                    ${replyQuoteHtml}
                    <div class="voice-bubble">
                        <button class="voice-play-btn" data-index="${index}" title="Play">
                            <i class="fas fa-play"></i>
                        </button>
                        <div class="voice-waveform-container">
                            <div class="voice-seek-bar" data-index="${index}">
                                <div class="voice-seek-track">
                                    <div class="voice-seek-progress" id="vsp-${index}"></div>
                                </div>
                                <div class="voice-seek-thumb" id="vst-${index}"></div>
                                <div class="voice-wave-bars" id="vwb-${index}">
                                    <span></span><span></span><span></span><span></span><span></span>
                                </div>
                            </div>
                            <div class="voice-time-row">
                                <span class="voice-elapsed" id="ve-${index}">0:00</span>
                                <span class="voice-total">${durationStr}</span>
                            </div>
                        </div>
                    </div>
                    <div class="message-time">${msg.time}${msg.status ? `<span class="message-status ${msg.status}"></span>` : ''}</div>
                </div>
            `;
        }
    } else if (msg.image) {
        // === IMAGE MESSAGE ===
        contentHtml = `
            <div class="message-content">
                ${replyQuoteHtml}
                <img src="${msg.image}" class="message-image" alt="Image">
                <div class="message-time">${msg.time}${msg.status ? `<span class="message-status ${msg.status}"></span>` : ''}</div>
            </div>
        `;
    } else if (msg.file) {
        // === FILE MESSAGE ===
        contentHtml = `
            <div class="message-content">
                ${replyQuoteHtml}
                <div class="message-file" data-index="${index}">
                    <i class="fas fa-file file-icon"></i>
                    <div class="file-info">
                        <span class="file-name">${escapeHtml(msg.file)}</span>
                        <span class="file-size">${msg.fileSize || ''}</span>
                    </div>
                </div>
                <div class="message-time">${msg.time}${msg.status ? `<span class="message-status ${msg.status}"></span>` : ''}</div>
            </div>
        `;
    } else {
        // === TEXT MESSAGE ===
        contentHtml = `
            <div class="message-content">
                ${replyQuoteHtml}
                <p>${escapeHtml(msg.text || '')}</p>
                <div class="message-time">${msg.time}${msg.status ? `<span class="message-status ${msg.status}"></span>` : ''}</div>
            </div>
        `;
    }

    // Reply action button (Facebook style - appears beside bubble)
    const replyBtnHtml = `
        <div class="message-actions">
            <button class="msg-action-btn reply-action-btn" title="Reply" data-index="${index}">
                <i class="fas fa-reply"></i>
            </button>
        </div>
    `;

    div.innerHTML = contentHtml + replyBtnHtml;

    // Bind events
    // Reply button
    div.querySelector('.reply-action-btn').addEventListener('click', () => {
        setReply(msg, index);
    });

    // Voice play
    if (msg.voiceMessage && currentTab !== 'visitors') {
        const playBtn = div.querySelector('.voice-play-btn');
        const seekBar = div.querySelector('.voice-seek-bar');
        playBtn.addEventListener('click', () => toggleVoicePlayback(msg, index, playBtn));
        seekBar.addEventListener('click', (e) => seekVoice(e, msg, index, seekBar));
    }

    // Image click → viewer
    if (msg.image) {
        div.querySelector('.message-image').addEventListener('click', () => openImageViewer(currentChat, index));
    }

    // File click → download
    if (msg.file) {
        div.querySelector('.message-file').addEventListener('click', () => downloadFile(msg.file, msg.fileData));
    }

    // Reply quote scroll to original
    if (msg.reply) {
        div.querySelector('.msg-reply-quote').addEventListener('click', () => {
            const targetIdx = msg.reply.index;
            const allMessages = chatMessagesEl.querySelectorAll('.message');
            if (allMessages[targetIdx]) {
                allMessages[targetIdx].scrollIntoView({ behavior: 'smooth', block: 'center' });
                allMessages[targetIdx].style.transition = 'background .2s';
                allMessages[targetIdx].style.background = 'rgba(18,159,255,.12)';
                setTimeout(() => { allMessages[targetIdx].style.background = ''; }, 1000);
            }
        });
    }

    return div;
}

// ===== SEND MESSAGE =====
function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;
    if (!currentChat) return;

    const msg = {
        text,
        time: getCurrentTime(),
        type: 'sent',
        status: 'delivered',
        read: false
    };

    if (replyTarget) {
        msg.reply = { ...replyTarget };
    }

    currentMessages[currentChat].push(msg);
    messageInput.value = '';
    clearReply();
    toggleInputButtons();
    renderMessages(currentChat);
}

// ===== REPLY (FB STYLE) =====
function setReply(msg, index) {
    const messages = currentMessages[currentChat];
    const senderName = msg.type === 'sent' ? 'You' : (currentTab === 'chats' ? chatUsers[currentChat]?.phone : visitorUsers[currentChat]?.ip);
    replyTarget = {
        index,
        text: msg.voiceMessage ? null : (msg.text || msg.file || 'Image'),
        voiceMessage: msg.voiceMessage || false,
        senderName: senderName || 'Message'
    };
    showReplyBar();
    messageInput.focus();
}

function showReplyBar() {
    replyBar.style.display = 'flex';
    if (replyTarget.voiceMessage) {
        replyBarText.innerHTML = '<i class="fas fa-microphone" style="margin-right:5px;color:var(--primary)"></i>Voice message';
    } else {
        replyBarText.textContent = replyTarget.text || '';
    }
}

function clearReply() {
    replyTarget = null;
    replyBar.style.display = 'none';
    replyBarText.textContent = '';
}

// ===== VOICE RECORDING =====
async function startRecording() {
    if (currentTab === 'visitors') return;
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        recordingSeconds = 0;

        const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/ogg';
        mediaRecorder = new MediaRecorder(stream, { mimeType });

        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = () => { stream.getTracks().forEach(t => t.stop()); };

        mediaRecorder.start(100);

        // Show record bar, hide input
        chatInput.style.display = 'none';
        replyBar.style.display = replyTarget ? 'flex' : 'none'; // keep reply bar if active
        voiceRecordBar.style.display = 'flex';

        // Timer
        recordingTimer = setInterval(() => {
            recordingSeconds++;
            voiceRecTime.textContent = formatDuration(recordingSeconds);
        }, 1000);

    } catch (err) {
        showToast('Microphone access denied', 'error');
    }
}

function cancelRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    clearInterval(recordingTimer);
    mediaRecorder = null;
    audioChunks = [];
    voiceRecordBar.style.display = 'none';
    chatInput.style.display = 'flex';
}

function stopAndSendRecording() {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') return;

    clearInterval(recordingTimer);
    const duration = recordingSeconds;

    mediaRecorder.onstop = () => {
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(audioChunks, { type: mimeType });
        const audioBlobUrl = URL.createObjectURL(audioBlob);

        if (currentChat) {
            const msg = {
                voiceMessage: true,
                audioBlobUrl,
                duration,
                time: getCurrentTime(),
                type: 'sent',
                status: 'delivered'
            };
            if (replyTarget) msg.reply = { ...replyTarget };
            currentMessages[currentChat].push(msg);
            clearReply();
            renderMessages(currentChat);
        }
        audioChunks = [];
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
    };

    mediaRecorder.stop();
    voiceRecordBar.style.display = 'none';
    chatInput.style.display = 'flex';
}

// ===== VOICE PLAYBACK =====
const audioElements = {}; // index -> Audio element

function toggleVoicePlayback(msg, index, playBtn) {
    const audio = getOrCreateAudio(msg, index);
    if (!audio) {
        showToast('No audio available for this message', 'info');
        return;
    }

    const icon = playBtn.querySelector('i');
    const waveBars = document.getElementById(`vwb-${index}`);

    if (!audio.paused) {
        // Pause
        audio.pause();
        icon.className = 'fas fa-play';
        playBtn.classList.remove('playing');
        if (waveBars) waveBars.classList.remove('playing');
    } else {
        // Stop any other playing audio
        if (activeAudioEl && activeAudioEl !== audio) {
            activeAudioEl.pause();
            activeAudioEl.currentTime = 0;
            // Reset other buttons
            document.querySelectorAll('.voice-play-btn').forEach(btn => {
                btn.classList.remove('playing');
                btn.querySelector('i').className = 'fas fa-play';
            });
            document.querySelectorAll('.voice-wave-bars').forEach(wb => wb.classList.remove('playing'));
        }

        activeAudioEl = audio;

        audio.play().then(() => {
            icon.className = 'fas fa-pause';
            playBtn.classList.add('playing');
            if (waveBars) waveBars.classList.add('playing');
        }).catch(() => {
            showToast('Could not play audio', 'error');
        });

        // Update seek bar while playing
        audio.ontimeupdate = () => updateSeekBar(audio, msg.duration, index);
        audio.onended = () => {
            icon.className = 'fas fa-play';
            playBtn.classList.remove('playing');
            if (waveBars) waveBars.classList.remove('playing');
            resetSeekBar(index);
            activeAudioEl = null;
        };
    }
}

function getOrCreateAudio(msg, index) {
    if (!msg.audioBlobUrl) return null;
    if (!audioElements[index]) {
        audioElements[index] = new Audio(msg.audioBlobUrl);
    }
    return audioElements[index];
}

function updateSeekBar(audio, totalDuration, index) {
    const duration = audio.duration || totalDuration || 1;
    const pct = (audio.currentTime / duration) * 100;

    const progress = document.getElementById(`vsp-${index}`);
    const thumb = document.getElementById(`vst-${index}`);
    const elapsed = document.getElementById(`ve-${index}`);

    if (progress) progress.style.width = pct + '%';
    if (thumb) thumb.style.left = pct + '%';
    if (elapsed) elapsed.textContent = formatDuration(Math.floor(audio.currentTime));
}

function resetSeekBar(index) {
    const progress = document.getElementById(`vsp-${index}`);
    const thumb = document.getElementById(`vst-${index}`);
    const elapsed = document.getElementById(`ve-${index}`);
    if (progress) progress.style.width = '0%';
    if (thumb) thumb.style.left = '0%';
    if (elapsed) elapsed.textContent = '0:00';
}

function seekVoice(e, msg, index, seekBarEl) {
    const audio = getOrCreateAudio(msg, index);
    if (!audio) return;

    const rect = seekBarEl.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const duration = audio.duration || msg.duration || 1;
    audio.currentTime = pct * duration;
    updateSeekBar(audio, duration, index);
}

// ===== FILE UPLOAD =====
function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file || !currentChat) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
        if (currentUploadType === 'image') {
            if (!chatImages[currentChat]) chatImages[currentChat] = [];
            chatImages[currentChat].push(ev.target.result);

            const msg = {
                image: ev.target.result,
                time: getCurrentTime(),
                type: 'sent',
                status: 'delivered'
            };
            if (replyTarget) msg.reply = { ...replyTarget };
            currentMessages[currentChat].push(msg);
            clearReply();
        } else {
            const msg = {
                file: file.name,
                fileSize: formatFileSize(file.size),
                fileData: ev.target.result,
                time: getCurrentTime(),
                type: 'sent',
                status: 'delivered'
            };
            if (replyTarget) msg.reply = { ...replyTarget };
            currentMessages[currentChat].push(msg);
            clearReply();
        }
        renderMessages(currentChat);
    };
    reader.readAsDataURL(file);
    e.target.value = '';
}

// ===== IMAGE VIEWER =====
function openImageViewer(chatId, index) {
    if (!chatImages[chatId]) return;
    // Find image index in chatImages array
    const msgs = currentMessages[chatId] || [];
    const msg = msgs[index];
    if (!msg || !msg.image) return;

    const imgIndex = chatImages[chatId].indexOf(msg.image);
    currentImageIndex = imgIndex >= 0 ? imgIndex : 0;
    imageViewerImg.src = msg.image;
    imageCountText.textContent = `1 / ${chatImages[chatId].length}`;
    imageViewerModal.classList.add('show');
}

function closeImageViewer() { imageViewerModal.classList.remove('show'); }

function downloadImage() {
    if (!chatImages[currentChat]) return;
    const link = document.createElement('a');
    link.href = chatImages[currentChat][currentImageIndex];
    link.download = `image-${currentImageIndex + 1}.jpg`;
    link.click();
}

// ===== FILE DOWNLOAD =====
function downloadFile(fileName, fileData) {
    if (!fileData) return;
    const link = document.createElement('a');
    link.href = fileData;
    link.download = fileName;
    link.click();
}

// ===== EMOJI =====
function loadEmojis() {
    emojiPicker.innerHTML = emojis.map(e => `<button class="emoji-btn">${e}</button>`).join('');
    emojiPicker.querySelectorAll('.emoji-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            messageInput.value += btn.textContent;
            messageInput.focus();
            toggleInputButtons();
        });
    });
}

// ===== MODAL =====
function showConfirmModal(title, body, cb) {
    confirmTitle.textContent = title;
    confirmBody.textContent = body;
    confirmCallback = cb;
    confirmModal.classList.add('show');
}
function closeConfirmModal() { confirmModal.classList.remove('show'); confirmCallback = null; }
function handleConfirmOk() { if (confirmCallback) confirmCallback(); closeConfirmModal(); }

// ===== STATUS =====
function toggleOnlineStatus() {
    const isOffline = statusDot.classList.contains('offline');
    if (isOffline) {
        statusDot.classList.replace('offline', 'online');
        statusText.textContent = 'Online';
        onlineBtn.textContent = 'Go Offline';
    } else {
        statusDot.classList.replace('online', 'offline');
        statusText.textContent = 'Offline';
        onlineBtn.textContent = 'Go Online';
    }
}

// ===== STATS =====
function toggleStats() {
    statsDropdown.classList.toggle('show');
    todayStats.classList.toggle('open');
}

// ===== ACTIONS =====
function endChat() {
    showConfirmModal('End Chat', 'Are you sure you want to end this chat?', () => {
        showToast('Chat ended', 'info');
    });
}

function goBack() {
    chatSidebar.classList.remove('hidden');
    chatMain.classList.add('hidden');
}

function hideOnMobile() {
    if (window.innerWidth <= 900) {
        chatSidebar.classList.add('hidden');
        chatMain.classList.remove('hidden');
    }
}

// ===== TOAST =====
function showToast(message, type = 'info') {
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = message;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}

// ===== UTILITIES =====
function getCurrentTime() {
    const now = new Date();
    let h = now.getHours(), m = String(now.getMinutes()).padStart(2, '0');
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return `${h}:${m} ${ampm}`;
}

function formatDuration(seconds) {
    const s = Math.floor(seconds);
    const m = Math.floor(s / 60);
    return `${m}:${String(s % 60).padStart(2, '0')}`;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

function createSampleVoiceUrl(duration = 3, frequency = 440) {
    const audioBlob = createToneAudioBlob(duration, frequency);
    return URL.createObjectURL(audioBlob);
}

function createToneAudioBlob(duration, frequency) {
    const sampleRate = 22050;
    const length = Math.floor(duration * sampleRate);
    const samples = new Float32Array(length);

    for (let i = 0; i < length; i++) {
        const t = i / sampleRate;
        const envelope = 1 - t / duration;
        samples[i] = Math.sin(2 * Math.PI * frequency * t) * 0.35 * envelope;
    }

    return encodeWav(samples, sampleRate);
}

function encodeWav(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeString(offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }

    return new Blob([view], { type: 'audio/wav' });
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function scrollToBottom() {
    setTimeout(() => { chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight; }, 30);
}

// ===== START =====
document.addEventListener('DOMContentLoaded', init);
