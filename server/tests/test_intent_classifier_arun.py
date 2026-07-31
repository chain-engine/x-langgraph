# -*- coding: utf-8 -*-
"""Verify chat-service intent_classifier call path."""
import asyncio
from unittest.mock import patch

from services.chat_service import ChatService


def test_intent_classifier_uses_supported_async_api():
    captured = {}

    async def fake_ainvoke(self, inputs, config=None):
        captured["inputs"] = inputs
        captured["config"] = config
        return {"intent": "product_inquiry", "output": "ok"}

    target = __import__(
        "workflows.intent_classifier.workflow",
        fromlist=["IntentClassifierWorkflow"],
    ).IntentClassifierWorkflow

    with patch.object(target, "ainvoke", new=fake_ainvoke):
        result = asyncio.run(
            ChatService().create({
                "message": "product price?",
                "workflow": "intent_classifier",
            })
        )

    assert captured["inputs"]["messages"][0]["content"] == "product price?"
    assert captured["inputs"]["messages"][0]["role"] == "user"
    assert captured["config"]["configurable"]["thread_id"] == "default"
    assert result["response"] == "ok"
    assert result["session_id"] == "default"
