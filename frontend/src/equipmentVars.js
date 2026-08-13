// TEP(Tennessee Eastman Process) 설비별 도식 + 관련 센서 변수 매핑.
//
// sensor_values는 [xmeas_1, ..., xmeas_41, xmv_1, ..., xmv_11] 순서의 52개
// 값 배열이다(anomaly-check 요청 윈도우의 마지막 시점 값). xmeas_n은 배열 인덱스
// (n-1), xmv_n은 배열 인덱스 (40 + n)에 해당한다.
//
// 각 설비 도식 이미지(assets/equipment/*.png)에는 빈 박스(placeholder)가 미리
// 그려져 있고, boxes 배열의 xPct/yPct는 그 박스의 중심 좌표를 이미지 가로/세로
// 대비 퍼센트로 표시한 값이다(OpenCV로 이미지의 사각형 윤곽선을 검출해서 얻음).
// 프론트에서는 이 퍼센트 좌표에 값 라벨을 절대위치로 얹는다.
//
// 변수 하나당 도식에 박스가 하나씩 있는데, 설비마다 관련 변수가 더 많은 경우
// (예: 반응기 냉각수 출구온도/유량) 도식에 박스가 없어서 secondaryVars로 따로
// 빼서 상세 페이지 하단에 칩(chip) 형태로만 보여준다.
import reactorImg from "./assets/equipment/reactor.webp";
import condenserImg from "./assets/equipment/condenser.webp";
import compressorImg from "./assets/equipment/compressor.webp";
import separatorImg from "./assets/equipment/separator.webp";
import stripperImg from "./assets/equipment/stripper.webp";
import plantOverviewImg from "./assets/equipment/plant_overview.webp";

export const EQUIPMENT_GROUPS = [
  {
    id: "reactor",
    name: "반응기",
    nameEn: "Reactor",
    image: reactorImg,
    boxes: [
      { label: "압력", unit: "kPa", index: 6, xPct: 63.3, yPct: 31.2 }, // xmeas_7
      { label: "레벨", unit: "%", index: 7, xPct: 63.3, yPct: 51.6 }, // xmeas_8
      { label: "온도", unit: "°C", index: 8, xPct: 63.3, yPct: 71.9 }, // xmeas_9
    ],
    secondaryVars: [
      { label: "냉각수 출구온도", unit: "°C", index: 20 }, // xmeas_21
      { label: "냉각수 유량", unit: "%", index: 50 }, // xmv_10
    ],
  },
  {
    id: "condenser",
    name: "응축기",
    nameEn: "Condenser",
    image: condenserImg,
    boxes: [
      { label: "냉각수 출구온도", unit: "°C", index: 21, xPct: 72.1, yPct: 26.2 }, // xmeas_22
      { label: "냉각수 유량", unit: "%", index: 51, xPct: 27.7, yPct: 72.9 }, // xmv_11
    ],
    secondaryVars: [],
  },
  {
    id: "compressor",
    name: "압축기",
    nameEn: "Compressor",
    image: compressorImg,
    boxes: [
      { label: "재순환 밸브", unit: "%", index: 44, xPct: 41.5, yPct: 15.6 }, // xmv_5
      { label: "재순환 유량", unit: "kscmh", index: 4, xPct: 32.8, yPct: 28.3 }, // xmeas_5
      { label: "작업량", unit: "kW", index: 19, xPct: 72.4, yPct: 65.5 }, // xmeas_20
    ],
    secondaryVars: [],
  },
  {
    id: "separator",
    name: "기액분리기",
    nameEn: "Separator",
    image: separatorImg,
    boxes: [
      { label: "온도", unit: "°C", index: 10, xPct: 62.9, yPct: 38.5 }, // xmeas_11
      { label: "레벨", unit: "%", index: 11, xPct: 62.9, yPct: 50.0 }, // xmeas_12
      { label: "압력", unit: "kPa", index: 12, xPct: 62.9, yPct: 61.5 }, // xmeas_13
      { label: "액체 유량", unit: "%", index: 46, xPct: 37.1, yPct: 50.0 }, // xmv_7
    ],
    secondaryVars: [],
  },
  {
    id: "stripper",
    name: "스트리퍼",
    nameEn: "Stripper",
    image: stripperImg,
    boxes: [
      { label: "레벨", unit: "%", index: 14, xPct: 60.5, yPct: 24.5 }, // xmeas_15
      { label: "압력", unit: "kPa", index: 15, xPct: 39.5, yPct: 47.3 }, // xmeas_16
      { label: "온도", unit: "°C", index: 17, xPct: 60.5, yPct: 61.3 }, // xmeas_18
    ],
    secondaryVars: [{ label: "스팀 유량", unit: "kg/h", index: 18 }], // xmeas_19
  },
];

// 전체 공정 흐름도(반응기→응축기→분리기→압축기 재순환/스트리퍼) 한 장짜리 도식.
// 도식에 미리 그려진 빈 원(상태등 자리)의 좌표를 OpenCV로 검출해서 얻었다.
// 압축기는 이 도식에 별도 상태등이 없는데, 지금 결함-설비 매핑(faultEquipment.js)
// 자체가 압축기를 원인 설비로 잡는 결함이 없어서(= 압축기 단독 이상 감지는 아직
// 근거가 없음) 상태등을 안 그려도 정보 손실이 없다.
// 같은 설비에 상태등이 여러 개인 경우(반응기 2개, 분리기 2개, 스트리퍼 3개)는
// 전부 그 설비의 상태를 그대로 반복해서 보여준다 — 밸브 단위로 개별 건강 상태를
// 판단할 데이터는 없고, 지금 가진 건 "설비 단위" 정상/이상 정보뿐이라는 걸
// 시각적으로 정직하게 반영한 것.
export const PLANT_OVERVIEW = {
  image: plantOverviewImg,
  dots: [
    { equipmentId: "reactor", xPct: 18.8, yPct: 42.3 },
    { equipmentId: "reactor", xPct: 18.8, yPct: 68.8 },
    { equipmentId: "condenser", xPct: 40.7, yPct: 42.3 },
    { equipmentId: "separator", xPct: 60.9, yPct: 44.6 },
    { equipmentId: "separator", xPct: 60.9, yPct: 60.7 },
    { equipmentId: "stripper", xPct: 91.2, yPct: 26.2 },
    { equipmentId: "stripper", xPct: 91.2, yPct: 70.8 },
    { equipmentId: "stripper", xPct: 92.7, yPct: 79.2 },
  ],
};

export function getEquipment(id) {
  return EQUIPMENT_GROUPS.find((e) => e.id === id);
}

// 최신 sensor_values(JSON 문자열)를 파싱해서 52개 값 배열로 반환. 실패하면 null.
export function parseSensorValues(sensorValuesJson) {
  if (!sensorValuesJson) return null;
  try {
    return JSON.parse(sensorValuesJson);
  } catch {
    return null;
  }
}
