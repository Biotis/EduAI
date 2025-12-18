import React from 'react';

export default function SummaryTab({ summary }) {
  return (
    <div className="summary-section">
      <h2>학습 내용 요약</h2>
      {summary ? (
        <div className="summary-box">
          {summary}
        </div>
      ) : (
        <div className="empty-state">
          <p>파일을 업로드하고 요약을 생성해주세요</p>
        </div>
      )}
    </div>
  );
}