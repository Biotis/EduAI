import React from 'react';
import { Plus, Home, BookOpen } from 'lucide-react';

export default function Sidebar({ sessions, currentSession, onNewSession, onSelectSession }) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>StudyAI</h1>
        <p>AI 학습 지원 시스템</p>
      </div>

      <div className="sidebar-new-btn">
        <button onClick={onNewSession} className="new-session-btn">
          <Plus size={18} /> 새로운 채팅
        </button>
      </div>

      <div className="sidebar-sessions">
        <p className="sessions-title">학습 세션</p>
        {sessions.map(session => (
          <button
            key={session.id}
            onClick={() => onSelectSession(session.id)}
            className={`session-item ${currentSession === session.id ? 'active' : ''}`}
          >
            <p className="session-name">{session.name}</p>
            <p className="session-date">{session.date}</p>
          </button>
        ))}
      </div>

      <div className="sidebar-footer">
        <button className="footer-btn">
          <Home size={18} /> <span>홈</span>
        </button>
        <button className="footer-btn">
          <BookOpen size={18} /> <span>학습 기록</span>
        </button>
      </div>
    </div>
  );
}