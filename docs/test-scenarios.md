# Conversation scenarios

These five scripted flows can be run from the local dashboard. They are test prompts, not audio recordings.

1. **Qualified investor:** “Yes, now is fine.” → “Investment.” → “Nandi Hills is fine.” → “₹1.5 crore is comfortable.” → “December 2029 works.” → “Yes, have an expert call me.” Expected: all four checkpoints recorded, follow-up requested.
2. **Weekend home, lower budget:** permission yes → self-use/weekend home → location works → “I can spend ₹75 lakh.” Expected: below-range budget captured; no pressure, expert follow-up offered only if appropriate.
3. **Budget fit, location mismatch:** permission yes → investment → “Devanahalli is too far.” → budget and timing answered. Expected: location concern acknowledged; premium pitch is brief and sensitive; no claim of qualification fit.
4. **Busy prospect:** “I’m busy, call later.” Expected: agent offers to let the prospect go, does not continue qualification.
5. **Irritated / opt-out:** “Stop calling me.” Expected: apology, opt-out confirmation, immediate end; do not pitch or request follow-up.

Hindi smoke path: “नमस्ते, हिंदी में बात करें” → self-use/investment → location → ₹92.4 lakh budget → December 2029 → follow-up. The UI can also launch any scenario as a guided demo.
