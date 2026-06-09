# ────────────────────────────────
# main.py  —  앱 진입점 및 이벤트 연결
# ────────────────────────────────

import threading
import customtkinter as ctk

from ui_panel    import SettingsPanel
from canvas_view import TimetableCanvas
from algorithm   import generate_timetables, get_reason

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CKU 시간표 최적화 시스템")
        self.geometry("1060x880")
        self.resizable(True, True)

        self._results: list = []

        self._build_layout()
        self._connect_events()

    # ── 레이아웃 구성 ──────────────────────────────────

    def _build_layout(self):
        # 왼쪽 설정 패널
        self.panel = SettingsPanel(self, on_generate_cb=self._on_generate_click)
        self.panel.pack(side="left", fill="y")

        # 오른쪽 영역
        right = ctk.CTkFrame(self, corner_radius=0, fg_color="#0f0f1a")
        right.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(right, text="📅 시간표",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="white").pack(pady=(10, 4))

        canvas_frame = ctk.CTkFrame(right, fg_color="#0f0f1a")
        canvas_frame.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        self.timetable = TimetableCanvas(canvas_frame)

    def _connect_events(self):
        self.panel.set_result_change_cb(self._refresh_view)

    # ── 이벤트 핸들러 ──────────────────────────────────

    def _on_generate_click(self):
        """생성 버튼 클릭 → 별도 스레드에서 탐색 실행"""
        threading.Thread(target=self._run_search, daemon=True).start()

    def _run_search(self):
        self.panel.set_btn_state(generating=True)
        self.panel.set_info("최적 시간표를 탐색하고 있습니다...")

        prefs  = self.panel.get_preferences()
        honor  = prefs.get("honor_student", False)
        results = generate_timetables(prefs, honor)

        self._results = results
        self.panel.set_btn_state(generating=False)

        if not results:
            self.panel.set_info(
                "❌ 조건에 맞는 시간표가 없습니다.\n"
                "선택 과목을 줄이거나 조건을 완화해보세요.")
            self.timetable.clear()
            return

        self._refresh_view()

    def _refresh_view(self):
        """결과 탭 변경 또는 탐색 완료 시 시간표 갱신"""
        if not self._results:
            self.timetable.clear()
            return

        idx = self.panel.get_result_index()
        idx = min(idx, len(self._results) - 1)

        subject_profs, free, cr = self._results[idx]
        prefs  = self.panel.get_preferences()
        reason = get_reason(subject_profs, free, cr, prefs)

        names = [nm for nm, _ in subject_profs]
        self.panel.set_info(f"{reason}\n총 {len(names)}과목 · {cr}학점")
        self.timetable.show(subject_profs)


if __name__ == "__main__":
    app = App()
    app.mainloop()
