const TITLES = {
  dashboard: "실시간 관제 대시보드",
  equipment: "설비 현황",
  anomaly: "이상탐지 테스트",
  faultRanking: "결함 순위",
  guide: "조치가이드 생성",
  history: "이력",
};

export default function Topbar({ page, apiOk, simulationMode, onToggleSimulation }) {
  const title = TITLES[page] || TITLES.dashboard;

  // API가 안 붙어있으면 그게 제일 중요한 정보라 그것부터 보여주고,
  // 붙어있으면 지금이 시뮬레이션(자동 재생) 모드인지 테스트(수동) 모드인지를 보여준다.
  // 이 배지 자체가 두 모드를 스위칭하는 버튼이기도 하다.
  const label = !apiOk ? "API 연결 안됨" : simulationMode ? "SIMULATION..." : "TESTING...";
  const badgeClass = !apiOk ? "badge-live off" : simulationMode ? "badge-live simulating" : "badge-live";

  return (
    <div className="topbar">
      <div>
        <div className="topbar-title">{title}</div>
      </div>
      <div className="topbar-right">
        <button
          type="button"
          className={badgeClass}
          onClick={onToggleSimulation}
          disabled={!apiOk}
          title={simulationMode ? "클릭하면 시뮬레이션을 멈추고 테스트 모드로 전환" : "클릭하면 실시간 시뮬레이션 시작"}
        >
          <span className="pulse"></span> {label}
        </button>
      </div>
    </div>
  );
}
