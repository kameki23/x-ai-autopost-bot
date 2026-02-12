from textwrap import shorten


def build_style_prompt(constraints: list[str]) -> str:
    return (
        "以下の制約で日本語投稿を作成: "
        + " / ".join(constraints)
        + "。文体は解説者として客観・知的・非扇情。"
    )


def write_three_posts(article: dict, rules: dict) -> dict[int, str]:
    title = article.get("title", "無題")
    body = article.get("body", "")
    source_url = article.get("url", "")
    image_source = article.get("image_source") or article.get("image_url") or "画像なし"

    key = shorten(body.replace("\n", " "), width=140, placeholder="…")
    style_note = build_style_prompt(rules.get("writer_constraints", []))

    p1 = (
        f"【導入】{title}\n"
        f"{key}\n"
        "まず事実関係を整理。何が成果に直結したかを次の投稿で分解します。\n"
        f"（執筆方針: {style_note}）"
    )

    p2 = (
        "【戦略】成功要因は“技術”単体でなく、\n"
        "1) 現場課題の定義\n2) ワークフロー組込み\n3) 計測と改善\n"
        "の反復です。AIツールは、既存業務の意思決定速度をどう上げたかで評価すると再現性が高い。"
    )

    p3 = (
        "【現代接続】いま実務で試すなら、小さな業務単位でKPIを先に置き、"
        "人のレビュー工程を残したまま導入するのが安全です。\n"
        f"出典(記事): {source_url}\n"
        f"出典(画像): {image_source}"
    )

    return {1: p1[:270], 2: p2[:270], 3: p3[:270]}
