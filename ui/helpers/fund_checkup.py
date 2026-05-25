"""v18.213：基金體檢表（郭老師「挑三揀四」PK 同類型）。

把每檔基金的含息報酬與 MoneyDJ「同類型平均」PK，
打敗同類＝🏆 優等生（抱緊）；明顯落後＝⚠️ 汰弱候選。

資料邊界（誠實告知，呼應 CLAUDE.md §4）：
  - 同類平均取自 MoneyDJ 績效評比頁 risk_metrics.peer_compare，約 3 成基金抓不到 → 標 ⬜ 不評。
  - 郭老師另兩項標準（成分股 ROE>15%/EPS 成長、規模流動性）資料源無法取得 → 不納入。
  - 買賣點（標準差／布林）沿用 MK 戰情室既算欄位，僅在本表附「買點」燈號。
純函式 + 單一 render，無 @st.cache_data（STATE.md 鐵律）。
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from ui.components.mk_dashboard import tag_price_zone

_DISPLAY_COLS = [
    "代碼", "標的名稱",
    "近1M(%)", "近3M(%)", "近6M(%)", "近1Y含息(%)",
    "同類平均(1Y%)", "超額(pp)",
    "夏普值", "年化波動(1Y%)", "買點", "體檢判定",
]

_ZONE_LABEL = {
    "Buy_Zone_Deep": "🟢🟢 超跌(-2σ)",
    "Buy_Zone": "🟢 便宜(-1σ)",
    "Take_Profit": "🟠 停利(+2σ)",
    "Hold": "—",
    "N/A": "—",
}

# 超額報酬（pp）分級門檻：打敗同類 ≥ +2 為優等生、落後 ≤ −2 為汰弱候選。
_EXCESS_GOOD = 2.0
_EXCESS_LAG = -2.0


def _safe_num(v):
    """寬鬆數值轉換：吃 float / "12.3%" / "1,234" / None → float 或 None。"""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        f = float(v)
    else:
        try:
            f = float(str(v).replace("%", "").replace(",", "").strip())
        except (TypeError, ValueError):
            return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _period_ret(fund: dict, perf_key: str, metric_key: str):
    """各期報酬：優先 MoneyDJ 官方 perf，缺則退本地 calc_metrics。"""
    mj = fund.get("moneydj_raw") or {}
    perf = mj.get("perf") or {}
    v = _safe_num(perf.get(perf_key))
    if v is not None:
        return v
    m = fund.get("metrics") or {}
    return _safe_num(m.get(metric_key))


def _ret_1y_total(fund: dict):
    """近 1Y 含息報酬：沿用全 app 一致的 compute_1y_total_return；缺則退 perf/metrics。"""
    try:
        from ui.helpers.macro_helpers import compute_1y_total_return
        _v, _ = compute_1y_total_return(fund)
        v = _safe_num(_v)
        if v is not None:
            return v
    except ImportError:
        pass
    mj = fund.get("moneydj_raw") or {}
    v = _safe_num((mj.get("perf") or {}).get("1Y"))
    if v is not None:
        return v
    m = fund.get("metrics") or {}
    for k in ("ret_1y_total", "ret_1y"):
        v = _safe_num(m.get(k))
        if v is not None:
            return v
    return None


def _extract_peer_1y(fund: dict):
    """從 peer_compare 取『同類型平均』報酬。回傳 (peer_ret 或 None, peer_label)。"""
    mj = fund.get("moneydj_raw") or {}
    peer = ((mj.get("risk_metrics") or {}).get("peer_compare")) or {}
    if not peer:
        return None, ""
    best_key = next(
        (k for k in peer
         if "平均" in k and ("同" in k or "類" in k or "型" in k or "區域" in k)),
        None,
    )
    if best_key is None:
        best_key = next((k for k in peer if "平均" in k), None)
    if best_key is None:
        return None, ""
    row = peer.get(best_key) or {}
    for v in row.values():
        f = _safe_num(v)
        if f is not None:
            return f, best_key
    return None, best_key


def _grade(ret_1y, peer_1y):
    """依超額報酬分級。回傳 (excess 或 None, 判定文字)。"""
    if peer_1y is None:
        return None, "⬜ 同類資料不足"
    if ret_1y is None:
        return None, "⬜ 報酬資料不足"
    excess = ret_1y - peer_1y
    if excess >= _EXCESS_GOOD:
        return excess, "🏆 優等生"
    if excess <= _EXCESS_LAG:
        return excess, "⚠️ 落後（汰弱）"
    return excess, "🟡 普通生"


def build_checkup_dataframe(portfolio_funds: list | None) -> pd.DataFrame:
    """把 portfolio_funds（已載入、依 code 去重）攤平成基金體檢 PK 表。"""
    if not portfolio_funds:
        return pd.DataFrame(columns=_DISPLAY_COLS)

    seen: set = set()
    rows: list = []
    for f in portfolio_funds:
        if not f.get("loaded") or f.get("load_error"):
            continue
        code = str(f.get("code", "") or "").strip().upper()
        if not code or code in seen:
            continue
        seen.add(code)

        m = f.get("metrics") or {}
        ret_1y = _ret_1y_total(f)
        peer_1y, _ = _extract_peer_1y(f)
        excess, verdict = _grade(ret_1y, peer_1y)
        rows.append({
            "代碼": f.get("code", "—"),
            "標的名稱": f.get("name") or f.get("code") or "—",
            "近1M(%)": _period_ret(f, "1M", "ret_1m"),
            "近3M(%)": _period_ret(f, "3M", "ret_3m"),
            "近6M(%)": _period_ret(f, "6M", "ret_6m"),
            "近1Y含息(%)": ret_1y,
            "同類平均(1Y%)": peer_1y,
            "超額(pp)": excess,
            "夏普值": _safe_num(m.get("sharpe")),
            "年化波動(1Y%)": _safe_num(m.get("std_1y")),
            "買點": _ZONE_LABEL.get(tag_price_zone(f), "—"),
            "體檢判定": verdict,
        })
    return pd.DataFrame(rows, columns=_DISPLAY_COLS)


def _style_checkup(df: pd.DataFrame):
    """🏆 優等生綠底 / ⚠️ 汰弱紅底 / 超跌價深綠底。"""
    def _row_color(row):
        v = str(row.get("體檢判定", ""))
        z = str(row.get("買點", ""))
        if v.startswith("🏆"):
            return ["background-color: #0f3a1a"] * len(row)
        if v.startswith("⚠️"):
            return ["background-color: #4a1f1f"] * len(row)
        if "超跌" in z:
            return ["background-color: #14361f"] * len(row)
        return [""] * len(row)
    return df.style.apply(_row_color, axis=1)


_CHECKUP_COL_CONFIG = {
    "近1M(%)": st.column_config.NumberColumn(
        "近1M(%)", format="%.2f", help="近一個月報酬（挑三揀四短期趨勢）"),
    "近3M(%)": st.column_config.NumberColumn(
        "近3M(%)", format="%.2f", help="近三個月報酬"),
    "近6M(%)": st.column_config.NumberColumn(
        "近6M(%)", format="%.2f", help="近六個月報酬"),
    "近1Y含息(%)": st.column_config.NumberColumn(
        "近1Y含息(%)", format="%.2f",
        help="近一年含息總報酬（淨值漲跌＋配息），PK 同類平均的主指標"),
    "同類平均(1Y%)": st.column_config.NumberColumn(
        "同類平均(1Y%)", format="%.2f",
        help="MoneyDJ 績效評比頁『同類型平均』報酬；約 3 成基金無此資料"),
    "超額(pp)": st.column_config.NumberColumn(
        "超額(pp)", format="%+.2f",
        help="近1Y含息 − 同類平均。≥ +2 為🏆優等生、≤ −2 為⚠️汰弱候選"),
    "夏普值": st.column_config.NumberColumn(
        "夏普值", format="%.2f",
        help="(年化報酬-無風險利率)/年化波動。<0 代表承擔風險卻沒賺錢"),
    "年化波動(1Y%)": st.column_config.NumberColumn(
        "年化波動(1Y%)", format="%.2f", help="近一年日報酬年化標準差"),
    "買點": st.column_config.TextColumn(
        "買點", help="標準差買點燈號：跌破 -1σ 便宜 / -2σ 超跌 / 破布林上軌停利"),
    "體檢判定": st.column_config.TextColumn(
        "體檢判定", help="與同類型 1Y 含息 PK：🏆優等生 / 🟡普通生 / ⚠️汰弱 / ⬜不評"),
}


def render_fund_checkup(portfolio_funds: list | None) -> None:
    """Tab3 expander：基金體檢 PK 表（與同類型比較，揪優等生 / 汰弱候選）。"""
    with st.expander("🩺 基金體檢表 — 與同類型 PK，揪出優等生 / 汰弱候選",
                     expanded=False):
        st.caption(
            "📖 郭老師「挑三揀四」法則：把每檔基金的含息報酬與『同類型平均』PK，"
            "打敗同類＝🏆 優等生（抱緊滾雪球），明顯落後＝⚠️ 汰弱候選。")

        df = build_checkup_dataframe(portfolio_funds)
        if df.empty:
            st.info("📊 載入基金後，這裡會列出每檔與同類型的 PK 體檢結果。")
            return

        st.markdown(
            "- **近 1M/3M/6M/1Y**：各區間報酬趨勢，連續落後同類是汰換警訊。\n"
            "- **同類平均(1Y)**：來自 MoneyDJ 績效評比頁，約 3 成基金抓不到 → 標 ⬜ 不評。\n"
            "- **超額(pp)** = 近1Y含息 − 同類平均：≥ +2 🏆優等生；±2 內 🟡普通生；≤ −2 ⚠️汰弱候選。\n"
            "- ⚠️ 老師另兩項標準（成分股 ROE>15%/EPS 成長、規模流動性）資料源無法取得，未納入；"
            "買賣點細節請見上方「MK 智能戰情室」。")

        _verdict = df["體檢判定"]
        n_good = int(_verdict.str.startswith("🏆").sum())
        n_lag = int(_verdict.str.startswith("⚠️").sum())
        n_na = int(_verdict.str.startswith("⬜").sum())
        st.markdown(
            f"**🏆 {n_good} 檔優等生** ・ ⚠️ {n_lag} 檔汰弱候選 ・ "
            f"⬜ {n_na} 檔同類資料不足（共 {len(df)} 檔）")

        df = df.sort_values(
            by="超額(pp)", ascending=False, na_position="last", kind="stable")
        st.dataframe(
            _style_checkup(df),
            column_config=_CHECKUP_COL_CONFIG,
            hide_index=True, use_container_width=True,
        )
