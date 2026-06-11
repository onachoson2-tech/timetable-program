# ────────────────────────────────
# main.py  —  앱 진입점 및 이벤트 연결
# ────────────────────────────────

import threading
import customtkinter as ctk

from ui_panel    import SettingsPanel
from canvas_view import TimetableCanvas
from algorithm   import generate_timetables, get_reason
from config      import (MAX_CREDITS, MAX_CREDITS_HONOR,
                         LIBERAL_AREA_COUNT, LIBERAL_AREA_DOMAINS)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 과목명 → 학점 매핑 (전공 과목 사전 학점 계산용)
# 사제동행세미나1(0.5학점)은 수강신청 학점에 포함되지 않으므로 제외
_MAJOR_CREDITS = {
    "프로그래밍기초":           3,
    "데이터리터러시와기초통계": 2,
    "데이터리터러시실습":       2,
    "AI소프트웨어개론":         3,
    "디지털헬스와사회":         2,
}

# 교양필수 영역 → 학점 매핑
_LIBERAL_CREDITS = {
    "VERUM인성:그리스도교문화": 2,
    "VERUM인간 (인간학)":       2,   # 1과목 × 2학점
    "디지털소통":               4,   # 2과목 × 2학점
    "디지털시대의사고와표현":   2,
}


def _calc_selected_credits(prefs: dict) -> tuple:
    """
    선택한 전공 과목 학점 합계와 교양필수 학점 합계를 반환.
    반환: (major_cr, liberal_cr)
    """
    major_cr   = sum(_MAJOR_CREDITS.get(nm, 2)
                     for nm in prefs.get("selected_major", []))
    liberal_cr = sum(_LIBERAL_CREDITS.get(area, 2)
                     for area in prefs.get("selected_liberal", []))
    return major_cr, liberal_cr


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CKU 시간표 최적화 시스템")
        self.geometry("1060x880")
        self.resizable(True, True)

        self._results: list = []
        self._result_idx: int = 0
        self._timed_out: bool = False

        self._build_layout()
        self._connect_events()

    # ── 레이아웃 구성 ──────────────────────────────────

    def _build_layout(self):
        self.panel = SettingsPanel(self, on_generate_cb=self._on_generate_click)
        self.panel.pack(side="left", fill="y")

        right = ctk.CTkFrame(self, corner_radius=0, fg_color="#0f0f1a")
        right.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(right, text="📅 시간표",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="white").pack(pady=(10, 4))

        canvas_frame = ctk.CTkFrame(right, fg_color="#0f0f1a")
        canvas_frame.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        self.timetable = TimetableCanvas(canvas_frame)

    def _connect_events(self):
        pass  # 추천 결과 탭 제거로 이벤트 연결 불필요

    # ── 이벤트 핸들러 ──────────────────────────────────

    def _on_generate_click(self):
        """생성 버튼 클릭 → 매번 새로 탐색하여 랜덤 시간표 반환"""
        prefs = self.panel.get_preferences()

        warning = self._check_credit_warning(prefs)
        if warning:
            self.panel.set_info(warning)

        threading.Thread(target=self._run_search, args=(prefs,), daemon=True).start()

    def _check_credit_warning(self, prefs: dict) -> str:
        """
        전공 + 교양필수 학점 합계가 최대 수강 학점을 초과하거나
        교양선택 여유가 없으면 경고 문자열 반환.
        정상이면 빈 문자열 반환.
        """
        honor    = prefs.get("honor_student", False)
        max_cr   = MAX_CREDITS_HONOR if honor else MAX_CREDITS

        major_cr, liberal_cr = _calc_selected_credits(prefs)
        total_fixed = major_cr + liberal_cr

        if total_fixed > max_cr:
            return (
                f"⚠️ 전공 {major_cr}학점 + 교양필수 {liberal_cr}학점 "
                f"= {total_fixed}학점으로\n"
                f"최대 수강학점({max_cr}학점)을 초과합니다.\n"
                f"이수 가능한 범위 내에서 최적 시간표를 탐색합니다."
            )

        # 교양선택 여유 학점이 2학점 미만이면 경고
        remaining = max_cr - total_fixed
        if remaining < 2 and len(prefs.get("selected_liberal", [])) > 0:
            return (
                f"⚠️ 전공 {major_cr}학점 + 교양필수 {liberal_cr}학점 "
                f"= {total_fixed}학점\n"
                f"교양선택 여유 학점이 {remaining}학점으로 부족합니다.\n"
                f"교양필수 선택을 줄이는 것을 권장합니다."
            )

        return ""

    def _run_search(self, prefs: dict):
        self.panel.set_btn_state(generating=True)
        self.panel.set_info("최적 시간표를 탐색하고 있습니다...")

        honor = prefs.get("honor_student", False)
        results, timed_out = generate_timetables(prefs, honor)

        self._results    = results
        self._timed_out  = timed_out
        self._result_idx = 0
        self.panel.set_btn_state(generating=False)

        if not results:
            self.panel.set_info(
                "❌ 조건에 맞는 시간표가 없습니다.\n"
                "선택 과목을 줄이거나 조건을 완화해보세요.")
            self.timetable.clear()
            return

        self._refresh_view()

    def _refresh_view(self):
        """결과 표시 — 현재 인덱스의 시간표를 표시"""
        if not self._results:
            self.timetable.clear()
            return

        idx = self._result_idx % len(self._results)
        subject_profs, free, cr = self._results[idx]
        prefs  = self.panel.get_preferences()
        reason = get_reason(subject_profs, free, cr, prefs)

        names = [nm for nm, _ in subject_profs]
        total = len(self._results)
        info  = f"{reason}\n총 {len(names)}과목 · {cr}학점 ({idx + 1}/{total})"

        if self._timed_out:
            info = (
                "⚠️ 탐색 시간(15초)이 초과되어 중단되었습니다.\n"
                "조건을 완화하면 더 많은 결과를 찾을 수 있습니다.\n"
                f"{info}"
            )

        self.panel.set_info(info)
        self.timetable.show(subject_profs)


if __name__ == "__main__":
    app = App()
    app.mainloop()
