// 개발 중(vite dev, 보통 5173포트)엔 FastAPI가 8000번 등 다른 포트에서 따로 돌기
// 때문에 절대주소가 필요하다. 배포 시엔 FastAPI가 이 빌드 결과물을 직접 정적
// 서빙해서 같은 origin이 되므로 빈 문자열(상대경로)로 충분하다.
const API_BASE = import.meta.env.DEV ? "http://localhost:8000" : "";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export function checkAnomaly(window) {
  return request("/anomaly-check", {
    method: "POST",
    body: JSON.stringify({ window }),
  });
}

export function getGuide(faultDescription) {
  return request("/get-guide", {
    method: "POST",
    body: JSON.stringify({ fault_description: faultDescription }),
  });
}

export function listSensorLogs(limit = 50, sinceDays = null) {
  const q = sinceDays != null ? `&since_days=${sinceDays}` : "";
  return request(`/sensor-logs?limit=${limit}${q}`);
}

// 알림 큐(App.jsx)용: "아직 상황종료 안 한 이상"만, 발생한 순서대로(오래된 것부터)
// 가져온다. 최신순으로 받아서 프론트에서 뒤집으면 limit에 걸려 잘린 뒷부분(오래된
// 미해결 건)이 아예 안 보일 수 있어서, 서버에 이 순서 그대로 요청한다.
export function listUnresolvedAnomalies(limit = 300) {
  return request(`/sensor-logs?limit=${limit}&unresolved_only=true&oldest_first=true`);
}

export function listGuideLogs(limit = 50) {
  return request(`/guide-logs?limit=${limit}`);
}

export function resolveSensorLog(id, confirmedFaultNumber) {
  return request(`/sensor-logs/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify({ confirmed_fault_number: confirmedFaultNumber }),
  });
}

// 같은 결함(fault_number)으로 아직 미해결인 로그를 한 번에 전부 처리한다.
// AlertOverlay가 이걸 쓴다 — 이유는 history.py의 resolve_sensor_logs_by_fault 참고.
export function resolveSensorLogsByFault(faultNumber, confirmedFaultNumber) {
  return request(`/sensor-logs/resolve-by-fault`, {
    method: "POST",
    body: JSON.stringify({ fault_number: faultNumber, confirmed_fault_number: confirmedFaultNumber }),
  });
}
