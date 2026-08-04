/**
 * app/static/js/ai-doctor.js
 *
 * Shared "AI Doctor Workspace" chat controller for CuraLink.
 * Fully data-driven: reads config from data-* attributes on
 * `.cl-ai-doctor` containers, so the same script powers the
 * report chat (/chat), diet chat (/diet/chat) and workout chat
 * (/workout/chat) endpoints without duplicating logic per page.
 *
 * No backend calls beyond the existing chat endpoints. No new
 * persistence is invented — conversation state lives only in
 * memory for the current page view, exactly like before.
 */

(function () {

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /* Very small markdown-lite renderer: turns "- " lines into a
       list and keeps everything else as paragraphs. This is the
       "rich content block" layer requested — no backend structure
       is assumed, just light formatting of the real AI text. */
    function renderRichContent(text) {
        var lines = text.split(/\n+/).map(function (l) { return l.trim(); }).filter(Boolean);
        var html = '';
        var listBuffer = [];

        function flushList() {
            if (listBuffer.length) {
                html += '<ul>' + listBuffer.map(function (li) { return '<li>' + escapeHtml(li) + '</li>'; }).join('') + '</ul>';
                listBuffer = [];
            }
        }

        lines.forEach(function (line) {
            if (/^[-•]\s+/.test(line)) {
                listBuffer.push(line.replace(/^[-•]\s+/, ''));
            } else {
                flushList();
                html += '<p>' + escapeHtml(line) + '</p>';
            }
        });
        flushList();

        return html || '<p>' + escapeHtml(text) + '</p>';
    }

    function formatTime(date) {
        try {
            return new Intl.DateTimeFormat('fa-IR', { hour: '2-digit', minute: '2-digit' }).format(date);
        } catch (e) {
            return date.toLocaleTimeString();
        }
    }

    function initWorkspace(root) {
        var endpoint = root.getAttribute('data-endpoint');
        var csrfToken = root.getAttribute('data-csrf') || '';
        var payloadType = root.getAttribute('data-payload-type'); // 'report' | 'diet' | 'workout'

        var messagesEl = root.querySelector('.cl-ai-doctor-messages');
        var welcomeEl = root.querySelector('.cl-ai-welcome');
        var form = root.querySelector('.cl-ai-doctor-composer form');
        var input = root.querySelector('.cl-ai-doctor-composer input');
        var sendBtn = form ? form.querySelector('button[type="submit"]') : null;
        var drawerToggle = root.querySelector('.cl-ai-context-toggle');
        var contextPanel = root.querySelector('.cl-ai-doctor-context');
        var drawerClose = root.querySelector('.cl-ai-context-close');

        if (!messagesEl || !form || !input) return;

        var conversation = [];
        var lastUserQuestion = null;

        function extraPayload() {
            if (payloadType === 'report') {
                return {
                    job_id: root.getAttribute('data-job-id') || null,
                    record_id: root.getAttribute('data-record-id') ? parseInt(root.getAttribute('data-record-id'), 10) : null,
                };
            }
            if (payloadType === 'diet') {
                var store = document.getElementById(root.getAttribute('data-plan-store'));
                return { diet_plan_text: store ? store.value : '' };
            }
            if (payloadType === 'workout') {
                var storeW = document.getElementById(root.getAttribute('data-plan-store'));
                return { workout_plan_text: storeW ? storeW.value : '' };
            }
            return {};
        }

        function scrollToBottom() {
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }

        function hideWelcome() {
            if (welcomeEl) welcomeEl.style.display = 'none';
        }

        function addUserMessage(text) {
            hideWelcome();
            var wrap = document.createElement('div');
            wrap.className = 'cl-ai-msg cl-ai-msg-user cl-fade-in';
            wrap.innerHTML =
                '<div class="cl-ai-msg-bubble">' + escapeHtml(text) + '</div>' +
                '<span class="cl-ai-msg-time">' + formatTime(new Date()) + '</span>';
            messagesEl.appendChild(wrap);
            scrollToBottom();
        }

        function addAIMessage(text) {
            hideWelcome();
            var wrap = document.createElement('div');
            wrap.className = 'cl-ai-msg cl-ai-msg-ai cl-fade-in';

            var bubble = document.createElement('div');
            bubble.className = 'cl-ai-msg-bubble cl-ai-msg-bubble-rich';
            bubble.innerHTML = renderRichContent(text);

            var toolbar = document.createElement('div');
            toolbar.className = 'cl-ai-msg-toolbar';
            toolbar.innerHTML =
                '<button type="button" class="cl-ai-msg-action" data-action="copy" title="کپی پاسخ"><span class="material-symbols-outlined">content_copy</span></button>' +
                '<button type="button" class="cl-ai-msg-action" data-action="regenerate" title="تولید مجدد پاسخ"><span class="material-symbols-outlined">refresh</span></button>' +
                '<button type="button" class="cl-ai-msg-action cl-ai-msg-feedback" data-action="up" title="پاسخ مفید بود"><span class="material-symbols-outlined">thumb_up</span></button>' +
                '<button type="button" class="cl-ai-msg-action cl-ai-msg-feedback" data-action="down" title="پاسخ مفید نبود"><span class="material-symbols-outlined">thumb_down</span></button>' +
                '<span class="cl-ai-msg-time">' + formatTime(new Date()) + '</span>';

            wrap.appendChild(bubble);
            wrap.appendChild(toolbar);
            messagesEl.appendChild(wrap);

            toolbar.querySelector('[data-action="copy"]').addEventListener('click', function () {
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(text).then(function () {
                        var icon = toolbar.querySelector('[data-action="copy"] .material-symbols-outlined');
                        icon.textContent = 'check';
                        setTimeout(function () { icon.textContent = 'content_copy'; }, 1500);
                    });
                }
            });

            toolbar.querySelector('[data-action="regenerate"]').addEventListener('click', function () {
                if (lastUserQuestion) sendQuestion(lastUserQuestion, true);
            });

            toolbar.querySelectorAll('.cl-ai-msg-feedback').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    toolbar.querySelectorAll('.cl-ai-msg-feedback').forEach(function (b) { b.classList.remove('is-active'); });
                    btn.classList.add('is-active');
                });
            });

            addFollowUpChips();
            scrollToBottom();
        }

        function addErrorMessage(text, retryQuestion) {
            hideWelcome();
            var wrap = document.createElement('div');
            wrap.className = 'cl-ai-msg cl-ai-msg-error cl-fade-in';
            wrap.innerHTML =
                '<div class="cl-ai-msg-bubble cl-ai-msg-bubble-error">' +
                    '<span class="material-symbols-outlined">error</span>' +
                    '<span>' + escapeHtml(text) + '</span>' +
                '</div>';
            if (retryQuestion) {
                var retryBtn = document.createElement('button');
                retryBtn.type = 'button';
                retryBtn.className = 'cl-btn cl-btn-outline cl-btn-sm';
                retryBtn.style.marginTop = '8px';
                retryBtn.textContent = 'تلاش مجدد';
                retryBtn.addEventListener('click', function () { sendQuestion(retryQuestion, true); });
                wrap.appendChild(retryBtn);
            }
            messagesEl.appendChild(wrap);
            scrollToBottom();
        }

        function addTyping() {
            var typing = document.createElement('div');
            typing.className = 'cl-ai-typing';
            typing.id = 'cl-ai-typing-' + Math.random().toString(36).slice(2);
            typing.innerHTML = '<span></span><span></span><span></span>';
            typing.setAttribute('data-typing-marker', '1');
            messagesEl.appendChild(typing);
            scrollToBottom();
            return typing;
        }

        function removeTyping(el) {
            if (el && el.parentNode) el.parentNode.removeChild(el);
        }

        var FOLLOWUPS_BY_TYPE = {
            report: ['توضیح بیشتر بده', 'این یافته چه اهمیتی دارد؟', 'باید به پزشک مراجعه کنم؟', 'روند این مقدار را نشان بده'],
            diet: ['برنامه هفتگی را خلاصه کن', 'آیا می‌توانم یک وعده را حذف کنم؟', 'جایگزین سالم پیشنهاد بده'],
            workout: ['اگر یک روز نتوانم تمرین کنم چه کنم؟', 'حرکت جایگزین برای زانو درد', 'شدت تمرین را کم کن'],
        };

        function addFollowUpChips() {
            var old = messagesEl.querySelector('.cl-ai-followups');
            if (old) old.remove();

            var list = FOLLOWUPS_BY_TYPE[payloadType] || [];
            if (!list.length) return;

            var wrap = document.createElement('div');
            wrap.className = 'cl-ai-followups cl-fade-in';
            list.forEach(function (q) {
                var chip = document.createElement('button');
                chip.type = 'button';
                chip.className = 'cl-prompt-chip';
                chip.textContent = q;
                chip.addEventListener('click', function () { sendQuestion(q); });
                wrap.appendChild(chip);
            });
            messagesEl.appendChild(wrap);
            scrollToBottom();
        }

        async function sendQuestion(question, isRegenerate) {
            question = (question || '').trim();
            if (!question) return;

            if (!isRegenerate) {
                addUserMessage(question);
                conversation.push({ role: 'user', content: question });
            }
            lastUserQuestion = question;

            input.value = '';
            input.disabled = true;
            if (sendBtn) sendBtn.disabled = true;

            var typingEl = addTyping();

            try {
                var body = Object.assign({
                    question: question,
                    history: conversation,
                }, extraPayload());

                var res = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
                    body: JSON.stringify(body),
                });

                var data = await res.json();
                removeTyping(typingEl);

                if (!res.ok) {
                    addErrorMessage(data.error || 'خطایی رخ داد. لطفاً دوباره تلاش کنید.', question);
                } else {
                    addAIMessage(data.answer);
                    conversation.push({ role: 'assistant', content: data.answer });
                }
            } catch (err) {
                removeTyping(typingEl);
                addErrorMessage('ارتباط با سرور برقرار نشد. اتصال اینترنت خود را بررسی کنید.', question);
            } finally {
                input.disabled = false;
                if (sendBtn) sendBtn.disabled = false;
                input.focus();
            }
        }

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            sendQuestion(input.value);
        });

        root.querySelectorAll('.cl-prompt-chip[data-prompt]').forEach(function (chip) {
            chip.addEventListener('click', function () {
                sendQuestion(chip.getAttribute('data-prompt'));
            });
        });

        /* Mobile drawer for the context panel */
        if (drawerToggle && contextPanel) {
            drawerToggle.addEventListener('click', function () {
                contextPanel.classList.add('is-open');
            });
        }
        if (drawerClose && contextPanel) {
            drawerClose.addEventListener('click', function () {
                contextPanel.classList.remove('is-open');
            });
        }

        /* Collapsible medical reference cards (accessible via native <details>) */
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.cl-ai-doctor').forEach(initWorkspace);
    });

})();