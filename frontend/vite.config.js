import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import basicSsl from '@vitejs/plugin-basic-ssl'

// Docker 환경에서는 'main'을, 로컬에서는 'localhost'를 사용
const BACKEND_HOST = process.env.BACKEND_HOST || 'localhost';
const MEDIAMTX_HOST = process.env.MEDIAMTX_HOST || 'localhost';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    svelte(),
    basicSsl()
  ],
  server: {
    // HTTPS 활성화 및 외부 접속 허용
    host: true, 
    https: true,
    proxy: {
      // API 요청을 백엔드(HTTP)로 프록시
      '/api': {
        target: `http://${BACKEND_HOST}:8000`,
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: `ws://${BACKEND_HOST}:8000`,
        ws: true,
        changeOrigin: true,
        secure: false
      },
      // MediaMTX WebRTC 프록시 (WHIP/WHEP)
      // WHIP: WebRTC-HTTP Ingestion Protocol (교사 PC 화면 공유 - 송신)
      // WHEP: WebRTC-HTTP Egress Protocol (학생 스트림 시청 - 수신)
      '/live': {
        target: `http://${MEDIAMTX_HOST}:8889`,
        changeOrigin: true,
        secure: false,
        configure: (proxy, _options) => {
          // 프록시 에러 로깅 (디버깅용)
          proxy.on('error', (err, _req, _res) => {
            console.error('[Vite Proxy Error]', err.message);
          });
        }
      }
    }
  }
})
