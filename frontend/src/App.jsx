import { useEffect, useRef, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import Dashboard from "./components/Dashboard.jsx";
import EquipmentPage from "./components/EquipmentPage.jsx";
import AnomalyCheck from "./components/AnomalyCheck.jsx";
import FaultRanking from "./components/FaultRanking.jsx";
import GuideGenerator from "./components/GuideGenerator.jsx";
import HistoryDashboard from "./components/HistoryDashboard.jsx";
import AlertOverlay from "./components/AlertOverlay.jsx";
import { checkAnomaly, listUnresolvedAnomalies, resolveSensorLogsByFault } from "./api.js";
import { getPlant } from "./plants.js";
import simulationData from "./assets/simulation_run.json";

const API_BASE = import.meta.env.DEV ? "http://localhost:8000" : "";
const ALERT_POLL_MS = 3000;
// 실제 TEP 테스트 run(샘플 1~960, 160번째부터 결함 진행)을 재생하는 간격.
// scripts/simulate_plant.py의 백엔드 버전과 같은 데이터를 쓰지만, 이건 프론트
// 버튼으로 바로 켜고 끌 수 있도록 브라우저 안에서 직접 /anomaly-check를 호출한다.
const SIMULATION_INTERVAL_MS = 3000;

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [equipmentInitial, setEquipmentInitial] = useState(null);
  const [apiOk, setApiOk] = useState(false);
  const [alertQueue, setAlertQueue] = useState([]); // 결함 유형별 미해결 "사고" 1건씩, 발생 순(오래된 것부터)
  const [promoting, setPromoting] = useState(false); // 방금 하나 처리해서 다음 게 중앙으로 승격되는 애니메이션 트리거
  const [plant, setPlant] = useState("tep");
  const [simulationMode, setSimulationMode] = useState(false);
  const simStepRef = useRef(0);
  const currentFaultRef = useRef(null); // 지금 작업 중인 결함 번호 — 폴링마다 대기열 순서가 흔들려도 이게 계속 맨 앞을 유지
  const plantInfo = getPlant(plant);

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((r) => setApiOk(r.ok))
      .catch(() => setApiOk(false));
  }, []);

  // 실제 현장이라면 센서가 스트리밍으로 계속 들어오면서 이상이 생기는 즉시
  // 알림이 뜨겠지만, 지금 구조는 짧은 주기로 폴링해서 "아직 상황종료 안 한
  // 이상 감지 건이 있는지"를 확인하는 방식으로 흉내낸다.
  //
  // 예전엔 "가장 최근 로그 1건"만 보고 판단했는데(rows[0]), 시뮬레이션 모드처럼
  // 3초마다 새 로그가 계속 쌓이는 상황에서 두 가지 문제가 있었다:
  // 1) 같은 결함이 한동안 계속되면(실제 결함 구간이 보통 그렇다) 매 윈도우마다
  //    "새로운 미해결 이상"이 하나씩 더 쌓여서, 방금 확인한 결함이 다음 폴링에서
  //    또(사실은 같은 사고인데) 뜬다 — "결함이 너무 많이 뜬다"는 문제.
  // 2) 지금 막 상황종료 드롭다운을 고르는 중인데, 그새 새 이상이 감지되면 그게
  //    "가장 최근"이 되면서 activeAlert가 통째로 바뀌어 작업 중이던 화면이
  //    사라졌다.
  //
  // 그래서 "로그 1건 = 알림 1건"이 아니라 "결함 유형(fault_number) 1개 = 사고
  // 1건"으로 묶는다. 대기열(alertQueue)은 아직 상황종료 안 한 결함 유형들을
  // 발생한 순서대로(오래된 것부터, FIFO) 담고, 화면엔 맨 앞(현재 처리 중)과
  // 그 다음(대기 미리보기) 둘만 보여준다. currentFaultRef로 "지금 작업 중인
  // 결함"을 고정해둬서, 폴링할 때마다 순서가 미묘하게 흔들려도 화면이 안 바뀐다
  // — 그 결함이 큐에서 사라지는(=상황종료 처리됨) 순간에만 다음 것으로 넘어간다.
  useEffect(() => {
    let cancelled = false;

    const poll = () => {
      listUnresolvedAnomalies(300)
        .then((rows) => {
          if (cancelled) return;
          const seen = new Set();
          const groups = [];
          for (const row of rows) {
            if (row.fault_number == null || seen.has(row.fault_number)) continue;
            seen.add(row.fault_number);
            groups.push(row);
          }
          if (currentFaultRef.current != null) {
            const idx = groups.findIndex((g) => g.fault_number === currentFaultRef.current);
            if (idx > 0) {
              const [item] = groups.splice(idx, 1);
              groups.unshift(item);
            }
          }
          currentFaultRef.current = groups.length > 0 ? groups[0].fault_number : null;
          setAlertQueue(groups);
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

  const handleResolve = async (faultNumber, confirmedFaultNumber) => {
    await resolveSensorLogsByFault(faultNumber, confirmedFaultNumber);
    // 다음 폴링(최대 3초)까지 안 기다리고 바로 큐에서 빼서, 대기 중이던 다음
    // 알림이 즉시 중앙으로 승격되는 걸 보여준다(애니메이션은 AlertOverlay 참고).
    setAlertQueue((prev) => prev.filter((g) => g.fault_number !== faultNumber));
    currentFaultRef.current = null;
    setPromoting(true);
    setTimeout(() => setPromoting(false), 450);
  };

  // 시뮬레이션 모드: 실제 TEP run을 처음부터 순서대로 재생하며 일정 간격으로
  // /anomaly-check를 호출한다. 대시보드/설비화면/알림은 이미 폴링 중이라 이
  // 호출 결과가 자동으로 화면에 반영된다 — 사람이 "이상탐지 테스트"에서 수동으로
  // 버튼을 누르는 대신, 진짜 센서가 계속 데이터를 보내는 것처럼 흉내내는 것.
  // 끝까지 재생하면 처음(정상 구간)으로 되돌아가 계속 반복한다.
  useEffect(() => {
    if (!simulationMode) return;

    const steps = simulationData.steps;
    let cancelled = false;

    const tick = () => {
      if (cancelled || steps.length === 0) return;
      const step = steps[simStepRef.current % steps.length];
      simStepRef.current += 1;
      checkAnomaly(step.window).catch(() => {});
    };

    tick();
    const id = setInterval(tick, SIMULATION_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [simulationMode]);

  const handleToggleSimulation = () => {
    setSimulationMode((prev) => {
      const next = !prev;
      if (next) {
        simStepRef.current = 0;
        // "이상탐지 테스트" 메뉴는 시뮬레이션 중엔 사이드바에서 사라지므로,
        // 마침 그 화면에 있었다면 대시보드로 돌려보낸다.
        if (page === "anomaly") setPage("dashboard");
      }
      return next;
    });
  };

  // 대시보드에서 특정 설비 카드를 클릭하면 그 설비 상세로 바로 들어가고,
  // 사이드바 메뉴로 이동하면 항상 설비 목록부터 보여준다(equipmentId 없이 호출).
  const navigate = (targetPage, equipmentId = null) => {
    setEquipmentInitial(equipmentId);
    setPage(targetPage);
  };

  const currentAlert = alertQueue[0] || null;
  const nextAlert = alertQueue[1] || null;

  return (
    <div className="app">
      <AlertOverlay
        current={currentAlert}
        next={nextAlert}
        onResolve={handleResolve}
        promoting={promoting}
      />
      <Sidebar
        active={page}
        onChange={navigate}
        plant={plant}
        onPlantChange={setPlant}
        simulationMode={simulationMode}
      />
      <div className="main">
        <Topbar
          page={page}
          apiOk={apiOk}
          simulationMode={simulationMode}
          onToggleSimulation={handleToggleSimulation}
        />
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
              {page === "dashboard" && <Dashboard onNavigate={navigate} simulationMode={simulationMode} />}
              {page === "equipment" && <EquipmentPage initialSelected={equipmentInitial} />}
              {page === "anomaly" && !simulationMode && <AnomalyCheck />}
              {page === "faultRanking" && <FaultRanking />}
              {page === "guide" && <GuideGenerator />}
              {page === "history" && <HistoryDashboard />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
