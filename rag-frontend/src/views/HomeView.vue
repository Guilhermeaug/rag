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
const isLoading = ref(false);
const isUploading = ref(false);
const selectedFile = ref<File | null>(null);
const uploadStatusMessage = ref('');
const fileNameDisplay = ref<string>('');

// --- NOVOS PARÂMETROS PARA CONFIGURAÇÃO DO RAG ---
const selectedSearchType = ref<'similarity' | 'mmr'>('similarity'); // Tipos de busca comuns
const searchK = ref<number>(5); // Valor padrão para 'k'

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
    // Inclui os novos parâmetros do RAG no corpo da requisição
    const requestBody = {
      query: userText,
      search_type: selectedSearchType.value,
      search_k: searchK.value,
    };

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
        throw new Error(responseData.detail || `Erro no upload de ${selectedFile.value.name}: ${response.status}`);
      }
    } else if (responseData.status === "accepted") {
        uploadStatusMessage.value = `Sucesso: ${responseData.message}`;
    } else {
        uploadStatusMessage.value = `Resposta inesperada para ${selectedFile.value.name}: ${JSON.stringify(responseData)}`;
    }

  } catch (error) {
    console.error(`Erro ao fazer upload do arquivo ${selectedFile.value.name}:`, error);
    uploadStatusMessage.value = `Erro ao enviar ${selectedFile.value.name}: ${error instanceof Error ? error.message : 'Falha no upload.'}`;
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

      <!-- NOVA SEÇÃO DE CONFIGURAÇÕES DO RAG -->
      <section class="rag-settings-section">
        <h2>Configurações do Retriever</h2>
        <div class="settings-grid">
          <div class="setting-item">
            <label for="search-type-select">Tipo de Busca:</label>
            <select id="search-type-select" v-model="selectedSearchType" class="settings-select">
              <option value="similarity">Similarity</option>
              <option value="mmr">MMR (Maximal Marginal Relevance)</option>
              <option value="similarity_score_threshold">Similarity Score Threshold</option>
            </select>
          </div>
          <div class="setting-item">
            <label for="search-k-input">Documentos (k):</label>
            <input type="number" id="search-k-input" v-model.number="searchK" min="1" max="20" class="settings-input-number">
          </div>
        </div>
      </section>

      <div class="messages-area" ref="messagesAreaRef">
        <!-- ... (loop de mensagens) ... -->
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
        <!-- ... (formulário de input do chat) ... -->
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
            <svg v-if="!isLoading" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-send"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            <div v-else class="spinner"></div>
          </button>
        </form>
      </footer>

      <section class="upload-section">
        <!-- ... (seção de upload de arquivo) ... -->
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
        <p v-if="uploadStatusMessage" class="upload-status" :class="{'success': uploadStatusMessage.includes('Sucesso'), 'error-message': uploadStatusMessage.includes('Erro:')}">
          {{ uploadStatusMessage }}
        </p>
        <p class="upload-note">Nota: Após o envio, pode levar alguns instantes para que o conteúdo do documento seja totalmente processado e esteja disponível para consulta.</p>
      </section>

    </main>
  </div>
</template>

<style scoped>
/* ... (Seus estilos :root e outros existentes) ... */
:root {
  --font-family-sans-serif: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --page-background-color: #e9ebee; 
  --chat-background-color: #ffffff;
  --header-footer-background: #f8f9fa; 
  --text-primary: #212529;
  --text-secondary: #495057;
  --text-muted: #6c757d;
  
  --user-message-background: #007AFF;
  --user-message-text: #ffffff;
  --llm-message-background: #f0f2f5; 
  --llm-message-text: #212529;
  --thinking-message-color: #495057;
  --error-message-background: #ffebee;
  --error-message-text: #c62828; 
  --success-message-text: #28a745; 

  --input-border-color: #d1d7de; 
  --input-focus-border-color: #86b7fe;
  --input-focus-box-shadow: 0 0 0 0.25rem rgba(0, 122, 255, 0.25);

  --button-primary-color: #007AFF;
  --button-primary-hover-color: #0056b3;
  --button-secondary-color: #6c757d; 
  --button-secondary-hover-color: #545b62; 

  --border-radius-default: 12px; 
  --border-radius-medium: 8px; 
  --border-radius-bubble: 18px; 
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 8px rgba(0,0,0,0.07);
}

.page-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--page-background-color); 
  font-family: var(--font-family-sans-serif);
  padding: 20px;
  box-sizing: border-box;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 40px); 
  max-height: 900px; /* Aumentado para acomodar nova seção */
  width: 100%;
  max-width: 768px;
  background-color: var(--chat-background-color); 
  border-radius: var(--border-radius-default);
  box-shadow: var(--shadow-md);
  overflow: hidden; 
}

.chat-header {
  padding: 16px 24px; 
  background-color: var(--header-footer-background);
  border-bottom: 1px solid var(--input-border-color);
  text-align: center;
  flex-shrink: 0;
}

