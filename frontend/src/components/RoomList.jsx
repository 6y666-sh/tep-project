import { useEffect, useState } from "react";
import { ROOMS } from "../rooms.js";
import { PLANT_OVERVIEW } from "../equipmentVars.js";
import { faultToEquipmentId } from "../faultEquipment.js";

function Clock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="cctv-time">{now.toLocaleTimeString("ko-KR", { hour12: false })}</span>;
}

export default function RoomList({ sensorLogs, onSelect }) {
  // PlantOverview와 같은 이유로 resolved를 체크해야 한다 — sensorLogs[0](가장
  // 최근 로그) 하나만 보면, 상황종료로 이미 확인 처리한 결함인데도(또는
  // 시뮬레이션 중 결함 로그 바로 다음이 아직 안 온 상태라면) "아직 이상 상태"로
  // 잘못 표시될 수 있다. "아직 상황종료 안 한 이상이 있는지"를 최근 로그들
  // 중에서 찾아야 정확하다.
  const latestUnresolved = sensorLogs.find((r) => r.is_anomaly && !r.resolved);
  const hasFault = !!latestUnresolved && !!faultToEquipmentId(latestUnresolved.fault_number);

  return (
    <div className="equip-status-grid">
      {ROOMS.map((room) => {
        const danger = room.functional && hasFault;
        return (
          <button key={room.id} className={`equip-status-card ${danger ? "danger" : ""}`} onClick={() => onSelect(room.id)}>
            <div className={`cctv-feed ${danger ? "danger" : ""} ${room.functional ? "" : "offline"}`}>
              <img src={PLANT_OVERVIEW.image} alt="" className="cctv-thumb" />
              <div className="cctv-live">
                <span className="rec-dot" /> {room.functional ? "LIVE" : "OFFLINE"}
              </div>
              {room.functional && <Clock />}
            </div>

            <div className="equip-status-top">
              <div>
                <div className="equip-status-name">{room.name}</div>
                <div className="equip-chart-name-en">{room.sub}</div>
              </div>
              {room.functional ? (
                <span className={`status-pill ${danger ? "err" : "run"}`}>{danger ? "이상" : "정상"}</span>
              ) : (
                <span className="status-pill">N/A</span>
              )}
            </div>

            {!room.functional && (
              <div className="hint" style={{ marginBottom: 0 }}>데모 미지원 (실시간 연동 안 됨)</div>
            )}
          </button>
        );
      })}
    </div>
  );
}
