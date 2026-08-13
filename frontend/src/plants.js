// 공장 선택 목록. 이 프로젝트는 TEP(Tennessee Eastman Process) 시뮬레이션
// 데이터 하나만 가지고 있어서, 다른 공장을 선택해도 실제로 보여줄 데이터가
// 없다. 그래도 "여러 공장을 스위치해서 볼 수 있는 구조"라는 걸 보여주기 위해
// 드롭다운 자체는 여러 개를 두고, TEP만 실제로 동작하게 하고 나머지는
// 껍데기(선택은 되지만 콘텐츠 영역이 안내 화면으로 바뀜)로 남겨뒀다.
export const PLANTS = [
  { id: "tep", name: "Tennessee Eastman Process", functional: true },
  { id: "plant-2", name: "울산 2공장 (화학)", functional: false },
  { id: "plant-3", name: "여수 3공장 (정유)", functional: false },
];

export function getPlant(id) {
  return PLANTS.find((p) => p.id === id);
}
