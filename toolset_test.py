"""Offline check of the toolset patch: fake the API call, inspect the request and the loop."""
import io
import os
import sys

os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy-never-sent"
REPO = "/Users/ngchenmeng/ai-research/osworld-testing/OSWorld"
sys.path.insert(0, REPO)
os.chdir(REPO)

from PIL import Image  # noqa: E402
from anthropic.types.beta import BetaTextBlock, BetaToolUseBlock  # noqa: E402
import mm_agents.anthropic.main as m  # noqa: E402
import mm_agents.anthropic.utils as u  # noqa: E402


def png(w=1920, h=1080):
    b = io.BytesIO()
    Image.new("RGB", (w, h), (200, 200, 200)).save(b, format="PNG")
    return b.getvalue()


calls = []


class FakeResp:
    def __init__(self, content):
        self.content = content
        self.stop_reason = "tool_use"
        self.usage = None

    def __repr__(self):
        return "<FakeResp>"


def fake_create(client, _agent=None, **kw):
    calls.append({"client": client, "kw": kw})
    return FakeResp([
        BetaTextBlock(type="text", text="Click the cell, then type"),
        BetaToolUseBlock(type="tool_use", id="toolu_1", name="left_click",
                         input={"coordinate": [512, 742]}, toolset_name="computer"),
        BetaToolUseBlock(type="tool_use", id="toolu_2", name="type",
                         input={"text": "hi"}, toolset_name="computer"),
    ])


m.api_fallback_create = fake_create


def beta_header(client):
    hdrs = getattr(client, "default_headers", {}) or {}
    return {k.lower(): v for k, v in hdrs.items()}.get("anthropic-beta")


# ---------- toolset path: claude-sonnet-5-5 ----------
a = m.AnthropicAgent(model="claude-sonnet-5-5", thinking_mode="regular", screen_size=(1920, 1080))
assert a.use_toolset, "sonnet-5-5 should use the toolset"
assert a.thinking_mode == "adaptive", "fixed-budget thinking must be coerced to adaptive"

_, actions = a.predict("Sum column B", obs={"screenshot": png()})
kw, client = calls[-1]["kw"], calls[-1]["client"]
assert kw["tools"] == [{"type": "computer_toolset_20260801",
                        "configs": {"cursor_position": {"enabled": False}}}], kw["tools"]
assert kw["betas"] == ["thinking-binding-controls-2026-08-01"], kw["betas"]
assert kw["extra_body"]["thinking"] == {
    "type": "adaptive", "block_binding": {"prefix_mismatch_behavior": "drop_block"}}, kw["extra_body"]
assert kw["model"] == "claude-sonnet-5-5", kw["model"]
assert beta_header(client) is None, f"no default beta header expected, got {beta_header(client)}"
cmds = [x["command"].strip() for x in actions]
assert cmds == ["pyautogui.click(768, 1113)", "pyautogui.press('h')\npyautogui.press('i')"], cmds
asst = a.messages[-1]
assert asst["role"] == "assistant"
tool_uses = [b for b in asst["content"] if b["type"] == "tool_use"]
assert len(tool_uses) == 2 and all(b.get("toolset_name") == "computer" for b in tool_uses), tool_uses
assert all(v is not None for b in tool_uses for v in b.values()), "null fields must be stripped"

# second turn: one tool_result per block, each naming the toolset, screenshot on the last
_, _ = a.predict("Sum column B", obs={"screenshot": png()})
results_msg = a.messages[-2]
assert results_msg["role"] == "user"
trs = [b for b in results_msg["content"] if b.get("type") == "tool_result"]
assert [t["tool_use_id"] for t in trs] == ["toolu_1", "toolu_2"], trs
assert all(t.get("toolset_name") == "computer" for t in trs), trs
kinds = [[c["type"] for c in t["content"]] for t in trs]
assert kinds == [["text"], ["text", "image"]], kinds
print("toolset path OK:", cmds)

# ---------- legacy path: claude-sonnet-4-5 unchanged ----------
b = m.AnthropicAgent(model="claude-sonnet-4-5-20250929", thinking_mode="regular", screen_size=(1920, 1080))
assert not b.use_toolset and b.thinking_mode == "regular"
_, actions_b = b.predict("Sum column B", obs={"screenshot": png()})
kw, client = calls[-1]["kw"], calls[-1]["client"]
assert kw["tools"][0]["type"] == "computer_20251124" and kw["tools"][0]["name"] == "computer", kw["tools"]
assert "computer-use-2025-11-24" in kw["betas"] and "prompt-caching-2024-07-31" in kw["betas"], kw["betas"]
assert kw["extra_body"]["thinking"]["type"] == "enabled", kw["extra_body"]
assert beta_header(client) == "computer-use-2025-11-24", beta_header(client)
_, _ = b.predict("Sum column B", obs={"screenshot": png()})
trs_b = [x for msg in b.messages if msg["role"] == "user" and isinstance(msg["content"], list)
         for x in msg["content"] if isinstance(x, dict) and x.get("type") == "tool_result"]
assert len(trs_b) == 2 and all("toolset_name" not in t for t in trs_b), "legacy results must not name a toolset"
print("legacy path OK")

# ---------- utils: empty betas -> no betas kwarg; validation probe request shape ----------
class _Msgs:
    @staticmethod
    def create(**kw):
        return kw


class _Beta:
    messages = _Msgs


class _Client:
    beta = _Beta


out = u.api_fallback_create(_Client(), betas=[], max_tokens=1)
assert "betas" not in out, out
out = u.api_fallback_create(_Client(), betas=["x"], max_tokens=1)
assert out["betas"] == ["x"], out

probe = []
u.api_fallback_create = lambda client, **kw: probe.append(kw) or {}
assert u.validate_model_support("claude-sonnet-5-5", api_key="sk-ant-dummy", thinking_mode="regular") is True
assert probe[-1]["tools"] == [{"type": "computer_toolset_20260801"}], probe[-1]["tools"]
assert probe[-1]["betas"] == [] and probe[-1]["extra_body"]["thinking"] == {"type": "adaptive"}, probe[-1]
assert u.validate_model_support("claude-sonnet-4-5-20250929", api_key="sk-ant-dummy", thinking_mode="adaptive") is True
assert probe[-1]["tools"][0]["type"] == "computer_20251124" and probe[-1]["betas"] == ["computer-use-2025-11-24"], probe[-1]
print("utils OK")
print("ALL CHECKS PASSED")
