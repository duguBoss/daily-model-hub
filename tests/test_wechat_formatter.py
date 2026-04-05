from __future__ import annotations

import unittest

from wechat_formatter import generate_wechat_payload
from wechat_template import FOOTER_GIF, TOP_FOLLOW_GIF


SAMPLE_MODELS = [
    {
        "rank": 1,
        "modelName": "org/model-a",
        "modelDescription": "A full width test card for WeChat articles.",
        "modelUrl": "https://huggingface.co/org/model-a",
        "modelCard": "assets/huggingface_model_cards/2026-04-05/01-model-a.png",
        "sourceDescription": "",
        "cardSummary": "",
    },
    {
        "rank": 2,
        "modelName": "org/model-b",
        "modelDescription": "Another card to verify multiple sections render correctly.",
        "modelUrl": "https://huggingface.co/org/model-b",
        "modelCard": "assets/huggingface_model_cards/2026-04-05/02-model-b.png",
        "sourceDescription": "",
        "cardSummary": "",
    },
]


class WechatFormatterTest(unittest.TestCase):
    def test_payload_uses_full_width_wechat_template(self) -> None:
        payload = generate_wechat_payload(SAMPLE_MODELS, "2026-04-05")
        html = payload["weixin_html"]

        self.assertIn(TOP_FOLLOW_GIF.replace("&", "&amp;"), html)
        self.assertIn(FOOTER_GIF, html)
        self.assertIn("display:block;width:100%;box-sizing:border-box", html)
        self.assertIn("查看模型详情", html)
        self.assertNotIn("box-shadow: 0 2px 8px rgba(0,0,0,0.08)", html)
        self.assertNotIn("padding: 16px; font-family: system-ui", html)


if __name__ == "__main__":
    unittest.main()
