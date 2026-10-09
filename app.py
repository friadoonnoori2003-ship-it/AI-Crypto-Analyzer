# -*- coding: utf-8 -*-
"""
Web GUI for AI_Crypto_Analyzer_OpenRouter_Free_Fallback_FIXED__2_.py

The original analyzer file is NOT modified. This wrapper:
  1. shows a web form (API key, AI model, exchange, coins),
  2. runs the original .py file and answers its input()/getpass() prompts
     from the form,
  3. shows the results as cards and tables (plus the full text log).

Run locally:   streamlit run app.py
"""

import ast
import builtins
import contextlib
import getpass as getpass_module
import io
import runpy
import threading
from pathlib import Path

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------
# The ORIGINAL program (keep this file next to app.py, unchanged)
# ------------------------------------------------------------------
SCRIPT_NAME = "AI_Crypto_Analyzer_OpenRouter_Free_Fallback_FIXED__2_.py"
SCRIPT_PATH = Path(__file__).resolve().parent / SCRIPT_NAME

# The original script uses global stdin/stdout, so only one analysis
# can run at a time. Extra users simply wait their turn.
RUN_LOCK = threading.Lock()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
@st.cache_data
def load_model_list():
    """Read OPENROUTER_MODELS from the original file without running it."""
    try:
        tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and any(getattr(t, "id", "") == "OPENROUTER_MODELS" for t in node.targets)
            ):
                return list(ast.literal_eval(node.value))
    except Exception:
        pass
    return ["openrouter/free"]


def run_original_script(api_key, model_answers, exchange_choice, coins):
    """
    Run the original script, feeding it the answers it would normally ask
    for in the terminal. Returns (namespace, log_text, error_text).
    """
    answers = iter(list(model_answers) + [exchange_choice, coins])

    def fake_input(prompt=""):
        print(prompt, end="")
        value = next(answers)
        print(value)
        return value

    def fake_getpass(prompt="", stream=None):
        print(prompt + "********")
        return api_key

    buffer = io.StringIO()
    namespace, error = {}, None

    with RUN_LOCK:
        old_input, old_getpass = builtins.input, getpass_module.getpass
        builtins.input, getpass_module.getpass = fake_input, fake_getpass
        try:
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                namespace = runpy.run_path(str(SCRIPT_PATH), run_name="crypto_analyzer")
        except SystemExit:
            error = "No market data could be analyzed (check the coin names / exchange)."
        except Exception as e:  # ValueError from bad input, network errors, etc.
            error = f"{type(e).__name__}: {e}"
        finally:
            builtins.input, getpass_module.getpass = old_input, old_getpass

    return namespace, buffer.getvalue(), error


SIGNAL_COLORS = {"BUY": "green", "SELL": "red", "WAIT": "orange"}


def show_decision(d):
    color = SIGNAL_COLORS.get(str(d.signal).upper(), "gray")
    with st.container(border=True):
        top = st.columns([2, 2, 1])
        top[0].markdown(f"### {d.symbol}")
        top[0].caption(d.exchange)
        top[1].markdown(f"### :{color}[{str(d.signal).upper()}]")
        top[2].metric("Confidence", f"{d.confidence}%")

        st.write(f"**Trend:** {d.trend}  |  **Momentum:** {d.momentum}")

        c = st.columns(3)
        c[0].metric("Entry (live)", d.entry if d.entry is not None else "-")
        c[1].metric("Stop loss", d.stop_loss if d.stop_loss is not None else "-")
        c[2].metric("Take profit", d.take_profit if d.take_profit is not None else "-")

        with st.expander("Key reasons & risk"):
            for r in d.reasons:
                st.write(f"• {r}")
            st.write(f"**Risk:** {d.risk}")


# ------------------------------------------------------------------
# Page
# ------------------------------------------------------------------
st.set_page_config(page_title="AI Crypto Market Analyzer", page_icon="📈", layout="wide")
st.title("📈 AI Crypto Market Analyzer")
st.caption(
    "Binance / MEXC technical analysis + OpenRouter AI. Analysis only — "
    "this tool does NOT place trades and is not financial advice."
)

if not SCRIPT_PATH.exists():
    st.error(f"Missing file: {SCRIPT_NAME}. Put it in the same folder as app.py.")
    st.stop()

models = load_model_list()

with st.sidebar:
    st.header("Settings")

    api_key = st.text_input(
        "OpenRouter API key",
        type="password",
        help="Used only for this run. It is not saved or stored.",
    )

    mode = st.radio(
        "AI model",
        ["Auto (free router + fallback)", "Choose models", "Custom model ID"],
    )

    model_answers = [""]  # "" = auto in the original script
    if mode == "Choose models":
        picked = st.multiselect("Models", models, default=models[:1])
        idx = ",".join(str(models.index(m) + 1) for m in picked)
        model_answers = [idx]
    elif mode == "Custom model ID":
        custom = st.text_input("OpenRouter model ID", placeholder="openai/gpt-5")
        model_answers = ["custom", custom.strip()]

    exchange = st.selectbox("Exchange", ["Binance", "MEXC"])
    coins = st.text_input("Coins (comma separated)", value="BTC, ETH, SOL")

    run = st.button("🚀 Run analysis", type="primary", width="stretch")

if run:
    problems = []
    if not api_key.strip():
        problems.append("Enter your OpenRouter API key.")
    if mode == "Choose models" and not model_answers[0]:
        problems.append("Pick at least one model.")
    if mode == "Custom model ID" and not model_answers[1]:
        problems.append("Enter a model ID.")
    if not coins.strip():
        problems.append("Enter at least one coin.")

    if problems:
        for p in problems:
            st.warning(p)
    else:
        with st.spinner("Fetching market data and asking the AI… this can take a minute."):
            ns, log, error = run_original_script(
                api_key.strip(),
                model_answers,
                "1" if exchange == "Binance" else "2",
                coins.strip(),
            )
        st.session_state["result"] = {"ns": ns, "log": log, "error": error}

res = st.session_state.get("result")

if res:
    ns, log, error = res["ns"], res["log"], res["error"]

    if error:
        st.error(error)

    ai_analyses = ns.get("ai_analyses") or {}
    results_df = ns.get("results_df")

    tab_ai, tab_tech, tab_log = st.tabs(["🤖 AI signals", "📊 Technical data", "🧾 Full log"])

    with tab_ai:
        if ai_analyses:
            for model_name, analysis in ai_analyses.items():
                st.subheader(f"Model: {model_name}")
                cols = st.columns(2)
                for i, decision in enumerate(analysis.decisions):
                    with cols[i % 2]:
                        show_decision(decision)
        elif not error:
            st.info("The AI step did not finish (free models are often rate-limited). "
                    "Try again in a moment or use Auto.")
        else:
            st.info("No AI results.")

    with tab_tech:
        if isinstance(results_df, pd.DataFrame):
            cols = [c for c in [
                "exchange", "symbol", "technical_signal", "final_score", "price",
                "price_fetched_at", "entry", "stop_loss", "take_profit",
                "rsi_15m", "rsi_1h", "rsi_4h", "score_15m", "score_1h", "score_4h",
            ] if c in results_df.columns]
            st.dataframe(results_df[cols], width="stretch", hide_index=True)
        else:
            st.info("No technical data.")

    with tab_log:
        st.code(log or "(empty)", language="text")

    st.caption("BUY / SELL / WAIT are analytical signals, not guarantees. "
               "Paper-trade before using real money.")
else:
    st.info("Fill in the settings on the left, then press **Run analysis**.")
