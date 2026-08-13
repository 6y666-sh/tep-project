import { useState } from "react";
import { faultLabel } from "../faultNames.js";
import { faultToEquipmentId } from "../faultEquipment.js";
import { getEquipment } from "../equipmentVars.js";

function formatTime(iso) {
  return new Date(iso).toLocaleString("ko-KR", { hour12: false });
}

// 페이지가 뭐든 상관없이(App.jsx 최상단에서 렌더) 화면 전체를 덮는 긴급 알림.
// 실제 현장이라면 이상탐지가 사람이 누르는 "테스트" 버튼이 아니라 센서에서
// 자동으로 들어오겠지만, 지금은 스트리밍 인프라가 없어 "이상탐지 테스트"
// 화면에서 수동으로 트리거한 결과를 그대로 이 알림에 흘려보내는 구조다.
export default function AlertOverlay({ alert, onResolve }) {
  const [resolving, setResolving] = useState(false);

  if (!alert) return null;

  const equipmentId = faultToEquipmentId(alert.fault_number);
  const equipment = equipmentId ? getEquipment(equipmentId) : null;

  const handleResolve = async () => {
    setResolving(true);
    try {
      await onResolve(alert.id);
    } finally {
      setResolving(false);
    }
  };

  return (
    <div className="alert-overlay">
      <div className="alert-box">
        <div className="alert-icon">⚠</div>
        <div className="alert-title">긴급 상황 감지</div>
        <div className="alert-fault">{faultLabel(alert.fault_number)}</div>
        {equipment && <div className="alert-equipment">발생 설비: {equipment.name}</div>}
        <div className="alert-meta">
          확신도 {(alert.confidence * 100).toFixed(1)}% · {formatTime(alert.created_at)}
        </div>
        <button className="alert-resolve" onClick={handleResolve} disabled={resolving}>
          {resolving ? "처리 중..." : "상황종료 (조치 완료)"}
        </button>
      </div>
    </div>
  );
}
