# ────────────────────────────────
# canvas_view.py  —  시간표 캔버스 그리기
# ────────────────────────────────

import tkinter as tk
from data_loader import load_data, time_to_min
from config import COLORS, DAYS, TIMETABLE_START_H, TIMETABLE_END_H


class TimetableCanvas:
    """시간표를 그리는 캔버스 위젯 래퍼"""

    HDR    = 32   # 요일 헤더 높이 (px)
    TIME_W = 48   # 시간 열 너비 (px)

    def __init__(self, parent):
        self.canvas = tk.Canvas(parent, bg="#0f0f1a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._subject_profs: list = []
        self.canvas.bind("<Configure>", self._on_resize)

    # ── 공개 메서드 ────────────────────────────────────

    def show(self, subject_profs: list):
        """(과목명, 교수명_분반번호) 튜플 목록을 받아 시간표를 그림"""
        self._subject_profs = subject_profs
        self._draw()

    def clear(self):
        """빈 시간표(안내 문구)를 표시"""
        self._subject_profs = []
        self._draw()

    # ── 내부 메서드 ────────────────────────────────────

    def _on_resize(self, _event):
        self._draw()

    def _get_online_subjects(self, df) -> list:
        """
        요일 정보가 없는 과목(온라인 강좌) 목록 반환.
        반환: [(과목명, 학점), ...]
        """
        online = []
        for nm, prof_key in self._subject_profs:
            try:
                last_sep  = prof_key.rfind("_")
                prof_name = prof_key[:last_sep]
                ban       = int(prof_key[last_sep + 1:])
            except Exception:
                continue

            rows = df[
                (df["과목명"] == nm) &
                (df["교수"]   == prof_name) &
                (df["분반"]   == ban)
            ]
            if rows.empty:
                continue

            days = [str(r["요일"]) for _, r in rows.iterrows()]
            if all(d in ("", "nan") for d in days):
                cr = float(rows.iloc[0].get("학점", 0))
                online.append((nm, cr))
        return online

    def _draw(self):
        c = self.canvas
        c.delete("all")

        W = c.winfo_width()
        H = c.winfo_height()
        if W < 100 or H < 50:
            return

        df = load_data()
        online = self._get_online_subjects(df) if self._subject_profs else []

        n_slots = TIMETABLE_END_H - TIMETABLE_START_H

        # 온라인 열 항상 유지 (6열 기준)
        dw = (W - self.TIME_W) // 6
        sh = (H - self.HDR) / n_slots

        self._draw_grid(c, W, H, dw, sh, n_slots)

        if not self._subject_profs:
            c.create_text(W // 2, H // 2,
                          text="조건을 선택하고\n시간표를 생성해주세요 😊",
                          fill="#444", font=("맑은 고딕", 15), justify="center")
            return

        self._draw_courses(c, dw, sh, df)
        self._draw_online_col(c, dw, sh, online)

    def _draw_grid(self, c, W, H, dw, sh, n_slots):
        HDR, TIME_W = self.HDR, self.TIME_W

        c.create_rectangle(0, 0, W, H, fill="#0f0f1a", outline="")

        # 요일 헤더 (월~금)
        for i, day in enumerate(DAYS):
            x0 = TIME_W + i * dw
            c.create_rectangle(x0, 0, x0 + dw, HDR,
                                fill="#1c1c30", outline="#2a2a45")
            c.create_text(x0 + dw // 2, HDR // 2, text=day,
                          fill="white", font=("맑은 고딕", 11, "bold"))

        # 온라인 열 헤더 (항상 표시)
        ox = TIME_W + 5 * dw
        c.create_rectangle(ox, 0, ox + dw, HDR,
                            fill="#1c2030", outline="#2a2a45")
        c.create_text(ox + dw // 2, HDR // 2, text="📡 온라인",
                      fill="#aad4ff", font=("맑은 고딕", 10, "bold"))

        # 시간 눈금 + 가로선 (월~금 영역만)
        grid_w = TIME_W + 5 * dw
        for i in range(n_slots + 1):
            y = HDR + i * sh
            c.create_line(TIME_W, y, grid_w, y, fill="#1e1e35")
            if i < n_slots:
                c.create_rectangle(0, y, TIME_W, y + sh,
                                   fill="#131320", outline="#1e1e35")
                c.create_text(TIME_W // 2, y + sh // 2,
                              text=f"{TIMETABLE_START_H + i}시",
                              fill="#555", font=("맑은 고딕", 9))

        # 세로선 (월~금 + 온라인)
        for i in range(7):
            c.create_line(TIME_W + i * dw, HDR,
                          TIME_W + i * dw, H, fill="#1e1e35")

    def _draw_courses(self, c, dw, sh, df):
        HDR, TIME_W = self.HDR, self.TIME_W
        base = TIMETABLE_START_H * 60

        names = [nm for nm, _ in self._subject_profs]

        # 색상 매핑
        cmap = {nm: COLORS[i % len(COLORS)]
                for i, nm in enumerate(names)}

        for nm, prof_key in self._subject_profs:
            try:
                last_sep  = prof_key.rfind("_")
                prof_name = prof_key[:last_sep]
                ban       = int(prof_key[last_sep + 1:])
            except Exception:
                continue

            rows = df[
                (df["과목명"] == nm) &
                (df["교수"]   == prof_name) &
                (df["분반"]   == ban)
            ]
            if rows.empty:
                continue

            for _, row in rows.iterrows():
                day = str(row["요일"])
                if day not in DAYS or day == "nan":
                    continue

                s = time_to_min(row["시작"])
                e = time_to_min(row["종료"])
                if s < 0 or e < 0:
                    continue

                s = max(s, base)
                e = min(e, TIMETABLE_END_H * 60)
                if s >= e:
                    continue

                di = DAYS.index(day)
                x0 = TIME_W + di * dw

                y0 = round(HDR + (s - base) / 60 * sh)
                y1 = round(HDR + (e - base) / 60 * sh)

                c.create_rectangle(x0 + 1, y0, x0 + dw - 1, y1,
                                   fill=cmap[nm], outline="")

                bh   = y1 - y0
                room = str(row.get("강의실", ""))
                room = "" if room == "nan" else room
                cx   = x0 + dw // 2

                if bh >= 80:
                    c.create_text(cx, y0 + bh // 2 - 18,
                                  text=nm, fill="white",
                                  font=("맑은 고딕", 11, "bold"),
                                  width=dw - 6)
                    c.create_text(cx, y0 + bh // 2 + 2,
                                  text=prof_name, fill="#ddd",
                                  font=("맑은 고딕", 10),
                                  width=dw - 6)
                    if room:
                        c.create_text(cx, y0 + bh // 2 + 18,
                                      text=room, fill="#bbb",
                                      font=("맑은 고딕", 9),
                                      width=dw - 6)

                elif bh >= 50:
                    c.create_text(cx, y0 + bh // 2 - 9,
                                  text=nm, fill="white",
                                  font=("맑은 고딕", 11, "bold"),
                                  width=dw - 6)
                    c.create_text(cx, y0 + bh // 2 + 9,
                                  text=prof_name, fill="#ddd",
                                  font=("맑은 고딕", 10),
                                  width=dw - 6)

                elif bh >= 28:
                    c.create_text(cx, y0 + bh // 2,
                                  text=nm, fill="white",
                                  font=("맑은 고딕", 10, "bold"),
                                  width=dw - 6)

    def _draw_online_col(self, c, dw, sh, online: list):
        """온라인 강좌를 오른쪽 열에 위에서부터 순서대로 블록으로 표시"""
        HDR, TIME_W = self.HDR, self.TIME_W

        ox   = TIME_W + 5 * dw   # 온라인 열 x 시작
        cx   = ox + dw // 2      # 온라인 열 가로 중심
        BH   = round(sh * 1.5)   # 블록 높이 (1.5시간 분량)
        PAD  = 4                  # 블록 간격

        names = [nm for nm, _ in self._subject_profs]
        cmap  = {nm: COLORS[i % len(COLORS)] for i, nm in enumerate(names)}

        y = HDR + PAD
        for nm, cr in online:
            y1 = y + BH
            color = cmap.get(nm, COLORS[0])

            c.create_rectangle(ox + 2, y, ox + dw - 2, y1,
                               fill=color, outline="")

            # 과목명
            c.create_text(cx, y + BH // 2 - 10,
                          text=nm, fill="white",
                          font=("맑은 고딕", 10, "bold"),
                          width=dw - 8)
            # 학점
            c.create_text(cx, y + BH // 2 + 10,
                          text=f"{cr}학점", fill="#eee",
                          font=("맑은 고딕", 10),
                          width=dw - 8)

            y = y1 + PAD
