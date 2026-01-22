# 📊 Performance Testing & Diagnostic Guide

## 🎯 Overview

This guide helps you identify and resolve performance bottlenecks in the WebRTC streaming pipeline:

```
Android App (Encoder) → RTMP → MediaMTX → WebRTC → Browser (Decoder)
```

## 🚀 Quick Start

### 1. **Update Android App**
Rebuild the app to include performance monitoring:
```bash
cd /Users/hwansi/Project/AirClass/ScreenCaptureApp/android
./gradlew installDebug
```

### 2. **Start Backend Server**
```bash
cd /Users/hwansi/Project/AirClass/ScreenCaptureApp/backend
python main.py
```

### 3. **Run Diagnostic Script**
```bash
cd /Users/hwansi/Project/AirClass/ScreenCaptureApp/backend
python performance_diagnostic.py
```

### 4. **Start Streaming**
- Open Android app
- Click **Settings (⚙️)** button
- Configure streaming settings
- Click **Start Streaming**

### 5. **Monitor Performance**

#### Android App Monitoring
```bash
~/Library/Android/sdk/platform-tools/adb logcat | grep "PERFORMANCE STATS"
```

**What to look for:**
- **Actual FPS vs Target FPS**: Should be 90%+ of target
- **Frame Drop Rate**: Should be < 2%
- **Memory Usage**: Should be < 80%
- **Frame Timing**: Max interval should be < 2x expected

#### Browser Monitoring
1. Open: http://localhost:8000/viewer
2. Click **"📊 Show Stats"** button in top-right
3. Monitor real-time metrics

**What to look for:**
- **FPS**: Should match target (30/60 fps)
- **Bitrate**: Should be stable (matching configured bitrate)
- **Packets Lost**: Should be < 2%
- **Jitter**: Should be < 30ms
- **Frames Dropped**: Should be < 2%
- **Decode Time**: Should be < 33ms (for 30fps) or < 16ms (for 60fps)
- **Buffer Health**: Should be > 0.5s

## 🔍 Performance Metrics Explained

### Android Encoder Metrics

| Metric | Good | Warning | Critical | What It Means |
|--------|------|---------|----------|---------------|
| **Actual FPS** | >90% of target | 70-90% | <70% | How many frames per second are being encoded |
| **Frame Drop Rate** | <2% | 2-5% | >5% | Percentage of frames dropped due to encoding overload |
| **Avg Frame Interval** | Close to expected | 1.5x expected | >2x expected | Time between frames (should be consistent) |
| **Memory Usage** | <70% | 70-85% | >85% | App memory consumption |

**Expected Frame Intervals:**
- 60 fps → 16.7ms
- 30 fps → 33.3ms
- 24 fps → 41.7ms
- 15 fps → 66.7ms

### Browser Decoder Metrics

| Metric | Good | Warning | Critical | What It Means |
|--------|------|---------|----------|---------------|
| **FPS** | Matches target | 70-90% | <70% | Frames being displayed per second |
| **Packet Loss** | <1% | 1-3% | >3% | Network packets lost in transmission |
| **Jitter** | <20ms | 20-40ms | >40ms | Variation in packet arrival time |
| **Decode Time** | <16ms (60fps) / <33ms (30fps) | Up to 2x | >2x | Time to decode each frame |
| **Buffer Health** | >1.0s | 0.5-1.0s | <0.5s | How much video is buffered ahead |

## 🐛 Common Issues & Solutions

### Issue 1: Low FPS on Android (Encoder Bottleneck)

**Symptoms:**
```
📊 PERFORMANCE STATS
   Target FPS: 60
   Actual FPS: 42.3  ⚠️
   Frame Drop Rate: 8.5%  ⚠️
```

**Cause:** Encoder cannot keep up with target framerate

**Solutions:**
1. **Reduce FPS**: 60 → 30 fps (maintains quality, reduces load)
2. **Reduce Resolution**: 4K → QHD or QHD → FHD
3. **Lower Bitrate**: Try 15-20 Mbps instead of 25+ Mbps
4. **Test on Real Device**: Emulator has limited encoding capability
5. **Check Other Apps**: Close background apps consuming resources

**How to fix:**
```kotlin
// In app settings (FAB button):
FPS: 30 fps (instead of 60)
Bitrate: 15-20 Mbps
Resolution: Keep FHD (1920x1080)
```

---

