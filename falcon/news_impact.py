from __future__ import annotations

import re
from collections.abc import Mapping

# Conservative topic cues, not a language model and not a market forecast.
_CUES: dict[str, tuple[str, ...]] = {
    "potentially_supportive": (
        "rate cut", "interest rate cut", "lower rates", "easing", "rate reduction",
        "disinflation", "inflation cooled", "inflation eased", "soft landing",
        "liquidity support", "economic growth", "employment increased",
        "خفض الفائدة", "تخفيض الفائدة", "تيسير", "تباطؤ التضخم", "انحسار التضخم",
        "نمو اقتصادي", "تحسن التوظيف",
    ),
    "potentially_adverse": (
        "rate hike", "interest rate increase", "higher for longer", "tightening",
        "quantitative tightening", "inflation accelerated", "inflation remains elevated",
        "recession", "economic contraction", "unemployment increased",
        "رفع الفائدة", "زيادة الفائدة", "تشديد نقدي", "تسارع التضخم",
        "ارتفاع التضخم", "ركود", "انكماش اقتصادي", "ارتفاع البطالة",
    ),
    "mixed_or_unclear": (
        "uncertainty", "uncertain", "mixed", "data dependent", "risks remain",
        "financial stability", "monitoring developments", "outlook",
        "عدم اليقين", "متباين", "يعتمد على البيانات", "مخاطر", "استقرار مالي",
    ),
}

_LABELS = {
    "potentially_supportive": "إيجابي محتمل للأسواق",
    "potentially_adverse": "سلبي محتمل للأسواق",
    "neutral": "محايد / لا توجد إشارة واضحة",
    "mixed_or_unclear": "مختلط / غير واضح",
}


def classify_news_impact(item: Mapping[str, object]) -> dict[str, str | int]:
    """Attach a cautious, explainable macro-impact label to a news item.

    This keyword baseline is intentionally not a prediction. It avoids assigning
    a directional label when evidence is weak or contradictory.
    """
    title = str(item.get("title") or "")
    description = str(item.get("description") or "")
    text = re.sub(r"\s+", " ", f"{title}. {description}").casefold()

    hits = {
        category: [cue for cue in cues if cue.casefold() in text]
        for category, cues in _CUES.items()
    }
    supportive = hits["potentially_supportive"]
    adverse = hits["potentially_adverse"]
    mixed = hits["mixed_or_unclear"]

    if (supportive and adverse) or mixed:
        category = "mixed_or_unclear"
        confidence = "منخفضة"
        reasons = mixed + supportive + adverse
    elif supportive:
        category = "potentially_supportive"
        confidence = "منخفضة" if len(supportive) == 1 else "متوسطة"
        reasons = supportive
    elif adverse:
        category = "potentially_adverse"
        confidence = "منخفضة" if len(adverse) == 1 else "متوسطة"
        reasons = adverse
    else:
        category = "neutral"
        confidence = "منخفضة"
        reasons = []

    reason = "؛ ".join(reasons[:3]) if reasons else "لم تُرصد كلمات دلالية كافية لتحديد أثر محتمل"
    return {
        "impact": category,
        "label": _LABELS[category],
        "confidence": confidence,
        "reason": reason,
        "method": "قواعد كلمات مفتاحية قابلة للتفسير؛ ليست نموذجاً مدرباً ولا توقعاً للسوق",
    }
