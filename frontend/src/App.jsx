import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import Dashboard from "./components/Dashboard.jsx";
import EquipmentPage from "./components/EquipmentPage.jsx";
import AnomalyCheck from "./components/AnomalyCheck.jsx";
import GuideGenerator from "./components/GuideGenerator.jsx";
import HistoryDashboard from "./components/HistoryDashboard.jsx";
import AlertOverlay from "./components/AlertOverlay.jsx";
import { listSensorLogs, resolveSensorLog } from "./api.js";
import { getPlant } from "./plants.js";

const API_BASE = import.meta.env.DEV ? "http://localhost:8000" : "";
const ALERT_POLL_MS = 3000;

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [equipmentInitial, setEquipmentInitial] = useState(null);
  const [apiOk, setApiOk] = useState(false);
  const [activeAlert, setActiveAlert] = useState(null);
  const [plant, setPlant] = useState("tep");
  const plantInfo = getPlant(plant);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => setApiOk(r.ok))
      .catch(() => setApiOk(false));
  }, []);

  // 실제 현장이라면 센서가 스트리밍으로 계속 들어오면서 이상이 생기는 즉시
  // 알림이 뜨겠지만, 지금 구조는 "이상탐지 테스트" 화면에서 사람이 판정을
  // 요청하는 방식이라 진짜 실시간 스트림이 없다. 그래서 최근 판정을 짧은
  // 주기로 폴링해서 "아직 상황종료 안 한 이상 감지 건이 있는지"를 확인하는
  // 방식으로 흉내낸다 — 페이지를 어디에 있든(대시보드든 이력이든) 이상이
  // 감지되면 화면 전체가 빨갛게 알림을 띄우게 하려는 목적.
  useEffect(() => {
    let cancelled = false;

    const poll = () => {
      listSensorLogs(1)
        .then((rows) => {
          if (cancelled) return;
          const latest = rows[0];
          setActiveAlert(latest && latest.is_anomaly && !latest.resolved ? latest : null);
        })
        .catch(() => {});
    };

    poll();
    const id = setInterval(poll, ALERT_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const handleResolve = async (logId) => {
    await resolveSensorLog(logId);
    setActiveAlert(null);
  };

  // 대시보드에서 특정 설비 카드를 클릭하면 그 설비 상세로 바로 들어가고,
  // 사이드바 메뉴로 이동하면 항상 설비 목록부터 보여준다(equipmentId 없이 호출).
  const navigate = (targetPage, equipmentId = null) => {
    setEquipmentInitial(equipmentId);
    setPage(targetPage);
  };

  return (
    <div className="app">
      <AlertOverlay alert={activeAlert} onResolve={handleResolve} />
      <Sidebar active={page} onChange={navigate} plant={plant} onPlantChange={setPlant} />
      <div className="main">
        <Topbar page={page} apiOk={apiOk} />
        <div className="content">
          {!plantInfo?.functional ? (
            <div className="card">
              <h2>{plantInfo?.name}</h2>
              <div className="equip-status-banner">
                이 공장은 데모 범위에 포함되지 않았습니다. 실제 서비스라면 Tennessee Eastman Process와
                동일한 방식으로 이 공장의 센서 데이터가 연동됩니다. 좌측 하단에서 "Tennessee Eastman Process"로
                다시 전환해보세요.
              </div>
            </div>
          ) : (
            <>
              {page === "dashboard" && <Dashboard onNavigate={navigate} />}
              {page === "equipment" && <EquipmentPage initialSelected={equipmentInitial} />}
              {page === "anomaly" && <AnomalyCheck />}
              {page === "guide" && <GuideGenerator />}
              {page === "history" && <HistoryDashboard />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
