<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

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
const isLoading = ref(false); // Para o chat
const isUploading = ref(false); // Para o upload de arquivos
const selectedFile = ref<File | null>(null);
const uploadStatusMessage = ref('');
const fileNameDisplay = ref('');

// Configura 'marked'
marked.setOptions({
  gfm: true,
  breaks: true,
});

const renderMarkdown = (markdownText: string) => {
  if (!markdownText) return '';
  const rawHtml = marked.parse(markdownText) as string;
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
  if (userText === '' || isLoading.value) return;

  messages.value.push({
    id: messageIdCounter++,
    text: userText,
    sender: 'user',
    timestamp: new Date(),
  });
  newMessage.value = '';
  isLoading.value = true;

  const thinkingMessageId = messageIdCounter++;
  messages.value.push({
    id: thinkingMessageId,
    text: 'LLM está processando sua pergunta...',
    sender: 'llm',
    timestamp: new Date(),
  });
  scrollToBottom();

  try {
    const backendUrl = 'http://localhost:8000/query';
    const requestBody = { query: userText };
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });

    const thinkingIndex = messages.value.findIndex(m => m.id === thinkingMessageId);
    if (thinkingIndex !== -1) {
      messages.value.splice(thinkingIndex, 1);
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: `Erro HTTP: ${response.status} ${response.statusText}` }));
      throw new Error(errorData.detail || `Erro ao contatar o backend: ${response.status}`);
    }

    const data = await response.json();
    const llmResponseText = data.answer || "Não foi possível obter uma resposta.";

    messages.value.push({
      id: messageIdCounter++,
      text: llmResponseText,
      sender: 'llm',
      timestamp: new Date(),
    });

  } catch (error) {
    console.error('Erro ao enviar mensagem:', error);
    const thinkingIndex = messages.value.findIndex(m => m.id === thinkingMessageId);
    if (thinkingIndex !== -1) {
      messages.value.splice(thinkingIndex, 1);
    }
    messages.value.push({
      id: messageIdCounter++,
      text: `Erro: ${error instanceof Error ? error.message : 'Falha na comunicação com o servidor.'}`,
      sender: 'llm',
      timestamp: new Date(),
    });
  } finally {
    isLoading.value = false;
  }
};

const handleFileSelected = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    selectedFile.value = target.files[0];
    fileNameDisplay.value = target.files[0].name;
    uploadStatusMessage.value = '';
  } else {
    selectedFile.value = null;
    fileNameDisplay.value = '';
    uploadStatusMessage.value = '';
  }
};

const uploadFile = async () => {
  if (!selectedFile.value) {
    uploadStatusMessage.value = 'Por favor, selecione um arquivo primeiro.';
    return;
  }
  if (isUploading.value) return;

  isUploading.value = true;
  uploadStatusMessage.value = `Enviando ${selectedFile.value.name}...`;

  const formData = new FormData();
  formData.append('file', selectedFile.value);

  try {
    const uploadUrl = 'http://localhost:8000/ingest/upload';
    const response = await fetch(uploadUrl, {
      method: 'POST',
      body: formData,
    });

    const responseData = await response.json();

    if (!response.ok) {
      if (response.status === 202 && responseData.status === "accepted") {
         uploadStatusMessage.value = `Sucesso: ${responseData.message}`;
      } else {
        throw new Error(responseData.detail || `Erro no upload: ${response.status} ${response.statusText}`);
      }
    } else if (responseData.status === "accepted") {
        uploadStatusMessage.value = `Sucesso: ${responseData.message}`;
    } else {
        uploadStatusMessage.value = `Resposta inesperada: ${JSON.stringify(responseData)}`;
    }

  } catch (error) {
    console.error('Erro ao fazer upload do arquivo:', error);
    uploadStatusMessage.value = `Erro: ${error instanceof Error ? error.message : 'Falha no upload.'}`;
  } finally {
    isUploading.value = false;
    selectedFile.value = null; 
    fileNameDisplay.value = '';
    const fileInput = document.getElementById('file-upload-input') as HTMLInputElement;
    if (fileInput) {
        fileInput.value = '';
    }
  }
};

const acceptedFileTypes = ".pdf,.doc,.docx,.txt,.md,.xls,.xlsx";

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
            <svg v-if="!isLoading" xmlns="http://www.w3.org/2000/svg" width="24" height="24" color="white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-send"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            <div v-else class="spinner"></div>
          </button>
        </form>
      </footer>

      <section class="upload-section">
        <h2>Adicionar Documento ao RAG</h2>
        <div class="file-upload-container">
          <label for="file-upload-input" class="file-upload-label" :class="{'disabled': isUploading}">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-upload-cloud"><polyline points="16 16 12 12 8 16"></polyline><line x1="12" y1="12" x2="12" y2="21"></line><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"></path><polyline points="16 16 12 12 8 16"></polyline></svg>
            <span>Escolher Arquivo</span>
          </label>
          <input 
            type="file" 
            @change="handleFileSelected" 
            class="file-input-hidden"
            id="file-upload-input"
            :accept="acceptedFileTypes"
            :disabled="isUploading"
          />
          <span v-if="fileNameDisplay" class="file-name-display">{{ fileNameDisplay }}</span>
          <button @click="uploadFile" class="upload-button" :disabled="!selectedFile || isUploading">
            <span v-if="isUploading" class="button-spinner"></span>
            <span v-else>Enviar</span>
          </button>
        </div>
        <p v-if="uploadStatusMessage" class="upload-status" :class="{'success': uploadStatusMessage.startsWith('Sucesso:'), 'error-message': uploadStatusMessage.startsWith('Erro:')}">
          {{ uploadStatusMessage }}
        </p>
      </section>

    </main>
  </div>
