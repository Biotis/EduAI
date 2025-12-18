import React, { useState, useRef, useEffect } from 'react';
import './App.css';

function App() {
  // --- 상태 관리 ---
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [documents, setDocuments] = useState([]); 
  const [currentDocId, setCurrentDocId] = useState(null);
  const [activeTab, setActiveTab] = useState("mcq");
  
  // 업로드 옵션
  const [audience, setAudience] = useState("novice");
  const [purpose, setPurpose] = useState("understanding");

  // 채팅
  const [chatInput, setChatInput] = useState("");
  const chatEndRef = useRef(null);

  // 현재 문서
  const activeDoc = documents.find(d => d.doc_id === currentDocId);

  // 스크롤 자동 이동
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeDoc?.chatHistory]);

  // --- [수정됨] 중요도 배지 변환 함수 (긴 문장 -> 짧은 단어) ---
  const renderImportanceBadge = (rawImportance) => {
    const text = (rawImportance || "").toString().toLowerCase();
    
    // 기본값 (Low)
    let label = "Low";
    let style = "bg-slate-100 text-slate-500 border-slate-200";

    // 1. High (매우 중요, 핵심)
    if (text.includes("매우") || text.includes("high") || text.includes("핵심") || text.includes("most")) {
      label = "High";
      style = "bg-rose-50 text-rose-600 border border-rose-100";
    }
    // 2. Mid (중요, 필수)
    else if (text.includes("중요") || text.includes("mid") || text.includes("필수") || text.includes("important")) {
      label = "Mid";
      style = "bg-indigo-50 text-indigo-600 border border-indigo-100";
    }

    return (
      <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold shadow-sm border ${style}`}>
        {label}
      </span>
    );
  };

  // --- 핸들러 ---
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return alert("파일을 선택해주세요.");
    setUploading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("audience", audience);
    formData.append("purpose", purpose);

    try {
      const response = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("업로드 실패");
      const result = await response.json();
      
      const newDoc = {
        ...result,
        name: file.name,
        audience, 
        purpose,
        chatHistory: [
          { role: "assistant", text: `반갑습니다! '${file.name}' 분석이 완료되었습니다. 궁금한 점이 있으신가요?` }
        ]
      };

      setDocuments(prev => [...prev, newDoc]);
      setCurrentDocId(result.doc_id);
      setFile(null);

    } catch (error) {
      console.error(error);
      alert("서버 연결에 실패했습니다. 백엔드가 실행 중인지 확인해주세요.");
    } finally {
      setUploading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !activeDoc) return;

    const userMsg = chatInput;
    const targetDocId = activeDoc.doc_id;

    setChatInput("");

    setDocuments(prev => prev.map(doc => 
      doc.doc_id === targetDocId 
        ? { ...doc, chatHistory: [...doc.chatHistory, { role: "user", text: userMsg }] }
        : doc
    ));

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ docId: targetDocId, message: userMsg })
      });
      const result = await response.json();

      setDocuments(prev => prev.map(doc => 
        doc.doc_id === targetDocId 
          ? { ...doc, chatHistory: [...doc.chatHistory, { role: "assistant", text: result.answer }] }
          : doc
      ));
    } catch (error) {
      setDocuments(prev => prev.map(doc => 
        doc.doc_id === targetDocId 
          ? { ...doc, chatHistory: [...doc.chatHistory, { role: "assistant", text: "오류가 발생했습니다. 잠시 후 다시 시도해주세요." }] }
          : doc
      ));
    }
  };

  // --- UI Components ---

  const SidebarItem = ({ icon, label, subLabel, active, onClick }) => (
    <div 
      onClick={onClick}
      className={`group flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all duration-200 ${
        active 
          ? "bg-brand-600 shadow-glow text-white" 
          : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
      }`}
    >
      <div className={`p-2 rounded-lg ${active ? "bg-white/20" : "bg-slate-800 group-hover:bg-slate-700"}`}>
        <span className="material-symbols-rounded text-lg">{icon}</span>
      </div>
      <div className="overflow-hidden">
        <p className={`text-sm font-semibold truncate ${active ? "text-white" : "text-slate-300 group-hover:text-white"}`}>
          {label}
        </p>
        {subLabel && <p className={`text-[11px] truncate ${active ? "text-brand-100" : "text-slate-500"}`}>{subLabel}</p>}
      </div>
    </div>
  );

  return (
    <div className="flex h-screen w-full bg-[#f8fafc] text-slate-800 font-sans overflow-hidden">
      
      {/* 1. 사이드바 */}
      <aside className="w-72 bg-slate-900 flex flex-col shadow-2xl z-20 shrink-0">
        <div className="p-6 pb-2">
          <div className="flex items-center gap-3 mb-8 cursor-pointer" onClick={() => setCurrentDocId(null)}>
            <div className="w-10 h-10 bg-brand-500 rounded-xl flex items-center justify-center shadow-lg shadow-brand-500/30">
              <span className="material-symbols-rounded text-white text-2xl">school</span>
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">EduAI</h1>
          </div>
          
          <button 
            onClick={() => setCurrentDocId(null)}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white py-3 rounded-xl font-semibold text-sm transition-all shadow-lg shadow-brand-500/20 active:scale-[0.98]"
          >
            <span className="material-symbols-rounded">add</span>
            새 학습 자료 추가
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
          <p className="px-2 text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">My Library</p>
          {documents.map((doc) => (
            <SidebarItem 
              key={doc.doc_id}
              active={currentDocId === doc.doc_id}
              onClick={() => setCurrentDocId(doc.doc_id)}
              icon="description"
              label={doc.name}
              subLabel={`${doc.audience === 'novice' ? '입문' : '심화'} · ${doc.purpose === 'exam' ? '시험' : '이해'}`}
            />
          ))}
          {documents.length === 0 && (
            <div className="text-center py-10 opacity-30">
               <span className="material-symbols-rounded text-4xl mb-2">folder_open</span>
               <p className="text-xs">등록된 문서가 없습니다.</p>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 p-2">
             <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 text-xs font-bold">ME</div>
             <div>
               <p className="text-xs font-bold text-slate-200">User Account</p>
               <p className="text-[10px] text-slate-500">Premium Plan</p>
             </div>
          </div>
        </div>
      </aside>

      {/* 2. 메인 콘텐츠 */}
      <main className="flex-1 flex overflow-hidden relative">
        <div className="flex-1 overflow-y-auto bg-[#f8fafc] scroll-smooth">
          {!activeDoc ? (
            // [업로드 화면]
            <div className="min-h-full flex flex-col items-center justify-center p-8 max-w-2xl mx-auto animate-[fadeIn_0.5s_ease-out]">
              <div className="text-center mb-10">
                <h2 className="text-3xl font-bold text-slate-900 mb-3 tracking-tight">어떤 자료를 공부할까요?</h2>
                <p className="text-slate-500 text-lg">AI가 문서를 분석하여 완벽한 학습 노트를 만들어드립니다.</p>
              </div>

              <div className="w-full bg-white rounded-3xl shadow-soft p-1 border border-slate-100">
                <div className="p-8">
                  <label className={`group relative flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-300 ${file ? "border-brand-500 bg-brand-50/50" : "border-slate-200 hover:border-brand-300 hover:bg-slate-50"}`}>
                    <input type="file" onChange={handleFileChange} accept=".pdf,.ppt,.pptx" className="hidden" />
                    <div className="w-16 h-16 bg-brand-50 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                      <span className={`material-symbols-rounded text-3xl ${file ? "text-brand-600" : "text-brand-400"}`}>
                        {file ? "check_circle" : "cloud_upload"}
                      </span>
                    </div>
                    <p className="text-lg font-bold text-slate-700">
                      {file ? file.name : "여기를 클릭해 파일을 올려주세요"}
                    </p>
                    <p className="text-sm text-slate-400 mt-2">PDF, PPTX (최대 50MB)</p>
                  </label>

                  <div className="mt-8 grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-3">학습 수준</label>
                      <div className="flex gap-2">
                        {['novice', 'intermediate'].map((level) => (
                          <button
                            key={level}
                            onClick={() => setAudience(level)}
                            className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all border ${
                              audience === level 
                                ? "bg-brand-50 border-brand-200 text-brand-700 shadow-sm" 
                                : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50"
                            }`}
                          >
                            {level === 'novice' ? '초심자' : '숙련자'}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-3">학습 목적</label>
                      <div className="flex gap-2">
                        {['understanding', 'exam'].map((p) => (
                          <button
                            key={p}
                            onClick={() => setPurpose(p)}
                            className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all border ${
                              purpose === p
                                ? "bg-brand-50 border-brand-200 text-brand-700 shadow-sm" 
                                : "bg-white border-slate-200 text-slate-500 hover:bg-slate-50"
                            }`}
                          >
                            {p === 'understanding' ? '이해' : '시험'}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <button 
                    onClick={handleUpload} 
                    disabled={uploading || !file}
                    className="mt-8 w-full bg-brand-600 text-white py-4 rounded-xl text-lg font-bold shadow-lg shadow-brand-500/30 hover:bg-brand-700 disabled:bg-slate-300 disabled:shadow-none transition-all flex items-center justify-center gap-2"
                  >
                    {uploading ? <span className="material-symbols-rounded animate-spin">progress_activity</span> : <span className="material-symbols-rounded">auto_awesome</span>}
                    {uploading ? "문서를 분석하고 있어요..." : "학습 노트 생성하기"}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            // [결과 뷰어]
            <div className="max-w-4xl mx-auto p-8 pb-32 space-y-10 animate-[fadeIn_0.3s_ease-out]">
              <div className="flex justify-between items-end border-b border-slate-200 pb-6">
                <div>
                  <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">{activeDoc.name}</h1>
                  <p className="text-slate-500 mt-2 flex items-center gap-2 text-sm">
                    <span className="material-symbols-rounded text-brand-500 text-base">check_circle</span>
                    분석 완료 · {new Date().toLocaleDateString()}
                  </p>
                </div>
                <div className="flex gap-2">
                   <span className="px-3 py-1 bg-white border border-slate-200 text-slate-600 text-xs font-bold rounded-full shadow-sm">
                     {activeDoc.audience === 'novice' ? '🌱 입문용' : '🚀 심화용'}
                   </span>
                </div>
              </div>

              {/* 1. 요약 카드 */}
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <span className="material-symbols-rounded text-brand-500">summarize</span>
                  <h3 className="text-xl font-bold text-slate-800">핵심 요약</h3>
                </div>
                <div className="bg-white rounded-2xl shadow-soft border border-slate-100 overflow-hidden">
                  <div className="p-6 bg-brand-50/50 border-b border-brand-100">
                    <p className="text-slate-700 leading-relaxed font-medium">{activeDoc.summary.high_level}</p>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {activeDoc.summary.sections.map((sec, idx) => (
                      <div key={idx} className="p-6">
                        <h4 className="font-bold text-lg text-slate-800 mb-3 flex items-center gap-2">
                          <span className="w-2 h-2 bg-brand-500 rounded-full"></span>
                          {sec.title}
                        </h4>
                        <ul className="space-y-2 pl-4">
                          {sec.bullets.map((b, i) => (
                            <li key={i} className="text-slate-600 text-sm list-disc marker:text-slate-300">{b}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              {/* 2. 용어 카드 */}
              <section>
                 <div className="flex items-center gap-2 mb-4">
                  <span className="material-symbols-rounded text-brand-500">text_fields</span>
                  <h3 className="text-xl font-bold text-slate-800">주요 용어</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {activeDoc.glossary.map((item, idx) => (
                    <div key={idx} className="bg-white p-5 rounded-2xl shadow-soft border border-slate-100 hover:border-brand-200 transition-colors">
                       <div className="flex justify-between items-start mb-2">
                         <span className="font-bold text-brand-700 text-lg">{item.term}</span>
                         {/* [수정] 긴 문장을 High/Mid/Low 단어로 강제 변환해서 보여줌 */}
                         {renderImportanceBadge(item.importance)}
                       </div>
                       <p className="text-sm text-slate-600 leading-relaxed">{item.definition}</p>
                    </div>
                  ))}
                </div>
              </section>

              {/* 3. 문제 카드 */}
              <section>
                 <div className="flex items-center gap-2 mb-4">
                  <span className="material-symbols-rounded text-brand-500">quiz</span>
                  <h3 className="text-xl font-bold text-slate-800">확인 문제</h3>
                </div>
                <div className="bg-white rounded-2xl shadow-soft border border-slate-100 p-6">
                   <div className="flex gap-2 mb-6 p-1 bg-slate-100 rounded-xl w-fit">
                      {['mcq', 'short'].map(type => (
                        <button 
                          key={type}
                          onClick={() => setActiveTab(type)}
                          className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === type ? "bg-white text-brand-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                        >
                          {type === 'mcq' ? '객관식' : '주관식'}
                        </button>
                      ))}
                   </div>

                   <div className="space-y-6">
                      {activeDoc.questions.filter(q => activeTab === 'mcq' ? q.type === 'mcq' : q.type !== 'mcq').map((q, idx) => {
                        const questionText = q.stem || q.question || q.text || "문제 내용이 없습니다.";
                        const choices = q.choices || q.options;
                        const answer = q.answer;
                        const explanation = q.rationale || q.explanation || "해설이 없습니다.";

                        return (
                          <div key={idx} className="border border-slate-100 rounded-xl p-5 hover:border-brand-200 transition-colors">
                            <div className="flex gap-3 mb-4">
                              <span className="flex-none flex items-center justify-center w-6 h-6 bg-slate-900 text-white text-xs font-bold rounded-md">Q</span>
                              <p className="font-bold text-slate-800">{questionText}</p>
                            </div>
                            
                            {choices && (
                              <div className="ml-9 space-y-2 mb-4">
                                {choices.map((c, i) => (
                                  <label key={i} className="flex items-center p-3 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer group transition-all">
                                    <input type="radio" name={`q-${idx}`} className="w-4 h-4 text-brand-600 border-slate-300 focus:ring-brand-500"/>
                                    <span className="ml-3 text-sm text-slate-600 group-hover:text-slate-900">{c}</span>
                                  </label>
                                ))}
                              </div>
                            )}

                            <div className="ml-9">
                                <details className="group">
                                  <summary className="inline-flex items-center gap-1 text-sm text-brand-600 font-bold cursor-pointer hover:text-brand-800 transition-colors">
                                    <span>정답 확인하기</span>
                                    <span className="material-symbols-rounded text-lg group-open:rotate-180 transition-transform">expand_more</span>
                                  </summary>
                                  <div className="mt-3 p-4 bg-brand-50/50 rounded-xl text-sm border border-brand-100">
                                    <p className="font-bold text-slate-800 mb-1">정답: <span className="text-brand-600">{answer}</span></p>
                                    <p className="text-slate-600">{explanation}</p>
                                  </div>
                                </details>
                            </div>
                          </div>
                        );
                      })}
                      {activeDoc.questions.length === 0 && <p className="text-center text-slate-400">문제가 없습니다.</p>}
                   </div>
                </div>
              </section>
            </div>
          )}
        </div>

        {/* 3. 채팅창 */}
        {activeDoc && (
          <aside className="w-[400px] bg-white border-l border-slate-200 flex flex-col z-10 shadow-xl">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-white/90 backdrop-blur sticky top-0 z-10">
               <div>
                 <h3 className="font-bold text-slate-800">AI 튜터</h3>
                 <p className="text-xs text-slate-500">문서 기반 질의응답</p>
               </div>
               <div className="w-8 h-8 rounded-full bg-brand-50 flex items-center justify-center">
                 <span className="material-symbols-rounded text-brand-600">smart_toy</span>
               </div>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-6 bg-slate-50">
              {activeDoc.chatHistory.map((msg, idx) => (
                <div key={idx} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === "user" ? "bg-slate-800" : "bg-brand-600"}`}>
                    <span className="material-symbols-rounded text-white text-sm">
                      {msg.role === "user" ? "person" : "smart_toy"}
                    </span>
                  </div>
                  
                  <div className={`max-w-[80%] p-3.5 rounded-2xl text-[13px] leading-relaxed shadow-sm ${
                    msg.role === "user" 
                      ? "bg-white text-slate-800 border border-slate-200 rounded-tr-none" 
                      : "bg-brand-600 text-white rounded-tl-none shadow-brand-500/20"
                  }`}>
                    {msg.text}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            <div className="p-5 bg-white">
              <div className="relative shadow-lg rounded-2xl border border-slate-200 focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-500/20 transition-all">
                <input 
                  type="text" 
                  className="w-full pl-4 pr-12 py-3.5 bg-transparent border-none rounded-2xl text-sm focus:ring-0 placeholder:text-slate-400"
                  placeholder="궁금한 점을 물어보세요..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                />
                <button 
                  onClick={handleSendMessage}
                  disabled={!chatInput.trim()}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:bg-slate-200 disabled:text-slate-400 transition-colors shadow-sm"
                >
                  <span className="material-symbols-rounded text-xl leading-none">arrow_upward</span>
                </button>
              </div>
            </div>
          </aside>
        )}
      </main>
    </div>
  );
}

export default App;