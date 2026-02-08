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

def get_docker_compose_cmd():
    """docker compose (v2) 또는 docker-compose (v1) 명령 반환. 크로스 플랫폼."""
    try:
        r = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0:
            return ["docker", "compose"]
    except Exception:
        pass
    return ["docker-compose"]


def get_local_interface_ips():
    """사용 가능한 로컬 인터페이스 IP 목록 (루프백 제외). 크로스 플랫폼."""
    ips = []
    try:
        import netifaces
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET) or []
            for a in addrs:
                addr = a.get("addr")
                if addr and not addr.startswith("127."):
                    ips.append(addr)
    except (ImportError, AttributeError):
        pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            ips.append("127.0.0.1")
    return ips if ips else ["127.0.0.1"]


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
        # 로그 영역: 선택 후 Ctrl+C / Cmd+C 로 복사 가능, 수정(입력·붙여넣기)은 막음
        self._bind_log_copy_and_readonly()

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

    def _bind_log_copy_and_readonly(self):
        """로그 텍스트: Ctrl+C 복사 가능, 입력/붙여넣기로 수정 불가."""
        # CustomTkinter 내부 tk Text 위젯 찾기 (버전별 _textbox 또는 자식 탐색)
        textbox = None
        try:
            textbox = getattr(self.log_text, "_textbox", None)
        except Exception:
            pass
        if textbox is None:
            for w in self.log_text.winfo_children():
                if w.winfo_class() == "Text":
                    textbox = w
                    break
        if textbox is None:
            textbox = self.log_text
        # 선택 가능하도록 (disabled면 드래그 선택이 안 될 수 있음)
        try:
            textbox.configure(state="normal")
        except Exception:
            pass

        def copy_selection(event=None):
            try:
                sel = textbox.get("sel.first", "sel.last")
                if not sel.strip():
                    return "break"
                root = self.winfo_toplevel()
                root.clipboard_clear()
                root.clipboard_append(sel)
                root.update()  # 클립보드 반영
            except (tk.TclError, AttributeError, Exception):
                pass
            return "break"

        def block_edit(event):
            # Ctrl+C, Cmd+C 허용 (복사)
            if (event.state & 0x4) or (event.state & 0x80000):  # Control or Command
                if event.keysym.lower() == "c":
                    copy_selection(event)
                    return "break"
                if event.keysym.lower() == "a":
                    try:
                        textbox.tag_add("sel", "1.0", "end")
                    except Exception:
                        pass
                    return "break"
            # 수정 방지
            if event.keysym in ("BackSpace", "Delete", "Return", "Tab"):
                return "break"
            if len(event.keysym) == 1 or event.keysym.startswith("KP_"):
                return "break"
            return None

        for seq in ("<Control-c>", "<Control-C>", "<Command-c>", "<Command-C>"):
            try:
                textbox.bind(seq, copy_selection)
            except Exception:
                pass
        textbox.bind("<Key>", block_edit)

        # 우클릭 메뉴: 복사
        def show_log_context_menu(event):
            try:
                menu = tk.Menu(self, tearoff=0)
                menu.add_command(label="복사 (Ctrl+C)", command=copy_selection)
                menu.tk_popup(event.x_root, event.y_root)
            except Exception:
                pass
        textbox.bind("<Button-3>", show_log_context_menu)  # Button-3 = 우클릭

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
            cmd = get_docker_compose_cmd() + ["ps", "--format", "json"]
            result = subprocess.run(
                cmd,
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

    def _ensure_env_complete(self):
        """docker-compose에 기본값이 없으므로 .env에 없는 변수만 기본값으로 추가"""
        load_dotenv(self.env_file)
        server_ip = os.getenv("SERVER_IP", "localhost")
        defaults = {
            "MONGO_USERNAME": "airclass",
            "MONGO_PASSWORD": "airclass2025",
            "LIVEKIT_API_KEY": "AIRClass2025DevKey123456789ABC",
            "LIVEKIT_API_SECRET": "AIRclass2025DevSecretXYZ987654321",
            "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY") or (__import__("secrets").token_hex(32)),
            "CLUSTER_SECRET": os.getenv("CLUSTER_SECRET") or "airclass2025",
            "MAIN_API_PORT": "8000",
            "MAIN_LIVEKIT_PORT": "7880",
            "MAIN_RTC_PORT_START": "50000",
            "MAIN_RTC_PORT_END": "50020",
            "SUB1_API_PORT": "8001",
            "SUB1_LIVEKIT_PORT": "7890",
            "SUB1_RTC_PORT_START": "51000",
            "SUB1_RTC_PORT_END": "51020",
            "CORS_ORIGINS": "*",
            "VITE_BACKEND_URL": f"http://{server_ip}:8000",
        }
        changed = False
        for key, val in defaults.items():
            if not os.getenv(key):
                set_key(self.env_file, key, val)
                changed = True
        if changed:
            load_dotenv(self.env_file, override=True)

    def start_server(self):
        """서버 시작"""
        if not self.docker_running:
            messagebox.showerror(
                "Docker 실행 필요",
                "Docker가 실행되고 있지 않습니다.\nDocker Desktop을 먼저 실행해주세요.",
            )
            return

        self._ensure_env_complete()
        self.log("서버를 시작하는 중...")
        self.start_button.configure(state="disabled", text="시작 중...")

        def start_thread():
            try:
                # docker compose up -d (v2) 또는 docker-compose up -d (v1)
                cmd = get_docker_compose_cmd() + ["up", "-d"]
                process = subprocess.Popen(
                    cmd,
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
                cmd = get_docker_compose_cmd() + ["down"]
                process = subprocess.Popen(
                    cmd,
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
            text="💡 자동 감지된 IP입니다. 필요시 수정하거나 아래에서 다른 인터페이스를 선택하세요.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        ip_hint.pack(pady=5, anchor="w", padx=20)

        # 인터페이스 선택 (크로스 플랫폼: 여러 IP 중 선택)
        iface_label = ctk.CTkLabel(
            form_frame,
            text="네트워크 인터페이스:",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        iface_label.pack(pady=(5, 2), anchor="w", padx=20)
        self.iface_combo = ctk.CTkComboBox(
            form_frame,
            values=get_local_interface_ips(),
            width=280,
            command=self._on_iface_selected,
        )
        self.iface_combo.pack(pady=2, padx=20, anchor="w")

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

    def _on_iface_selected(self, choice):
        """인터페이스 선택 시 IP 입력란에 반영"""
        self.ip_entry.delete(0, "end")
        self.ip_entry.insert(0, choice)

    def detect_ip(self):
        """로컬 IP 자동 감지"""
        ips = get_local_interface_ips()
        if ips:
            self.ip_entry.insert(0, ips[0])
            if hasattr(self, "iface_combo") and self.iface_combo.cget("values"):
                try:
                    self.iface_combo.set(ips[0])
                except Exception:
                    pass
        else:
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

        # TOTP 시크릿 생성 (Sub 등록·Android 연동 시 6자리 코드 검증용, QR로 앱에 등록)
        try:
            import pyotp
            totp_secret = pyotp.random_base32()
        except ImportError:
            import base64
            totp_secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

        # .env 파일 생성 (docker-compose에서 기본값 없으므로 필요한 변수 전부 기입)
        env_content = f"""# AIRClass 서버 설정 파일 (GUI로 생성)
# 서버(인터페이스) IP - 접속 URL·LiveKit URL 등 모두 이 주소 기준
SERVER_IP={server_ip}
VITE_BACKEND_URL=http://{server_ip}:8000
CORS_ORIGINS=*
JWT_SECRET_KEY={jwt_secret}
CLUSTER_SECRET={cluster_secret}
# TOTP 시크릿 (Sub 등록·디바이스 연동 시 6자리 코드 검증). 서버 기동 후 /cluster/totp-setup 에서 QR 스캔
TOTP_SECRET={totp_secret}

# MongoDB
MONGO_USERNAME=airclass
MONGO_PASSWORD=airclass2025

# LiveKit (개발용)
LIVEKIT_API_KEY=AIRClass2025DevKey123456789ABC
LIVEKIT_API_SECRET=AIRclass2025DevSecretXYZ987654321

# Main 노드 포트
MAIN_API_PORT=8000
MAIN_LIVEKIT_PORT=7880
MAIN_RTC_PORT_START=50000
MAIN_RTC_PORT_END=50020

# Sub 노드 포트 (sub-1 사용 시)
SUB1_API_PORT=8001
SUB1_LIVEKIT_PORT=7890
SUB1_RTC_PORT_START=51000
SUB1_RTC_PORT_END=51020

USE_MAIN_WEBRTC=false
"""

        with open(self.parent.env_file, "w", encoding="utf-8") as f:
            f.write(env_content)

        msg = "설정이 저장되었습니다!\n\n이제 '서버 시작' 버튼을 클릭한 뒤,\nTOTP 앱 등록: 서버 주소/cluster/totp-setup 에서 QR 스캔하세요.\n(Sub 등록·Android 연동 시 6자리 코드 사용)"
        messagebox.showinfo("설정 완료", msg)

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

        # 인터페이스 선택 (다른 IP로 변경 시)
        iface_label = ctk.CTkLabel(
            form_frame,
            text="네트워크 인터페이스:",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        iface_label.pack(pady=(5, 2), anchor="w", padx=20)
        self.iface_combo = ctk.CTkComboBox(
            form_frame,
            values=get_local_interface_ips(),
            width=280,
            command=self._on_iface_selected,
        )
        self.iface_combo.pack(pady=2, padx=20, anchor="w")

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

    def _on_iface_selected(self, choice):
        """인터페이스 선택 시 IP 입력란에 반영"""
        self.ip_entry.delete(0, "end")
        self.ip_entry.insert(0, choice)

    def load_current_config(self):
        """현재 설정 로드"""
        load_dotenv(self.parent.env_file)
        server_ip = os.getenv("SERVER_IP", "")
        self.ip_entry.insert(0, server_ip)
        self.pwd_entry.insert(0, os.getenv("CLUSTER_SECRET", ""))
        if server_ip and self.iface_combo.cget("values") and server_ip not in self.iface_combo.cget("values"):
            self.iface_combo.configure(values=list(self.iface_combo.cget("values")) + [server_ip])
        try:
            self.iface_combo.set(server_ip)
        except Exception:
            pass

    def save_config(self):
        """설정 저장"""
        server_ip = self.ip_entry.get().strip()
        cluster_secret = self.pwd_entry.get().strip()

        if not server_ip or not cluster_secret:
            messagebox.showerror("입력 오류", "모든 항목을 입력해주세요.")
            return

        # .env 업데이트 (SERVER_IP만; LIVEKIT_PUBLIC_URL은 docker-compose에서 자동)
        set_key(self.parent.env_file, "SERVER_IP", server_ip)
        set_key(self.parent.env_file, "VITE_BACKEND_URL", f"http://{server_ip}:8000")
        set_key(self.parent.env_file, "CLUSTER_SECRET", cluster_secret)

        messagebox.showinfo("저장 완료", "설정이 저장되었습니다!")
        self.parent.load_config()
        self.destroy()


if __name__ == "__main__":
    app = AIRClassGUI()
    app.mainloop()