</template>

<style scoped>
:root {
  --font-family-sans-serif: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --page-background-color: #e9ebee; /* Cor de fundo da página um pouco mais escura */
  --chat-background-color: #ffffff;
  --header-footer-background: #f8f9fa; /* Fundo para header, input e upload section */
  --text-primary: #212529;
  --text-secondary: #495057;
  --text-muted: #6c757d;
  
  --user-message-background: #007AFF;
  --user-message-text: #ffffff;
  --llm-message-background: #f0f2f5; /* Fundo da mensagem LLM um pouco mais claro */
  --llm-message-text: #212529;
  --thinking-message-color: #495057;
  --error-message-background: #ffebee;
  --error-message-text: #c62828; 
  --success-message-text: #28a745; 

  --input-border-color: #d1d7de; /* Borda do input um pouco mais suave */
  --input-focus-border-color: #86b7fe;
  --input-focus-box-shadow: 0 0 0 0.25rem rgba(0, 122, 255, 0.25);

  --button-primary-color: #007AFF;
  --button-primary-hover-color: #0056b3;
  --button-secondary-color: #6c757d;
  --button-secondary-hover-color: #545b62; /* Escurecido um pouco */

  --border-radius-default: 12px; /* Reduzido para um visual mais contido */
  --border-radius-medium: 8px; 
  --border-radius-bubble: 18px; /* Mantido para bolhas */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 8px rgba(0,0,0,0.07);
}

.page-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--page-background-color); /* Aplicando nova cor de fundo da página */
  font-family: var(--font-family-sans-serif);
  padding: 20px;
  box-sizing: border-box;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 40px); 
  max-height: 850px; 
  width: 100%;
  max-width: 768px;
  background-color: var(--chat-background-color); /* Fundo do chat */
  border-radius: var(--border-radius-default);
  box-shadow: var(--shadow-md);
  overflow: hidden; 
}

.chat-header {
  padding: 16px 24px; /* Ajustado padding */
  background-color: var(--header-footer-background);
  border-bottom: 1px solid var(--input-border-color);
  text-align: center;
  flex-shrink: 0;
}

