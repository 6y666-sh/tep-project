import { BarChart3, Bot, Factory, History, LayoutDashboard, Radio } from "lucide-react";
import { PLANTS } from "../plants.js";

// 이모지 대신 lucide-react(무료 오픈소스 라인 아이콘)를 써서 색깔 있는
// 이모지 티가 안 나게 통일된 스타일로 맞춘다.
const NAV = [
  { key: "dashboard", icon: LayoutDashboard, label: "대시보드" },
  { key: "equipment", icon: Factory, label: "설비 현황" },
  { key: "anomaly", icon: Radio, label: "이상탐지 테스트" },
  { key: "faultRanking", icon: BarChart3, label: "결함 순위" },
  { key: "guide", icon: Bot, label: "조치가이드 생성" },
  { key: "history", icon: History, label: "이력" },
];

export default function Sidebar({ active, onChange, plant, onPlantChange, simulationMode }) {
  // 시뮬레이션 모드에서는 백그라운드에서 실제 TEP 시계열을 자동 재생하며
  // /anomaly-check를 계속 호출하는 중이라, 사람이 수동으로 윈도우를 골라 보내는
  // "이상탐지 테스트" 메뉴는 혼란만 준다(두 흐름이 같은 API를 동시에 두드리게 됨).
  const navItems = simulationMode ? NAV.filter((item) => item.key !== "anomaly") : NAV;

  return (
    <div className="sidebar">
      <div className="brand">
        <div className="brand-mark">TEP</div>
        <div className="brand-name">TEP Guard</div>
      </div>

      <div className="nav-section">
        <div className="nav-label">모니터링</div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.key}
              className={active === item.key ? "nav-item active" : "nav-item"}
              onClick={() => onChange(item.key)}
            >
              <Icon className="nav-icon" size={16} strokeWidth={2} /> {item.label}
            </button>
          );
        })}
      </div>

      <div className="sidebar-footer">
        <div className="plant-select">
          <span className="label">공장 선택</span>
          <select value={plant} onChange={(e) => onPlantChange(e.target.value)}>
            {PLANTS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}{!p.functional ? " (데모 미지원)" : ""}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
