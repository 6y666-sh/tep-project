import { PLANTS } from "../plants.js";

const NAV = [
  { key: "dashboard", icon: "▣", label: "대시보드" },
  { key: "equipment", icon: "⚙", label: "설비 현황" },
  { key: "anomaly", icon: "📡", label: "이상탐지 테스트" },
  { key: "guide", icon: "🤖", label: "조치가이드 생성" },
  { key: "history", icon: "📈", label: "이력" },
];

export default function Sidebar({ active, onChange, plant, onPlantChange }) {
  return (
    <div className="sidebar">
      <div className="brand">
        <div className="brand-mark">TEP</div>
        <div>
          <div className="brand-name">TEP Guard</div>
          <div className="brand-sub">ANOMALY + RAG</div>
        </div>
      </div>

      <div className="nav-section">
        <div className="nav-label">모니터링</div>
        {NAV.map((item) => (
          <button
            key={item.key}
            className={active === item.key ? "nav-item active" : "nav-item"}
            onClick={() => onChange(item.key)}
          >
            <span className="nav-icon">{item.icon}</span> {item.label}
          </button>
        ))}
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
