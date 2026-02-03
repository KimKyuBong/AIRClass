#!/usr/bin/env node
/**
 * 브라우저를 열어서 실제 화면을 보여주는 테스트
 */
const { chromium } = require('playwright');

const STUDENT_URL = process.env.STUDENT_URL || 'https://localhost:5173/?name=test-user#/student';
const INSECURE_HTTPS = process.env.INSECURE_HTTPS === '1';
const TIMEOUT_MS = parseInt(process.env.TIMEOUT_MS || '60000', 10);

async function main() {
  let browser;
  try {
    // headless: false로 설정하여 브라우저 창을 띄움
    browser = await chromium.launch({ 
      headless: false,
      slowMo: 100 // 동작을 천천히 보여줌
    });
    
    const context = await browser.newContext(
      INSECURE_HTTPS ? { ignoreHTTPSErrors: true } : {}
    );
    
    const page = await context.newPage();
    
    // 콘솔 로그 수집
    const logs = [];
    page.on('console', (msg) => {
      const text = msg.text();
      logs.push(text);
      console.log('[CONSOLE]', text);
    });
    
    // 페이지 에러 수집
    page.on('pageerror', (error) => {
      console.error('[PAGE ERROR]', error.message);
    });
    
    console.log('🌐 브라우저를 열어서', STUDENT_URL, '로 이동합니다...');
    await page.goto(STUDENT_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    
    console.log('⏳ 스트림이 재생될 때까지 대기 중... (최대', TIMEOUT_MS / 1000, '초)');
    
    // 비디오 요소가 준비될 때까지 대기
    const result = await Promise.race([
      page.evaluate((timeout) => {
        return new Promise((resolve) => {
          const deadline = Date.now() + timeout;
          const check = () => {
            const video = document.querySelector('video');
            
            // 비디오가 재생 중인지 확인
            if (video && video.readyState >= 2 && video.videoWidth > 0 && video.videoHeight > 0) {
              resolve({ 
                success: true, 
                reason: 'video_playing', 
                videoWidth: video.videoWidth, 
                videoHeight: video.videoHeight,
                readyState: video.readyState
              });
              return;
            }
            
            // 트랙이 수신되었는지 확인
            if (video && video.srcObject && video.srcObject.getTracks && video.srcObject.getTracks().length > 0) {
              const tracks = video.srcObject.getTracks();
              const videoTrack = tracks.find(t => t.kind === 'video');
              if (videoTrack && videoTrack.readyState === 'live') {
                resolve({ 
                  success: true, 
                  reason: 'track_received', 
                  tracks: tracks.length,
                  videoTrackReady: videoTrack.readyState
                });
                return;
              }
            }
            
            if (Date.now() > deadline) {
              resolve({
                success: false,
                reason: 'timeout',
                videoExists: !!video,
                videoReady: video ? video.readyState : null,
                hasSrcObject: video && !!video.srcObject,
                tracksCount: video && video.srcObject && video.srcObject.getTracks ? video.srcObject.getTracks().length : 0
              });
              return;
            }
            setTimeout(check, 500);
          };
          check();
        });
      }, TIMEOUT_MS),
      new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Overall timeout')), TIMEOUT_MS + 5000)
      ),
    ]).catch((e) => ({ success: false, reason: e.message }));
    
    if (result && result.success) {
      console.log('\n✅ 성공! 비디오가 재생되고 있습니다.');
      console.log('결과:', result);
      console.log('\n브라우저 창을 10초간 열어둡니다. 확인 후 닫으세요...');
      
      // 스크린샷 저장
      try {
        await page.screenshot({ path: '/tmp/student_page_test.png', fullPage: true });
        console.log('📸 스크린샷 저장됨: /tmp/student_page_test.png');
      } catch (e) {
        console.log('스크린샷 저장 실패:', e.message);
      }
      
      // 10초 대기 (사용자가 화면 확인)
      await new Promise(resolve => setTimeout(resolve, 10000));
      
      process.exit(0);
    } else {
      console.log('\n❌ 실패:', result);
      console.log('\n마지막 30개 콘솔 로그:');
      logs.slice(-30).forEach((l) => console.log(l));
      
      // 실패해도 스크린샷 저장
      try {
        await page.screenshot({ path: '/tmp/student_page_failed.png', fullPage: true });
        console.log('📸 스크린샷 저장됨: /tmp/student_page_failed.png');
      } catch (e) {
        console.log('스크린샷 저장 실패:', e.message);
      }
      
      // 5초 대기
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      process.exit(1);
    }
  } catch (err) {
    console.error('❌ 에러:', err.message);
    process.exit(1);
  } finally {
    if (browser) {
      console.log('브라우저를 닫습니다...');
      await browser.close();
    }
  }
}

main();