### Issue 2: High Frame Drops (Encoder Overload)

**Symptoms:**
```
Frame Drop Rate: 12.3%  ⚠️
Max Interval: 156 ms  (expected: 16.7ms)
```

**Cause:** Encoder is overwhelmed and skipping frames

**Solutions:**
1. **Reduce Bitrate First**: Lower to 10-15 Mbps
2. **Then Reduce FPS**: 60 → 30 fps
3. **Check Device Temperature**: Throttling may occur when hot
4. **Profile Selection**: Ensure using hardware encoder

---

### Issue 3: High Packet Loss (Network Bottleneck)

**Symptoms in Browser:**
```
Packets Lost: 235 (5.2%)  ⚠️
Jitter: 67 ms  ⚠️
```

**Cause:** Network cannot handle the bitrate or has instability

**Solutions:**
1. **Reduce Bitrate**: Try 8-10 Mbps instead of 20+ Mbps
2. **Check WiFi Signal**: Use 5GHz band if available
3. **Test Wired Connection**: Connect laptop via ethernet
4. **Check Network Load**: Other devices streaming?
5. **Emulator Network**: Virtual network may have limitations

---

### Issue 4: Slow Decode Time (Browser/GPU Bottleneck)

**Symptoms in Browser:**
```
Decode Time: 48 ms  ⚠️  (target: <33ms for 30fps)
Frames Dropped: 89 (4.2%)  ⚠️
```

**Cause:** Browser/GPU cannot decode fast enough

**Solutions:**
1. **Close Other Browser Tabs**: Free up GPU resources
2. **Update Graphics Drivers**: Especially on Windows/Linux
3. **Try Different Browser**: Chrome/Edge often better for WebRTC
4. **Reduce Video Resolution**: Lower incoming resolution
5. **Check GPU Usage**: Monitor task manager during playback

---

### Issue 5: Emulator Performance Limitations

**Symptoms:**
```
Target: 60 fps @ 25 Mbps
Actual: 35 fps with high drops
Memory: 78% usage
```

**Cause:** Android emulator has limited hardware encoding support

**Solution:**
```bash
# Deploy to physical device for real performance testing
~/Library/Android/sdk/platform-tools/adb install -r android/app/build/outputs/apk/debug/app-debug.apk

# Or use emulator with lower settings:
FPS: 30 fps
Resolution: FHD (1920x1080)
Bitrate: 10-15 Mbps
```

---

## 📈 Recommended Settings by Use Case

### High Quality (Classroom Recording)
```
Resolution: FHD (1920x1080)
FPS: 30 fps
Bitrate: 15 Mbps
Audio: Enabled

Expected: Smooth playback, low latency (~200-300ms)
```

### Ultra High Quality (Presentation/Demo)
```
Resolution: QHD (2560x1440)
FPS: 30 fps
Bitrate: 20-25 Mbps
Audio: Enabled

Note: Requires powerful device, may not work on emulator
```

### Low Latency (Real-time Interaction)
```
Resolution: FHD (1920x1080)
FPS: 24 fps
Bitrate: 8-10 Mbps
Audio: Enabled

Expected: ~150-200ms latency
```

### Testing on Emulator
```
Resolution: FHD (1920x1080)
FPS: 24 fps
Bitrate: 10 Mbps
Audio: Enabled

Note: Emulator limitations may still cause issues
```

---

## 🔧 MediaMTX Optimization

For lower latency, update `mediamtx.yml`:

```yaml
paths:
  live:
    readTimeout: 10s
    writeTimeout: 10s
    readBufferCount: 1      # Minimize buffering
    writeQueueSize: 512      # Reduce queue for lower latency
```

Restart MediaMTX after changes:
```bash
# Kill current process
lsof -ti:8889 | xargs kill -9
lsof -ti:1935 | xargs kill -9

# Restart via main.py
cd /Users/hwansi/Project/AirClass/ScreenCaptureApp/backend
python main.py
```

---

## 📊 Performance Testing Checklist

- [ ] **Pre-Testing**
  - [ ] Backend server running
  - [ ] Android app installed with latest code
  - [ ] Device/emulator connected
  - [ ] Browser opened to viewer page

- [ ] **During Testing**
  - [ ] Monitor Android logcat for encoder stats
  - [ ] Enable browser performance stats
  - [ ] Record metrics every 30 seconds
  - [ ] Note any visible stuttering or freezing

