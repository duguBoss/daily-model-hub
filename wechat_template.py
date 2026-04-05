from __future__ import annotations

from html import escape


TOP_FOLLOW_GIF = "https://mmbiz.qpic.cn/mmbiz_gif/xm1dT1jCe8lIO3P2oFVtd1x040PKGCRPN033gUTrHQQz0Licdqug5X1QgUPQBRCicoTqdYMrpgk7etibXLkK9rwcg/0?wx_fmt=gif&from=appmsg"
FOOTER_GIF = "https://mmbiz.qpic.cn/mmbiz_gif/qHfXxy1pes1eXWicJWxHTLGxL323Gh029A2JkOLQP3EibEUYlkLeB2vgvuhnUoyqoPg1etjxySFodeOgR45dHqS2s2kZ8KyjA65MCPMPbBBGo/0?wx_fmt=gif"

FOLLOW_ALT = "\u5173\u6ce8\u63d0\u793a"
FOOTER_ALT = "\u5e95\u90e8\u5f15\u5bfc"
SOURCE_NOTE = "\u6570\u636e\u6765\u6e90\uff1aHugging Face Trending\u3002\u5185\u5bb9\u7531\u811a\u672c\u81ea\u52a8\u6574\u7406\uff0c\u5efa\u8bae\u70b9\u51fb\u5361\u7247\u94fe\u63a5\u67e5\u770b\u6a21\u578b\u539f\u9875\u548c\u6700\u65b0\u8be6\u60c5\u3002"
GENERATED_AT_LABEL = "\u751f\u6210\u65f6\u95f4\uff1a"
BUTTON_LABEL = "\u67e5\u770b\u6a21\u578b\u8be6\u60c5"


def _minify_html(html: str) -> str:
    lines = html.strip().split("\n")
    return "".join(line.strip() for line in lines if line.strip())


PAGE_TEMPLATE = _minify_html(
    """
<section data-side-margin="0" style="margin:0;padding:0;width:100%;box-sizing:border-box;background-color:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:15px;line-height:1.75;color:#1f2937;overflow:hidden;">
  <section style="margin:0;padding:0;width:100%;">
    <img src="{top_follow_gif}" alt="{follow_alt}" style="display:block;width:100%;height:auto;border:0;" />
  </section>
  <section style="margin:0;padding:24px 0 8px;background:linear-gradient(180deg,#fff8f1 0%,#ffffff 100%);">
    <section style="margin:0;padding:0 16px 20px;">
      <p style="margin:0 0 10px;font-size:12px;line-height:1.4;color:#f97316;letter-spacing:0.08em;font-weight:700;text-transform:uppercase;">Daily Model Hub</p>
      <h1 style="margin:0;font-size:22px;line-height:1.4;color:#111827;font-weight:800;">每日精选HuggingFace热门模型</h1>
      <p style="margin:12px 0 0;font-size:13px;line-height:1.6;color:#6b7280;">{subtitle}</p>
    </section>
    {cards}
  </section>
  <section style="margin:0;padding:8px 16px 24px;background-color:#ffffff;">
    <section style="margin:0;padding:16px;border:1px solid #fed7aa;background-color:#fff7ed;">
      <p style="margin:0;font-size:13px;line-height:1.7;color:#9a3412;">{source_note}</p>
      <p style="margin:10px 0 0;font-size:12px;line-height:1.6;color:#c2410c;">{generated_at_label}{generated_at}</p>
    </section>
  </section>
  <section style="margin:0;padding:0;width:100%;">
    <img src="{footer_gif}" alt="{footer_alt}" style="display:block;width:100%;height:auto;border:0;" />
  </section>
</section>
"""
)


CARD_TEMPLATE = _minify_html(
    """
<section style="margin:0 0 24px;padding:0;width:100%;background-color:#ffffff;border-top:1px solid #f3f4f6;border-bottom:1px solid #f3f4f6;">
  <section style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;background:linear-gradient(135deg,#ea580c 0%,#fb923c 100%);">
    <span style="font-size:14px;line-height:1.4;color:#ffffff;font-weight:700;">#{rank} Trending Model</span>
    <span style="font-size:12px;line-height:1.4;color:rgba(255,255,255,0.88);">Hugging Face</span>
  </section>
  <section style="margin:0;padding:0;width:100%;height:200px;overflow:hidden;line-height:0;">
    <img src="{image_url}" alt="{model_name}" style="display:block;width:100%;height:100%;object-fit:cover;object-position:center;border:0;margin:0;padding:0;" />
  </section>
  <section style="margin:0;padding:16px 16px 18px;background-color:#ffffff;">
    <h2 style="margin:0 0 10px;font-size:19px;line-height:1.45;color:#111827;font-weight:700;word-break:break-word;">{model_name}</h2>
    <p style="margin:0 0 14px;font-size:14px;line-height:1.85;color:#374151;text-align:left;word-break:break-word;">{model_desc}</p>
    <a href="{model_url}" style="display:block;width:100%;box-sizing:border-box;padding:11px 16px;background-color:#111827;color:#ffffff;font-size:14px;line-height:1.4;font-weight:600;text-align:center;text-decoration:none;">{button_label}</a>
  </section>
</section>
"""
)


def render_model_card(*, rank: int, model_name: str, model_desc: str, model_url: str, image_url: str) -> str:
    return CARD_TEMPLATE.format(
        rank=rank,
        model_name=escape(model_name),
        model_desc=escape(model_desc),
        model_url=escape(model_url, quote=True),
        image_url=escape(image_url, quote=True),
        button_label=escape(BUTTON_LABEL),
    )


def render_page(*, title: str, subtitle: str, cards_html: str, generated_at: str) -> str:
    return PAGE_TEMPLATE.format(
        top_follow_gif=escape(TOP_FOLLOW_GIF, quote=True),
        footer_gif=escape(FOOTER_GIF, quote=True),
        follow_alt=escape(FOLLOW_ALT),
        footer_alt=escape(FOOTER_ALT),
        title=escape(title),
        subtitle=escape(subtitle),
        cards=cards_html,
        source_note=escape(SOURCE_NOTE),
        generated_at_label=escape(GENERATED_AT_LABEL),
        generated_at=escape(generated_at),
    )
