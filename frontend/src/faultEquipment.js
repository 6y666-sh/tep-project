// 결함 번호 -> 주로 원인이 되는 설비 매핑.
//
// 실제로는 결함 하나가 여러 설비에 연쇄적으로 영향을 줄 수 있다(예: 반응기 이상이
// 압축기 재순환 흐름에도 영향). 하지만 설비별 상세 화면에서 "이 결함은 이 설비
// 문제다"를 바로 보여주려면 단순화가 필요해서, Downs & Vogel(1993) 원 논문의
// 결함 설명 문구를 기준으로 "가장 직접적인 원인 설비" 하나만 골라 매핑했다.
// (이건 실제 현장이라면 인과관계 분석 모델이 따로 필요한 부분이라, 여기서는
// "결함 설명에 등장하는 설비"를 1차 근사치로 쓴다는 것을 문서화해둔다.)
export const FAULT_EQUIPMENT = {
  1: "reactor", // A/C 공급비 이상 -> 반응기 투입 조성
  2: "reactor", // B 성분 조성 이상 -> 반응기 투입 조성
  3: "reactor", // D 공급 온도 이상 -> 반응기 투입 온도
  4: "reactor", // 반응기 냉각수 입구온도 이상
  5: "condenser", // 응축기 냉각수 입구온도 이상
  6: "reactor", // A 공급 유실 -> 반응기 압력/피드 급감
  7: "reactor", // C 헤더 압력 손실 -> 반응기 압력 변동
  8: "reactor", // A/B/C 공급 조성 변동
  9: "reactor", // D 공급 온도 변동
  10: "reactor", // C 공급 온도 변동
  11: "reactor", // 반응기 냉각수 입구온도 변동
  12: "condenser", // 응축기 냉각수 입구온도 변동
  13: "reactor", // 반응 속도 이상
  14: "reactor", // 반응기 냉각수 밸브 고착
  15: "condenser", // 응축기 냉각수 밸브 고착
  // 16~20은 Downs&Vogel 원 논문에서도 "Unknown"으로만 분류돼 특정 설비로
  // 단정할 근거가 없어서 매핑하지 않는다(= 설비 상세 화면엔 안 뜨고, 목록/이력
  // 화면에서 "결함 N (미상)"으로만 표시됨).
};

export function faultToEquipmentId(faultNumber) {
  if (faultNumber == null) return null;
  return FAULT_EQUIPMENT[faultNumber] || null;
}