- [ ] **Identify Bottleneck**
  - [ ] If Android FPS < target → **Encoder bottleneck**
  - [ ] If high packet loss → **Network bottleneck**
  - [ ] If high decode time → **Browser/GPU bottleneck**
  - [ ] If buffer health low → **Buffering issue**

- [ ] **Apply Solutions**
  - [ ] Start with lowest-impact changes (bitrate reduction)
  - [ ] Test one change at a time
  - [ ] Document what works

- [ ] **Validate**
  - [ ] Actual FPS ≥ 90% of target
  - [ ] Frame drop rate < 2%
  - [ ] Packet loss < 2%
  - [ ] No visible stuttering
  - [ ] Latency < 500ms

---

## 📝 Log Analysis Commands

### Real-time Android Monitoring
```bash
# Full performance stats
~/Library/Android/sdk/platform-tools/adb logcat | grep "PERFORMANCE STATS"

# Just warnings
~/Library/Android/sdk/platform-tools/adb logcat | grep "WARNING"

# Frame-related issues
~/Library/Android/sdk/platform-tools/adb logcat | grep -E "(frame|drop|skip)"

# Clear logs and start fresh
~/Library/Android/sdk/platform-tools/adb logcat -c
~/Library/Android/sdk/platform-tools/adb logcat ScreenCaptureService:I *:S
```

### Browser Console Monitoring
Open browser console (F12) and look for:
```
📊 BROWSER PERFORMANCE STATS
```

Logs appear every 5 seconds with detailed metrics and warnings.

---

## 🎯 Expected Results

### Good Performance Profile
```
Android:
  Actual FPS: 59.2 / 60 (98.7%)
  Frame Drop: 0.8%
  Memory: 245 MB / 512 MB (47.8%)

Network:
  Bitrate: 24.8 Mbps (target: 25 Mbps)
  Packets Lost: 12 (0.3%)
  Jitter: 8 ms

Browser:
  FPS: 59.8
  Decode Time: 12 ms
  Buffer Health: 1.2s
  Frames Dropped: 3 (0.1%)
```

### Problematic Profile (Encoder Bottleneck)
```
Android:
  Actual FPS: 42.3 / 60 (70.5%)  ⚠️
  Frame Drop: 8.2%  ⚠️
  Max Interval: 128 ms (expected: 16.7ms)  ⚠️

→ SOLUTION: Reduce FPS to 30 or lower resolution
```

### Problematic Profile (Network Bottleneck)
```
Network:
  Packets Lost: 432 (6.2%)  ⚠️
  Jitter: 84 ms  ⚠️
  Bitrate: 18.3 Mbps (target: 25 Mbps)

→ SOLUTION: Reduce bitrate to 15 Mbps
```

---

## 🆘 Getting Help

If issues persist after trying solutions:

1. **Run full diagnostic**:
   ```bash
   python performance_diagnostic.py
   ```

2. **Collect logs**:
   ```bash
   ~/Library/Android/sdk/platform-tools/adb logcat -d > android_logs.txt
   ```

3. **Check MediaMTX logs**:
   ```bash
   tail -100 server.log
   ```

4. **Test on real device** (not emulator) to verify hardware capabilities

---

## 📚 Technical Reference

### Encoding Pipeline
```
Screen → MediaProjection → Surface → MediaCodec (H264) → RTMP Muxer → Network
         (Android API)      (buffer)  (hardware enc)     (RootEncoder)
```

### Network Pipeline
```
RTMP (TCP) → MediaMTX → WebRTC (UDP) → Browser
Port 1935     (transcode)  Port 8889    (decode)
```

### Key Performance Factors
1. **Encoder Capability**: Device CPU/GPU power
2. **Network Bandwidth**: Must sustain bitrate + overhead
3. **Network Stability**: Low jitter, no packet loss
4. **Decoder Performance**: Browser/GPU rendering speed
5. **Configuration**: FPS/resolution/bitrate balance

---

## ✅ Success Criteria

Your streaming is performing well when:
- ✅ Android FPS ≥ 90% of target
- ✅ Frame drop rate < 2%
- ✅ Packet loss < 2%
- ✅ Jitter < 30ms
- ✅ Browser FPS matches target
- ✅ No visible stuttering or freezing
- ✅ Latency < 500ms (preferably < 300ms)
- ✅ Can maintain performance for 10+ minutes

Good luck with performance optimization! 🚀
