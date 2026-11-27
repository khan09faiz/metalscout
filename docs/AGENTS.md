# Agents: the crew behind each lead

Inspired by [OpenMausBot](https://github.com/milind-soni/OpenMausBot)'s roster of bots, where each has its own model, memory and tools. In MetalScout the "bots" are specialists in one pipeline, and a rules-based orchestrator decides who works on what. The agents are **optional**: with no model configured, the stage is skipped and the deterministic engine works exactly as before.

```
crawl ─► profile (regex, free) ─► Orchestrator (rules, no model)
                                     ├─ Sorter    small model   only if the regex classifier is unsure or sees both maker and trader words
                                     ├─ Analyst   large model   manufacturers/unclear: raw materials, forms, volume, people, buying signals
                                     ├─ Writer    large model   only Tier A/B after analysis: first-email draft (never sent)
                                     └─ Scout     small model   tender / buy-lead pages: buyer, items, quantity, deadline
                                                    │
                                     Grounding gate: every fact must quote the crawled page text, or it's rejected
                                                    │
                                     observations (AGENT_*) ─► fit score ─► dashboard / Excel
```

## Why this design
- **Cheapest model that can do the job.** Classification needs a small fast model; extraction and writing get the strongest free model. The orchestrator is plain code, because deciding *who runs* doesn't need a model.
- **Agents never invent contacts.** Emails and phones still come only from the regex extractors. Agents add judgement and structure: what they make, which metal and grade, how much, who's in charge.
- **The grounding gate makes hallucination visible.** Each fact carries a `quote`. `agents/ground.py` normalises case and whitespace and checks that the quote occurs in the crawled text. The page it was found on becomes the fact's `source_url`. Anything else is counted as *rejected* on the Agents tab and never stored.
- **Idempotent.** A company goes through the crew once per profile run (`companies.agents_run`). Re-running costs no model calls until the site is re-crawled, by default every 30 days.

## Free model providers
The router (`agents/llm.py`) speaks the OpenAI-compatible chat API that all of these offer. It lists each provider's current models at run time and picks one by pattern, because free-tier model names change often. On a 429, quota error or bad JSON it falls through to the next provider.

| Provider | Key | Free tier (check their pages; limits change) | Default small / large pattern |
|---|---|---|---|
| Groq | `GROQ_API_KEY` | Free tier, no card; per-model RPM/RPD limits shown in the console | llama-3.1-8b / llama-3.3-70b, gpt-oss-120b |
| Cerebras | `CEREBRAS_API_KEY` | Free tier with daily token caps | llama3.1-8b / llama-3.3-70b |
| Google Gemini | `GEMINI_API_KEY` | Free tier in AI Studio; per-project RPM/RPD | *flash-lite* / *flash* |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/free` router: about 20 req/min, 50 req/day (1,000/day after a $10 credit purchase) | openrouter/free |
| Ollama (local) | `OLLAMA_BASE_URL` (default `http://localhost:11434/v1`) | Unlimited, runs on your PC; slow on CPU | qwen2.5 / llama3 / mistral |

Order, limits and patterns are in `metalscout.yaml` under `agents:`:
```yaml
agents:
  enabled: true
  order: [groq, cerebras, gemini, openrouter, ollama]
  companies_per_run: 40      # leads analysed per run
  signals_per_run: 30        # buyer-signal pages read by the Scout
  max_calls_per_run: 150     # hard budget across all agents
  min_confidence: 0.7        # Sorter verdict needed to override the regex classifier
  write_for_tiers: [A, B]
  analyst_max_chars: 12000   # page text the Analyst reads; use ~4000 for CPU-only Ollama
  providers:                 # optional overrides
    groq: {rpm: 20, large: ["gpt-oss-120b", "llama-3.3-70b"]}
```

## Measured on real sites (local test, Nov 2026)
- `llama3.2:1b` (Ollama, CPU) as Analyst: 24 of 25 facts **rejected**, because it paraphrases instead of quoting. That's why models of 3B or smaller are never used for the large tier.
- `mistral:7b` (Ollama, CPU) as Writer: about 1 min, a good grounded email ("Matching Metals for Your 9000 MT/Year Production"). As Analyst on a 12k-character digest it timed out after 10 min on CPU; set `analyst_max_chars: 4000` or use a cloud free tier.
- Cloud free tiers (Groq, Cerebras) answer in seconds, so use them for scheduled runs.

## Editing agents
Prompts are Markdown in [`metalscout/prompts/agents/`](../metalscout/prompts/agents/) (`sorter.md`, `analyst.md`, `writer.md`, `scout.md`). Change wording, add fields or tighten rules there. To add an agent, write a prompt and add one branch in `agents/crew.py: Crew.run_company`.

## What you see
- **Agents tab:** roster cards (calls, ok, rejected, models used), provider switches, and a per-model table with latency.
- **Lead drawer:** "AI analysis" box. Every item shows its quote and a link to the page, and a "Copy email" button for the draft.
- **Buyer signals:** the Scout's reading (buyer, items, quantity, deadline) next to each tender or buy lead.
- **Excel:** agent facts are part of the observations and feed the score and reasons (prefixed `AI:`).
