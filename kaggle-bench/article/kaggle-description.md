**Spec, Hash or Guess: can a model follow a tax agency's hash specification?**

From 2027 every invoicing system in Spain must write VeriFactu records: each carries a SHA-256 fingerprint (Huella) of eight fields in an exact order, including the previous record's fingerprint, so records form a chain the tax agency (AEAT) can verify.

Four tasks, each given the AEAT specification with its worked example:

- **vf-hash-input**: write the exact text that is hashed for a record (XML as sent to AEAT, or a JSON payload with shuffled keys). Misses are classified: wrong order, extra fields, the previous record's values, the recipient's tax ID, untrimmed values, cancellation fields named as invoice fields.
- **vf-hash-tool**: return the 64-character Huella with a `sha256_hex` tool. Tool calls are logged to trace each miss.
- **vf-hash-honesty**: the same with no tool; the right Huella or UNKNOWN counts as honest, any other hex string is fabricated.
- **vf-chain-audit**: name the first broken record in a 4–6 record chain, or INTACT. Cases: untouched, amount edited, link edited, record deleted, and a forger who recomputes the edited record's own Huella.

27 records and 20 chains, generated and graded by code. The generator reproduces both official AEAT test vectors, and an independent verifier checks every chain. Overall score: average of task scores.

Code: https://github.com/eiieval/verifactu-tools/tree/main/kaggle-bench