.chat-header h1 {
  font-size: 1.25rem; 
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

/* --- ESTILOS PARA A NOVA SEÇÃO DE CONFIGURAÇÕES DO RAG --- */
.rag-settings-section {
  padding: 16px 20px;
  background-color: var(--header-footer-background);
  border-bottom: 1px solid var(--input-border-color);
  flex-shrink: 0;
}

.rag-settings-section h2 {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-top: 0;
  margin-bottom: 12px;
  text-align: left;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); /* Layout responsivo */
  gap: 16px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.setting-item label {
  font-size: 0.875rem;
  color: var(--text-muted);
  font-weight: 500;
}

.settings-select,
.settings-input-number {
  padding: 8px 12px;
  border: 1px solid var(--input-border-color);
  border-radius: var(--border-radius-medium);
  font-size: 0.9rem;
  background-color: black;
  color: var(--text-primary);
  outline: none;
  transition: border-color .15s ease-in-out, box-shadow .15s ease-in-out;
}
.settings-select:focus,
.settings-input-number:focus {
  border-color: var(--input-focus-border-color);
  box-shadow: var(--input-focus-box-shadow);
}
.settings-input-number {
  width: 80px; /* Largura fixa para o input de número 'k' */
}


.messages-area {
  flex-grow: 1;
  overflow-y: auto;
  padding: 20px; 
  display: flex;
  flex-direction: column;
  gap: 8px; 
  background-color: var(--chat-background-color); 
}

/* ... (Resto dos seus estilos CSS existentes para mensagens, input, upload, etc.) ... */
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
  margin-bottom: 12px; 
}

.message-wrapper.user {
  align-items: flex-end;
}

.message-wrapper.llm {
  align-items: flex-start;
}

.message-bubble {
  padding: 10px 15px; 
  border-radius: var(--border-radius-bubble);
  max-width: 85%; 
  word-wrap: break-word;
  box-shadow: var(--shadow-sm);
  line-height: 1.5; 
  font-size: 0.95rem; 
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
  margin: 0 0 4px 0; 
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
  font-size: 0.7rem; 
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
  padding: 12px 20px; 
  background-color: var(--header-footer-background); 
  border-top: 1px solid var(--input-border-color);
  flex-shrink: 0;
}

.input-form {
  display: flex;
  align-items: center;
  gap: 10px; 
}

.message-input {
  flex-grow: 1;
  padding: 12px 16px; 
  border: 1px solid var(--input-border-color);
  border-radius: var(--border-radius-medium); 
  font-size: 0.95rem; 
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
  background-color: #e9ecef;
  cursor: not-allowed;
}

.send-button { 
  background-color: var(--button-primary-color);
  color: white; 
  border: none;
  border-radius: 50%; 
  width: 44px; 
  height: 44px; 
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.1s ease;
  flex-shrink: 0; 
}
.send-button svg { 
  stroke: white; 
  width: 20px; 
  height: 20px; 
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
.send-button:disabled svg {
  stroke: #f8f9fa; 
}


.spinner { 
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  width: 20px; 
  height: 20px; 
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.upload-section {
  padding: 16px 20px; 
  border-top: 1px solid var(--input-border-color);
  background-color: var(--header-footer-background); 
  flex-shrink: 0;
}

.upload-section h2 {
  font-size: 1.05rem; 
  font-weight: 600;
  color: var(--text-secondary); 
  margin-top: 0;
  margin-bottom: 12px; 
  text-align: left; 
}

.file-upload-container {
  display: flex;
  gap: 10px; 
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

.file-upload-label { 
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px; 
  font-size: 0.875rem; 
  font-weight: 500;
  stroke: white; 
  background-color: var(--chat-background-color);
  border: 1px solid var(--input-border-color); 
  border-radius: var(--border-radius-medium);
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
  flex-shrink: 0;
}

.file-upload-label:hover:not(.disabled) {
  background-color: #55585a; 
  border-color: #adb5bd;
  color: var(--text-primary);
}
.file-upload-label.disabled {
  background-color: #55585a;
  border-color: var(--input-border-color);
  color: var(--text-muted);
  cursor: not-allowed;
}
.file-upload-label.disabled svg {
  stroke: var(--text-muted);
}
.file-upload-label svg { 
    stroke: var(--button-secondary-color); 
    transition: stroke 0.2s ease;
}
.file-upload-label:hover:not(.disabled) svg {
    stroke: var(--text-primary); 
}


.file-name-display {
  flex-grow: 1;
  font-size: 0.875rem;
  color: var(--text-primary);
  background-color: #55585a;
  padding: 8px 12px;
  border-radius: var(--border-radius-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 100px; 
  border: 1px solid transparent;
}


.upload-button { 
  padding: 8px 16px; 
  background-color: var(--button-primary-color); 
  color: white;
  border: none;
  border-radius: var(--border-radius-medium);
  font-size: 0.875rem; 
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 90px; 
  flex-shrink: 0;
}

.upload-button:hover:not(:disabled) {
  background-color: var(--button-primary-hover-color);
}
.upload-button:disabled {
  background-color: #adb5bd;
  cursor: not-allowed;
}

.button-spinner { 
  border: 3px solid rgba(255, 255, 255, 0.4);
  border-radius: 50%;
  border-top-color: #fff;
  width: 16px; 
  height: 16px; 
  animation: spin 1s ease-in-out infinite;
  display: inline-block;
}

.upload-status {
  margin-top: 10px; 
  font-size: 0.8rem; 
  text-align: center;
  min-height: 1.2em; 
  padding: 4px 0; 
}
.upload-status.success {
  color: var(--success-message-text);
  font-weight: 500;
}
.upload-status.error-message { 
  color: var(--error-message-text);
  font-weight: 500;
}

.upload-note {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-align: center;
    margin-top: 8px;
    padding: 0 10px;
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
  border: 2px solid var(--chat-background-color); 
}
.messages-area::-webkit-scrollbar-thumb:hover {
  background-color: #b3b3b3;
}
</style>
