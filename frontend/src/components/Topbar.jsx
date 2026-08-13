const TITLES = {
  dashboard: ["실시간 관제 대시보드", "이상탐지 + RAG 조치가이드 통합 현황"],
  equipment: ["설비 현황", "설비별 공정 도식과 실시간 값을 확인합니다"],
  anomaly: ["이상탐지 테스트", "센서 윈도우를 보내 이상 여부를 확인합니다"],
  guide: ["조치가이드 생성", "KOSHA GUIDE 기반 RAG 조치가이드"],
  history: ["이력", "이상탐지 · 조치가이드 요청 로그"],
};

export default function Topbar({ page, apiOk }) {
  const [title, sub] = TITLES[page] || TITLES.dashboard;
  return (
    <div className="topbar">
      <div>
        <div className="topbar-title">{title}</div>
        <div className="topbar-sub">{sub}</div>
      </div>
      <div className="topbar-right">
        <div className={apiOk ? "badge-live" : "badge-live off"}>
          <span className="pulse"></span> {apiOk ? "API LIVE" : "API 연결 안됨"}
        </div>
      </div>
    </div>
  );
}
