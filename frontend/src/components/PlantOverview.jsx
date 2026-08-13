import { PLANT_OVERVIEW, getEquipment } from "../equipmentVars.js";
import { faultToEquipmentId } from "../faultEquipment.js";
import { faultLabel } from "../faultNames.js";

// 전체 공정도 한 장 위에 설비별 상태등(초록/빨강)을 얹은 뷰.
// "현재 상태"는 EquipmentList/EquipmentDetail과 동일하게 가장 최근 판정 하나만 본다.
export default function PlantOverview({ sensorLogs, onSelect }) {
  const latest = sensorLogs[0];
  const faultyEquipmentId = latest?.is_anomaly ? faultToEquipmentId(latest.fault_number) : null;

  return (
    <div className="plant-overview">
      <img src={PLANT_OVERVIEW.image} alt="TEP 전체 공정도" />
      {PLANT_OVERVIEW.dots.map((dot, i) => {
        const isFaulty = dot.equipmentId === faultyEquipmentId;
        return (
          <button
            key={i}
            className={`plant-dot ${isFaulty ? "danger" : "ok"}`}
            style={{ left: `${dot.xPct}%`, top: `${dot.yPct}%` }}
            title={`${getEquipment(dot.equipmentId)?.name} — ${isFaulty ? faultLabel(latest.fault_number) : "정상"}`}
            onClick={() => onSelect(dot.equipmentId)}
          />
        );
      })}
    </div>
  );
}
