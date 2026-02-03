#!/usr/bin/env node
/**
 * WebRTC ICE 결과 확인: 학생 페이지에서 WHEP 연결 후 ICE 상태/영상 수신 여부 확인
 * 사용: node scripts/tests/webrtc_ice_result.js
 * 요구: npx playwright install chromium && npm install playwright (또는 프로젝트 의존성)
 */
const { chromium } = require('playwright');

const STUDENT_URL = process.env.STUDENT_URL || 'http://localhost:5173/student?name=ice-test';
const INSECURE_HTTPS = process.env.INSECURE_HTTPS === '1';
const API_HOST = process.env.API_HOST || 'localhost:8000';
const TIMEOUT_MS = 35000;

async function main() {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext(INSECURE_HTTPS ? { ignoreHTTPSErrors: true } : {});
    const page = await context.newPage();

    const logs = [];
    page.on('console', (msg) => {
      const text = msg.text();
      logs.push(text);
      if (text.includes('ICE') || text.includes('Server ICE') || text.includes('connected') || text.includes('Track') || text.includes('WHEP') || text.includes('error')) {
        console.log('[CONSOLE]', text);
      }
    });

    console.log('Navigating to', STUDENT_URL);
    await page.goto(STUDENT_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });

    // 학생 페이지는 name이 있으면 자동 join → WebRTC 시작
    console.log('Waiting for ICE connected or video ready (max ' + TIMEOUT_MS / 1000 + 's)...');

    const result = await Promise.race([
      page.evaluate((timeout) => {
        return new Promise((resolve) => {
          const deadline = Date.now() + timeout;
          const check = () => {
            const video = document.querySelector('video');
            if (video && video.readyState >= 2 && video.videoWidth > 0) {
              resolve({ success: true, reason: 'video_playing', videoWidth: video.videoWidth, videoHeight: video.videoHeight });
              return;
            }
            if (video && video.srcObject && video.srcObject.getTracks && video.srcObject.getTracks().length > 0) {
              resolve({ success: true, reason: 'track_received', tracks: video.srcObject.getTracks().length });
              return;
            }
            if (Date.now() > deadline) {
              resolve({
                success: false,
                reason: 'timeout',
                videoReady: video ? video.readyState : null,
                hasSrcObject: video && !!video.srcObject,
              });
              return;
            }
            setTimeout(check, 500);
          };
          check();
        });
      }, TIMEOUT_MS),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Overall timeout')), TIMEOUT_MS + 5000)),
    ]).catch((e) => ({ success: false, reason: e.message }));

    if (result && result.success) {
      console.log('\n✅ RESULT: SUCCESS -', result.reason, result);
      process.exit(0);
    }

    console.log('\n❌ RESULT: FAILED -', result);
    console.log('Last 30 console lines:');
    logs.slice(-30).forEach((l) => console.log(l));
    process.exit(1);
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  } finally {
    if (browser) await browser.close();
  }
}

main();
