import { useState } from "react";
import { getGuide } from "../api.js";

const EXAMPLES = [
  "반응기 압력이 비정상적으로 상승하고 있습니다.",
  "스트리퍼 온도가 급격히 떨어지고 있습니다.",
  "압축기에서 이상 진동이 감지되었습니다.",
];

export default function GuideGenerator() {
  const [description, setDescription] = useState(EXAMPLES[0]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await getGuide(description);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>조치가이드 생성</h2>
      <p className="hint">
        결함 상황을 문장으로 설명하면, KOSHA GUIDE에서 관련 지침을 검색해 조치가이드를 생성합니다.
      </p>

      <div className="row">
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => setDescription(ex)} className="tag">
            {ex}
          </button>
        ))}
      </div>

      <textarea
        rows={3}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="결함 상황을 입력하세요"
      />

      <button onClick={handleSubmit} disabled={loading} className="primary">
        {loading ? "생성 중... (LLM 호출이라 몇 초 걸릴 수 있습니다)" : "조치가이드 생성"}
      </button>

      {error && <div className="error">에러: {error}</div>}

      {result && (
        <div className="result-card">
          <div className={`badge ${result.confidence === "high" ? "badge-ok" : "badge-warn"}`}>
            신뢰도: {result.confidence === "high" ? "높음" : "낮음"}
          </div>
          <pre className="guide-text">{result.guide_text}</pre>

          {result.reference_docs.length > 0 && (
            <>
              <h3>참고 문서</h3>
              <ul className="ref-list">
                {result.reference_docs.map((ref, i) => (
                  <li key={i}>
                    <strong>{ref.code}</strong> {ref.title} ({ref.year}년) p.{ref.page}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
