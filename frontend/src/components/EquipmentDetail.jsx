import { getEquipment, parseSensorValues } from "../equipmentVars.js";
import { faultToEquipmentId } from "../faultEquipment.js";
import { faultLabel } from "../faultNames.js";

function formatTime(iso) {
  return new Date(iso).toLocaleString("ko-KR", { hour12: false });
}

// 단일 변수 하나의 시계열을 그 변수 자신의 min~max로만 스케일링해서 그린다.
// (여러 변수를 겹쳐 그리면 스케일이 달라 헷갈린다는 이유로 걷어냈던 방식과
// 반대로, 이번엔 변수별로 그래프를 완전히 분리했기 때문에 굳이 정규화해서
// 0~1로 눌러줄 필요 없이 그 변수의 실제 변동폭을 그대로 보여줄 수 있다.)
function VarSparkline({ raw }) {
  const nums = raw.filter((v) => v != null && !Number.isNaN(v));
  if (nums.length < 2) return null;
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;
  const w = 220;
  const h = 64;
  const step = w / (raw.length - 1);
  const points = raw
    .map((v, i) => (v == null ? null : `${i * step},${h - ((v - min) / span) * h}`))
    .filter(Boolean)
    .join(" ");
  const last = raw[raw.length - 1];
  const lastX = (raw.length - 1) * step;
  const lastY = h - ((last - min) / span) * h;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline fill="none" stroke="var(--blue)" strokeWidth="2" points={points} />
      <circle cx={lastX} cy={lastY} r="3" fill="var(--amber)" />
    </svg>
  );
}

// 설비 도식 아래에 "이 설비의 최근 변수 변화" 추이를 변수별로 각각 따로 그려준다.
function VarTrendGrid({ vars, sensorLogsAscending }) {
  const parsed = sensorLogsAscending
    .filter((l) => l.sensor_values)
    .map((l) => parseSensorValues(l.sensor_values))
    .filter(Boolean);

  if (parsed.length < 2) {
    return <div className="hint" style={{ marginBottom: 0 }}>추이를 그리기엔 데이터가 부족합니다 (2건 이상 필요).</div>;
  }

  return (
    <div className="equip-var-grid">
      {vars.map((v) => {
        const raw = parsed.map((p) => p[v.index]);
        const last = raw[raw.length - 1];
        return (
          <div key={v.label} className="equip-var-card">
            <div className="equip-var-head">
              <span className="equip-var-label">{v.label}</span>
              <span className="equip-var-val">{last != null ? last.toFixed(2) : "-"} {v.unit}</span>
            </div>
            <VarSparkline raw={raw} />
          </div>
        );
      })}
    </div>
  );
}

export default function EquipmentDetail({ equipmentId, sensorLogs, onBack }) {
  const equipment = getEquipment(equipmentId);
  if (!equipment) return null;

  const latest = sensorLogs[0];
  const values = latest ? parseSensorValues(latest.sensor_values) : null;
  const sensorLogsAscending = [...sensorLogs].reverse();
  const allVars = [...equipment.boxes, ...equipment.secondaryVars];

  // 위험 배지는 "아직 상황종료로 확인 안 한 이상" 기준이어야 한다 (PlantOverview/
  // RoomList와 동일한 이유 — resolved 체크 없이 latest만 보면, 이미 확인 처리한
  // 결함도 계속 위험 배지로 남는다). 그래프용 values는 그냥 최신 센서값을 보여주면
  // 되는 거라 resolved와 무관하게 latest를 그대로 쓴다.
  const latestUnresolved = sensorLogs.find((l) => l.is_anomaly && !l.resolved);
  const isRelatedFault = !!latestUnresolved && faultToEquipmentId(latestUnresolved.fault_number) === equipment.id;

  return (
    <div className="card">
      <div className="equip-detail-head">
        <button onClick={onBack}>← 설비 목록으로</button>
        <div>
          <h2 style={{ marginBottom: 2 }}>
            {equipment.name} <span className="equip-chart-name-en">{equipment.nameEn}</span>
          </h2>
          {latest && <div className="hint" style={{ marginBottom: 0 }}>최근 판정: {formatTime(latest.created_at)}</div>}
        </div>
      </div>

      {isRelatedFault ? (
        <div className="equip-status-banner danger">
          ⚠ 이상 감지 — {faultLabel(latestUnresolved.fault_number)} (확신도 {(latestUnresolved.confidence * 100).toFixed(1)}%)
        </div>
      ) : (
        <div className="equip-status-banner ok">✓ 정상 가동 중</div>
      )}

      {!values ? (
        <div className="hint">
          아직 이 설비의 센서 데이터가 없습니다. "이상탐지 테스트"를 실행하면 최신 값이 여기 표시됩니다.
        </div>
      ) : (
        <>
          <div className="equip-detail-image">
            <img src={equipment.image} alt={equipment.name} />
            {equipment.boxes.map((b) => (
              <div
                key={b.label}
                className="equip-detail-box"
                style={{ left: `${b.xPct}%`, top: `${b.yPct}%` }}
              >
                <span className="equip-detail-box-label">{b.label}</span>
                <span className="equip-detail-box-val">
                  {values[b.index] != null ? values[b.index].toFixed(2) : "-"}
                  <span className="equip-detail-box-unit"> {b.unit}</span>
                </span>
              </div>
            ))}
          </div>

          <div className="section-head" style={{ marginTop: 18, marginBottom: 8 }}>
            <div className="section-title">변수별 최근 추이</div>
          </div>
          <VarTrendGrid vars={allVars} sensorLogsAscending={sensorLogsAscending} />
        </>
      )}
    </div>
  );
}
