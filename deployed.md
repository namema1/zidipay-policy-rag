# Deployed URL

The live deployed instance of the Zidipay Policy RAG will be available at:

> **TODO:** paste the public Hugging Face Space URL here after the first successful deploy.
>
> Expected form: `https://huggingface.co/spaces/<your-username>/zidipay-policy-rag`

## How to verify

Once you have the URL, the following should all succeed:

1. Open the URL in a browser. The chat UI should load. Ask: *"How many days of annual leave do I get?"* — expect a cited answer.
2. `curl https://<space-url>/health` should return JSON with `"status": "ok"` and a positive `index_chunks` count.
3. `curl -X POST https://<space-url>/chat -H "Content-Type: application/json" -d '{"question":"What is the per-head limit for a client dinner?"}'` should return JSON with an answer, citations, and a non-zero `latency_ms`.
4. Ask an out-of-corpus question (e.g. *"What is the share price?"*) — expect the refusal *"I can only answer questions about Zidipay's policies and procedures."*

## Notes

- HF Spaces free tier sleeps after ~30 minutes of inactivity. Open the URL once before recording the demo to warm it up.
- The first request after a cold start triggers index ingestion if the persist directory is empty; expect ~20–40 s on the first request only.
