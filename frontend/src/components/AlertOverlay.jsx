import { useState } from "react";
import { faultLabel } from "../faultNames.js";
import { faultToEquipmentId } from "../faultEquipment.js";
import { getEquipment } from "../equipmentVars.js";

function formatTime(iso) {
  return new Date(iso).toLocaleString("ko-KR", { hour12: false });
}

// 0=정상(오탐), 1~20=결함 번호. 상황종료 전에 작업자가 "진짜" 결함이 뭐였는지
// 직접 골라야 한다 — 이 값이 나중에 RandomForest 재학습용 정답 라벨이 된다.
const FAULT_OPTIONS = ["0", ...Array.from({ length: 20 }, (_, i) => String(i + 1))];

function confirmLabel(key) {
  if (key === "0") return "0 · 정상 (오탐이었음)";
  return `${key} · ${faultLabel(Number(key))}`;
}

// 페이지가 뭐든 상관없이(App.jsx 최상단에서 렌더) 화면 전체를 덮는 긴급 알림.
// alert는 "결함 유형 1개 = 사고 1건"으로 묶인 대표 로그다(App.jsx 참고) —
// 상황종료를 누르면 그 결함 유형으로 아직 미해결인 로그가 전부 한 번에 처리된다.
function AlertBox({ alert, onResolve, className = "" }) {
  const [confirmed, setConfirmed] = useState(""); // "" = 아직 선택 안 함
  const [resolving, setResolving] = useState(false);

  const equipmentId = faultToEquipmentId(alert.fault_number);
  const equipment = equipmentId ? getEquipment(equipmentId) : null;

  const handleResolve = async () => {
    setResolving(true);
    try {
      await onResolve(alert.fault_number, Number(confirmed));
    } finally {
      setResolving(false);
    }
  };

  return (
    <div className={`alert-box ${className}`}>
      <div className="alert-icon">⚠</div>
      <div className="alert-title">긴급 상황 감지</div>
      <div className="alert-fault">{faultLabel(alert.fault_number)}</div>
      {equipment && <div className="alert-equipment">발생 설비: {equipment.name}</div>}
      <div className="alert-meta">
        확신도 {(alert.confidence * 100).toFixed(1)}% · {formatTime(alert.created_at)}
      </div>

      {/* 하네스(src/orchestration/harness.py)가 이상 감지 직후 백그라운드로 자동
          생성해준 조치가이드. confidence가 너무 낮으면 하네스가 아예 안 만들기도
          하고, 만들었어도 폴링 주기(3초)상 아주 잠깐은 비어 보일 수 있다 —
          그래서 없을 땐 아무것도 안 보여주고 조용히 넘어간다. */}
      {alert.guide_text && (
        <div className="alert-guide">
          <div className="alert-guide-lbl">🤖 자동 생성된 조치가이드</div>
          <div className="alert-guide-text">{alert.guide_text}</div>
          {alert.guide_reference_count > 0 && (
            <div className="alert-guide-ref">참고문서 {alert.guide_reference_count}건</div>
          )}
        </div>
      )}

      <div className="alert-confirm">
        <label className="alert-confirm-label">실제 결함이 무엇이었나요?</label>
        <select value={confirmed} onChange={(e) => setConfirmed(e.target.value)}>
          <option value="" disabled>선택하세요</option>
          {FAULT_OPTIONS.map((key) => (
            <option key={key} value={key}>{confirmLabel(key)}</option>
          ))}
        </select>
      </div>

      {confirmed !== "" && (
        <button className="alert-resolve" onClick={handleResolve} disabled={resolving}>
          {resolving ? "처리 중..." : "상황종료 (조치 완료)"}
        </button>
      )}
    </div>
  );
}

// current: 지금 작업 중인 사고(중앙에 크게, 조작 가능).
// next: 대기 중인 다음 사고 미리보기(옆에 작고 반투명하게, 조작 불가) — current를
// 처리하고 나면 여기 있던 게 애니메이션과 함께 중앙으로 넘어간다(promoting prop).
export default function AlertOverlay({ current, next, onResolve, promoting }) {
  if (!current) return null;
  return (
    <div className="alert-overlay">
      <div className="alert-stack">
        {/* key를 fault_number로 걸어서, 같은 결함이 계속 갱신(폴링)되는 동안은
            드롭다운 선택 상태가 유지되고, 다른 결함으로 바뀔 때만(=처리 완료 후
            다음 사고로 넘어갈 때만) 초기화된다. */}
        <AlertBox
          key={current.fault_number}
          alert={current}
          onResolve={onResolve}
          className={promoting ? "alert-box-promote" : ""}
        />
        {next && (
          <div className="alert-peek" key={next.fault_number}>
            <div className="alert-peek-label">⚠ 다음 대기 중인 결함</div>
            <div className="alert-peek-fault">{faultLabel(next.fault_number)}</div>
            {getEquipment(faultToEquipmentId(next.fault_number))?.name && (
              <div className="alert-peek-meta">
                발생 설비: {getEquipment(faultToEquipmentId(next.fault_number)).name}
              </div>
            )}
            <div className="alert-peek-meta">확신도 {(next.confidence * 100).toFixed(1)}%</div>
          </div>
        )}
      </div>
    </div>
  );
}
