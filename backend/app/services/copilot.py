from __future__ import annotations
import json
import httpx
from ..config import OLLAMA_URL, OLLAMA_MODEL


def deterministic_answer(result: dict, question: str) -> str:
    q = question.lower()
    p = result["primary"]
    lift = p.get("relative_lift_pct")
    lift_text = "not defined" if lift is None else f"{lift:+.2f}%"
    segments = result.get("segments", [])
    harmful = [s for s in segments if s.get("significant") and s.get("effect", 0) < 0]
    strongest = max(segments, key=lambda s: abs(s.get("effect", 0)), default=None)
    srm = result["sample_ratio_mismatch"]

    if any(word in q for word in ("segment", "cohort", "mobile", "desktop", "country", "who benefited", "who was harmed")):
        if harmful:
            details = "; ".join(
                f"{s['feature']}={s['segment']} effect {s['effect']:+.4f} (adjusted p={s.get('adjusted_p_value', s['p_value']):.4f})"
                for s in harmful[:3]
            )
            return f"The main segment risk is negative treatment response in: {details}. Segment significance uses Benjamini-Hochberg correction. Treat these as exploratory findings and validate them with follow-up experiments."
        if strongest:
            return f"No negative segment survives the multiple-testing correction. The strongest observed slice is {strongest['feature']}={strongest['segment']} with effect {strongest['effect']:+.4f} and adjusted p={strongest.get('adjusted_p_value', strongest['p_value']):.4f}."
        return "No segment met the minimum sample threshold for reliable subgroup analysis."

    if any(word in q for word in ("random", "srm", "assignment", "ratio")):
        status = "detected" if srm["detected"] else "not detected"
        return f"Sample-ratio mismatch was {status}. Control has {srm['control_n']} users and treatment has {srm['treatment_n']} users against an expected 50/50 split (p={srm['p_value']:.4f})."

    if any(word in q for word in ("sample", "power", "more data", "size")):
        n = result.get("recommended_sample_size_per_variant")
        if n:
            return f"For the binary primary metric, the rough 80%-power planning estimate for a 5% relative minimum detectable effect is about {n:,} users per variant. This is a planning approximation, not a post-hoc guarantee."
        return "This release only provides the quick sample-size planning estimate for binary metrics. Use a dedicated power analysis for continuous metrics."

    if any(word in q for word in ("ship", "launch", "decision", "recommend")):
        reasons = [f"the primary effect is {lift_text} relative to control with p={p['p_value']:.4f}"]
        if srm["detected"]:
            reasons.append("a sample-ratio mismatch makes the assignment pipeline suspect")
        if harmful:
            reasons.append(f"{len(harmful)} negative segment(s) remain significant after multiple-testing correction")
        if not p["significant"]:
            reasons.append("the primary result is not significant at the 5% level")
        return f"Recommendation: {result['decision']}. The decision is based on " + ", and ".join(reasons) + ". The statistical engine, not the language model, sets this launch status."

    pieces = [
        f"Decision: {result['decision']}.",
        f"Treatment changed the primary metric by {lift_text} relative to control (p={p['p_value']:.4f}).",
    ]
    if srm["detected"]:
        pieces.append("A sample-ratio mismatch was detected, so randomization or assignment logging should be investigated before launch.")
    if harmful:
        pieces.append(f"There are {len(harmful)} negative segment(s) that remain significant after multiple-testing correction.")
    elif strongest:
        pieces.append(f"The strongest exploratory segment is {strongest['feature']}={strongest['segment']} with effect {strongest['effect']:+.4f}.")
    if not p["significant"]:
        pieces.append("The primary result is not statistically significant at the 5% level, so more data or a larger effect is needed before a confident decision.")
    pieces.append("The statistical engine, not the language model, determines significance and launch status.")
    return " ".join(pieces)


async def answer_question(result: dict, question: str) -> tuple[str, str]:
    base = deterministic_answer(result, question)
    prompt = {
        "role": "You are an experimentation analyst. Never change computed statistics. Explain only the supplied JSON results. Be concise, mention uncertainty, and treat subgroup/ML findings as exploratory.",
        "question": question,
        "results": result,
        "fallback_summary": base,
    }
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.post(
                f"{OLLAMA_URL.rstrip('/')}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": prompt["role"]},
                        {"role": "user", "content": json.dumps(prompt, default=str)},
                    ],
                },
            )
            response.raise_for_status()
            text = response.json().get("message", {}).get("content", "").strip()
            if text:
                return "ollama", text
    except Exception:
        pass
    return "deterministic", base
