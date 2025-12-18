import React from 'react';
import { Send } from 'lucide-react';

export default function ChatTab({ messages, inputMessage, onInputChange, onSendMessage }) {
  return (
    <div className="chat-section">
      <div className="messages-container">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.type}`}>
            <div className="message-bubble">
              {msg.text}
            </div>
          </div>
        ))}
      </div>
      <div className="chat-input-area">
        <input
          type="text"
          value={inputMessage}
          onChange={onInputChange}
          onKeyPress={e => e.key === 'Enter' && onSendMessage()}
          placeholder="질문을 입력하세요..."
          className="chat-input"
        />
        <button onClick={onSendMessage} className="send-btn">
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}