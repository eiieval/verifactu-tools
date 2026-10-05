# Cómo publicarlo (DEV x Kaggle Benchmarking Challenge)

**Plazo:** 11-oct-2026, 23:59 PDT = **lunes 12-oct, 08:59 en Madrid**. Publica el post el **sábado 10** para tener margen y acumular reacciones.
**Premio:** 5 ganadores × 500 $ + DEV++. **Un único post por persona** con el tag `#kagglechallenge`: no publiques borradores con ese tag.
**Cuota de Kaggle para modelos:** unos 10 $ al día y 100 $ al mes. Reparte las ejecuciones en dos días si usas modelos caros.

## 1. Preparar (15 min)

```shell
pip install kaggle kaggle-benchmarks
# kaggle.com → Settings → API → Create New Token → guarda kaggle.json en ~/.kaggle/
kaggle b auth -y          # clave del proxy de modelos (caduca: repítelo si da error de autenticación)
kaggle b t models         # lista los modelos disponibles; copia los nombres exactos
cd verifactu-tools/kaggle-bench
python3 tasks/check.py    # debe terminar en "all checks passed"
```

## 2. Subir las 4 tareas

```shell
kaggle b t push vf-hash-input   -f tasks/vf_hash_input.py   --wait
kaggle b t push vf-hash-tool    -f tasks/vf_hash_tool.py    --wait
kaggle b t push vf-hash-honesty -f tasks/vf_hash_honesty.py --wait
kaggle b t push vf-chain-audit  -f tasks/vf_chain_audit.py  --wait
```

Cada `push` ejecuta la tarea una vez con el modelo por defecto. Si `kaggle b t status <tarea>` muestra `Errored` (por ejemplo, sin cuota), corrige la causa y vuelve a hacer `push`.

## 3. Ejecutar los modelos

Elige 6-8 modelos de `kaggle b t models` que mezclen familias y tamaños: dos Gemini (uno Flash), Gemma (pesos abiertos), gpt-oss, dos GPT (nano y mini) y dos Claude (Haiku y Sonnet). Repite `-m` por cada modelo; no los separes con espacios dentro de un mismo `-m`.

```shell
for t in vf-hash-input vf-hash-tool vf-hash-honesty vf-chain-audit; do
  kaggle b t run $t -m MODELO_1 -m MODELO_2 -m MODELO_3 --wait
done
```

Empieza por `vf-hash-honesty` y `vf-hash-input`, que son las más baratas. **No relances un modelo que ya salió bien:** el leaderboard muestra la última ejecución, y una ejecución fallida por cuota sustituye a la buena.

## 4. Crear el benchmark en Kaggle (web)

1. Kaggle → Benchmarks → *New benchmark*. Título: **Spec, Hash or Guess: VeriFactu**.
2. Añade las 4 tareas.
3. Puntuación global: **Average of task scores**.
4. Descripción: pega `article/kaggle-description.md`.
5. Ponlo en **Public**. Comprueba que la URL abre sin iniciar sesión (ventana privada).

## 5. Resultados y post

```shell
for t in vf-hash-input vf-hash-tool vf-hash-honesty vf-chain-audit; do kaggle b t download $t -o results -f; done
python3 tasks/report.py results > article/results.md
```

Abre `article/devto-draft.md` y rellena cada `<!-- FILL ... -->` con las cifras de `article/results.md`. Un post que solo enumera números puntúa poco: explica qué significan. Si usas Claude Code, pídele: *"Rellena los FILL de article/devto-draft.md con article/results.md, sin inventar nada"*.

Publica en DEV con estos tags: `devchallenge, kagglechallenge, ai, machinelearning`.
Comprueba que el post enlaza al benchmark público. Sin ese enlace no entra a concurso.

## Si algo falla

- `RateLimitError` o cuota agotada: espera al día siguiente. Las filas que fallan se marcan como `errored`, no como incorrectas.
- Para probar sin gastar cuota: `pip install kaggle-benchmarks`, después `python3 tasks/mock_proxy.py 8765 &` y ejecuta cualquier tarea con `MODEL_PROXY_URL=http://127.0.0.1:8765 MODEL_PROXY_API_KEY=x LLM_DEFAULT=mock-good`.
