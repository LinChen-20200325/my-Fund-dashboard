"""ui/helpers/story_nav.py — v18.193：故事化動線「敘事導覽列」

v5.0 Task2.2：讓使用者順著 spec 敘事閱讀 —
🌐 總經環境 → 📊 核心/衛星配置 → 🔍 單一基金深掘。
三個敘事 tab 頂部各放一行麵包屑、highlight 目前所在站，建立連貫敘事。
純展示、零資料依賴；內容（`story_nav_markdown`）與渲染分離以便單元測試。
"""
from __future__ import annotations

# 故事三站：key → (emoji+標籤, 這站在幹嘛)
_STEPS: tuple[tuple[str, str, str], ...] = (
    ("macro",     "① 🌐 總經環境",     "看懂景氣位階與拐點"),
    ("portfolio", "② 📊 核心/衛星配置", "決定資產怎麼擺"),
    ("fund",      "③ 🔍 單一基金深掘",  "挑出 / 汰換每一檔"),
)
_VALID = {s[0] for s in _STEPS}


def story_nav_markdown(current: str) -> str:
    """組敘事麵包屑 markdown（純函式、可測）。current 為目前站 key。

    目前站用藍色粗體 highlight，其餘灰色；尾端附目前站的一句話提示。
    """
    parts: list[str] = []
    for _key, _label, _hint in _STEPS:
        if _key == current:
            parts.append(f"**:blue[{_label}]**")
        else:
            parts.append(f":gray[{_label}]")
    line = "　→　".join(parts)
    _cur_hint = next((h for k, _, h in _STEPS if k == current), "")
    return f"{line}　·　_{_cur_hint}_" if _cur_hint else line


def render_story_nav(current: str) -> None:
    """在 tab 頂部渲染敘事導覽列（無效 key 時不渲染、不佔版面）。"""
    if current not in _VALID:
        return
    import streamlit as st
    st.caption(story_nav_markdown(current))
