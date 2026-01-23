#!/usr/bin/env python3
"""
AIRClass GUI Manager
교사를 위한 간단한 서버 관리 도구
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, scrolledtext
import subprocess
import threading
import os
import sys
import platform
import socket
import webbrowser
from pathlib import Path
from dotenv import load_dotenv, set_key
import time
import requests
import json

# 다크 모드 설정
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AIRClassGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 프로젝트 루트 경로
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"

        # 윈도우 설정
        self.title("AIRClass 서버 관리")
        self.geometry("900x700")
        self.resizable(True, True)

        # 서버 상태
        self.server_running = False
        self.docker_installed = False
        self.docker_running = False

        # UI 구성
        self.create_widgets()

        # 초기 상태 확인
        self.check_docker_status()
        self.check_server_status()

        # .env 파일이 없으면 설정 창 표시
        if not self.env_file.exists():
            self.show_setup_wizard()
        else:
            self.load_config()

        # 자동 상태 업데이트 (5초마다)
        self.start_auto_refresh()

    def create_widgets(self):
        """UI 위젯 생성"""

        # ========== 헤더 ==========
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.pack(pady=20, padx=20, fill="x")

        title_label = ctk.CTkLabel(
            header_frame,
            text="🎓 AIRClass 서버 관리",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title_label.pack(pady=15)

        # ========== 상태 표시 영역 ==========
        status_frame = ctk.CTkFrame(self, corner_radius=10)
        status_frame.pack(pady=10, padx=20, fill="x")

        # Docker 상태
        self.docker_status_label = ctk.CTkLabel(
            status_frame, text="🐳 Docker: 확인 중...", font=ctk.CTkFont(size=16)
        )
        self.docker_status_label.pack(pady=5, padx=20, anchor="w")

        # 서버 상태
        self.server_status_label = ctk.CTkLabel(
            status_frame, text="⚡ 서버: 중지됨", font=ctk.CTkFont(size=16)
        )
        self.server_status_label.pack(pady=5, padx=20, anchor="w")

        # 접속 주소
        self.url_label = ctk.CTkLabel(
            status_frame,
            text="📍 접속 주소: 설정 필요",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        self.url_label.pack(pady=5, padx=20, anchor="w")

        # ========== 컨트롤 버튼 ==========
        button_frame = ctk.CTkFrame(self, corner_radius=10)
        button_frame.pack(pady=10, padx=20, fill="x")

        # 버튼 그리드 설정
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.start_button = ctk.CTkButton(
            button_frame,
            text="▶ 서버 시작",
            command=self.start_server,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="green",
            hover_color="darkgreen",
        )
        self.start_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⬛ 서버 중지",
            command=self.stop_server,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="red",
            hover_color="darkred",
            state="disabled",
        )
        self.stop_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.settings_button = ctk.CTkButton(
            button_frame,
            text="⚙️ 설정",
            command=self.show_settings,
            font=ctk.CTkFont(size=16),
            height=50,
        )
        self.settings_button.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        # ========== 빠른 접속 버튼 ==========
        quick_access_frame = ctk.CTkFrame(self, corner_radius=10)
        quick_access_frame.pack(pady=10, padx=20, fill="x")

        quick_label = ctk.CTkLabel(
            quick_access_frame,
            text="빠른 접속",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        quick_label.pack(pady=5, padx=20, anchor="w")

        quick_btn_frame = ctk.CTkFrame(quick_access_frame, fg_color="transparent")
        quick_btn_frame.pack(pady=5, padx=20, fill="x")
        quick_btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.teacher_btn = ctk.CTkButton(
            quick_btn_frame,
            text="👩‍🏫 선생님 페이지",
            command=self.open_teacher_page,
            height=40,
        )
        self.teacher_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.student_btn = ctk.CTkButton(
            quick_btn_frame,
            text="👨‍🎓 학생 페이지",
            command=self.open_student_page,
            height=40,
        )
        self.student_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.admin_btn = ctk.CTkButton(
            quick_btn_frame,
            text="📊 관리자 페이지",
            command=self.open_admin_page,
            height=40,
        )
        self.admin_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # ========== 로그 영역 ==========
        log_frame = ctk.CTkFrame(self, corner_radius=10)
        log_frame.pack(pady=10, padx=20, fill="both", expand=True)

        log_label = ctk.CTkLabel(
            log_frame, text="📜 서버 로그", font=ctk.CTkFont(size=14, weight="bold")
        )
        log_label.pack(pady=5, padx=20, anchor="w")

        self.log_text = ctk.CTkTextbox(
            log_frame, font=ctk.CTkFont(family="Courier", size=12), wrap="word"
        )
        self.log_text.pack(pady=5, padx=20, fill="both", expand=True)

        # ========== 푸터 ==========
        footer_frame = ctk.CTkFrame(self, corner_radius=10, height=40)
        footer_frame.pack(pady=10, padx=20, fill="x")

        footer_label = ctk.CTkLabel(
            footer_frame,
            text="Made with ❤️ for Teachers",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        footer_label.pack(pady=10)

    def log(self, message):
        """로그 메시지 추가"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")

    def check_docker_status(self):
        """Docker 설치 및 실행 상태 확인"""
        try:
            # Docker 설치 확인
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=5
            )
            self.docker_installed = result.returncode == 0

            if self.docker_installed:
                # Docker 실행 확인
                result = subprocess.run(
                    ["docker", "ps"], capture_output=True, text=True, timeout=5
                )
                self.docker_running = result.returncode == 0

                if self.docker_running:
                    self.docker_status_label.configure(
                        text="🐳 Docker: ✅ 실행 중", text_color="green"
                    )
                else:
                    self.docker_status_label.configure(
                        text="🐳 Docker: ⚠️ 설치됨 (실행 필요)", text_color="orange"
                    )
            else:
                self.docker_status_label.configure(
                    text="🐳 Docker: ❌ 미설치", text_color="red"
                )
        except Exception as e:
            self.docker_status_label.configure(
                text="🐳 Docker: ❌ 확인 실패", text_color="red"
            )

    def check_server_status(self):
        """서버 실행 상태 확인"""
        try:
            # docker-compose ps 실행
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout.strip():
                # 실행 중인 컨테이너가 있는지 확인
                containers = result.stdout.strip().split("\n")
                running_count = 0
                for container in containers:
                    try:
                        data = json.loads(container)
                        if data.get("State") == "running":
                            running_count += 1
                    except:
                        pass

                if running_count > 0:
                    self.server_running = True
                    self.server_status_label.configure(
                        text=f"⚡ 서버: ✅ 실행 중 ({running_count}개 컨테이너)",
                        text_color="green",
                    )
                    self.start_button.configure(state="disabled")
                    self.stop_button.configure(state="normal")

                    # 클러스터 정보 가져오기
                    self.update_cluster_info()
                else:
                    self.server_running = False
                    self.server_status_label.configure(
                        text="⚡ 서버: 중지됨", text_color="gray"
                    )
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
            else:
                self.server_running = False
                self.server_status_label.configure(
                    text="⚡ 서버: 중지됨", text_color="gray"
                )
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
        except Exception as e:
            pass

    def update_cluster_info(self):
        """클러스터 정보 업데이트"""
        try:
            response = requests.get("http://localhost:8000/cluster/nodes", timeout=2)
            if response.status_code == 200:
                data = response.json()
                total_nodes = data.get("total_nodes", 0)
                healthy_nodes = data.get("healthy_nodes", 0)
                total_capacity = data.get("total_capacity", 0)

                self.server_status_label.configure(
                    text=f"⚡ 서버: ✅ 실행 중 ({healthy_nodes}/{total_nodes} 노드, 최대 {total_capacity}명)"
                )
        except:
            pass

    def load_config(self):
        """설정 파일 로드"""
        load_dotenv(self.env_file)
        server_ip = os.getenv("SERVER_IP", "localhost")
        self.url_label.configure(
            text=f"📍 선생님: http://{server_ip}:5173/teacher | 학생: http://{server_ip}:5173/student"
        )

    def start_server(self):
        """서버 시작"""
        if not self.docker_running:
            messagebox.showerror(
                "Docker 실행 필요",
                "Docker가 실행되고 있지 않습니다.\nDocker Desktop을 먼저 실행해주세요.",
            )
            return

        self.log("서버를 시작하는 중...")
        self.start_button.configure(state="disabled", text="시작 중...")

        def start_thread():
            try:
                # docker-compose up -d 실행
                process = subprocess.Popen(
                    ["docker-compose", "up", "-d"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=self.project_root,
                )

                for line in process.stdout:
                    self.log(line.strip())

                process.wait()

                if process.returncode == 0:
                    self.log("✅ 서버가 성공적으로 시작되었습니다!")
                    self.server_running = True
                    self.after(
                        0,
                        lambda: self.start_button.configure(
                            state="disabled", text="▶ 서버 시작"
                        ),
                    )
                    self.after(0, lambda: self.stop_button.configure(state="normal"))

                    # 15초 대기 후 상태 확인
                    time.sleep(15)
                    self.after(0, self.check_server_status)
                else:
                    self.log("❌ 서버 시작에 실패했습니다.")
                    self.after(
                        0,
                        lambda: self.start_button.configure(
                            state="normal", text="▶ 서버 시작"
                        ),
                    )
            except Exception as e:
                self.log(f"❌ 오류: {str(e)}")
                self.after(
                    0,
                    lambda: self.start_button.configure(
                        state="normal", text="▶ 서버 시작"
                    ),
                )

        thread = threading.Thread(target=start_thread, daemon=True)
        thread.start()

    def stop_server(self):
        """서버 중지"""
        self.log("서버를 중지하는 중...")
        self.stop_button.configure(state="disabled", text="중지 중...")

        def stop_thread():
            try:
                process = subprocess.Popen(
                    ["docker-compose", "down"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=self.project_root,
                )

                for line in process.stdout:
                    self.log(line.strip())

                process.wait()

                if process.returncode == 0:
                    self.log("✅ 서버가 중지되었습니다.")
                    self.server_running = False
                    self.after(0, lambda: self.start_button.configure(state="normal"))
                    self.after(
                        0,
                        lambda: self.stop_button.configure(
                            state="disabled", text="⬛ 서버 중지"
                        ),
                    )
                    self.after(0, self.check_server_status)
                else:
                    self.log("❌ 서버 중지에 실패했습니다.")
                    self.after(
                        0,
                        lambda: self.stop_button.configure(
                            state="normal", text="⬛ 서버 중지"
                        ),
                    )
            except Exception as e:
                self.log(f"❌ 오류: {str(e)}")
                self.after(
                    0,
                    lambda: self.stop_button.configure(
                        state="normal", text="⬛ 서버 중지"
                    ),
                )

        thread = threading.Thread(target=stop_thread, daemon=True)
        thread.start()

    def show_settings(self):
        """설정 창 표시"""
        SettingsWindow(self)

    def show_setup_wizard(self):
        """초기 설정 마법사"""
        SetupWizard(self)

    def open_teacher_page(self):
        """선생님 페이지 열기"""
        load_dotenv(self.env_file)
        server_ip = os.getenv("SERVER_IP", "localhost")
        url = f"http://{server_ip}:5173/teacher"
        webbrowser.open(url)
        self.log(f"브라우저에서 열기: {url}")

    def open_student_page(self):
        """학생 페이지 열기"""
        load_dotenv(self.env_file)
        server_ip = os.getenv("SERVER_IP", "localhost")
        url = f"http://{server_ip}:5173/student"
        webbrowser.open(url)
        self.log(f"브라우저에서 열기: {url}")

    def open_admin_page(self):
        """관리자 페이지 열기"""
        load_dotenv(self.env_file)
        server_ip = os.getenv("SERVER_IP", "localhost")
        url = f"http://{server_ip}:8000/cluster/nodes"
        webbrowser.open(url)
        self.log(f"브라우저에서 열기: {url}")

    def start_auto_refresh(self):
        """자동 상태 업데이트"""
        self.check_docker_status()
        self.check_server_status()
        self.after(5000, self.start_auto_refresh)  # 5초마다


class SetupWizard(ctk.CTkToplevel):
    """초기 설정 마법사"""

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent
        self.title("AIRClass 초기 설정")
        self.geometry("600x500")
        self.resizable(False, False)

        # 모달 윈도우로 설정
        self.transient(parent)
        self.grab_set()

        self.create_widgets()

        # 자동으로 IP 주소 감지
        self.detect_ip()

    def create_widgets(self):
        # 헤더
        header = ctk.CTkLabel(
            self, text="🎓 AIRClass 초기 설정", font=ctk.CTkFont(size=24, weight="bold")
        )
        header.pack(pady=20)

        # 설명
        desc = ctk.CTkLabel(
            self, text="서버 설정을 입력해주세요.", font=ctk.CTkFont(size=14)
        )
        desc.pack(pady=10)

        # 폼 프레임
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(pady=20, padx=40, fill="both", expand=True)

        # 서버 IP
        ip_label = ctk.CTkLabel(
            form_frame, text="서버 IP 주소:", font=ctk.CTkFont(size=14, weight="bold")
        )
        ip_label.pack(pady=(20, 5), anchor="w", padx=20)

        self.ip_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="예: 192.168.0.100",
            font=ctk.CTkFont(size=14),
            height=40,
        )
        self.ip_entry.pack(pady=5, padx=20, fill="x")

        ip_hint = ctk.CTkLabel(
            form_frame,
            text="💡 자동 감지된 IP입니다. 필요시 수정하세요.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        ip_hint.pack(pady=5, anchor="w", padx=20)

        # 클러스터 비밀번호
        pwd_label = ctk.CTkLabel(
            form_frame,
            text="클러스터 비밀번호:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        pwd_label.pack(pady=(20, 5), anchor="w", padx=20)

        self.pwd_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="예: myclass2025",
            font=ctk.CTkFont(size=14),
            height=40,
        )
        self.pwd_entry.pack(pady=5, padx=20, fill="x")

        pwd_hint = ctk.CTkLabel(
            form_frame,
            text="💡 다른 선생님의 서버와 구분하기 위한 비밀번호입니다.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        pwd_hint.pack(pady=5, anchor="w", padx=20)

        # 저장 버튼
        save_btn = ctk.CTkButton(
            self,
            text="✅ 저장하고 시작",
            command=self.save_config,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="green",
            hover_color="darkgreen",
        )
        save_btn.pack(pady=20, padx=40, fill="x")

    def detect_ip(self):
        """로컬 IP 자동 감지"""
        try:
            # 외부 연결을 시도하여 로컬 IP 확인
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            self.ip_entry.insert(0, local_ip)
        except:
            self.ip_entry.insert(0, "localhost")

    def save_config(self):
        """설정 저장"""
        server_ip = self.ip_entry.get().strip()
        cluster_secret = self.pwd_entry.get().strip()

        if not server_ip:
            messagebox.showerror("입력 오류", "서버 IP 주소를 입력해주세요.")
            return

        if not cluster_secret:
            messagebox.showerror("입력 오류", "클러스터 비밀번호를 입력해주세요.")
            return

        # JWT 키 생성
        import secrets

        jwt_secret = secrets.token_hex(32)

        # .env 파일 생성
        env_content = f"""# AIRClass 서버 설정 파일
# GUI로 생성됨

# 서버 IP 주소
SERVER_IP={server_ip}

# 프론트엔드 백엔드 URL
VITE_BACKEND_URL=http://{server_ip}:8000

# CORS 설정
CORS_ORIGINS=*

# JWT 보안 키
JWT_SECRET_KEY={jwt_secret}

# Main 노드 WebRTC 사용 여부
USE_MAIN_WEBRTC=false

# 클러스터 보안 비밀번호
CLUSTER_SECRET={cluster_secret}
"""

        with open(self.parent.env_file, "w", encoding="utf-8") as f:
            f.write(env_content)

        messagebox.showinfo(
            "설정 완료", "설정이 저장되었습니다!\n이제 '서버 시작' 버튼을 클릭하세요."
        )

        self.parent.load_config()
        self.destroy()


class SettingsWindow(ctk.CTkToplevel):
    """설정 창"""

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent
        self.title("설정")
        self.geometry("600x400")
        self.resizable(False, False)

        self.transient(parent)

        self.create_widgets()
        self.load_current_config()

    def create_widgets(self):
        # 헤더
        header = ctk.CTkLabel(
            self, text="⚙️ 서버 설정", font=ctk.CTkFont(size=24, weight="bold")
        )
        header.pack(pady=20)

        # 폼
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(pady=10, padx=40, fill="both", expand=True)

        # 서버 IP
        ip_label = ctk.CTkLabel(
            form_frame, text="서버 IP 주소:", font=ctk.CTkFont(size=14, weight="bold")
        )
        ip_label.pack(pady=(20, 5), anchor="w", padx=20)

        self.ip_entry = ctk.CTkEntry(form_frame, font=ctk.CTkFont(size=14), height=40)
        self.ip_entry.pack(pady=5, padx=20, fill="x")

        # 클러스터 비밀번호
        pwd_label = ctk.CTkLabel(
            form_frame,
            text="클러스터 비밀번호:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        pwd_label.pack(pady=(20, 5), anchor="w", padx=20)

        self.pwd_entry = ctk.CTkEntry(form_frame, font=ctk.CTkFont(size=14), height=40)
        self.pwd_entry.pack(pady=5, padx=20, fill="x")

        # 버튼
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20, padx=40, fill="x")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        save_btn = ctk.CTkButton(
            btn_frame,
            text="✅ 저장",
            command=self.save_config,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color="green",
        )
        save_btn.grid(row=0, column=0, padx=5, sticky="ew")

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="❌ 취소",
            command=self.destroy,
            font=ctk.CTkFont(size=14),
            height=40,
        )
        cancel_btn.grid(row=0, column=1, padx=5, sticky="ew")

    def load_current_config(self):
        """현재 설정 로드"""
        load_dotenv(self.parent.env_file)
        self.ip_entry.insert(0, os.getenv("SERVER_IP", ""))
        self.pwd_entry.insert(0, os.getenv("CLUSTER_SECRET", ""))

    def save_config(self):
        """설정 저장"""
        server_ip = self.ip_entry.get().strip()
        cluster_secret = self.pwd_entry.get().strip()

        if not server_ip or not cluster_secret:
            messagebox.showerror("입력 오류", "모든 항목을 입력해주세요.")
            return

        # .env 업데이트
        set_key(self.parent.env_file, "SERVER_IP", server_ip)
        set_key(self.parent.env_file, "VITE_BACKEND_URL", f"http://{server_ip}:8000")
        set_key(self.parent.env_file, "CLUSTER_SECRET", cluster_secret)

        messagebox.showinfo("저장 완료", "설정이 저장되었습니다!")
        self.parent.load_config()
        self.destroy()


if __name__ == "__main__":
    app = AIRClassGUI()
    app.mainloop()
