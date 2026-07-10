# Deployed URL

The live deployed instance of the Zidipay Policy RAG will be available at: `https://asena-victor-zidipay-policy-rag.hf.space`.

## How to verify

Once you have the URL, the following should all succeed:

1. Open the URL in a browser. The chat UI should load. Ask: *"How many days of annual leave do I get?"* — expect a cited answer.
2. `curl https://asena-victor-zidipay-policy-rag.hf.space/health` should return JSON with `"status": "ok"` and a positive `index_chunks` count. Alternatively, you don't have to curl this at all — the chat UI has a `/health` link in the footer; clicking it opens the same JSON response in a new tab.
3. `curl -X POST https://asena-victor-zidipay-policy-rag.hf.space/chat -H "Content-Type: application/json" -d '{"question":"What is the per-head limit for a client dinner?"}'` should return JSON with an answer, citations, and a non-zero `latency_ms`.
4. Ask an out-of-corpus question (e.g. *"What is the share price?"*) — expect the refusal *"I can only answer questions about Zidipay's policies and procedures."*
