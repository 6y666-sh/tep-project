import { PLANT_OVERVIEW } from "../equipmentVars.js";
import { getRoom } from "../rooms.js";

// 데모 범위에 포함되지 않은 설비실(껍데기). 실제 데이터는 없지만 도면 자체는
// 보여줘서 "실제 서비스라면 여기도 1번 설비실과 동일한 방식으로 연동된다"는
// 걸 시각적으로 전달한다. 정상/이상 상태등은 실제 데이터가 없으므로 아예
// 그리지 않는다(없는 데이터를 있는 것처럼 보여주지 않기 위함).
export default function RoomPlaceholder({ roomId, onBack }) {
  const room = getRoom(roomId);

  return (
    <div className="card">
      <div className="equip-detail-head">
        <button onClick={onBack}>← 설비실 목록으로</button>
        <div>
          <h2 style={{ marginBottom: 2 }}>{room?.name}</h2>
          <div className="hint" style={{ marginBottom: 0 }}>{room?.sub}</div>
        </div>
      </div>

      <div className="equip-status-banner">
        이 설비실은 데모 범위에 포함되지 않았습니다. 실제 서비스라면 설비실 1과 동일한 방식으로 실시간 데이터가 연동됩니다.
      </div>

      <div className="plant-overview offline-plant">
        <img src={PLANT_OVERVIEW.image} alt={room?.name} />
      </div>
    </div>
  );
}
