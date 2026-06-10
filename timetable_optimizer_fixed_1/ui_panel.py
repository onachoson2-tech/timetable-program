# ────────────────────────────────
# ui_panel.py  —  왼쪽 설정 패널 UI
# ────────────────────────────────

import customtkinter as ctk
from config import (SW_COURSES, HC_COURSES, COMMON_COURSES,
                    LIBERAL_AREAS, TRACK_HINTS)


class SettingsPanel(ctk.CTkScrollableFrame):
    """왼쪽 설정 패널. 모든 선택 값을 get_preferences()로 반환."""

    def __init__(self, parent, on_generate_cb, **kwargs):
        super().__init__(parent, width=340, corner_radius=0, **kwargs)
        self._on_generate = on_generate_cb
        self._major_vars: dict = {}
        self._major_cbs:  dict = {}
        self._build()

    # ── 공개 메서드 ────────────────────────────────────

    def get_preferences(self) -> dict:
        return {
            "year":             "1학년",
            "track":            self._track_var.get(),
            "selected_major":   [nm for nm, v in self._major_vars.items() if v.get()],
            "selected_liberal": [nm for nm, v in self._lib_vars.items() if v.get()],
            "avoid_morning":    self._avoid_morning.get(),
            "no_friday":        self._no_friday.get(),
            "keep_lunch":       self._keep_lunch.get(),
            "honor_student":    self._honor_st.get(),
        }

    def get_result_index(self) -> int:
        return {"🥇 균형형": 0, "🥈 공강형": 1, "🥉 몰아듣기형": 2}.get(
            self._result_var.get(), 0)

    def set_result_change_cb(self, cb):
        self._result_var.trace_add("write", lambda *_: cb())

    def set_info(self, text: str):
        self._info_lbl.configure(text=text)

    def set_btn_state(self, generating: bool):
        if generating:
            self._btn.configure(state="disabled", text="⏳ 계산 중...")
        else:
            self._btn.configure(state="normal", text="🔍 시간표 생성하기")

    # ── 내부 빌드 ──────────────────────────────────────

    def _section(self, title: str, subtitle: str = ""):
        f = ctk.CTkFrame(self)
        f.pack(pady=4, padx=10, fill="x")
        ctk.CTkLabel(f, text=title,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(
                     pady=(10, 2), padx=12, anchor="w")
        if subtitle:
            ctk.CTkLabel(f, text=subtitle,
                         font=ctk.CTkFont(size=10), text_color="gray",
                         justify="left").pack(padx=12, anchor="w")
        return f

    def _build(self):
        ctk.CTkLabel(self, text="🎓 CKU 시간표 최적화",
                     font=ctk.CTkFont(size=17, weight="bold")
                     ).pack(pady=(16, 2), padx=14)
        ctk.CTkLabel(self, text="AI소프트웨어융합학부",
                     font=ctk.CTkFont(size=11), text_color="gray"
                     ).pack(pady=(0, 8))

        self._build_year()
        self._build_track()
        self._build_major()
        self._build_liberal()
        self._build_conditions()
        self._build_result_selector()
        self._build_info_and_btn()

        # 초기 트랙 상태 적용
        self._on_track_change()

    def _build_year(self):
        f = self._section("📚 학년")
        ctk.CTkLabel(f, text="1학년 (고정)",
                     font=ctk.CTkFont(size=12),
                     text_color="#88ccff"
                     ).pack(pady=(4, 10), padx=12, anchor="w")

    def _build_track(self):
        f = self._section("🔀 전공 트랙",
                          subtitle="2학년 때 어느 전공으로 갈 예정인가요?")
        self._track_var = ctk.StringVar(value="소프트웨어")
        ctk.CTkSegmentedButton(f, values=["소프트웨어", "헬스케어"],
                               variable=self._track_var,
                               font=ctk.CTkFont(size=12)
                               ).pack(pady=(6, 6), padx=12, fill="x")
        self._track_hint = ctk.CTkLabel(f, text="",
                                        font=ctk.CTkFont(size=10),
                                        text_color="#aaa", wraplength=290,
                                        justify="left")
        self._track_hint.pack(padx=12, pady=(0, 8), anchor="w")
        self._track_var.trace_add("write", lambda *_: self._on_track_change())

    def _on_track_change(self):
        """트랙 변경 시 전공 과목 체크 상태 및 활성화 여부 자동 조정"""
        track = self._track_var.get()
        self._track_hint.configure(text=TRACK_HINTS.get(track, ""))

        if track == "소프트웨어":
            for nm in SW_COURSES:
                self._major_vars[nm].set(True)
                self._major_cbs[nm].configure(state="disabled")
            for nm in HC_COURSES:
                self._major_vars[nm].set(False)
                self._major_cbs[nm].configure(state="normal")

        elif track == "헬스케어":
            for nm in HC_COURSES:
                self._major_vars[nm].set(True)
                self._major_cbs[nm].configure(state="disabled")
            for nm in SW_COURSES:
                self._major_vars[nm].set(False)
                self._major_cbs[nm].configure(state="normal")

    def _build_major(self):
        f = self._section("📌 전공 과목 선택",
                          subtitle="필수 과목은 트랙에 따라 자동 선택됩니다")

        groups = [
            ("── 소프트웨어 전공 과목 ──", "#64B5F6", SW_COURSES),
            ("── 헬스케어 전공 과목 ──",   "#81C784", HC_COURSES),
            ("── 공통 필수 ──",            "#FFD54F", COMMON_COURSES),
        ]
        for label, color, courses in groups:
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                         text_color=color).pack(padx=12, pady=(6, 2), anchor="w")
            for nm in courses:
                var = ctk.BooleanVar(value=False)
                self._major_vars[nm] = var
                cb = ctk.CTkCheckBox(f, text=nm, variable=var,
                                     font=ctk.CTkFont(size=11))
                cb.pack(pady=2, padx=20, anchor="w")
                self._major_cbs[nm] = cb

        ctk.CTkFrame(f, height=6, fg_color="transparent").pack()

    def _build_liberal(self):
        f = self._section("📋 교양필수 선택",
                          subtitle="영역 선택 시 충돌 없는 과목을 자동 배정합니다")
        self._lib_vars = {}

        hints = {
            "VERUM인성:그리스도교문화": "공동체 역량 · 2학점",
            "VERUM인간 (인간학)":       "공동체 역량 · 2학점 · 7개 과목 중 자동 배정",
            "디지털소통":               "소통·공감 역량 · 2학점 · 33개 과목 중 자동 배정",
            "디지털시대의사고와표현":   "소통·공감 역량 · 2학점 · 4개 과목 중 자동 배정",
        }

        for nm in LIBERAL_AREAS:
            var = ctk.BooleanVar(value=False)
            self._lib_vars[nm] = var

            row_f = ctk.CTkFrame(f, fg_color="transparent")
            row_f.pack(pady=(4, 0), padx=12, fill="x")

            ctk.CTkCheckBox(row_f, text=nm, variable=var,
                            font=ctk.CTkFont(size=11)
                            ).pack(anchor="w")
            ctk.CTkLabel(row_f, text=hints.get(nm, ""),
                         font=ctk.CTkFont(size=10), text_color="gray",
                         justify="left").pack(padx=22, anchor="w")

        ctk.CTkFrame(f, height=6, fg_color="transparent").pack()

    def _build_conditions(self):
        f = self._section("⚙️ 시간표 조건")
        self._avoid_morning = ctk.BooleanVar()
        self._no_friday     = ctk.BooleanVar()
        self._keep_lunch    = ctk.BooleanVar()
        self._honor_st      = ctk.BooleanVar()
        for var, txt in [
            (self._avoid_morning, "🌅 오전 수업 피하기"),
            (self._no_friday,     "🎉 금공강 원함"),
            (self._keep_lunch,    "🍱 점심시간 확보 (12~13시)"),
            (self._honor_st,      "⭐ 직전학기 4.0이상 → 최대 21학점"),
        ]:
            ctk.CTkCheckBox(f, text=txt, variable=var,
                            font=ctk.CTkFont(size=11)
                            ).pack(pady=3, padx=14, anchor="w")
        ctk.CTkFrame(f, height=6, fg_color="transparent").pack()

    def _build_result_selector(self):
        f = self._section("📅 추천 결과")
        self._result_var = ctk.StringVar(value="🥇 균형형")
        ctk.CTkSegmentedButton(f,
            values=["🥇 균형형", "🥈 공강형", "🥉 몰아듣기형"],
            variable=self._result_var, font=ctk.CTkFont(size=11)
        ).pack(pady=(0, 10), padx=12, fill="x")

    def _build_info_and_btn(self):
        self._info_lbl = ctk.CTkLabel(self, text="",
                                      font=ctk.CTkFont(size=11),
                                      text_color="#88ccff",
                                      wraplength=320, justify="center")
        self._info_lbl.pack(pady=4, padx=10)

        self._btn = ctk.CTkButton(self,
            text="🔍 시간표 생성하기",
            command=self._on_generate,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=46, corner_radius=8)
        self._btn.pack(pady=10, padx=10, fill="x")
