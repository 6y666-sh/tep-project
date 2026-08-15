import { useEffect, useState } from "react";
import { listGuideLogs, listSensorLogs } from "../api.js";
import { faultLabel } from "../faultNames.js";

function formatTime(iso) {
  return new Date(iso).toLocaleString("ko-KR");
}

export default function HistoryDashboard() {
  const [sensorLogs, setSensorLogs] = useState([]);
  const [guideLogs, setGuideLogs] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, g] = await Promise.all([listSensorLogs(50), listGuideLogs(50)]);
      setSensorLogs(s);
      setGuideLogs(g);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const anomalyCount = sensorLogs.filter((l) => l.is_anomaly).length;

  return (
    <div className="card">
      <h2>이력 대시보드</h2>
      <div className="row">
        <button onClick={load}>새로고침</button>
      </div>

      {error && <div className="error">에러: {error}</div>}
      {loading && <p className="hint">불러오는 중...</p>}

      {!loading && (
        <>
          <div className="stats-row">
            <div className="stat-box">
              <span className="stat-value">{sensorLogs.length}</span>
              <span className="stat-label">전체 이상탐지 요청</span>
            </div>
            <div className="stat-box">
              <span className="stat-value">{anomalyCount}</span>
              <span className="stat-label">이상 감지 건수</span>
            </div>
            <div className="stat-box">
              <span className="stat-value">{guideLogs.length}</span>
              <span className="stat-label">조치가이드 요청</span>
            </div>
          </div>

          <h3>최근 이상탐지 로그</h3>
          <table>
            <thead>
              <tr>
                <th>시각</th>
                <th>판정</th>
                <th>결함번호</th>
                <th>확신도</th>
              </tr>
            </thead>
            <tbody>
              {sensorLogs.map((log) => (
                <tr key={log.id}>
                  <td>{formatTime(log.created_at)}</td>
                  <td>
                    <span className={`badge ${log.is_anomaly ? "badge-danger" : "badge-ok"}`}>
                      {log.is_anomaly ? "이상" : "정상"}
                    </span>
                  </td>
                  <td>{faultLabel(log.fault_number)}</td>
                  <td>{(log.confidence * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>최근 조치가이드 요청 로그</h3>
          <table>
            <thead>
              <tr>
                <th>시각</th>
                <th>결함 설명</th>
                <th>참고문서 수</th>
              </tr>
            </thead>
            <tbody>
              {guideLogs.map((log) => (
                <tr key={log.id}>
                  <td>{formatTime(log.created_at)}</td>
                  <td>{log.fault_description}</td>
                  <td>{log.reference_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
