"""Dashboard 6 panel doc tu data/logs.jsonl theo config/dashboard.yaml.

Chay (o thu muc goc repo, da activate venv):
    pip install streamlit altair pandas pyyaml
    streamlit run dashboard/app.py
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import yaml

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config" / "dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]
PANELS = {p["id"]: p for p in CFG["panels"]}
RANGE_MIN = CFG["time_range_minutes"]
REFRESH = CFG["refresh_seconds"]

st.set_page_config(page_title=CFG["title"], layout="wide")
st.title(CFG["title"])
anchor = st.sidebar.checkbox("Lay moc thoi gian theo log moi nhat (thay vi gio hien tai)", value=True)


def load():
    rows = []
    path = ROOT / "data" / "logs.jsonl"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
    return df


def window(df):
    end = df["ts"].max() if anchor else pd.Timestamp.now(tz="UTC")
    start = (df["ts"].min() - timedelta(minutes=1)) if anchor else (end - timedelta(minutes=RANGE_MIN))
    return df[(df["ts"] >= start) & (df["ts"] <= end)], start, end


def per_minute(s, how, start, end):
    idx = pd.date_range(start.floor("min"), end.floor("min"), freq="1min")
    r = s.resample("1min")
    out = getattr(r, how)()
    return out.reindex(idx)


def chart(data, title, unit, thr, thr_label):
    """data: DataFrame index=time, columns=series. thr: gia tri threshold."""
    data = data.copy()
    data.index = data.index.tz_convert(None)
    data.index.name = "time"
    d = data.reset_index().melt("time", var_name="series", value_name="value")
    line = alt.Chart(d).mark_line(point=True).encode(
        x=alt.X("time:T", title="Time (UTC)"),
        y=alt.Y("value:Q", title=unit),
        color="series:N",
    )
    rule = alt.Chart(pd.DataFrame({"y": [thr]})).mark_rule(color="red", strokeDash=[6, 4]).encode(y="y:Q")
    label = alt.Chart(pd.DataFrame({"y": [thr], "t": [thr_label]})).mark_text(
        align="left", dx=4, dy=-6, color="red"
    ).encode(y="y:Q", text="t:N", x=alt.value(4))
    st.altair_chart((line + rule + label).properties(height=260), width="stretch")


def head(p):
    t = p["threshold"]
    st.subheader(f'{p["title"]}  ({p["unit"]})')
    st.caption(
        f'time range {RANGE_MIN} phut | refresh {REFRESH}s | '
        f'threshold: {t["aggregation"]} {t["operator"]} {t["value"]}'
    )


def status(ok):
    return "OK" if ok else "VUOT THRESHOLD"


@st.fragment(run_every=REFRESH)
def render():
    df = load()
    if df.empty or "ts" not in df:
        st.warning("Chua co du lieu trong data/logs.jsonl. Chay scripts/load_test.py truoc.")
        return
    df, start, end = window(df)
    if df.empty:
        st.warning(f"Khong co log trong {RANGE_MIN} phut gan nhat. Bat 'Lay moc theo log moi nhat' o sidebar hoac chay load_test.")
        return
    st.caption(f"Khoang du lieu: {start:%H:%M} - {end:%H:%M} UTC | {len(df)} events")

    resp = df[df["event"] == "response_sent"].set_index("ts")
    recv = df[df["event"] == "request_received"].set_index("ts")
    fail = df[df["event"] == "request_failed"].set_index("ts")

    c1, c2, c3 = st.columns(3)
    # 1. Latency
    with c1:
        p = PANELS["latency"]; head(p)
        if not resp.empty:
            q = resp["latency_ms"].quantile([.5, .95, .99])
            ttft95 = resp["ttft_ms"].quantile(.95)
            m = st.columns(4)
            m[0].metric("P50", f"{q[.5]:.0f}"); m[1].metric("P95", f"{q[.95]:.0f}")
            m[2].metric("P99", f"{q[.99]:.0f}"); m[3].metric("TTFT P95", f"{ttft95:.0f}")
            st.write(status(q[.95] <= p["threshold"]["value"]))
            g = pd.DataFrame({
                "P50": resp["latency_ms"].resample("1min").quantile(.5),
                "P95": resp["latency_ms"].resample("1min").quantile(.95),
                "P99": resp["latency_ms"].resample("1min").quantile(.99),
                "TTFT P95": resp["ttft_ms"].resample("1min").quantile(.95),
            })
            chart(g, p["title"], "ms", p["threshold"]["value"], "P95 <= 3000 ms")
    # 2. Traffic
    with c2:
        p = PANELS["traffic"]; head(p)
        t = per_minute(recv["event"], "count", start, end).fillna(0)
        rate = len(recv) / RANGE_MIN if not anchor else len(recv) / max((end - start).total_seconds() / 60, 1)
        st.metric("Requests", len(recv)); st.write(status(rate >= p["threshold"]["value"]) + f" (rate {rate:.2f}/phut)")
        chart(pd.DataFrame({"requests/min": t}), p["title"], "requests_per_minute", p["threshold"]["value"], "rate >= 1/min")
    # 3. Errors
    with c3:
        p = PANELS["errors"]; head(p)
        err_pct = len(fail) / len(recv) * 100 if len(recv) else 0
        ts_ok = resp["tool_success"].dropna() if "tool_success" in resp else pd.Series(dtype=bool)
        ret_pct = (ts_ok == True).mean() * 100 if len(ts_ok) else 100.0  # noqa: E712
        m = st.columns(2)
        m[0].metric("Error rate %", f"{err_pct:.1f}"); m[1].metric("Retrieval success %", f"{ret_pct:.1f}")
        st.write(status(err_pct <= p["threshold"]["value"]))
        f_min = per_minute(fail["event"], "count", start, end).fillna(0) if not fail.empty else per_minute(recv["event"], "count", start, end).fillna(0) * 0
        r_min = per_minute(recv["event"], "count", start, end).fillna(0)
        rate_min = (f_min.astype(float) / r_min.astype(float).where(r_min > 0) * 100).fillna(0)
        chart(pd.DataFrame({"error rate %": rate_min}), p["title"], "percent", p["threshold"]["value"], "error <= 2 %")
        if not fail.empty and "error_type" in fail:
            st.bar_chart(fail["error_type"].value_counts())

    c4, c5, c6 = st.columns(3)
    # 4. Cost
    with c4:
        p = PANELS["cost"]; head(p)
        total = resp["cost_usd"].sum() if not resp.empty else 0
        st.metric("Total cost (USD)", f"{total:.4f}"); st.write(status(total <= p["threshold"]["value"]))
        cum = per_minute(resp["cost_usd"], "sum", start, end).fillna(0).cumsum()
        chart(pd.DataFrame({"cumulative cost": cum}), p["title"], "usd", p["threshold"]["value"], "total <= 2.5 USD")
    # 5. Tokens
    with c5:
        p = PANELS["tokens"]; head(p)
        ti, to = resp["tokens_in"].sum(), resp["tokens_out"].sum()
        m = st.columns(2); m[0].metric("Tokens in", int(ti)); m[1].metric("Tokens out", int(to))
        st.write(status(max(ti, to) <= p["threshold"]["value"]))
        g = pd.DataFrame({
            "tokens_in": per_minute(resp["tokens_in"], "sum", start, end).fillna(0).cumsum(),
            "tokens_out": per_minute(resp["tokens_out"], "sum", start, end).fillna(0).cumsum(),
        })
        chart(g, p["title"], "tokens", p["threshold"]["value"], "sum <= 50000")
    # 6. Quality
    with c6:
        p = PANELS["quality"]; head(p)
        mean = resp["quality_score"].mean() if not resp.empty else 0
        st.metric("Mean quality", f"{mean:.2f}"); st.write(status(mean >= p["threshold"]["value"]))
        qm = resp["quality_score"].resample("1min").mean()
        chart(pd.DataFrame({"quality": qm}), p["title"], "score_0_to_1", p["threshold"]["value"], "mean >= 0.75")


render()