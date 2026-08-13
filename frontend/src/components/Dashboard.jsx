import { useEffect, useState } from "react";
import { listGuideLogs, listSensorLogs } from "../api.js";
import { faultLabel } from "../faultNames.js";

function formatTime(iso) {
  return new Date(iso).toLocaleString("ko-KR", { hour12: false });
}

export default function Dashboard({ onNavigate }) {
  const [sensorLogs, setSensorLogs] = useState([]);
  const [guideLogs, setGuideLogs] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([listSensorLogs(50), listGuideLogs(20)])
      .then(([s, g]) => {
        setSensorLogs(s);
        setGuideLogs(g);
      })
      .catch((e) => setError(e.message));
  }, []);

  const total = sensorLogs.length;
  const anomalies = sensorLogs.filter((l) => l.is_anomaly);
  const anomalyRate = total ? ((anomalies.length / total) * 100).toFixed(1) : "0.0";
  const avgConfidence = total
    ? ((sensorLogs.reduce((sum, l) => sum + l.confidence, 0) / total) * 100).toFixed(1)
    : "0.0";

  // 결함 번호별로 최근 감지 건수 집계 (설비 카드 대신, 결함 유형별 현황 카드)
  const faultCounts = {};
  anomalies.forEach((l) => {
    if (l.fault_number != null) {
      faultCounts[l.fault_number] = (faultCounts[l.fault_number] || 0) + 1;
    }
  });
  const topFaults = Object.entries(faultCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);

  const latestAlert = anomalies[0];
  const latestGuide = guideLogs[0];

  if (error) return <div className="error">데이터를 불러오지 못했습니다: {error}</div>;

  return (
    <>
      <div className="kpi-row">
        <div className="kpi-card">
          <span className="kpi-lbl">전체 이상탐지 요청</span>
          <span className="kpi-val">{total}</span>
          <div className="kpi-bar"><i style={{ width: "100%", background: "var(--blue)" }} /></div>
        </div>
        <div className="kpi-card">
          <span className="kpi-lbl">이상 감지율</span>
          <span className="kpi-val">{anomalyRate}<span className="unit">%</span></span>
          <div className="kpi-bar"><i style={{ width: `${anomalyRate}%` }} /></div>
        </div>
        <div className="kpi-card">
          <span className="kpi-lbl">평균 확신도</span>
          <span className="kpi-val">{avgConfidence}<span className="unit">%</span></span>
          <div className="kpi-bar"><i style={{ width: `${avgConfidence}%`, background: "var(--green)" }} /></div>
        </div>
        <div className="kpi-card">
          <span className="kpi-lbl">조치가이드 요청</span>
          <span className="kpi-val">{guideLogs.length}</span>
          <div className="kpi-bar"><i style={{ width: "100%", background: "var(--amber)" }} /></div>
        </div>
      </div>

      <div className="grid-2">
        <div>
          <div className="section-head">
            <div className="section-title">최근 감지된 결함 유형 <span>{topFaults.length}</span></div>
            <button onClick={() => onNavigate("anomaly")}>이상탐지 실행하기 →</button>
          </div>

          {topFaults.length === 0 ? (
            <div className="card hint">아직 감지된 이상이 없습니다. "이상탐지 테스트" 메뉴에서 실행해보세요.</div>
          ) : (
            <div className="equip-grid" style={{ marginBottom: 18 }}>
              {topFaults.map(([faultNo, count]) => (
                <div key={faultNo} className={count >= 3 ? "equip-card err" : "equip-card warn"}>
                  <div className="equip-top">
                    <div>
                      <div className="equip-name">{faultLabel(Number(faultNo))}</div>
                      <div className="equip-id">FAULT-{String(faultNo).padStart(2, "0")}</div>
                    </div>
                    <div className={count >= 3 ? "status-pill err" : "status-pill warn"}>
                      {count}건 감지
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="card">
            <div className="section-head">
              <div className="section-title">최근 알림</div>
              <button onClick={() => onNavigate("history")}>전체 이력 보기 →</button>
            </div>
            <table>
              <thead>
                <tr><th>시각</th><th>결함</th><th>확신도</th></tr>
              </thead>
              <tbody>
                {anomalies.slice(0, 6).map((log) => (
                  <tr key={log.id}>
                    <td>{formatTime(log.created_at)}</td>
                    <td><span className="sev critical">{faultLabel(log.fault_number)}</span></td>
                    <td>{(log.confidence * 100).toFixed(1)}%</td>
                  </tr>
                ))}
                {anomalies.length === 0 && (
                  <tr><td colSpan={3} className="hint">감지된 이상이 없습니다</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="ai-panel">
            <div className="ai-head">
              <span className="ai-dot"></span>
              <div className="ai-title">AI 인사이트</div>
            </div>
            <div className="ai-body">
              {latestAlert ? (
                <div className="msg alert">
                  <div className="msg-lbl">⚠ 최근 이상 탐지</div>
                  {faultLabel(latestAlert.fault_number)} — 확신도 {(latestAlert.confidence * 100).toFixed(1)}%
                  ({formatTime(latestAlert.created_at)})
                </div>
              ) : (
                <div className="msg">아직 감지된 이상이 없습니다.</div>
              )}

              {latestGuide ? (
                <div className="msg guide">
                  <div className="msg-lbl">🤖 최근 조치가이드</div>
                  {(latestGuide.guide_text || "").slice(0, 220)}
                  {(latestGuide.guide_text || "").length > 220 ? "..." : ""}
                  <div className="doc-ref">📄 참고문서 {latestGuide.reference_count}건</div>
                </div>
              ) : (
                <div className="msg">아직 생성된 조치가이드가 없습니다.</div>
              )}

              <button className="primary" onClick={() => onNavigate("guide")}>
                조치가이드 생성하러 가기
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
