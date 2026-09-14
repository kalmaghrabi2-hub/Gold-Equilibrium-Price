#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/gold/data/latest.json"
CAL = ROOT / "docs/gold/data/weekly_calibration.json"
FCAL = ROOT / "docs/gold/data/fundamentals_calibration.json"
UA = "Mozilla/5.0 GoldEquilibriumPrice/3.1"
MACRO_SERIES = ["DX-Y.NYB", "^TNX", "^VIX", "TIP"]


def get_text(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def get_json(url):
    return json.loads(get_text(url))


def yahoo_quote(symbol):
    q = urllib.parse.quote(symbol, safe="")
    now = int(datetime.now(timezone.utc).timestamp())
    start = now - 21 * 86400
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?period1={start}&period2={now}&interval=1d&events=history"
    payload = get_json(url)
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError("Yahoo empty " + symbol)
    ts = result.get("timestamp") or []
    closes = (((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
    for t, value in reversed(list(zip(ts, closes))):
        if value is not None and math.isfinite(float(value)) and float(value) > 0:
            return {
                "series": symbol,
                "date": datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat(),
                "value": float(value),
                "source": url,
            }
    raise RuntimeError("Yahoo no valid close " + symbol)


def fetch_spot():
    try:
        payload = get_json("https://xaus.com/api/v1/spot?compact=1")
        ds = payload.get("data_state") or {}
        value = payload.get("spot_usd_oz") or (payload.get("xau") or {}).get("price")
        if value is None:
            raise RuntimeError("XAUS price missing")
        return {
            "usd_oz": float(value),
            "as_of": ds.get("as_of") or payload.get("updated_at"),
            "freshness_status": ds.get("status", "unknown"),
            "provider": "XAUS",
            "source": "https://xaus.com/api/v1/spot",
        }
    except Exception:
        try:
            quote = yahoo_quote("GC=F")
            return {
                "usd_oz": quote["value"],
                "as_of": quote["date"],
                "freshness_status": "futures_fallback",
                "provider": "Yahoo GC=F",
                "source": quote["source"],
            }
        except Exception as exc:
            payload = get_json("https://api.gold-api.com/price/XAU")
            value = payload.get("price")
            if value is None:
                raise RuntimeError("spot feeds failed " + str(exc))
            return {
                "usd_oz": float(value),
                "as_of": payload.get("updatedAt") or payload.get("updated_at"),
                "freshness_status": "fallback",
                "provider": "Gold API",
                "source": "https://api.gold-api.com/price/XAU",
            }


def wgc_urls(now):
    q = (now.month - 1) // 3 + 1
    year = now.year
    q -= 1
    if q == 0:
        q, year = 4, year - 1
    out = []
    for _ in range(8):
        out.append(f"https://www.gold.org/goldhub/research/gold-demand-trends/gold-demand-trends-q{q}-{year}")
        q -= 1
        if q == 0:
            q, year = 4, year - 1
    return out


def parse_wgc(page, url):
    text = html.unescape(page)
    text = re.sub(r"<[^>]+>", " ", text).replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)

    def value(*labels):
        for label in labels:
            pattern = re.escape(label) + r"\s*\|?\s*([\-\d,.]+)\s*\|?\s*([\-\d,.]+)\s*\|?\s*([\-\d,.]+)\s*\|?\s*([\-\d,.]+)\s*\|?\s*([\-\d,.]+)"
            match = re.search(pattern, text, re.I)
            if match:
                return float(match.group(5).replace(",", ""))
        raise RuntimeError("missing WGC " + labels[0])

    data = {
        "mine_production_t": value("Mine Production"),
        "producer_hedging_t": value("Net Producer Hedging"),
        "recycled_gold_t": value("Recycled Gold"),
        "total_supply_t": value("Total Supply"),
        "jewellery_fabrication_t": value("Jewellery Fabrication"),
        "technology_t": value("Technology"),
        "investment_t": value("Investment"),
        "bar_coin_t": value("Total Bar and Coin", "Bar and Coin"),
        "etf_t": value("ETFs & Similar Products", "Gold ETFs", "ETFs"),
        "central_banks_t": value("Central Banks & Other inst.", "Central Banks"),
        "gold_demand_ex_otc_t": value("Gold Demand"),
        "otc_other_t": value("OTC and Other"),
        "total_demand_t": value("Total Demand"),
        "quarter_avg_lbma_usd_oz": value("LBMA Gold Price (US$/oz)", "LBMA (PM) Gold Price (US$/oz)"),
        "source": url,
    }
    match = re.search(r"Gold Demand Trends:\s*Q([1-4])\s*(\d{4})", text, re.I)
    if match:
        data["quarter"] = f"{match.group(2)}-Q{match.group(1)}"
    return data


def fetch_wgc(now):
    errors = []
    for url in wgc_urls(now):
        try:
            page = get_text(url)
            if "Total Supply" not in html.unescape(page):
                raise RuntimeError("table absent")
            return parse_wgc(page, url)
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("WGC unavailable: " + " | ".join(errors))


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def physical_features(wgc):
    supply = max(wgc["total_supply_t"], 1.0)
    strategic = wgc["bar_coin_t"] + wgc["etf_t"] + wgc["central_banks_t"]
    return [
        strategic / supply,
        wgc["recycled_gold_t"] / supply,
        (wgc.get("producer_hedging_t") or 0.0) / supply,
    ]


def physical_overlay(wgc, fcal):
    x = physical_features(wgc)
    raw = 1.0
    predicted = 0.0
    gate = (fcal or {}).get("walk_forward_gate") or "PENDING"
    if fcal:
        beta = fcal.get("beta") or []
        means = fcal.get("means") or []
        sds = fcal.get("sds") or []
        if len(beta) == len(x) + 1 and len(means) == len(x) and len(sds) == len(x):
            z = [1.0] + [(v - m) / s for v, m, s in zip(x, means, sds)]
            predicted = sum(a * b for a, b in zip(beta, z))
            raw = math.exp(predicted)
    diagnostic_multiplier = min(max(raw, 0.88), 1.12)
    applied = gate == "PASS"
    effective_multiplier = diagnostic_multiplier if applied else 1.0
    return {
        "strategic_demand_share": x[0],
        "recycling_share": x[1],
        "producer_hedging_share": x[2],
        "predicted_next_quarter_return_pct": 100.0 * (raw - 1.0),
        "raw_multiplier": raw,
        "diagnostic_multiplier": diagnostic_multiplier,
        "effective_multiplier": effective_multiplier,
        "multiplier": effective_multiplier,
        "applied_to_pstar": applied,
        "guardrail_active": diagnostic_multiplier != raw,
        "status": "APPLIED_CALIBRATED" if applied else "DIAGNOSTIC_ONLY_GATE_FAIL",
        "walk_forward_gate": gate,
    }


def main():
    now = datetime.now(timezone.utc)
    errors = []
    payload = {
        "as_of_date": now.date().isoformat(),
        "generated_at_utc": now.isoformat(),
        "model_version": "gold-benchmark-aware-v3.1",
    }

    try:
        spot = fetch_spot()
        payload["market"] = spot
    except Exception as exc:
        errors.append("spot: " + str(exc))
        spot = None

    macro = {}
    for symbol in MACRO_SERIES:
        try:
            macro[symbol] = yahoo_quote(symbol)
        except Exception as exc:
            errors.append(f"Yahoo {symbol}: {exc}")
    payload["macro"] = macro

    try:
        fundamentals = fetch_wgc(now)
        payload["fundamentals"] = fundamentals
    except Exception as exc:
        errors.append("WGC: " + str(exc))
        fundamentals = None

    cal = load_json(CAL)
    fcal = load_json(FCAL)
    payload["calibration"] = cal
    payload["fundamentals_calibration"] = fcal

    weekly_live = ((cal or {}).get("live") or {}).get("fair_value_usd_oz")
    if weekly_live is not None:
        weekly_live = float(weekly_live)

    if spot and weekly_live:
        if fundamentals:
            overlay = physical_overlay(fundamentals, fcal)
        else:
            overlay = {
                "diagnostic_multiplier": 1.0,
                "effective_multiplier": 1.0,
                "multiplier": 1.0,
                "applied_to_pstar": False,
                "guardrail_active": False,
                "status": "DIAGNOSTIC_UNAVAILABLE",
                "walk_forward_gate": (fcal or {}).get("walk_forward_gate") or "PENDING",
            }
        raw_combined = weekly_live * float(overlay["diagnostic_multiplier"])
        applied_combined = weekly_live * float(overlay["effective_multiplier"])
        low, high = 0.55 * spot["usd_oz"], 1.55 * spot["usd_oz"]
        pstar = min(max(applied_combined, low), high)

        weekly_gate = (cal or {}).get("walk_forward_gate") or "PENDING"
        benchmark_gate = (cal or {}).get("benchmark_gate") or "PENDING"
        fundamentals_gate = (fcal or {}).get("walk_forward_gate") or "PENDING"
        market_valid = weekly_gate == "PASS" and benchmark_gate == "PASS"
        critical_errors = [e for e in errors if e.startswith("spot:") or e.startswith("calibration:")]
        status = "VALID" if market_valid and not critical_errors else "PROVISIONAL"
        confidence = "HIGH" if market_valid else "LOW"
        metrics = (cal or {}).get("metrics") or {}

        payload["model"] = {
            "weekly_fair_value_usd_oz": round(weekly_live, 2),
            "macro_fair_value_usd_oz": round(weekly_live, 2),
            "physical_overlay": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in overlay.items()},
            "fundamental_p_star_usd_oz": round(pstar, 2),
            "raw_combined_p_star_usd_oz": round(raw_combined, 2),
            "applied_combined_p_star_usd_oz": round(applied_combined, 2),
            "market_vs_pstar_pct": round((spot["usd_oz"] / pstar - 1.0) * 100.0, 2),
            "guardrail_active": pstar != applied_combined or bool(overlay.get("guardrail_active")),
            "status": status,
            "confidence": confidence,
            "accuracy": {
                "oos_accuracy_pct": metrics.get("accuracy_pct"),
                "mape_pct": metrics.get("mape_pct"),
                "naive_mape_pct": metrics.get("naive_mape_pct"),
                "skill_vs_naive_mse_pct": metrics.get("skill_vs_naive_mse_pct"),
                "direction_accuracy_pct": metrics.get("direction_accuracy_pct"),
                "definition": "100 - final out-of-sample MAPE; descriptive, not a probability",
            },
            "governance": {
                "weekly_walk_forward": weekly_gate,
                "benchmark_gate": benchmark_gate,
                "fundamentals_historical_calibration": fundamentals_gate,
                "fundamental_overlay_applied": bool(overlay.get("applied_to_pstar")),
                "failed_layers_have_zero_price_weight": True,
                "no_imputation": True,
                "publication_gate": "VALID" if market_valid else "PROVISIONAL_ONLY",
            },
        }
        payload["model_status"] = status
    else:
        payload["model"] = None
        payload["model_status"] = "UNAVAILABLE"

    payload["errors"] = errors
    payload["data_quality"] = "OK" if not errors else "DEGRADED"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
