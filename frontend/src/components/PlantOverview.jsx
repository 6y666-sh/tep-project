import { PLANT_OVERVIEW, getEquipment } from "../equipmentVars.js";
import { faultToEquipmentId } from "../faultEquipment.js";
import { faultLabel } from "../faultNames.js";

// 전체 공정도 한 장 위에 설비별 상태등(초록/빨강)을 얹은 뷰.
// "현재 상태" = "아직 작업자가 상황종료로 확인 안 한 이상이 있는지".
export default function PlantOverview({ sensorLogs, onSelect }) {
  // sensorLogs[0](가장 최근 로그 1건)만 보면 안 된다 — 시뮬레이션 모드처럼
  // 로그가 계속 새로 쌓이는 상황에서는, 결함이 뜬 바로 다음 윈도우가 정상으로
  // 나오기만 해도 sensorLogs[0]이 바뀌면서 "아직 확인 안 한 결함"인데 점이
  // 초록으로 돌아가버린다(AlertOverlay가 사라지는 것과 같은 종류의 버그).
  // 최근 로그들 중 "아직 상황종료 안 한 이상" 중 제일 최신 걸 찾아야 한다.
  const latestUnresolved = sensorLogs.find((r) => r.is_anomaly && !r.resolved);
  const faultyEquipmentId = latestUnresolved ? faultToEquipmentId(latestUnresolved.fault_number) : null;

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
            title={`${getEquipment(dot.equipmentId)?.name} — ${isFaulty ? faultLabel(latestUnresolved?.fault_number) : "정상"}`}
            onClick={() => onSelect(dot.equipmentId)}
          />
        );
      })}
    </div>
  );
}
