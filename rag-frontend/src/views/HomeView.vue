<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';
import { marked } from 'marked'; // Importa o 'marked'
import DOMPurify from 'dompurify'; // Importa o DOMPurify

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'llm';
  timestamp: Date;
}

const messages = ref<Message[]>([]);
const newMessage = ref('');
let messageIdCounter = 0;
const messagesAreaRef = ref<HTMLElement | null>(null);
const isLoading = ref(false); // Novo estado para controlar o carregamento

// Configurar 'marked' (opcional, mas recomendado para GFM e quebras de linha)
marked.setOptions({
  gfm: true, // Habilita GitHub Flavored Markdown (GFM)
  breaks: true, // Converte quebras de linha GFM (um único Enter) em <br>
  // A opção 'sanitize' foi removida do marked. Usaremos DOMPurify.
});

// Função para renderizar Markdown para HTML seguro
const renderMarkdown = (markdownText: string) => {
  if (!markdownText) return '';
  // 1. Converte Markdown para HTML usando marked
  const rawHtml = marked.parse(markdownText) as string;
  // 2. Sanitiza o HTML gerado para prevenir XSS
  const cleanHtml = DOMPurify.sanitize(rawHtml);
  return cleanHtml;
};

const scrollToBottom = () => {
  nextTick(() => {
    const area = messagesAreaRef.value;
    if (area) {
      area.scrollTop = area.scrollHeight;
    }
  });
};

watch(messages, () => {
  scrollToBottom();
}, { deep: true });

const sendMessage = async () => {
  const userText = newMessage.value.trim();
  if (userText === '') return;

  // Adiciona a mensagem do usuário à UI
  messages.value.push({
    id: messageIdCounter++,
    text: userText,
    sender: 'user',
    timestamp: new Date(),
  });
  newMessage.value = ''; // Limpa o input

  isLoading.value = true; // Ativa o indicador de carregamento

  // Adiciona mensagem de "pensando"
  const thinkingMessageId = messageIdCounter++;
  messages.value.push({
    id: thinkingMessageId,
    text: 'LLM está processando sua pergunta...',
    sender: 'llm',
    timestamp: new Date(),
  });
  scrollToBottom();

  try {
    // Define a URL do backend
    const backendUrl = 'http://localhost:8000/query'; // Certifique-se que esta é a URL correta

    // Monta o corpo da requisição
    const requestBody = {
      query: userText,
    };

    // Faz a chamada fetch para o backend
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Adicione outros cabeçalhos aqui se necessário (ex: Authorization)
      },
      body: JSON.stringify(requestBody),
    });

    // Remove a mensagem de "pensando"
    const thinkingIndex = messages.value.findIndex(m => m.id === thinkingMessageId);
    if (thinkingIndex !== -1) {
      messages.value.splice(thinkingIndex, 1);
    }

    if (!response.ok) {
      // Se a resposta não for OK (ex: 4xx, 5xx), trata como erro
      const errorData = await response.json().catch(() => ({ detail: `Erro HTTP: ${response.status} ${response.statusText}` }));
      throw new Error(errorData.detail || `Erro ao contatar o backend: ${response.status}`);
    }

    // Extrai os dados da resposta JSON
    const data = await response.json();

    // Adiciona a resposta da LLM à UI
    // Assumindo que a resposta está em data.results
    const llmResponseText = data.answer || "Não foi possível obter uma resposta.";
    messages.value.push({
      id: messageIdCounter++,
      text: llmResponseText,
      sender: 'llm',
      timestamp: new Date(),
    });

  } catch (error) {
    console.error('Erro ao enviar mensagem:', error);
    // Remove a mensagem de "pensando" em caso de erro também
    const thinkingIndex = messages.value.findIndex(m => m.id === thinkingMessageId);
    if (thinkingIndex !== -1) {
      messages.value.splice(thinkingIndex, 1);
    }
    // Adiciona uma mensagem de erro à UI
    messages.value.push({
      id: messageIdCounter++,
      text: `Erro: ${error instanceof Error ? error.message : 'Falha na comunicação com o servidor.'}`,
      sender: 'llm', // Pode ser 'system' ou 'llm' com estilo de erro
      timestamp: new Date(),
    });
  } finally {
    isLoading.value = false; // Desativa o indicador de carregamento
    // O watch já cuidará do scrollToBottom
  }
};
</script>

