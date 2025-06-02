<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'llm';
  timestamp: Date;
}

const messages = ref<Message[]>([]);
const newMessage = ref('');
let messageIdCounter = 0;
const messagesAreaRef = ref<HTMLElement | null>(null); // Referência para a área de mensagens

const scrollToBottom = () => {
  nextTick(() => { // Garante que o DOM foi atualizado
    const area = messagesAreaRef.value;
    if (area) {
      area.scrollTop = area.scrollHeight;
    }
  });
};

// Observa o array de mensagens e rola para baixo quando novas mensagens são adicionadas
watch(messages, () => {
  scrollToBottom();
}, { deep: true });


const sendMessage = async () => {
  const text = newMessage.value.trim();
  if (text === '') return;

  messages.value.push({
    id: messageIdCounter++,
    text: text,
    sender: 'user',
    timestamp: new Date(),
  });
  newMessage.value = '';

  // Simulação da resposta da LLM
  // Adiciona um spinner ou indicador de "digitando" aqui
  const thinkingMessageId = messageIdCounter++;
  messages.value.push({
    id: thinkingMessageId,
    text: 'LLM está pensando...', // Ou um componente de spinner
    sender: 'llm',
    timestamp: new Date(),
  });
  scrollToBottom(); // Rola para ver a mensagem de "pensando"

  await new Promise(resolve => setTimeout(resolve, 1500)); // Simula o tempo de resposta da rede

  // Remove a mensagem de "pensando"
  const thinkingIndex = messages.value.findIndex(m => m.id === thinkingMessageId);
  if (thinkingIndex !== -1) {
    messages.value.splice(thinkingIndex, 1);
  }

  const llmResponseText = `Esta é uma resposta minimalista e elegante para: "${text}"`;
  messages.value.push({
    id: messageIdCounter++, // Garante ID único para a resposta final
    text: llmResponseText,
    sender: 'llm',
    timestamp: new Date(),
  });
  // O watch já cuidará do scrollToBottom para a mensagem final
};
</script>

<template>
  <div class="page-container">
    <main class="chat-container">
      <header class="chat-header">
        <h1>💬 Chat</h1>
      </header>

      <div class="messages-area" ref="messagesAreaRef">
        <div v-if="messages.length === 0" class="no-messages-placeholder">
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
          <div class="message-bubble" :class="{'thinking': message.text === 'LLM está pensando...'}">
            <p class="message-text">{{ message.text }}</p>
            <span v-if="message.text !== 'LLM está pensando...'" class="timestamp">{{ message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}</span>
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
          />
          <button type="submit" class="send-button" aria-label="Enviar mensagem">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-send"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
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
  --text-primary: #212529; /* Cor de texto mais escura para melhor contraste */
  --text-secondary: #495057;
  --text-muted: #6c757d;
  
  --user-message-background: #007AFF;
  --user-message-text: #ffffff;
  --llm-message-background: #e9ecef; /* Um pouco mais claro que antes */
  --llm-message-text: #212529; /* Texto mais escuro para contraste */
  --thinking-message-color: #495057;


  --input-border-color: #ced4da;
  --button-primary-color: #007AFF;
  --button-hover-color: #0056b3;

  --border-radius-default: 16px; /* Aumentado para um visual mais suave */
  --border-radius-bubble: 20px; /* Aumentado */
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
  padding: 20px; /* Aumentado o padding da página */
  box-sizing: border-box;
}

.chat-container {
  display: flex;
  flex-direction: column;
  /* Ajusta altura considerando o padding da page-container e max-height */
  height: calc(100vh - 40px); /* 20px de padding em cima e 20px em baixo */
  max-height: 750px; /* Aumentada a altura máxima */
  width: 100%;
  max-width: 768px; /* LARGURA AUMENTADA para melhor visualização em desktop */
  background-color: var(--container-background);
  border-radius: var(--border-radius-default);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.chat-header {
  padding: 18px 24px; /* Ajustado padding */
  background-color: var(--header-background);
  border-bottom: 1px solid var(--input-border-color);
  text-align: center;
  flex-shrink: 0; /* Impede que o header encolha */
}

.chat-header h1 {
  font-size: 1.3rem; /* Levemente aumentado */
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.messages-area {
  flex-grow: 1;
  overflow-y: auto;
  padding: 24px; /* Aumentado padding */
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
  padding: 12px 18px; /* Aumentado padding interno */
  border-radius: var(--border-radius-bubble);
  max-width: 85%; 
  word-wrap: break-word;
  box-shadow: var(--shadow-sm);
  line-height: 1.55; /* Melhorado espaçamento entre linhas */
  font-size: 0.98rem; /* Levemente aumentado */
}

.message-bubble.thinking {
  background-color: var(--llm-message-background);
  color: var(--thinking-message-color);
  font-style: italic;
}
.message-bubble.thinking .message-text {
   margin-bottom: 0;
}


.message-text {
  margin: 0 0 5px 0; 
}

.user .message-bubble {
  background-color: var(--user-message-background);
  color: var(--user-message-text);
  border-bottom-right-radius: 8px; 
}

.llm .message-bubble:not(.thinking) { /* Aplica apenas se não for a mensagem de "pensando" */
  background-color: var(--llm-message-background);
  color: var(--llm-message-text);
  border-bottom-left-radius: 8px;
}

.timestamp {
  font-size: 0.75rem; /* Levemente aumentado */
  display: block; 
}

.user .timestamp {
  color: rgba(255, 255, 255, 0.75); 
  text-align: right;
}
.llm .timestamp {
  color: var(--text-muted); /* Usando text-muted para consistência */
  text-align: left;
}


.input-area {
  padding: 16px 24px; /* Aumentado padding */
  background-color: var(--header-background); 
  border-top: 1px solid var(--input-border-color);
  flex-shrink: 0; /* Impede que a área de input encolha */
}

.input-form {
  display: flex;
  align-items: center;
  gap: 12px; /* Aumentado gap */
}

.message-input {
  flex-grow: 1;
  padding: 14px 18px; /* Aumentado padding */
  border: 1px solid var(--input-border-color);
  border-radius: var(--border-radius-default); /* Usando border-radius maior */
  font-size: 1rem; /* Tamanho de fonte padrão */
  background-color: var(--container-background); 
  color: var(--text-primary);
  outline: none; 
}
.message-input:focus {
  border-color: var(--button-primary-color);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.15); /* Ajustado shadow no focus */
}

.send-button {
  background-color: var(--button-primary-color);
  color: white;
  border: none;
  border-radius: 50%; 
  width: 48px; /* Aumentado tamanho do botão */
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.1s ease;
  flex-shrink: 0; 
}

.send-button:hover {
  background-color: var(--button-hover-color);
}
.send-button:active {
  transform: scale(0.95); /* Efeito de clique */
}

.send-button svg {
  width: 22px; 
  height: 22px;
}

.messages-area::-webkit-scrollbar {
  width: 8px; /* Levemente mais larga */
}

.messages-area::-webkit-scrollbar-track {
  background: transparent; 
}

.messages-area::-webkit-scrollbar-thumb {
  background-color: #d1d1d1; /* Cor mais clara para o scrollbar */
  border-radius: 10px;
  border: 2px solid var(--container-background); /* Adiciona borda para parecer mais fino */
}
.messages-area::-webkit-scrollbar-thumb:hover {
  background-color: #b3b3b3;
}
</style>
