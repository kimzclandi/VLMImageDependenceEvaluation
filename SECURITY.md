# Security and privacy

The default workflow generates original non-personal synthetic data and makes no external model calls. It does not execute model output as code. Streamlit binds to loopback by default, has telemetry disabled, and is intended for local demos, not an authenticated multi-user service.

Never commit secrets, provider raw responses containing sensitive data, browser sessions, personal photos or private/company datasets. `.env`, API cache, local reports and Streamlit secrets are ignored. `scripts/privacy_check.py` scans publishable text for common secret and personal-path patterns; it cannot guarantee that every possible secret is detected. Review the Git diff and images before publishing.

API mode sends only synthetic image/question and the prompt to the configured HTTPS provider. Credentials come from environment variables. Exceptions record bounded status labels rather than response bodies, request URLs or headers. Image paths must resolve inside the dataset root. Do not point the adapter at untrusted endpoints with a valuable credential.

For a suspected vulnerability, do not post credentials or exploit data in a public issue. If the published repository has private security reporting enabled, use its Security tab; otherwise open a minimal non-sensitive issue requesting a private reporting channel. No private reporting channel or hosting security has been configured in this local-only version. Rotate any exposed credentials immediately and review history before making the repository public.
