# Optional pixels-only model adapter

Default execution is fully offline. This adapter is an opt-in example for a provider supporting vision inputs and the Chat Completions JSON-mode contract. It has only been exercised using `httpx.MockTransport`, **not a real paid provider**.

The request contains a system instruction, user question and base64 PNG in `image_url`. It requests `response_format={"type":"json_object"}` and `max_tokens=100`. Providers/models may differ in support; errors remain visible rather than silently switching parameters. Use a compatible vision model and pin a snapshot where available. The payload follows the [official OpenAI Chat Completions reference](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create); compatibility with third-party servers is not guaranteed.

```bash
# In your shell, set VLM_API_KEY securely; never paste it into a tracked file.
export VLM_MODEL='your-compatible-vision-model'
export VLM_BASE_URL='https://api.openai.com/v1'
flywheel infer --adapter api --outputs reports/local/api_outputs.jsonl
flywheel evaluate --outputs reports/local/api_outputs.jsonl --report-dir reports/local/api
```

`VLM_API_KEY` is required only for the explicit API command. `.env.example` documents variables; the program does not auto-load `.env`. Use a secret manager or environment variables. Never commit keys or cached provider responses. The command sends the synthetic image/question collection to your configured provider and can incur usage charges; no external call was made during this project's offline demo.

To estimate cost, append `--input-price` and `--output-price` in USD per million tokens, according to your provider's current pricing. Missing usage/prices produce null. There is no hard spending cap; retry timeouts may have incurred unreported server-side costs. Default is serial inference, 30-second per-attempt timeout and at most two retries for 429, 5xx and network failures. HTTP 4xx errors other than 429 do not retry. Redirects are disabled; URLs with inline credentials/query/fragment are rejected.

Cache directory defaults to ignored `.cache-api`. Cache key hashes endpoint, model, prompt content/version, image, question, inference settings and price settings. Only successful envelopes are cached; a successful envelope containing an invalid answer remains raw evidence and is caught by the parser. A cache hit records attempts=0 and zero incremental estimated cost, but keeps original usage fields. Use a fresh cache directory for a fresh provider run. Provider aliases can change behind identical names; the caller must manage this.

The reference interface carries scene/query for offline pipeline controls. **The API adapter must never serialize them.** Payload-leakage tests assert this boundary. `provider_model` preserves the model name returned by the endpoint; model_version records the requested identifier. Outputs also preserve actual timestamps, latency, parameters, dataset version and sample content hash.

A Hugging Face local adapter and LLM Judge are intentionally not dependencies or claimed capabilities. Add a local adapter behind the same protocol only when a suitable model/runtime can actually be tested.
