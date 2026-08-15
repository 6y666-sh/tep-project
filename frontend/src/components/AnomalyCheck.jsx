import { useState } from "react";
import { checkAnomaly } from "../api.js";
import { faultLabel } from "../faultNames.js";
import SAMPLE_WINDOWS from "../assets/sample_windows.json";

const WINDOW_SIZE = 10;
const VAR_COUNT = 52; // xmeas_1..41 + xmv_1..11

// 예전에는 0~100 사이 순수 랜덤 값을 만들어서 테스트했는데, 그러면 52개 변수가
// 실제 TEP 데이터의 스케일/분포와 전혀 안 맞는 값이 되어서 매번 같은 극단적인
// 특징 벡터가 나오고, 그 결과 분류기가 거의 항상 같은 결함 하나로만 판정하는
// 문제가 있었다. 그래서 TEP 테스트 데이터셋에서 결함별로 실제 윈도우를 하나씩
// 미리 뽑아 assets/sample_windows.json에 저장해두고, 여기서는 그중 하나를
// 그대로 보내는 방식으로 바꿨다. (키 "0"은 정상 구간, "1"~"20"은 해당 결함이
// 실제로 발생한 이후 구간에서 뽑은 진짜 윈도우다.)
const SCENARIO_KEYS = Object.keys(SAMPLE_WINDOWS).sort((a, b) => Number(a) - Number(b));

function scenarioLabel(key) {
  if (key === "0") return "0 · 정상 (결함 없음)";
  return `${key} · ${faultLabel(Number(key))}`;
}

export default function AnomalyCheck() {
  const [scenario, setScenario] = useState("1");
  const [windowJson, setWindowJson] = useState(JSON.stringify(SAMPLE_WINDOWS["1"]));
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const applyScenario = (key) => {
    setScenario(key);
    setWindowJson(JSON.stringify(SAMPLE_WINDOWS[key]));
    setResult(null);
    setError(null);
  };

  const handleRandomScenario = () => {
    const key = SCENARIO_KEYS[Math.floor(Math.random() * SCENARIO_KEYS.length)];
    applyScenario(key);
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
    <div className="card">
      <h2>이상탐지 테스트</h2>
      <p className="hint">
        센서 윈도우(최근 {WINDOW_SIZE}개 시점 × {VAR_COUNT}개 변수)를 보내 이상 여부를 확인합니다.
        TEP 테스트 데이터셋에서 뽑은 실제 시나리오로 테스트합니다.
      </p>

      <div className="row">
        <select
          value={scenario}
          onChange={(e) => applyScenario(e.target.value)}
          style={{ background: "var(--panel-2)", color: "var(--text)", border: "1px solid var(--line)", borderRadius: 6, padding: "8px 10px", fontSize: 12.5 }}
        >
          {SCENARIO_KEYS.map((key) => (
            <option key={key} value={key}>{scenarioLabel(key)}</option>
          ))}
        </select>
        <button onClick={handleRandomScenario}>무작위 시나리오</button>
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
            <span className="label">결함 유형</span>
            <span>{faultLabel(result.fault_number)}</span>
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
