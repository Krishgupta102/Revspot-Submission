# Divyasree - Whispers of the Wind Voice Agent

A local-first lead qualification demo for the WOW premium villa plots project. The app uses Python's standard library and SQLite; it runs without paid API credentials. The dashboard includes an interactive simulated voice conversation (typed input, optional browser speech recognition, and speech synthesis), lead management, call history and five demo scenarios.

## Start locally

```bash
python3 backend/server.py
```

Open http://localhost:8000. SQLite data is stored in `data/voice_agent.db`.

## Deploy a shareable demo on Render

The repository includes `render.yaml` for a free Render web service. After committing and pushing the project to GitHub:

1. Sign in to Render and connect the GitHub account that contains this repository.
2. Choose **New → Blueprint** and select the project repository.
3. Review the service named `divyasree-wow-voice-agent` and deploy it. Render reads the build command, start command, health check and safe `CALL_MODE=demo` setting from `render.yaml`.
4. When the deploy succeeds, open the `onrender.com` URL shown on the service page and test the dashboard.

The free service can sleep when idle, so its first request after a quiet period may take about a minute. Its filesystem is temporary; demo leads and calls stored in SQLite can be lost after a restart or spin-down. Use an external database or a paid persistent disk if you need records to survive. This demo deployment does not place real calls.

## Real outbound calling

The Twilio adapter is opt-in. Copy `.env.example` to `.env`, set `CALL_MODE=twilio`, and configure Twilio credentials, a verified caller ID/number and a public HTTPS `BASE_URL` that can receive Twilio webhooks. Do not put real prospects into the demo without appropriate consent and calling permissions. The local demo never places a real call by default. Start a call from a lead row after configuration. Twilio voice webhooks use the same conversational state machine and gather speech via `<Gather>`.

The LLM adapter is optional; configure `OPENAI_API_KEY` and `OPENAI_MODEL` to generate natural responses. Qualification facts and required checkpoints remain controlled by the application. Without credentials, responses are generated locally.

## Assessment coverage

The flow seeks permission first, captures self-use/investment intent, Nandi Hills/Devanahalli corridor fit, budget versus ₹92.4 lakh, possession timing (December 2029), delivers the Private Valley pitch and asks permission for a property expert follow-up. It avoids repeating already answered checkpoints, supports English/Hindi prompts, handles refusal/irritation and logs each turn. See `docs/test-scenarios.md` and `docs/system-prompt.md`.

## Test

```bash
python3 -m unittest discover -s tests -v
```

## Configuration

See `.env.example`. This implementation deliberately uses SQLite for a zero-setup local demo; the schema is portable to PostgreSQL if required for deployment. Live voice calls require valid provider credentials and a public webhook URL; actual calls were not initiated during development.
