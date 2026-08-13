// "설비실" 목록. 실제 공장이라면 라인/구역별로 동일한 형태의 관제실이 여러 개
// 있을 텐데(1공장 설비실, 2공장 설비실 ...), 이 프로젝트는 TEP 시뮬레이션 데이터
// 하나만 가지고 있어서 실제로 서로 다른 공정 데이터를 가진 설비실을 여러 개
// 만들 수는 없다. 그래서 "여러 설비실이 있는 화면 구조"만 보여주기 위해 같은
// 전체 공정도를 복제해서 여러 카드로 늘리되, 실제 데이터가 연동되는 곳은 1번
// 설비실 하나뿐이고 나머지는 껍데기(방문은 가능하지만 실시간 데이터 없음)로
// 남겨뒀다. 실제 서비스로 확장한다면 나머지도 같은 방식으로 그대로 연동하면 된다.
export const ROOMS = [
  { id: "room-1", name: "설비실 1", sub: "TEP 라인 A", functional: true },
  { id: "room-2", name: "설비실 2", sub: "TEP 라인 B", functional: false },
  { id: "room-3", name: "설비실 3", sub: "TEP 라인 C", functional: false },
  { id: "room-4", name: "설비실 4", sub: "TEP 라인 D", functional: false },
];

export function getRoom(id) {
  return ROOMS.find((r) => r.id === id);
}
