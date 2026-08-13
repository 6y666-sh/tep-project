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

export function listSensorLogs(limit = 50) {
  return request(`/sensor-logs?limit=${limit}`);
}

export function listGuideLogs(limit = 50) {
  return request(`/guide-logs?limit=${limit}`);
}
