import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { listGuideLogs, listSensorLogs } from "../api.js";
import { faultLabel } from "../faultNames.js";

function formatTime(iso) {
  return new Date(iso).toLocaleString("ko-KR", { hour12: false });
}

const REFRESH_MS = 5000;

export default function Dashboard({ onNavigate, simulationMode }) {
  const [sensorLogs, setSensorLogs] = useState([]);
  const [guideLogs, setGuideLogs] = useState([]);
  const [error, setError] = useState(null);

  // 처음 마운트될 때 한 번만 불러오면, 이 화면에 계속 머물러 있는 동안
  // "이상탐지 테스트"에서 새로 감지한 결과가 반영이 안 된다(페이지를 벗어났다가
  // 돌아와야만 새로고침됨). 그래서 AlertOverlay의 긴급알림 폴링과 같은 방식으로,
  // 대시보드도 일정 주기로 최신 로그를 다시 가져오게 했다.
  useEffect(() => {
    let cancelled = false;

    const load = () => {
      Promise.all([listSensorLogs(50), listGuideLogs(20)])
        .then(([s, g]) => {
          if (cancelled) return;
          setSensorLogs(s);
          setGuideLogs(g);
        })
        .catch((e) => {
          if (!cancelled) setError(e.message);
        });
    };

    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const total = sensorLogs.length;
  const anomalies = sensorLogs.filter((l) => l.is_anomaly);
  const anomalyRate = total ? ((anomalies.length / total) * 100).toFixed(1) : "0.0";
  const avgConfidence = total
    ? ((sensorLogs.reduce((sum, l) => sum + l.confidence, 0) / total) * 100).toFixed(1)
    : "0.0";

  // 결함 유형별 카드: 카드 제목이 "최근 감지된"이니까 정렬 기준도 "가장 최근에
  // 감지된 순서"여야 한다. 원래는 건수(count)로 정렬했는데, JS 객체는 숫자
  // 형태의 key를 항상 오름차순으로 순회하기 때문에(삽입 순서 무시) count가
  // 동률(대부분 1건씩)이면 정렬이 사실상 "결함 번호가 작은 순"으로 고정되고,
  // 새로 테스트한 결함이 몇 번을 눌러도 카드에 안 보이는 버그가 있었다.
  // anomalies는 이미 최신순(created_at desc)으로 오니까, 그 순서 그대로 훑으면서
  // 처음 보는 결함 번호만 추려내면 "진짜 최근 감지 순"이 된다.
  const faultCounts = {};
  anomalies.forEach((l) => {
    if (l.fault_number != null) {
      faultCounts[l.fault_number] = (faultCounts[l.fault_number] || 0) + 1;
    }
  });
  const seenFaults = new Set();
  const topFaults = [];
  for (const log of anomalies) {
    if (log.fault_number == null || seenFaults.has(log.fault_number)) continue;
    seenFaults.add(log.fault_number);
    topFaults.push([log.fault_number, faultCounts[log.fault_number]]);
    if (topFaults.length >= 4) break;
  }

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
          </div>

          {topFaults.length === 0 ? (
            <div className="card hint">
              {simulationMode
                ? "시뮬레이션이 실시간으로 재생 중입니다. 결함이 감지되면 여기에 표시됩니다."
                : '아직 감지된 이상이 없습니다. "이상탐지 테스트" 메뉴에서 실행해보세요.'}
            </div>
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
              <button
                className="ai-search-btn"
                title="조치가이드 생성으로 이동"
                onClick={() => onNavigate("guide")}
              >
                <Search size={13} strokeWidth={2} />
              </button>
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
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
