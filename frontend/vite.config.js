import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "" 로 두면 배포 시 FastAPI가 서빙하는 상대경로에서도 정적 파일을
// 올바르게 찾는다 (절대경로 "/"로 두면 서브패스 배포 시 깨질 수 있어서)
export default defineConfig({
  plugins: [react()],
});
