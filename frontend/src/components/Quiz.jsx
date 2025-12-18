import React from 'react';
import { Brain } from 'lucide-react';

export default function Quiz({ 
  quizzes, 
  currentQuiz, 
  quizAnswers, 
  showAnswer, 
  onAnswerChange, 
  onShowAnswer, 
  onPrevQuiz, 
  onNextQuiz 
}) {
  const currentQuizItem = quizzes[currentQuiz];

  return (
    <div className="quiz-panel">
      <div className="quiz-header">
        <div className="quiz-title">
          <Brain size={20} />
          <h3>AI 퀴즈</h3>
        </div>
        <p className="quiz-progress">{currentQuiz + 1} / {quizzes.length}</p>
      </div>

      <div className="quiz-content">
        {currentQuizItem && (
          <div>
            <div className="quiz-question">
              <p>{currentQuizItem.question}</p>
            </div>

            {currentQuizItem.type === 'multiple' ? (
              <div className="quiz-options">
                {currentQuizItem.options.map((option, idx) => (
                  <button
                    key={idx}
                    onClick={() => onAnswerChange(idx)}
                    className={`quiz-option ${quizAnswers[currentQuiz] === idx ? 'selected' : ''}`}
                  >
                    <span>{option}</span>
                  </button>
                ))}
              </div>
            ) : (
              <textarea
                placeholder="답변을 입력하세요..."
                className="quiz-textarea"
                value={quizAnswers[currentQuiz] || ''}
                onChange={e => onAnswerChange(e.target.value)}
              />
            )}

            {quizAnswers[currentQuiz] !== undefined && (
              <button
                onClick={onShowAnswer}
                className="check-answer-btn"
              >
                {showAnswer ? '정답 숨기기' : '정답 확인'}
              </button>
            )}

            {showAnswer && (
              <div className="answer-box">
                <p className="answer-label">✓ 정답</p>
                <p className="answer-text">{currentQuizItem.answer}</p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="quiz-nav">
        <button
          onClick={onPrevQuiz}
          disabled={currentQuiz === 0}
          className="nav-btn prev"
        >
          이전
        </button>
        <button
          onClick={onNextQuiz}
          disabled={currentQuiz === quizzes.length - 1}
          className="nav-btn next"
        >
          다음
        </button>
      </div>
    </div>
  );
}