import { useState } from "react";
import { checkAnomaly } from "../api.js";

const WINDOW_SIZE = 10;
const VAR_COUNT = 52; // xmeas_1..41 + xmv_1..11

// 실제 센서 데이터를 손으로 입력하긴 어려우니, 데모용으로 그럴듯한 랜덤 값을
// 만들어주는 버튼을 둔다. 값 자체의 의미보다 "형식이 맞는 윈도우를 보내면
// 어떻게 응답이 오는지" 보여주는 게 목적.
function randomWindow() {
  return Array.from({ length: WINDOW_SIZE }, () =>
    Array.from({ length: VAR_COUNT }, () => +(Math.random() * 100).toFixed(2))
  );
}

export default function AnomalyCheck() {
  const [windowJson, setWindowJson] = useState(JSON.stringify(randomWindow()));
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleRandom = () => {
    setWindowJson(JSON.stringify(randomWindow()));
    setResult(null);
    setError(null);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const window = JSON.parse(windowJson);
      const res = await checkAnomaly(window);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2>이상탐지 테스트</h2>
      <p className="hint">
        센서 윈도우(최근 {WINDOW_SIZE}개 시점 × {VAR_COUNT}개 변수)를 보내 이상 여부를 확인합니다.
        실제 값 대신 데모용 랜덤 값으로 테스트해볼 수 있습니다.
      </p>

      <div className="row">
        <button onClick={handleRandom}>랜덤 윈도우 생성</button>
        <button onClick={handleSubmit} disabled={loading} className="primary">
          {loading ? "확인 중..." : "이상탐지 실행"}
        </button>
      </div>

      <textarea
        className="code-input"
        rows={6}
        value={windowJson}
        onChange={(e) => setWindowJson(e.target.value)}
      />

      {error && <div className="error">에러: {error}</div>}

      {result && (
        <div className="result-card">
          <div className={`badge ${result.is_anomaly ? "badge-danger" : "badge-ok"}`}>
            {result.is_anomaly ? "이상 감지" : "정상"}
          </div>
          <div className="field">
            <span className="label">결함 번호</span>
            <span>{result.fault_number ?? "-"}</span>
          </div>
          <div className="field">
            <span className="label">확신도</span>
            <div className="confidence-bar">
              <div
                className="confidence-fill"
                style={{ width: `${Math.round(result.confidence * 100)}%` }}
              />
            </div>
            <span>{(result.confidence * 100).toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
