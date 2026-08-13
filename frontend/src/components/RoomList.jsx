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
  const latest = sensorLogs[0];
  const hasFault = latest?.is_anomaly && !!faultToEquipmentId(latest.fault_number);

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
