import React from 'react';
import { BookOpen, Trash2 } from 'lucide-react';

export default function SourceTab({ uploadedFiles, onFileUpload, onDeleteFile, onGenerateSummary }) {
  return (
    <div className="source-section">
      <h2>강의 자료 업로드</h2>
      <div className="upload-area">
        <input
          type="file"
          accept=".pdf"
          onChange={onFileUpload}
          className="file-input"
          id="file-upload"
        />
        <label htmlFor="file-upload" className="upload-label">
          <BookOpen size={40} />
          <p>PDF 파일을 드래그하거나 클릭하여 업로드</p>
          <p className="upload-hint">최대 100MB까지 지원</p>
        </label>
      </div>

      <div className="files-section">
        <h3>업로드된 파일 ({uploadedFiles.length}개)</h3>
        <div className="file-list">
          {uploadedFiles.map(file => (
            <div key={file.id} className="file-item">
              <div className="file-info">
                <BookOpen size={20} />
                <div>
                  <p className="file-name">{file.name}</p>
                  <p className="file-size">{file.size}</p>
                </div>
              </div>
              <button 
                onClick={() => onDeleteFile(file.id)}
                className="delete-btn"
              >
                <Trash2 size={18} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {uploadedFiles.length > 0 && (
        <button onClick={onGenerateSummary} className="summary-btn">
          요약 생성하기
        </button>
      )}
    </div>
  );
}