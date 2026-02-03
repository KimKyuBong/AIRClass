/**
 * WebRTC SDP 호환성 테스트 스크립트
 * Node.js 환경에서 실행하여 브라우저 없이 테스트
 */

const http = require('http');

// 테스트용 minimal SDP (curl로 성공한 형식)
const minimalSdp = `v=0
o=- 123456789 987654321 IN IP4 0.0.0.0
s=-
t=0 0
a=group:BUNDLE 0
a=ice-lite
m=video 9 UDP/TLS/RTP/SAVPF 96
c=IN IP4 0.0.0.0
a=mid:0
a=recvonly
a=rtcp-mux
a=rtpmap:96 H264/90000
a=fmtp:96 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f
a=ice-ufrag:abcdefgh
a=ice-pwd:abcdefghijklmnopqrstuvwx
a=fingerprint:sha-256 AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99
a=setup:active
`;

async function testWebRTC() {
    try {
        console.log('🔑 1. JWT 토큰 발급 중...');
        
        // 토큰 발급
        const tokenResponse = await fetch('http://localhost:8000/api/token?user_type=student&user_id=test-browser&action=read', {
            method: 'POST'
        });
        
        if (!tokenResponse.ok) {
            throw new Error(`토큰 발급 실패: ${tokenResponse.status}`);
        }
        
        const tokenData = await tokenResponse.json();
        const token = tokenData.token;
        const whepUrl = tokenData.webrtc_url;
        
        console.log('✅ 토큰 발급 성공');
        console.log(`📍 노드: ${tokenData.node_name || tokenData.mode}`);
        console.log(`🔗 WHEP URL: ${whepUrl}`);
        console.log(`🔑 Token: ${token.substring(0, 50)}...`);
        
        console.log('\n🌐 2. WHEP 요청 전송 중...');
        console.log(`SDP 길이: ${minimalSdp.length}자`);
        console.log(`SDP 내용:\n${minimalSdp}`);
        
        // WHEP 요청
        const whepResponse = await fetch(whepUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/sdp'
            },
            body: minimalSdp
        });
        
        console.log(`\n📥 응답 상태: ${whepResponse.status} ${whepResponse.statusText}`);
        
        if (!whepResponse.ok) {
            const errorText = await whepResponse.text();
            console.error(`❌ WHEP 요청 실패:`);
            console.error(`상태 코드: ${whepResponse.status}`);
            console.error(`응답 내용: ${errorText}`);
            return;
        }
        
        const answerSdp = await whepResponse.text();
        console.log('✅ WHEP 요청 성공!');
        console.log(`📥 Answer SDP 길이: ${answerSdp.length}자`);
        console.log(`Answer SDP 첫 500자:\n${answerSdp.substring(0, 500)}`);
        
        // Session URL 확인
        const sessionUrl = whepResponse.headers.get('Location');
        if (sessionUrl) {
            console.log(`🔗 Session URL: ${sessionUrl}`);
        }
        
        console.log('\n✅ 테스트 완료! WebRTC 연결이 성공적으로 설정되었습니다.');
        
    } catch (error) {
        console.error('❌ 테스트 실패:', error.message);
        console.error(error.stack);
    }
}

// Node.js 18+ fetch 지원 확인
if (typeof fetch === 'undefined') {
    console.error('❌ Node.js 18+ 또는 node-fetch 패키지가 필요합니다.');
    console.log('💡 해결 방법:');
    console.log('   1. Node.js 18+ 사용');
    console.log('   2. 또는: npm install node-fetch');
    process.exit(1);
}

testWebRTC();