.chat-header h1 {
  font-size: 1.25rem; /* Ajustado */
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.messages-area {
  flex-grow: 1;
  overflow-y: auto;
  padding: 20px; /* Ajustado padding */
  display: flex;
  flex-direction: column;
  gap: 8px; 
  background-color: var(--chat-background-color); /* Garante fundo branco aqui também */
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
  margin-bottom: 12px; /* Ajustado */
}

.message-wrapper.user {
  align-items: flex-end;
}

.message-wrapper.llm {
  align-items: flex-start;
}

.message-bubble {
  padding: 10px 15px; /* Ajustado */
  border-radius: var(--border-radius-bubble);
  max-width: 85%; 
  word-wrap: break-word;
  box-shadow: var(--shadow-sm);
  line-height: 1.5; /* Ajustado */
  font-size: 0.95rem; /* Ajustado */
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
  margin: 0 0 4px 0; /* Ajustado */
  white-space: pre-wrap;
}

.markdown-content {
  white-space: normal;
}
.markdown-content p:first-child {
  margin-top: 0;
}
.markdown-content p:last-child {
  margin-bottom: 0;
}

.user .message-bubble {
  background-color: var(--user-message-background);
  color: var(--user-message-text);
  border-bottom-right-radius: var(--border-radius-medium); 
}

.llm .message-bubble:not(.thinking):not(.error) {
  background-color: var(--llm-message-background);
  color: var(--llm-message-text);
  border-bottom-left-radius: var(--border-radius-medium);
}

.timestamp {
  font-size: 0.7rem; /* Ajustado */
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
  padding: 12px 20px; /* Ajustado padding */
  background-color: var(--header-footer-background); 
  border-top: 1px solid var(--input-border-color);
  flex-shrink: 0;
}

.input-form {
  display: flex;
  align-items: center;
  gap: 10px; /* Ajustado */
}

.message-input {
  flex-grow: 1;
  padding: 12px 16px; /* Ajustado */
  border: 1px solid var(--input-border-color);
  border-radius: var(--border-radius-medium); /* Usando medium */
  font-size: 0.95rem; /* Ajustado */
  background-color: var(--chat-background-color); 
  color: var(--text-primary);
  outline: none; 
  transition: border-color .15s ease-in-out, box-shadow .15s ease-in-out;
}
.message-input:focus {
  border-color: var(--input-focus-border-color);
  box-shadow: var(--input-focus-box-shadow);
}
.message-input:disabled {
  /*background-color: #e9ecef;*/
  cursor: not-allowed;
}

.send-button {
  background-color: var(--button-primary-color);
  color: white;
  border: none;
  border-radius: 50%; 
  width: 44px; /* Ajustado */
  height: 44px; /* Ajustado */
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.1s ease;
  flex-shrink: 0; 
}

.send-button:hover:not(:disabled) {
  background-color: var(--button-primary-hover-color);
}
.send-button:active:not(:disabled) {
  transform: scale(0.95);
}
.send-button:disabled {
  background-color: #adb5bd;
  cursor: not-allowed;
}

.send-button svg {
  width: 20px; /* Ajustado */
  height: 20px; /* Ajustado */
}

.spinner { 
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  width: 20px; /* Ajustado */
  height: 20px; /* Ajustado */
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* --- ESTILOS REFINADOS PARA A SEÇÃO DE UPLOAD --- */
.upload-section {
  padding: 16px 20px; /* Ajustado padding */
  border-top: 1px solid var(--input-border-color);
  background-color: var(--header-footer-background); /* Mesmo fundo do header e input chat */
  flex-shrink: 0;
}

.upload-section h2 {
  font-size: 1.05rem; /* Ajustado */
  font-weight: 600;
  color: var(--text-secondary); /* Cor mais suave para o título da seção */
  margin-top: 0;
  margin-bottom: 12px; /* Ajustado */
  text-align: left; /* Alinhado à esquerda para um visual mais de formulário */
}

.file-upload-container {
  display: flex;
  gap: 10px; /* Ajustado */
  align-items: center;
}

.file-input-hidden {
  width: 0.1px;
  height: 0.1px;
  opacity: 0;
  overflow: hidden;
  position: absolute;
  z-index: -1;
}

.file-upload-label { /* Botão "Escolher Arquivo" */
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px; /* Ajustado */
  font-size: 0.875rem; /* Ajustado */
  font-weight: 500;
  color: var(--button-secondary-color); /* Usando cor secundária para o botão de escolher */
  stroke: white;
  background-color: var(--chat-background-color);
  border: 1px solid var(--input-border-color); /* Borda sutil */
  border-radius: var(--border-radius-medium);
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
  flex-shrink: 0;
}

.file-upload-label:hover:not(.disabled) {
  background-color: #6c6e6f; /* Leve hover */
  border-color: #adb5bd;
  color: var(--text-primary);
}
.file-upload-label.disabled {
  background-color: #f8f9fa;
  border-color: var(--input-border-color);
  color: var(--text-muted);
  cursor: not-allowed;
}
.file-upload-label.disabled svg {
  stroke: var(--text-muted);
}
.file-upload-label svg {
    stroke: var(--button-secondary-color); /* Cor do ícone */
    transition: stroke 0.2s ease;
}
.file-upload-label:hover:not(.disabled) svg {
    stroke: var(--text-primary);
}


.file-name-display {
  flex-grow: 1;
  font-size: 0.875rem; /* Ajustado */
  color: var(--text-primary); /* Cor primária para o nome do arquivo */
  background-color: #292e35; /* Fundo sutil para destacar o nome */
  padding: 8px 12px; /* Ajustado */
  border-radius: var(--border-radius-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 100px; 
  border: 1px solid transparent; /* Para manter o alinhamento mesmo sem borda visível */
}


.upload-button { /* Botão "Enviar" (para upload) */
  padding: 8px 16px; /* Ajustado */
  background-color: var(--button-primary-color); /* Usando cor primária para o botão de ação */
  color: white;
  border: none;
  border-radius: var(--border-radius-medium);
  font-size: 0.875rem; /* Ajustado */
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 90px; /* Ajustado */
  flex-shrink: 0;
}

.upload-button:hover:not(:disabled) {
  background-color: var(--button-primary-hover-color);
}
.upload-button:disabled {
  background-color: #9ca2a8;
  cursor: not-allowed;
}

.button-spinner { 
  border: 3px solid rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  border-top-color: #fff;
  width: 16px; /* Ajustado */
  height: 16px; /* Ajustado */
  animation: spin 1s ease-in-out infinite;
  display: inline-block;
}

.upload-status {
  margin-top: 10px; /* Ajustado */
  font-size: 0.8rem; /* Ajustado */
  text-align: center;
  min-height: 1.2em; 
  padding: 4px 0; /* Pequeno padding vertical */
}
.upload-status.success {
  color: var(--success-message-text);
  font-weight: 500;
}
.upload-status.error-message { 
  color: var(--error-message-text);
  font-weight: 500;
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
  border: 2px solid var(--chat-background-color); /* Usa o fundo do chat para a borda */
}
.messages-area::-webkit-scrollbar-thumb:hover {
  background-color: #b3b3b3;
}
</style>
