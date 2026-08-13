import { useState } from "react";
import AnomalyCheck from "./components/AnomalyCheck.jsx";
import GuideGenerator from "./components/GuideGenerator.jsx";
import HistoryDashboard from "./components/HistoryDashboard.jsx";

const TABS = [
  { key: "anomaly", label: "이상탐지 테스트", component: AnomalyCheck },
  { key: "guide", label: "조치가이드 생성", component: GuideGenerator },
  { key: "history", label: "이력 대시보드", component: HistoryDashboard },
];

export default function App() {
  const [active, setActive] = useState("anomaly");
  const ActiveComponent = TABS.find((t) => t.key === active).component;

  return (
    <div className="app">
      <header>
        <h1>TEP 화학공정 이상탐지 + RAG 조치가이드</h1>
        <nav>
          {TABS.map((tab) => (
            <button
              key={tab.key}
              className={active === tab.key ? "tab active" : "tab"}
              onClick={() => setActive(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        <ActiveComponent />
      </main>
    </div>
  );
}
