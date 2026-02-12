from .utils import normalize_text


def rank_article(article: dict, people: list[dict], themes: list[str]) -> tuple[float, str, str | None, str | None]:
    text = normalize_text(f"{article.get('title', '')} {article.get('body', '')}")
    score = 0.0

    # Theme signals
    theme_hits = 0
    for th in themes:
        tokens = normalize_text(th).split()
        if any(t in text for t in tokens if t):
            theme_hits += 1
    score += theme_hits * 2.0

    # Practical signal
    for kw in ["導入", "運用", "成果", "効率", "revenue", "productivity", "enterprise", "workflow"]:
        if kw in text:
            score += 0.5

    person = None
    image_source = None
    for p in people:
        p_tokens = [normalize_text(p["name"])] + [normalize_text(k) for k in p.get("keywords", [])]
        if any(tok and tok in text for tok in p_tokens):
            score += 3.0
            person = p.get("name")
            image_source = p.get("image_source")
            break

    topic = "AI活用事例"
    if "medical" in text or "医療" in text:
        topic = "医療AI"
    elif "education" in text or "教育" in text:
        topic = "教育AI"
    elif "finance" in text or "金融" in text:
        topic = "金融AI"

    return score, topic, person, image_source
