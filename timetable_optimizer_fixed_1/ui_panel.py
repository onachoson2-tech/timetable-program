# ────────────────────────────────
# ui_panel.py  —  왼쪽 설정 패널 UI
# ────────────────────────────────

import customtkinter as ctk
from config import (SW_COURSES, HC_COURSES, COMMON_COURSES,
                    LIBERAL_COMMUNITY, LIBERAL_COMMUNICATION, TRACK_HINTS)


class SettingsPanel(ctk.CTkScrollableFrame):
    """왼쪽 설정 패널. 모든 선택 값을 get_preferences()로 반환."""

    def __init__(self, parent, on_generate_cb, **kwargs):
        super().__init__(parent, width=340, corner_radius=0, **kwargs)
        self._on_generate = on_generate_cb
        self._build()

    # ── 공개 메서드 ────────────────────────────────────

    def get_preferences(self) -> dict:
        return {
            "year":             self._year_var.get(),
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

    def _section(self, title: str, subtitle: str = "다수 선택 가능"):
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
        # 제목
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

    def _build_year(self):
        f = self._section("📚 학년 선택")
        self._year_var = ctk.StringVar(value="1학년")
        ctk.CTkSegmentedButton(f, values=["1학년","2학년","3학년","4학년"],
                               variable=self._year_var,
                               font=ctk.CTkFont(size=11)
                               ).pack(pady=(4,10), padx=12, fill="x")

    def _build_track(self):
        f = self._section("🔀 전공 트랙",
                          subtitle="2학년 때 어느 전공으로 갈 예정인가요?")
        self._track_var = ctk.StringVar(value="소프트웨어")
        ctk.CTkSegmentedButton(f, values=["소프트웨어","헬스케어"],
                               variable=self._track_var,
                               font=ctk.CTkFont(size=12)
                               ).pack(pady=(6,6), padx=12, fill="x")
        self._track_hint = ctk.CTkLabel(f, text="",
                                        font=ctk.CTkFont(size=10),
                                        text_color="#aaa", wraplength=290,
                                        justify="left")
        self._track_hint.pack(padx=12, pady=(0,8), anchor="w")
        self._track_var.trace_add("write", lambda *_: self._update_track_hint())
        self._update_track_hint()

    def _update_track_hint(self):
        self._track_hint.configure(
            text=TRACK_HINTS.get(self._track_var.get(), ""))

    def _build_major(self):
        f = self._section("📌 전공 과목 선택",
                          subtitle="트랙 기준에 따라 선택해주세요")
        self._major_vars = {}

        groups = [
            ("── 소프트웨어 전공 과목 ──", "#64B5F6", SW_COURSES),
            ("── 헬스케어 전공 과목 ──",   "#81C784", HC_COURSES),
            ("── 공통 필수 ──",            "#FFD54F", COMMON_COURSES),
        ]
        for label, color, courses in groups:
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                         text_color=color).pack(padx=12, pady=(6,2), anchor="w")
            for nm in courses:
                var = ctk.BooleanVar(value=False)
                self._major_vars[nm] = var
                ctk.CTkCheckBox(f, text=nm, variable=var,
                                font=ctk.CTkFont(size=11)
                                ).pack(pady=2, padx=20, anchor="w")
        ctk.CTkFrame(f, height=6, fg_color="transparent").pack()

    def _build_liberal(self):
        f = self._section("📋 교양필수 선택",
                          subtitle="각 역량에서 한 학기에 1개씩 권장")
        self._lib_vars = {}

        groups = [
            ("── 공동체 역량 (택1) ──",   "#888", LIBERAL_COMMUNITY),
            ("── 소통공감 역량 (택1) ──", "#888", LIBERAL_COMMUNICATION),
        ]
        for label, color, courses in groups:
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                         text_color=color).pack(padx=12, pady=(6,2), anchor="w")
            for nm in courses:
                var = ctk.BooleanVar(value=False)
                self._lib_vars[nm] = var
                ctk.CTkCheckBox(f, text=nm, variable=var,
                                font=ctk.CTkFont(size=11)
                                ).pack(pady=2, padx=20, anchor="w")
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
            values=["🥇 균형형","🥈 공강형","🥉 몰아듣기형"],
            variable=self._result_var, font=ctk.CTkFont(size=11)
        ).pack(pady=(0,10), padx=12, fill="x")

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
