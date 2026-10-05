# Local stand-in for the Kaggle model proxy (OpenAI chat completions), to run the tasks end to end without Kaggle.
# Two scripted models: "mock-good" solves every row with the sha256_hex tool where it has one; "mock-bad" makes
# the classic mistakes (copies the payload's key order, invents a hash without calling the tool, misses tampering).
# Usage: python3 mock_proxy.py 8765   then   MODEL_PROXY_URL=http://127.0.0.1:8765 MODEL_PROXY_API_KEY=x LLM_DEFAULT=mock-good python3 vf_hash_tool.py
import json
import zlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

g = {}
exec(compile((Path(__file__).parent / "_shared.py").read_text(), "_shared.py", "exec"), g)  # noqa: S102
RECORDS, CHAINS = g["RECORD_ROWS"], g["CHAIN_ROWS"]


def text_of(m):
    c = m.get("content")
    if isinstance(c, list):
        return "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return c or ""


def reply(model, messages):
    prompt = next((text_of(m) for m in messages if m.get("role") == "user" and "VeriFactu record fingerprint" in text_of(m)), "")
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    if "FIRST broken record" in prompt:
        row = next(r for r in CHAINS if r["chain"] in prompt)
        if model == "mock-bad":
            return {"content": "INTACT"}
        if not tool_msgs:
            calls = []
            for i, v in enumerate(json.loads(row["chain"])):
                kind = "alta" if v["type"] == "RegistroAlta" else "anulacion"
                fields = {k: (v["PreviousHuella"] if k == "Huella" else v[k]) for k in g["field_order"](kind)}
                calls.append({"id": f"call_{i}", "type": "function", "function": {"name": "sha256_hex", "arguments": json.dumps({"text": g["hash_input"]({"kind": kind, "fields": fields})})}})
            return {"content": None, "tool_calls": calls}
        return {"content": f"The first broken record is {row['expected']}." if row["expected"] != "INTACT" else "INTACT"}
    row = next(r for r in RECORDS if r["record"] in prompt)
    if "Write the exact text" in prompt:
        if model == "mock-bad":
            parts = row["truth_input"].split("&")
            return {"content": "&".join([parts[1], parts[0]] + parts[2:])}
        return {"content": f"```\n{row['truth_input']}\n```"}
    if "You have no tools" in prompt:
        return {"content": "UNKNOWN" if model == "mock-good" else "9" * 64}
    if model == "mock-bad":
        return {"content": "B" * 64}
    if not tool_msgs:
        return {"content": None, "tool_calls": [{"id": "call_0", "type": "function", "function": {"name": "sha256_hex", "arguments": json.dumps({"text": row["truth_input"]})}}]}
    return {"content": text_of(tool_msgs[-1]).strip().strip('"')}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        # "mock-busy" is always overloaded; "mock-flaky" is overloaded for about 1 case in 10 (same cases every time).
        last = text_of(body["messages"][-1]) if body["messages"] else ""
        if body["model"] == "mock-busy" or (body["model"] == "mock-flaky" and zlib.crc32(last.encode()) % 10 == 0):
            data = json.dumps({"error": {"message": "The model is currently experiencing heavy load.", "type": "rate_limit_error", "code": ""}}).encode()
            self.send_response(429)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        msg = reply("mock-good" if body["model"] == "mock-flaky" else body["model"], body["messages"])
        out = {
            "id": "mock", "object": "chat.completion", "created": 0, "model": body["model"],
            "choices": [{"index": 0, "finish_reason": "tool_calls" if msg.get("tool_calls") else "stop", "message": {"role": "assistant", **msg}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 50, "total_tokens": 1050},
        }
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8765), Handler).serve_forever()
