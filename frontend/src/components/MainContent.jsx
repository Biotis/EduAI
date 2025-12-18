import React from 'react';
import { BookOpen, CheckCircle, MessageSquare } from 'lucide-react';
import SourceTab from './tabs/SourceTab';
import SummaryTab from './tabs/SummaryTab';
import ChatTab from './tabs/ChatTab';

export default function MainContent({
  activeTab,
  onTabChange,
  uploadedFiles,
  onFileUpload,
  onDeleteFile,
  onGenerateSummary,
  summary,
  messages,
  inputMessage,
  onInputChange,
  onSendMessage
}) {
  return (
    <div className="main-content">
      <div className="tabs">
        <button
          onClick={() => onTabChange('source')}
          className={`tab ${activeTab === 'source' ? 'active' : ''}`}
        >
          <BookOpen size={18} /> 정보 제공 출처
        </button>
        <button
          onClick={() => onTabChange('summary')}
          className={`tab ${activeTab === 'summary' ? 'active' : ''}`}
        >
          <CheckCircle size={18} /> 정보 요약
        </button>
        <button
          onClick={() => onTabChange('chat')}
          className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
        >
          <MessageSquare size={18} /> AI 질문
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'source' && (
          <SourceTab 
            uploadedFiles={uploadedFiles}
            onFileUpload={onFileUpload}
            onDeleteFile={onDeleteFile}
            onGenerateSummary={onGenerateSummary}
          />
        )}
        {activeTab === 'summary' && (
          <SummaryTab summary={summary} />
        )}
        {activeTab === 'chat' && (
          <ChatTab 
            messages={messages}
            inputMessage={inputMessage}
            onInputChange={onInputChange}
            onSendMessage={onSendMessage}
          />
        )}
      </div>
    </div>
  );
}