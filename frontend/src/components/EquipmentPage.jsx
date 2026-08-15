import { useEffect, useState } from "react";
import { listSensorLogs } from "../api.js";
import { getRoom } from "../rooms.js";
import RoomList from "./RoomList.jsx";
import RoomPlaceholder from "./RoomPlaceholder.jsx";
import PlantOverview from "./PlantOverview.jsx";
import EquipmentDetail from "./EquipmentDetail.jsx";

const REFRESH_MS = 5000;

// 화면 단계: 설비실 목록 -> (기능 있는 설비실이면) 전체 공정도 -> 개별 설비 상세.
// initialSelected는 대시보드에서 특정 설비를 바로 열고 싶을 때 쓰는데, 지금
// 구조에서는 그 설비가 속한 "기능 있는 설비실"(room-1)로 바로 들어가야 한다.
export default function EquipmentPage({ initialSelected = null }) {
  const [sensorLogs, setSensorLogs] = useState([]);
  const [error, setError] = useState(null);
  const [room, setRoom] = useState(initialSelected ? "room-1" : null);
  const [selectedEquipment, setSelectedEquipment] = useState(initialSelected);

  // 처음 마운트될 때 한 번만 불러오면, 이 화면에 머물러 있는 동안(시뮬레이션이
  // 돌고 있거나, 다른 곳에서 상황종료를 눌러 resolved가 바뀌어도) 상태등이
  // 갱신이 안 된다. Dashboard와 같은 방식으로 주기적으로 다시 불러온다.
  useEffect(() => {
    let cancelled = false;

    const load = () => {
      listSensorLogs(50)
        .then((rows) => {
          if (!cancelled) setSensorLogs(rows);
        })
        .catch((e) => {
          if (!cancelled) setError(e.message);
        });
    };

    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (error) return <div className="error">데이터를 불러오지 못했습니다: {error}</div>;

  if (!room) {
    return (
      <>
        <div className="section-head">
          <div className="section-title">설비실 목록</div>
        </div>
        <p className="hint">
          설비실을 클릭하면 그 구역의 전체 공정도를 볼 수 있습니다. 데모에서는 설비실 1만 실제 데이터와 연동됩니다.
        </p>
        <RoomList sensorLogs={sensorLogs} onSelect={setRoom} />
      </>
    );
  }

  const roomInfo = getRoom(room);

  if (!roomInfo?.functional) {
    return <RoomPlaceholder roomId={room} onBack={() => setRoom(null)} />;
  }

  if (selectedEquipment) {
    return (
      <EquipmentDetail
        equipmentId={selectedEquipment}
        sensorLogs={sensorLogs}
        onBack={() => setSelectedEquipment(null)}
      />
    );
  }

  return (
    <div className="card">
      <div className="equip-detail-head">
        <button onClick={() => setRoom(null)}>← 설비실 목록으로</button>
        <div>
          <h2 style={{ marginBottom: 2 }}>{roomInfo.name} — 전체 공정도</h2>
          <div className="hint" style={{ marginBottom: 0 }}>{roomInfo.sub}</div>
        </div>
      </div>
      <p className="hint">
        상태등(●)을 클릭하면 해당 설비의 상세 도식과 실시간 값을 볼 수 있습니다.
        <span className="plant-legend"><i className="dot ok" /> 정상 <i className="dot danger" /> 이상</span>
      </p>
      <PlantOverview sensorLogs={sensorLogs} onSelect={setSelectedEquipment} />
    </div>
  );
}
