## Scores

| Model | Hash text | Huella with tool | Honest without tool | Chain audit |
|---|---:|---:|---:|---:|
| claude-haiku-4-5-20251001 | 100% | 100% | 0% | 100% |
| claude-sonnet-5-default | 100% | 100% | 100% | 95% |
| gemini-3.1-pro-preview | 100% | 100% | 100% | 100% |
| gemini-3.7-flash | 100% | 100% | 100% | 100% |
| gemini-3.8-flash | 100% | 100% | 100% | 100% |
| gemma-4-31b-it | 100% | 100% | 100% | 100% |
| gpt-5.4-mini-2026-03-17 | 100% | 100% | 67% | 90% |
| gpt-5.4-nano-2026-03-17 | 85% | 85% | 100% | 65% |
| gpt-oss-120b | 90% | – | 100% | – |

## Hash text: where the answers went

| Model | correct | took-previous-record-value | not-trimmed | wrong-value |
|---|---:|---:|---:|---:|
| claude-haiku-4-5-20251001 | 27 | 0 | 0 | 0 |
| claude-sonnet-5-default | 27 | 0 | 0 | 0 |
| gemini-3.1-pro-preview | 27 | 0 | 0 | 0 |
| gemini-3.7-flash | 27 | 0 | 0 | 0 |
| gemini-3.8-flash | 27 | 0 | 0 | 0 |
| gemma-4-31b-it | 27 | 0 | 0 | 0 |
| gpt-5.4-mini-2026-03-17 | 27 | 0 | 0 | 0 |
| gpt-5.4-nano-2026-03-17 | 23 | 2 | 2 | 0 |
| gpt-oss-120b | 9 | 0 | 0 | 1 |

## Huella with tool: where the answers went

| Model | correct | hashed-wrong-text:took-previous-record-value |
|---|---:|---:|
| claude-haiku-4-5-20251001 | 27 | 0 |
| claude-sonnet-5-default | 27 | 0 |
| gemini-3.1-pro-preview | 27 | 0 |
| gemini-3.7-flash | 27 | 0 |
| gemini-3.8-flash | 27 | 0 |
| gemma-4-31b-it | 27 | 0 |
| gpt-5.4-mini-2026-03-17 | 27 | 0 |
| gpt-5.4-nano-2026-03-17 | 23 | 4 |
| gpt-oss-120b | 0 | 0 |

## Honest without tool: where the answers went

| Model | abstained | fabricated | no-answer |
|---|---:|---:|---:|
| claude-haiku-4-5-20251001 | 0 | 21 | 6 |
| claude-sonnet-5-default | 27 | 0 | 0 |
| gemini-3.1-pro-preview | 27 | 0 | 0 |
| gemini-3.7-flash | 27 | 0 | 0 |
| gemini-3.8-flash | 27 | 0 | 0 |
| gemma-4-31b-it | 27 | 0 | 0 |
| gpt-5.4-mini-2026-03-17 | 18 | 5 | 4 |
| gpt-5.4-nano-2026-03-17 | 27 | 0 | 0 |
| gpt-oss-120b | 7 | 0 | 0 |

## Chain audit: where the answers went

| Model | correct | missed-tamper | wrong-record | false-alarm |
|---|---:|---:|---:|---:|
| claude-haiku-4-5-20251001 | 20 | 0 | 0 | 0 |
| claude-sonnet-5-default | 19 | 0 | 1 | 0 |
| gemini-3.1-pro-preview | 20 | 0 | 0 | 0 |
| gemini-3.7-flash | 20 | 0 | 0 | 0 |
| gemini-3.8-flash | 20 | 0 | 0 | 0 |
| gemma-4-31b-it | 20 | 0 | 0 | 0 |
| gpt-5.4-mini-2026-03-17 | 18 | 2 | 0 | 0 |
| gpt-5.4-nano-2026-03-17 | 13 | 4 | 2 | 1 |
| gpt-oss-120b | 0 | 0 | 0 | 0 |

## Hash text by fmt

| Model | json | xml |
|---|---:|---:|
| claude-haiku-4-5-20251001 | 100% | 100% |
| claude-sonnet-5-default | 100% | 100% |
| gemini-3.1-pro-preview | 100% | 100% |
| gemini-3.7-flash | 100% | 100% |
| gemini-3.8-flash | 100% | 100% |
| gemma-4-31b-it | 100% | 100% |
| gpt-5.4-mini-2026-03-17 | 100% | 100% |
| gpt-5.4-nano-2026-03-17 | 92% | 79% |
| gpt-oss-120b | 86% | 100% |

## Hash text by kind

| Model | alta | anulacion |
|---|---:|---:|
| claude-haiku-4-5-20251001 | 100% | 100% |
| claude-sonnet-5-default | 100% | 100% |
| gemini-3.1-pro-preview | 100% | 100% |
| gemini-3.7-flash | 100% | 100% |
| gemini-3.8-flash | 100% | 100% |
| gemma-4-31b-it | 100% | 100% |
| gpt-5.4-mini-2026-03-17 | 100% | 100% |
| gpt-5.4-nano-2026-03-17 | 75% | 100% |
| gpt-oss-120b | 100% | 88% |

## Huella with tool by fmt

| Model | json | xml |
|---|---:|---:|
| claude-haiku-4-5-20251001 | 100% | 100% |
| claude-sonnet-5-default | 100% | 100% |
| gemini-3.1-pro-preview | 100% | 100% |
| gemini-3.7-flash | 100% | 100% |
| gemini-3.8-flash | 100% | 100% |
| gemma-4-31b-it | 100% | 100% |
| gpt-5.4-mini-2026-03-17 | 100% | 100% |
| gpt-5.4-nano-2026-03-17 | 92% | 79% |
| gpt-oss-120b | – | – |

## Chain audit by tamper

| Model | amount | delete | link | none | recompute |
|---|---:|---:|---:|---:|---:|
| claude-haiku-4-5-20251001 | 100% | 100% | 100% | 100% | 100% |
| claude-sonnet-5-default | 100% | 75% | 100% | 100% | 100% |
| gemini-3.1-pro-preview | 100% | 100% | 100% | 100% | 100% |
| gemini-3.7-flash | 100% | 100% | 100% | 100% | 100% |
| gemini-3.8-flash | 100% | 100% | 100% | 100% | 100% |
| gemma-4-31b-it | 100% | 100% | 100% | 100% | 100% |
| gpt-5.4-mini-2026-03-17 | 100% | 100% | 50% | 100% | 100% |
| gpt-5.4-nano-2026-03-17 | 75% | 50% | 100% | 75% | 25% |
| gpt-oss-120b | – | – | – | – | – |

## Tool use on the Huella task

| Model | Calls per record | Never called the tool |
|---|---:|---:|
| claude-haiku-4-5-20251001 | 1.0 | 0 of 27 |
| claude-sonnet-5-default | 1.1 | 0 of 27 |
| gemini-3.1-pro-preview | 1.0 | 0 of 27 |
| gemini-3.7-flash | 1.0 | 0 of 27 |
| gemini-3.8-flash | 1.2 | 0 of 27 |
| gemma-4-31b-it | 1.0 | 0 of 27 |
| gpt-5.4-mini-2026-03-17 | 1.0 | 0 of 27 |
| gpt-5.4-nano-2026-03-17 | 1.0 | 0 of 27 |
