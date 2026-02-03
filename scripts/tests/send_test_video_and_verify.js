#!/usr/bin/env node
/**
 * 테스트 영상을 RTMP로 전송한 뒤, 학생 페이지에서 WebRTC 재생되는지 Playwright로 검증
 *
 * 요구: ffmpeg, node, frontend/node_modules (NODE_PATH 자동 설정)
 * 사용: node scripts/tests/send_test_video_and_verify.js
 *
 * HTTPS 프론트엔드에서 재생 검증하려면:
 *   백엔드 기동 시 MODE=standalone WHEP_BASE_URL=https://localhost:5175 설정
 *   (프론트와 같은 origin으로 WHEP 요청 → Vite proxy /live → MediaMTX 8889)
 * RTMP_URL은 MediaMTX가 수신하는 주소(기본 rtmp://localhost:1935/live/stream)
 */
const { spawn } = require('child_process');
const path = require('path');

const RTMP_URL = process.env.RTMP_URL || 'rtmp://localhost:1935/live/stream';
const STREAM_DURATION_SEC = parseInt(process.env.STREAM_DURATION_SEC || '45', 10);
const STUDENT_URL = process.env.STUDENT_URL || 'https://localhost:5175/?name=ice-test#/student';
const INSECURE_HTTPS = process.env.INSECURE_HTTPS === '1';
const TIMEOUT_MS = parseInt(process.env.TIMEOUT_MS || '40000', 10);

function runFfmpegStream() {
  // 테스트 패턴: 색상 그라데이션 + 1kHz 사인파, 저지연 인코딩
  const args = [
    '-re',
    '-f', 'lavfi', '-i', `testsrc=duration=${STREAM_DURATION_SEC}:size=1280x720:rate=30`,
    '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=' + STREAM_DURATION_SEC,
    '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
    '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '128k',
    '-f', 'flv',
    RTMP_URL,
  ];
  const ff = spawn('ffmpeg', args, {
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stderr = '';
  ff.stderr.on('data', (d) => { stderr += d.toString(); });
  ff.on('error', (err) => {
    console.error('ffmpeg spawn error:', err.message);
    process.exit(1);
  });
  ff.on('exit', (code) => {
    if (code !== 0 && code !== null) {
      console.error('ffmpeg exit', code);
      console.error(stderr.slice(-1500));
    }
  });
  return ff;
}

async function runPlaywrightTest() {
  const projectRoot = path.resolve(__dirname, '../..');
  const frontendNodeModules = path.join(projectRoot, 'frontend', 'node_modules');
  const scriptDir = path.join(__dirname, 'webrtc_ice_result.js');
  return new Promise((resolve, reject) => {
    const env = {
      ...process.env,
      NODE_PATH: frontendNodeModules,
      STUDENT_URL,
      INSECURE_HTTPS: INSECURE_HTTPS ? '1' : '',
      TIMEOUT_MS: String(TIMEOUT_MS),
    };
    const node = spawn('node', [scriptDir], {
      env,
      stdio: 'inherit',
      cwd: projectRoot,
    });
    node.on('error', reject);
    node.on('exit', (code) => {
      if (code === 0) resolve();
      else reject(new Error('Playwright test exited with ' + code));
    });
  });
}

async function main() {
  console.log('RTMP URL:', RTMP_URL);
  console.log('Stream duration:', STREAM_DURATION_SEC, 's');
  console.log('Student URL:', STUDENT_URL);
  console.log('');

  const ff = runFfmpegStream();
  console.log('Started ffmpeg (PID %s), waiting for stream to be ready...', ff.pid);
  
  // MediaMTX에 스트림이 준비될 때까지 대기 (최대 20초)
  let streamReady = false;
  for (let i = 0; i < 20; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    try {
      const http = require('http');
      const res = await new Promise((resolve, reject) => {
        const req = http.get('http://localhost:8889/v2/paths/list', (res) => {
          let data = '';
          res.on('data', (chunk) => { data += chunk; });
          res.on('end', () => {
            try {
              const paths = JSON.parse(data);
              if (paths.items && paths.items.some(p => p.name === 'live/stream' && p.sourceReady)) {
                resolve(true);
              } else {
                resolve(false);
              }
            } catch (e) {
              resolve(false);
            }
          });
        });
        req.on('error', () => resolve(false));
        req.setTimeout(2000, () => { req.destroy(); resolve(false); });
      });
      if (res) {
        streamReady = true;
        console.log('✅ Stream ready in MediaMTX');
        break;
      }
    } catch (e) {
      // Continue waiting
    }
  }
  
  if (!streamReady) {
    console.warn('⚠️ Stream not ready in MediaMTX, proceeding anyway...');
  }

  let testOk = false;
  try {
    console.log('Running Playwright test...');
    await runPlaywrightTest();
    testOk = true;
  } finally {
    ff.kill('SIGTERM');
    try {
      await new Promise((r) => setTimeout(r, 500));
      if (ff.exitCode === null) ff.kill('SIGKILL');
    } catch (_) {}
  }

  if (testOk) {
    console.log('\n✅ Test video was sent and student page received/played the stream.');
    process.exit(0);
  } else {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