<template>
  <div class="page-container">
    <main class="chat-container">
      <header class="chat-header">
        <h1>💬 Chat com RAG-LLM</h1>
      </header>

      <div class="messages-area" ref="messagesAreaRef">
        <div v-if="messages.length === 0 && !isLoading" class="no-messages-placeholder">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" class="feather feather-message-square"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          <p>Comece uma conversa!</p>
          <span>Envie sua primeira mensagem abaixo.</span>
        </div>

        <div
          v-for="message in messages"
          :key="message.id"
          class="message-wrapper"
          :class="{ 'user': message.sender === 'user', 'llm': message.sender === 'llm' }"
        >
          <div class="message-bubble" :class="{'thinking': message.text === 'LLM está processando sua pergunta...', 'error': message.sender === 'llm' && message.text.startsWith('Erro:')}">
            
            <div 
              v-if="message.sender === 'llm' && message.text !== 'LLM está processando sua pergunta...' && !message.text.startsWith('Erro:')" 
              class="message-text markdown-content" 
              v-html="renderMarkdown(message.text)">
            </div>
            <p v-else class="message-text">{{ message.text }}</p>
            <span v-if="message.text !== 'LLM está processando sua pergunta...'" class="timestamp">
              {{ message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
            </span>
          </div>
        </div>
      </div>

      <footer class="input-area">
        <form @submit.prevent="sendMessage" class="input-form">
          <input
            type="text"
            v-model="newMessage"
            class="message-input"
            placeholder="Digite sua mensagem..."
            aria-label="Mensagem"
            :disabled="isLoading"
          />
          <button type="submit" class="send-button" aria-label="Enviar mensagem" :disabled="isLoading">
            <svg v-if="!isLoading" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-send"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            <div v-else class="spinner"></div>
          </button>
        </form>
      </footer>
    </main>
  </div>
</template>

<style scoped>
/* Estilos Globais para o Componente */
:root {
  --font-family-sans-serif: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --background-color: #f4f7f6;
  --container-background: #ffffff;
  --header-background: #ffffff;
  --text-primary: #212529;
  --text-secondary: #495057;
  --text-muted: #6c757d;
  
  --user-message-background: #007AFF;
  --user-message-text: #ffffff;
  --llm-message-background: #e9ecef;
  --llm-message-text: #212529;
  --thinking-message-color: #495057;
  --error-message-background: #ffebee; /* Fundo vermelho claro para erros */
  --error-message-text: #c62828; /* Texto vermelho escuro para erros */


  --input-border-color: #ced4da;
  --button-primary-color: #007AFF;
  --button-hover-color: #0056b3;

  --border-radius-default: 16px;
  --border-radius-bubble: 20px;
  --shadow-sm: 0 2px 4px rgba(0,0,0,0.04);
  --shadow-md: 0 6px 12px rgba(0,0,0,0.07);
}

.page-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--background-color);
  font-family: var(--font-family-sans-serif);
  padding: 20px;
  box-sizing: border-box;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 40px); 
  max-height: 750px;
  width: 100%;
  max-width: 768px;
  background-color: var(--container-background);
  border-radius: var(--border-radius-default);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.chat-header {
  padding: 18px 24px;
  background-color: var(--header-background);
  border-bottom: 1px solid var(--input-border-color);
  text-align: center;
  flex-shrink: 0;
}

.chat-header h1 {
  font-size: 1.3rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.messages-area {
  flex-grow: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px; 
}

.no-messages-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--text-muted);
}
.no-messages-placeholder svg {
  margin-bottom: 16px;
  color: #adb5bd; 
}
.no-messages-placeholder p {
  font-size: 1.1rem;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--text-secondary);
}
.no-messages-placeholder span {
  font-size: 0.9rem;
}


.message-wrapper {
  display: flex;
  flex-direction: column;
  margin-bottom: 14px; 
}

.message-wrapper.user {
  align-items: flex-end;
}

.message-wrapper.llm {
  align-items: flex-start;
}

.message-bubble {
  padding: 12px 18px;
  border-radius: var(--border-radius-bubble);
  max-width: 85%; 
  word-wrap: break-word;
  box-shadow: var(--shadow-sm);
  line-height: 1.55;
  font-size: 0.98rem;
}

.message-bubble.thinking {
  background-color: var(--llm-message-background);
  color: var(--thinking-message-color);
  font-style: italic;
}
.message-bubble.thinking .message-text {
   margin-bottom: 0;
}

.message-bubble.error {
  background-color: var(--error-message-background);
  color: var(--error-message-text);
  border: 1px solid var(--error-message-text);
}


.message-text {
  margin: 0 0 5px 0; 
}

.user .message-bubble {
  background-color: var(--user-message-background);
  color: var(--user-message-text);
  border-bottom-right-radius: 8px; 
}

.llm .message-bubble:not(.thinking):not(.error) {
  background-color: var(--llm-message-background);
  color: var(--llm-message-text);
  border-bottom-left-radius: 8px;
}

.timestamp {
  font-size: 0.75rem;
  display: block; 
}

.user .timestamp {
  color: rgba(255, 255, 255, 0.75); 
  text-align: right;
}
.llm .timestamp {
  color: var(--text-muted);
  text-align: left;
}


.input-area {
  padding: 16px 24px;
  background-color: var(--header-background); 
  border-top: 1px solid var(--input-border-color);
  flex-shrink: 0;
}

.input-form {
  display: flex;
  align-items: center;
  gap: 12px;
}

.message-input {
  flex-grow: 1;
  padding: 14px 18px;
  border: 1px solid var(--input-border-color);
  border-radius: var(--border-radius-default);
  font-size: 1rem;
  background-color: var(--container-background); 
  color: var(--text-primary);
  outline: none; 
}
.message-input:focus {
  border-color: var(--button-primary-color);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.15);
}
.message-input:disabled {
  background-color: #e9ecef; /* Indica que está desabilitado */
  cursor: not-allowed;
}


.send-button {
  background-color: var(--button-primary-color);
  color: white;
  border: none;
  border-radius: 50%; 
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.1s ease;
  flex-shrink: 0; 
}

.send-button:hover:not(:disabled) {
  background-color: var(--button-hover-color);
}
.send-button:active:not(:disabled) {
  transform: scale(0.95);
}
.send-button:disabled {
  background-color: #adb5bd; /* Cor para botão desabilitado */
  cursor: not-allowed;
}

.send-button svg {
  width: 22px; 
  height: 22px;
}

/* Spinner simples */
.spinner {
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  width: 22px;
  height: 22px;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}


.messages-area::-webkit-scrollbar {
  width: 8px;
}
.messages-area::-webkit-scrollbar-track {
  background: transparent; 
}
.messages-area::-webkit-scrollbar-thumb {
  background-color: #d1d1d1;
  border-radius: 10px;
  border: 2px solid var(--container-background);
}
.messages-area::-webkit-scrollbar-thumb:hover {
  background-color: #b3b3b3;
}
</style>
