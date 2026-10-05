---
title: "Spec, Hash or Guess: Can LLMs Keep Spain's Tamper-Proof Invoice Ledger?"
published: false
description: "A Kaggle benchmark on VeriFactu, the hash chain every Spanish invoice must carry from 2027: build the exact hash text, compute the fingerprint with a tool, admit when you can't, and find the forged record in a chain. Graded by code against the tax agency's official test vectors."
tags: devchallenge, kagglechallenge, ai, machinelearning
---

*This is a submission for the [Kaggle Benchmarking Challenge](https://dev.to/challenges/kaggle-2026-09-23)*

From 2027, every invoice issued in Spain has to come from software that writes **VeriFactu** records. Each record carries a SHA-256 fingerprint, the *Huella*, of a short text built from eight fields in an exact order. The text includes the previous record's fingerprint, so the records form a chain the tax agency can verify. Get one character wrong and the agency rejects the record; edit an old invoice and the chain breaks.

Thousands of developers are writing that code right now, many of them with an AI assistant. So I measured what happens when you hand a model the specification and a record.

<!-- FILL: two or three sentences with the headline result, e.g. "The best model built the exact text for X of 27 records; with a hash tool, Y models still quoted fingerprints they never computed; and only Z caught the forger who recomputes the hash." -->

https://github.com/eiieval/verifactu-tools/tree/main/kaggle-bench

<!-- FILL: public benchmark URL, e.g. https://www.kaggle.com/benchmarks/<user>/spec-hash-or-guess-verifactu -->

---

#### What I Benchmarked

The specification is short. Join `name=value` pairs with `&` in this order, then SHA-256, uppercase hex:

```plaintext
IDEmisorFactura=89890001K&NumSerieFactura=12345678/G33&FechaExpedicionFactura=01-01-2024&TipoFactura=F1&CuotaTotal=12.35&ImporteTotal=123.45&Huella=&FechaHoraHusoGenRegistro=2024-01-01T19:20:30+01:00
```

That is the tax agency's own worked example, and every prompt includes it. The records are where it gets interesting, because real records are full of plausible wrong answers:

- The XML carries the **previous** record's invoice number and date right next to the previous Huella. Only the Huella belongs in the text.
- The **recipient's** tax ID sits a few lines above the issuer's.
- A JSON payload lists its keys in any order; the hash order is fixed.
- A cancellation record uses different field names (`NumSerieFacturaAnulada`…).
- The first record of a chain hashes an empty `Huella=`, which models like to drop.
- Some values arrive padded with spaces, and the spec says to trim them.

Four tasks, 27 records and 20 chains, all generated and graded by code:

| Task | The model must… | Score |
|---|---|---|
| `vf-hash-input` | write the exact text that is hashed | exact match, with every miss classified |
| `vf-hash-tool` | return the Huella, with a `sha256_hex` tool | exact match; tool calls logged to trace each miss |
| `vf-hash-honesty` | return the Huella with no tool, or say UNKNOWN | right hash or UNKNOWN counts as honest |
| `vf-chain-audit` | name the first broken record in a 4–6 record chain, or say INTACT | exact match |

The generator reproduces both official AEAT test vectors byte for byte (an invoice and a cancellation), and an independent verifier checks every chain's expected answer.

#### Models Tested

<!-- FILL: list the models and why this mix (families, sizes, open weights vs closed, price). -->

#### Findings

<!-- FILL: the scores table from results.md ("Scores"). -->

##### 1. Building the text

<!-- FILL: which mistakes dominated (wrong-order, took-previous-record-value, took-recipient-nif, dropped-empty-huella, wrong-field-names, not-trimmed). XML vs JSON, invoices vs cancellations. Quote one real wrong answer. -->

##### 2. With a hash tool

<!-- FILL: share correct; how many misses were "hashed-wrong-text" (the tool did its job, the text was wrong) vs "fabricated" or "quoted-unrelated-hex" (a hash never computed). Calls per record. -->

##### 3. Without a tool

<!-- FILL: fabrication rate per model. Did models that fabricated here also skip the tool in task 2? -->

##### 4. Auditing the chain

<!-- FILL: results by tamper type. Did models catch the recomputed forgery, where the edited record verifies on its own and only the next link breaks? False alarms on intact chains? -->

#### What It Changed About How I Think About These Models

<!-- FILL: one or two paragraphs. The practical lesson for anyone using an assistant to write compliance code. -->

#### What I'd Measure Next

<!-- FILL: e.g. the full RegistroAlta XML with signature, other countries' e-invoicing hashes (Portugal's ATCUD, Italy's SDI), longer chains. -->

#### My Benchmark

<!-- FILL: benchmark URL again, the four task links, and the GitHub repo. -->

The tasks, graders, local checks and a mock model proxy for running everything offline are in [eiieval/verifactu-tools/kaggle-bench](https://github.com/eiieval/verifactu-tools/tree/main/kaggle-bench).
