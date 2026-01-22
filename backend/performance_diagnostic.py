#!/usr/bin/env python3
"""
Performance Diagnostic Tool for WebRTC Streaming System
Analyzes the entire pipeline: Android App -> RTMP -> MediaMTX -> WebRTC -> Browser
"""

import subprocess
import json
import time
import re
from datetime import datetime
from pathlib import Path


class PerformanceDiagnostic:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "android_metrics": {},
            "mediamtx_metrics": {},
            "browser_metrics": {},
            "bottleneck_analysis": [],
            "recommendations": [],
        }
        self.backend_path = Path(__file__).parent

    def check_mediamtx_config(self):
        """Analyze MediaMTX configuration for performance issues"""
        print("\n" + "=" * 60)
        print("📋 CHECKING MEDIAMTX CONFIGURATION")
        print("=" * 60)

        config_file = self.backend_path / "mediamtx.yml"
        if not config_file.exists():
            print("❌ MediaMTX config not found")
            return

        with open(config_file, "r") as f:
            config = f.read()

        # Check for performance-related settings
        checks = {
            "readTimeout": "Connection timeout settings",
            "writeTimeout": "Write timeout settings",
            "readBufferCount": "Read buffer size",
            "writeQueueSize": "Write queue size (affects latency)",
            "udpMaxPayloadSize": "UDP packet size (affects bandwidth)",
            "runOnReady": "On-ready commands",
            "runOnDemand": "On-demand starting",
        }

        print("\n🔍 Configuration Analysis:")
        for key, description in checks.items():
            if key in config:
                # Extract the value
                match = re.search(f"{key}:\\s*(.+)", config)
                if match:
                    value = match.group(1).strip()
                    print(f"   ✓ {key}: {value}")
                    print(f"     ({description})")
            else:
                print(f"   ⚠️  {key}: Not configured (using default)")

        # Check for specific issues
        if "writeQueueSize" in config:
            match = re.search(r"writeQueueSize:\s*(\d+)", config)
            if match:
                queue_size = int(match.group(1))
                if queue_size > 1024:
                    self.results["bottleneck_analysis"].append(
                        {
                            "component": "MediaMTX",
                            "issue": "Large write queue",
                            "detail": f"writeQueueSize={queue_size} may introduce latency",
                            "severity": "medium",
                        }
                    )

    def check_process_health(self):
        """Check if required processes are running"""
        print("\n" + "=" * 60)
        print("🔍 CHECKING PROCESS HEALTH")
        print("=" * 60)

        processes = {"FastAPI": 8000, "MediaMTX RTMP": 1935, "MediaMTX WebRTC": 8889}

        for name, port in processes.items():
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"], capture_output=True, text=True
                )
                if result.stdout.strip():
                    pid = result.stdout.strip()
                    print(f"   ✓ {name} (port {port}): Running (PID {pid})")
                else:
                    print(f"   ❌ {name} (port {port}): Not running")
                    self.results["bottleneck_analysis"].append(
                        {
                            "component": name,
                            "issue": "Process not running",
                            "detail": f"Required service on port {port} is not active",
                            "severity": "critical",
                        }
                    )
            except Exception as e:
                print(f"   ❌ {name}: Error checking ({e})")

    def check_android_logcat(self, duration=10):
        """Monitor Android logcat for performance metrics"""
        print("\n" + "=" * 60)
        print(f"📱 MONITORING ANDROID LOGCAT ({duration}s)")
        print("=" * 60)
        print("Looking for performance stats...")

        try:
            # Check if adb is available
            result = subprocess.run(
                ["~/Library/Android/sdk/platform-tools/adb", "devices"],
                capture_output=True,
                text=True,
                shell=True,
            )

            if "device" not in result.stdout:
                print("   ⚠️  No Android device/emulator connected")
                return

            print("\n   Capturing logs... (this will take a moment)")

            # Clear logcat and start monitoring
            subprocess.run(
                ["~/Library/Android/sdk/platform-tools/adb", "logcat", "-c"], shell=True
            )

            # Capture logs for specified duration
            result = subprocess.run(
                [
                    f"timeout {duration} ~/Library/Android/sdk/platform-tools/adb logcat ScreenCaptureService:I *:S"
                ],
                capture_output=True,
                text=True,
                shell=True,
            )

            logs = result.stdout

            # Parse performance stats
            if "PERFORMANCE STATS" in logs:
                print("   ✓ Found performance statistics")

                # Extract FPS
                fps_match = re.search(r"Actual FPS:\s*([\d.]+)", logs)
                if fps_match:
                    actual_fps = float(fps_match.group(1))
                    self.results["android_metrics"]["actual_fps"] = actual_fps
                    print(f"      Actual FPS: {actual_fps}")

                    # Check target FPS
                    target_match = re.search(r"Target FPS:\s*(\d+)", logs)
                    if target_match:
                        target_fps = int(target_match.group(1))
                        self.results["android_metrics"]["target_fps"] = target_fps
                        print(f"      Target FPS: {target_fps}")

                        if actual_fps < target_fps * 0.9:
                            self.results["bottleneck_analysis"].append(
                                {
                                    "component": "Android Encoder",
                                    "issue": "FPS below target",
                                    "detail": f"Actual: {actual_fps} fps, Target: {target_fps} fps ({(actual_fps / target_fps) * 100:.1f}%)",
                                    "severity": "high",
                                }
                            )

                # Extract frame drop rate
                drop_match = re.search(r"Frame Drop Rate:\s*([\d.]+)%", logs)
                if drop_match:
                    drop_rate = float(drop_match.group(1))
                    self.results["android_metrics"]["frame_drop_rate"] = drop_rate
                    print(f"      Frame Drop Rate: {drop_rate}%")

                    if drop_rate > 5:
                        self.results["bottleneck_analysis"].append(
                            {
                                "component": "Android Encoder",
                                "issue": "High frame drop rate",
                                "detail": f"Dropping {drop_rate}% of frames",
                                "severity": "high",
                            }
                        )

                # Extract memory usage
                mem_match = re.search(r"Used:\s*(\d+)\s*MB.*?Max:\s*(\d+)\s*MB", logs)
                if mem_match:
                    used_mb = int(mem_match.group(1))
                    max_mb = int(mem_match.group(2))
                    usage_pct = (used_mb / max_mb) * 100
                    self.results["android_metrics"]["memory_usage_mb"] = used_mb
                    self.results["android_metrics"]["memory_usage_pct"] = usage_pct
                    print(
                        f"      Memory: {used_mb} MB / {max_mb} MB ({usage_pct:.1f}%)"
                    )

                    if usage_pct > 80:
                        self.results["bottleneck_analysis"].append(
                            {
                                "component": "Android App",
                                "issue": "High memory usage",
                                "detail": f"Using {usage_pct:.1f}% of available memory",
                                "severity": "medium",
                            }
                        )

            else:
                print("   ⚠️  No performance statistics found in logs")
                print(
                    "      Make sure the app is streaming and performance monitoring is active"
                )

        except Exception as e:
            print(f"   ❌ Error monitoring logcat: {e}")

    def generate_recommendations(self):
        """Generate performance recommendations based on analysis"""
        print("\n" + "=" * 60)
        print("💡 GENERATING RECOMMENDATIONS")
        print("=" * 60)

        # Analyze bottlenecks
        critical = [
            b
            for b in self.results["bottleneck_analysis"]
            if b["severity"] == "critical"
        ]
        high = [
            b for b in self.results["bottleneck_analysis"] if b["severity"] == "high"
        ]
        medium = [
            b for b in self.results["bottleneck_analysis"] if b["severity"] == "medium"
        ]

        if critical:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in critical:
                print(f"   • {issue['component']}: {issue['issue']}")
                print(f"     {issue['detail']}")

        if high:
            print("\n⚠️  HIGH PRIORITY ISSUES:")
            for issue in high:
                print(f"   • {issue['component']}: {issue['issue']}")
                print(f"     {issue['detail']}")

        if medium:
            print("\n⚡ MEDIUM PRIORITY ISSUES:")
            for issue in medium:
                print(f"   • {issue['component']}: {issue['issue']}")
                print(f"     {issue['detail']}")

        # Generate specific recommendations
        recommendations = []

        # Check Android encoder performance
        if (
            "android_metrics" in self.results
            and "actual_fps" in self.results["android_metrics"]
        ):
            actual_fps = self.results["android_metrics"]["actual_fps"]
            target_fps = self.results["android_metrics"].get("target_fps", 60)

            if actual_fps < target_fps * 0.9:
                recommendations.append(
                    {
                        "priority": "high",
                        "component": "Android Encoder",
                        "recommendation": "Reduce FPS or Resolution",
                        "detail": f"Current encoder cannot maintain {target_fps} fps. Try 30 fps or lower resolution (FHD instead of QHD/4K)",
                        "action": "In app settings: Set FPS to 30 or reduce resolution",
                    }
                )

            drop_rate = self.results["android_metrics"].get("frame_drop_rate", 0)
            if drop_rate > 5:
                recommendations.append(
                    {
                        "priority": "high",
                        "component": "Android Encoder",
                        "recommendation": "Encoder overload detected",
                        "detail": f"Encoder is dropping {drop_rate}% of frames. This is likely due to insufficient encoding capacity.",
                        "action": "1) Reduce bitrate to 15-20 Mbps, 2) Try hardware encoder profile, 3) Test on real device (not emulator)",
                    }
                )

        # MediaMTX recommendations
        recommendations.append(
            {
                "priority": "medium",
                "component": "MediaMTX",
                "recommendation": "Optimize for low latency",
                "detail": "Adjust MediaMTX settings to minimize buffering",
                "action": "Add to mediamtx.yml: readBufferCount: 1, writeQueueSize: 512 (under 'paths' section)",
            }
        )

        # Network recommendations
        recommendations.append(
            {
                "priority": "low",
                "component": "Network",
                "recommendation": "Monitor network stability",
                "detail": "High packet loss or jitter can cause stuttering",
                "action": "Check browser performance stats for packet loss % and jitter values",
            }
        )

        # Emulator vs Real Device
        recommendations.append(
            {
                "priority": "high",
                "component": "Testing Environment",
                "recommendation": "Test on real device",
                "detail": "Android emulator has limited hardware encoding capabilities. Real devices perform significantly better.",
                "action": "Deploy to physical Android device for accurate performance testing",
            }
        )

        self.results["recommendations"] = recommendations

        print("\n📋 RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            print(
                f"\n{i}. [{priority_emoji[rec['priority']]} {rec['priority'].upper()}] {rec['recommendation']}"
            )
            print(f"   Component: {rec['component']}")
            print(f"   Detail: {rec['detail']}")
            print(f"   Action: {rec['action']}")

    def save_report(self):
        """Save diagnostic report to file"""
        report_file = (
            self.backend_path
            / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Report saved to: {report_file}")

    def run(self):
        """Run full diagnostic"""
        print("\n" + "=" * 60)
        print("🔬 WEBRTC STREAMING PERFORMANCE DIAGNOSTIC")
        print("=" * 60)
        print(f"Started at: {self.results['timestamp']}")

        self.check_process_health()
        self.check_mediamtx_config()
        self.check_android_logcat(duration=10)
        self.generate_recommendations()
        self.save_report()

        print("\n" + "=" * 60)
        print("✅ DIAGNOSTIC COMPLETE")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start streaming from Android app")
        print("2. Open browser viewer: http://localhost:8000/viewer")
        print("3. Click '📊 Show Stats' button in browser to see real-time metrics")
        print("4. Check Android logcat for encoder performance:")
        print(
            "   ~/Library/Android/sdk/platform-tools/adb logcat | grep 'PERFORMANCE STATS'"
        )
        print("5. Compare metrics across the pipeline to identify bottleneck")


if __name__ == "__main__":
    diagnostic = PerformanceDiagnostic()
    diagnostic.run()
