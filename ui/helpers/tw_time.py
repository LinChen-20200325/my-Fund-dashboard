"""台灣時間 (UTC+8) 顯示用 helper（v18.181）。

Streamlit Cloud 伺服器跑 UTC，bare `datetime.now()` 會比台灣慢 8 小時，
使用者會誤以為「上次寫入時間不會動 / 對不上 Google Drive」。
所有給使用者看的 wall-clock 時間戳統一走這裡轉成台灣時間。

採固定 UTC+8 offset（台灣無日光節約時間），不依賴 tzdata，最穩。
"""
from __future__ import annotations

import datetime as _dt

TW_TZ = _dt.timezone(_dt.timedelta(hours=8))


def tw_now() -> _dt.datetime:
    """現在時間（台灣 UTC+8，timezone-aware datetime）。"""
    return _dt.datetime.now(TW_TZ)


def tw_now_str(fmt: str = "%Y-%m-%d %H:%M") -> str:
    """台灣時間格式化字串（預設 `YYYY-MM-DD HH:MM`）。"""
    return tw_now().strftime(fmt)
