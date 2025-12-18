import React, { useState } from 'react';
import Sidebar from './Sidebar';
import MainContent from './MainContent';
import Quiz from './Quiz';
import './StudySystem.css';

export default function StudySystem() {
  const [sessions, setSessions] = useState([
    { id: 1, name: '새 세션 1', date: '2025-01-15' },
    { id: 2, name: '새 세션 2', date: '2025-01-10' }
  ]);
  const [currentSession, setCurrentSession] = useState(1);

  const [activeTab, setActiveTab] = useState('source');
  const [uploadedFiles, setUploadedFiles] = useState([
    { id: 1, name: 'Chapter1.pdf', size: '2.4MB', content: 'Sample content' }
  ]);
  const [summary, setSummary] = useState('');
  const [messages, setMessages] = useState([
    { id: 1, type: 'ai', text: '안녕하세요! 어떤 주제에 대해 질문하고 싶으신가요?' }
  ]);
  const [inputMessage, setInputMessage] = useState('');

  const [quizzes] = useState([
    { id: 1, type: 'multiple', question: '다음 중 올바른 것은?', options: ['선택지 1', '선택지 2', '선택지 3'], answer: 1 },
    { id: 2, type: 'essay', question: '주요 개념을 설명하세요', answer: '모범 답안' }
  ]);
  const [currentQuiz, setCurrentQuiz] = useState(0);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [showAnswer, setShowAnswer] = useState(false);

  const handleNewSession = () => {
    const newSession = { 
      id: Math.max(...sessions.map(s => s.id), 0) + 1, 
      name: `새 세션 ${sessions.length + 1}`, 
      date: new Date().toISOString().split('T')[0] 
    };
    setSessions([...sessions, newSession]);
    setCurrentSession(newSession.id);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const fileId = Math.random();
    const fileSize = (file.size / 1024 / 1024).toFixed(1) + 'MB';
    
    if (file.type === 'application/pdf') {
      try {
        const text = await extractTextFromPDF(file);
        setUploadedFiles(prev => [...prev, { 
          id: fileId, 
          name: file.name, 
          size: fileSize,
          content: text
        }]);
      } catch (error) {
        alert('PDF 읽기에 실패했습니다: ' + error.message);
      }
    } else {
      alert('PDF 파일만 업로드 가능합니다.');
    }
  };

  const extractTextFromPDF = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          const pdfData = event.target.result;
          const text = await getPDFText(pdfData);
          resolve(text);
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = () => reject(new Error('파일 읽기 실패'));
      reader.readAsArrayBuffer(file);
    });
  };

  const getPDFText = (pdfData) => {
    const uint8Array = new Uint8Array(pdfData);
    let text = '';
    for (let i = 0; i < uint8Array.length; i++) {
      const code = uint8Array[i];
      if ((code > 31 && code < 127) || code === 10 || code === 13) {
        text += String.fromCharCode(code);
      }
    }
    return text.substring(0, 2000);
  };

  const handleSendMessage = () => {
    if (inputMessage.trim()) {
      setMessages([...messages, { id: messages.length + 1, type: 'user', text: inputMessage }]);
      setInputMessage('');
      setTimeout(() => {
        setMessages(prev => [...prev, { id: prev.length + 1, type: 'ai', text: 'AI 답변 준비 중입니다...' }]);
      }, 500);
    }
  };

  const handleGenerateSummary = () => {
    const allContent = uploadedFiles.map(f => f.content || '').join('\n\n');
    
    if (!allContent.trim()) {
      alert('PDF 내용이 없습니다.');
      return;
    }
    
    const summary = `📌 학습 내용 요약:\n\n${allContent.substring(0, 500)}...\n\n[자세한 요약은 AI 처리 예정]\n\n📊 파일 통계:\n- 총 파일 수: ${uploadedFiles.length}개\n- 총 내용: ${allContent.length}자`;
    setSummary(summary);
    setActiveTab('summary');
  };

  const handleQuizAnswer = (answer) => {
    setQuizAnswers({ ...quizAnswers, [currentQuiz]: answer });
  };

  const handleDeleteFile = (fileId) => {
    setUploadedFiles(uploadedFiles.filter(f => f.id !== fileId));
  };

  return (
    <div className="study-container">
      <Sidebar 
        sessions={sessions}
        currentSession={currentSession}
        onNewSession={handleNewSession}
        onSelectSession={setCurrentSession}
      />

      <MainContent
        activeTab={activeTab}
        onTabChange={setActiveTab}
        uploadedFiles={uploadedFiles}
        onFileUpload={handleFileUpload}
        onDeleteFile={handleDeleteFile}
        onGenerateSummary={handleGenerateSummary}
        summary={summary}
        messages={messages}
        inputMessage={inputMessage}
        onInputChange={(e) => setInputMessage(e.target.value)}
        onSendMessage={handleSendMessage}
      />

      <Quiz
        quizzes={quizzes}
        currentQuiz={currentQuiz}
        quizAnswers={quizAnswers}
        showAnswer={showAnswer}
        onAnswerChange={handleQuizAnswer}
        onShowAnswer={() => setShowAnswer(!showAnswer)}
        onPrevQuiz={() => setCurrentQuiz(Math.max(0, currentQuiz - 1))}
        onNextQuiz={() => setCurrentQuiz(Math.min(quizzes.length - 1, currentQuiz + 1))}
      />
    </div>
  );
}