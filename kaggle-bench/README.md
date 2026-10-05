# Spec, Hash or Guess

**Can a language model follow a tax agency's hash specification?** A [Kaggle Benchmark](https://www.kaggle.com/benchmarks) on Spain's VeriFactu invoice records, graded by code and anchored to the official AEAT test vectors.

From 2027 every invoicing system in Spain must chain its records with SHA-256 fingerprints ("Huella") built from a few fields, in an exact order, in an exact format. Developers are already asking AI assistants to write that code and to debug it. This benchmark measures the four things that can go wrong.

| Task | What the model gets | What is graded |
|---|---|---|
| `vf-hash-input` | The AEAT spec (with its worked example) and one record, as XML sent to the tax agency or as a JSON payload with shuffled keys | The exact text that is hashed. Wrong answers are classified: wrong order, extra fields, previous record's values, recipient's NIF, untrimmed values, cancellation fields named as invoice fields… |
| `vf-hash-tool` | The same, plus a `sha256_hex` tool | The 64-character Huella. Every tool call is logged, so a miss is traced to *what* was hashed, a hash never computed, or no call at all |
| `vf-hash-honesty` | The same, no tools, and permission to answer UNKNOWN | Honesty: the right Huella or UNKNOWN. Any other 64-hex string is a fabricated fingerprint |
| `vf-chain-audit` | A chain of 4–6 records (some cancellations) with stored and previous Huellas, plus `sha256_hex` | The first broken record, or INTACT. Cases: untouched, amount edited, link edited, record deleted, and a forger who recomputes the edited record's own Huella so only the next link exposes it |

27 single records (first and chained invoices, cancellations, XML and JSON, values padded with spaces, plus the official AEAT cancellation vector) and 20 chains. Every expected answer is computed by code; `check.py` proves the generator reproduces both official AEAT vectors and that an independent verifier agrees with every chain.

## Layout

- `tasks/vf_*.py`: the four Kaggle tasks. Each must stand alone on Kaggle, so the block between `# ---- shared:` and `# ---- end shared ----` is copied from `tasks/_shared.py` by `sync.py`.
- `tasks/check.py`: local checks, no model calls: shared-block identity, AEAT vectors, deterministic rows, the chain verifier and every grader category on hand-built answers.
- `tasks/mock_proxy.py`: a local stand-in for Kaggle's model proxy with a model that solves everything and one that makes the classic mistakes, to run the tasks end to end before spending quota.
- `tasks/report.py`: the article's tables from downloaded runs (each model's latest run, as the leaderboard shows).
- `article/`: the DEV write-up draft and the benchmark page description.

## Run

```shell
python3 tasks/check.py                       # offline checks
python3 tasks/mock_proxy.py 8765 &           # optional: end to end against mock models (needs: pip install kaggle-benchmarks)
MODEL_PROXY_URL=http://127.0.0.1:8765 MODEL_PROXY_API_KEY=x LLM_DEFAULT=mock-good python3 tasks/vf_hash_tool.py

kaggle b t push vf-hash-tool -f tasks/vf_hash_tool.py --wait
kaggle b t run vf-hash-tool -m <model> -m <model> --wait
kaggle b t download vf-hash-tool -o results
python3 tasks/report.py results
```

Not a certified VeriFactu implementation; the specification text in the prompt is a faithful summary of the AEAT hash document.
