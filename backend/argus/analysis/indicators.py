"""Technical-indicator math built directly on numpy/pandas (no ta-lib runtime dep)."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..markets.base import Candle


def candles_to_df(candles: list[Candle]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
    df = pd.DataFrame([c.model_dump() for c in candles])
    df = df.sort_values("time").reset_index(drop=True)
    return df


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd = _ema(close, fast) - _ema(close, slow)
    signal_line = _ema(macd, signal)
    return pd.DataFrame({"macd": macd, "macd_signal": signal_line, "macd_hist": macd - signal_line})


def _bbands(close: pd.Series, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    mid = close.rolling(period).mean()
    sd = close.rolling(period).std()
    return pd.DataFrame({
        "bb_mid": mid,
        "bb_upper": mid + std * sd,
        "bb_lower": mid - std * sd,
    })


def _kdj(df: pd.DataFrame, period: int = 9, k_smooth: int = 3, d_smooth: int = 3) -> pd.DataFrame:
    low = df["low"].rolling(period).min()
    high = df["high"].rolling(period).max()
    rsv = (df["close"] - low) / (high - low).replace(0, np.nan) * 100
    k = rsv.ewm(alpha=1 / k_smooth, adjust=False).mean()
    d = k.ewm(alpha=1 / d_smooth, adjust=False).mean()
    j = 3 * k - 2 * d
    return pd.DataFrame({"kdj_k": k, "kdj_d": d, "kdj_j": j})


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h_l = df["high"] - df["low"]
    h_c = (df["high"] - df["close"].shift()).abs()
    l_c = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([h_l, h_c, l_c], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff()).fillna(0)
    return (direction * df["volume"]).cumsum()


def compute_indicators(candles: list[Candle]) -> dict[str, Any]:
    df = candles_to_df(candles)
    if df.empty:
        return {"series": [], "latest": {}}

    close = df["close"]
    df["sma_20"] = close.rolling(20).mean()
    df["sma_50"] = close.rolling(50).mean()
    df["sma_200"] = close.rolling(200).mean()
    df["ema_12"] = _ema(close, 12)
    df["ema_26"] = _ema(close, 26)
    df["rsi_14"] = _rsi(close, 14)
    df = pd.concat([df, _macd(close)], axis=1)
    df = pd.concat([df, _bbands(close)], axis=1)
    df = pd.concat([df, _kdj(df)], axis=1)
    df["atr_14"] = _atr(df)
    df["obv"] = _obv(df)

    df = df.replace({np.nan: None})
    series = df.assign(time=df["time"].astype(str)).to_dict(orient="records")
    latest = series[-1] if series else {}
    return {"series": series, "latest": latest}


def latest_signals(indicators: dict[str, Any]) -> dict[str, str]:
    """Quick rule-based read of the latest indicator values (used by Technical Analyst agent)."""
    latest = indicators.get("latest") or {}
    if not latest:
        return {}
    out: dict[str, str] = {}
    rsi = latest.get("rsi_14")
    if rsi is not None:
        if rsi > 70:
            out["rsi"] = f"overbought ({rsi:.1f})"
        elif rsi < 30:
            out["rsi"] = f"oversold ({rsi:.1f})"
        else:
            out["rsi"] = f"neutral ({rsi:.1f})"
    macd, signal = latest.get("macd"), latest.get("macd_signal")
    if macd is not None and signal is not None:
        out["macd"] = "bullish crossover" if macd > signal else "bearish crossover"
    sma50, sma200 = latest.get("sma_50"), latest.get("sma_200")
    if sma50 is not None and sma200 is not None:
        out["trend"] = "golden cross / uptrend" if sma50 > sma200 else "death cross / downtrend"
    close = latest.get("close")
    upper, lower = latest.get("bb_upper"), latest.get("bb_lower")
    if all(v is not None for v in (close, upper, lower)):
        if close >= upper:
            out["bbands"] = "near upper band — extended"
        elif close <= lower:
            out["bbands"] = "near lower band — compressed"
        else:
            out["bbands"] = "mid-channel"
    k, d = latest.get("kdj_k"), latest.get("kdj_d")
    if k is not None and d is not None:
        if k > d and k < 80:
            out["kdj"] = "bullish, room to run"
        elif k < d and k > 20:
            out["kdj"] = "bearish, room to fall"
        else:
            out["kdj"] = f"K={k:.1f} D={d:.1f}"
    return out
