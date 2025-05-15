// 一次性返回全部数据的AI请求------------------------------------------------------------------------------
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        const chatMessages = document.querySelector('.chat-messages');

        // 添加消息到聊天窗口
        function addMessage(content, isUser = true) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('chat-message', isUser ? 'from-user' : 'from-ai');
            messageDiv.textContent = content;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // 处理用户输入
        async function handleSend() {
            const userInput = chatInput.value.trim();
            if (!userInput) return;

            // 清空输入框
            chatInput.value = '';
            addMessage(userInput, true);

            try {
                // 显示加载状态
                sendButton.disabled = true;
                sendButton.innerHTML = '发送中...';

                // 模拟API请求
                const response = await fetch('/api/chatAll', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        messages: [{ role: "user", content: userInput }]
                    })
                });

                const data = await response.json();
                addMessage(data.choices[0].message.reasoning_content, false);
            } catch (error) {
                addMessage("⚠️ 请求失败，请检查网络连接后重试", false);
            } finally {
                sendButton.disabled = false;
                sendButton.innerHTML = '发送 <svg...></svg>';
            }
        }

        // 事件监听
        sendButton.addEventListener('click', handleSend);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        });
// 不断的返回数据的AI请求 流式------------------------------------------------------------------------------

 // 流式请求核心实现
    const streamSendButton = document.getElementById('stream-send-button');
    let isStreaming = false;
    let controller = null;

    // 增强的消息添加函数
    function addMessage(content, isUser = true, isStream = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', isUser ? 'from-user' : 'from-ai');

        if (isStream) {
            messageDiv.id = `stream-${Date.now()}`;
            messageDiv.innerHTML = '<span class="stream-cursor">█</span>';
        } else {
            messageDiv.textContent = content;
        }

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageDiv;
    }

    // 流式请求处理
    async function handleStreamSend() {
        if (isStreaming) {
            controller?.abort();
            return;
        }

        const userInput = chatInput.value.trim();
        if (!userInput) return;

        // 创建消息容器
        chatInput.value = '';
        addMessage(userInput, true);
        const aiMessage = addMessage('', false, true);

        try {
            isStreaming = true;
            updateStreamButton(true);

            controller = new AbortController();
            const response = await fetch('/api/chatStream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages: [{ content: userInput }] }),
                signal: controller.signal
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            if (!response.body) throw new Error('No response body');

            await processStream(response.body, aiMessage);
        } catch (error) {
            if (error.name !== 'AbortError') {
                aiMessage.innerHTML = `<span class="error">⚠️ ${error.message}</span>`;
            }
        } finally {
            isStreaming = false;
            controller = null;
            updateStreamButton(false);
        }
    }

    // 流数据处理
    async function processStream(stream, container) {
        const decoder = new TextDecoder();
        const reader = stream.getReader();
        let buffer = '';
        let content = '';

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split('\n\n');
                buffer = events.pop() || '';

                for (const event of events) {
                    if (!event.startsWith('data:')) continue;

                    try {
                        const data = JSON.parse(event.slice(5).trim());
                        if (data.error) throw new Error(data.error);
                        if (data.content) {
                            content += data.content;
                            container.innerHTML = content + '<span class="stream-cursor">█</span>';
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    } catch (e) {
                        console.error('解析错误:', e);
                    }
                }
            }
        } finally {
            // 移除光标
            container.innerHTML = content;
            reader.releaseLock();
        }
    }

    // 按钮状态管理
    function updateStreamButton(flag) {
        const streamSendButton = document.getElementById('stream-send-button');
        streamSendButton.disabled = flag;
        const spanElement = streamSendButton.querySelector('span');
        spanElement.textContent = flag ? '停止生成' : '流式发送';
    }


    // 事件绑定
    streamSendButton.addEventListener('click', handleStreamSend);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey && !isStreaming) {
            e.preventDefault();
            handleStreamSend();
        }
    });