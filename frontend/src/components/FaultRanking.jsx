import { useEffect, useState } from "react";
import { listSensorLogs } from "../api.js";
import { faultLabel } from "../faultNames.js";

const WINDOW_DAYS = 30;
const REFRESH_MS = 10000;

// 설비 문제로 같은 결함이 반복 발생하는지 한눈에 보려는 화면. Dashboard의
// "최근 감지된 결함 유형" 카드는 정렬 기준이 "최근 감지 순"이라 반복 빈도
// 자체는 안 보였다. 여기는 반대로 최근 30일 발생 "횟수" 기준으로 1위부터
// 순위를 매긴다 — 목적이 다르니 굳이 하나로 합치지 않고 별도 메뉴로 뺐다.
export default function FaultRanking() {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    listSensorLogs(1000, WINDOW_DAYS)
      .then((rows) => {
        setLogs(rows);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, []);

  const anomalies = logs.filter((l) => l.is_anomaly && l.fault_number != null);
  const counts = {};
  anomalies.forEach((l) => {
    counts[l.fault_number] = (counts[l.fault_number] || 0) + 1;
  });
  const ranked = Object.entries(counts)
    .map(([faultNo, count]) => [Number(faultNo), count])
    .sort((a, b) => b[1] - a[1]);
  const maxCount = ranked.length ? ranked[0][1] : 0;

  if (error) return <div className="error">데이터를 불러오지 못했습니다: {error}</div>;

  return (
    <div className="card">
      <div className="section-head">
        <div className="section-title">최근 {WINDOW_DAYS}일 결함 발생 순위 <span>{ranked.length}</span></div>
        <button onClick={load}>새로고침</button>
      </div>

      {loading && ranked.length === 0 ? (
        <div className="hint">불러오는 중...</div>
      ) : ranked.length === 0 ? (
        <div className="hint">최근 {WINDOW_DAYS}일 동안 감지된 결함이 없습니다.</div>
      ) : (
        <div className="rank-list">
          {ranked.map(([faultNo, count], i) => (
            <div key={faultNo} className="rank-row">
              <div className={i === 0 ? "rank-num rank-1" : "rank-num"}>{i + 1}</div>
              <div className="rank-info">
                <div className="rank-name">{faultLabel(faultNo)}</div>
                <div className="rank-id">FAULT-{String(faultNo).padStart(2, "0")}</div>
                <div className="kpi-bar">
                  <i style={{ width: `${maxCount ? (count / maxCount) * 100 : 0}%` }} />
                </div>
              </div>
              <div className="rank-count">
                {count}
                <span className="unit">건</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
