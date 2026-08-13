// TEP 데이터셋(Downs & Vogel) 공식 결함 정의 중 잘 알려진 일부만 이름을 붙였다.
// 나머지(16~20 등)는 원 논문에서도 "Unknown"으로 분류돼 별도 설명이 없다.
export const FAULT_NAMES = {
  1: "A/C 공급비 이상 (Step)",
  2: "B 성분 조성 이상 (Step)",
  3: "D 공급 온도 이상 (Step)",
  4: "반응기 냉각수 입구온도 이상 (Step)",
  5: "응축기 냉각수 입구온도 이상 (Step)",
  6: "A 공급 유실 (Step)",
  7: "C 헤더 압력 손실 (Step)",
  8: "A/B/C 공급 조성 변동 (Random)",
  9: "D 공급 온도 변동 (Random)",
  10: "C 공급 온도 변동 (Random)",
  11: "반응기 냉각수 입구온도 변동 (Random)",
  12: "응축기 냉각수 입구온도 변동 (Random)",
  13: "반응 속도 이상 (Slow Drift)",
  14: "반응기 냉각수 밸브 고착",
  15: "응축기 냉각수 밸브 고착",
};

export function faultLabel(faultNumber) {
  if (faultNumber == null) return "정상";
  return FAULT_NAMES[faultNumber] || `Fault ${faultNumber} (미상)`;
}
