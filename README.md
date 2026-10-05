# Herramientas VeriFactu

Herramientas gratuitas y open source para desarrolladores que integran VeriFactu. Todo se calcula en el navegador: ningún dato sale de tu equipo.

*Free, open-source VeriFactu developer tools that run entirely in the browser.*

## Qué hace

- **Huella.** Calcula la huella SHA-256 de un RegistroAlta con el orden y formato exactos de la especificación de la AEAT, y reproduce su ejemplo oficial. Si tienes una huella que no coincide, prueba los errores de formato más habituales y te dice cuál es: importes con ceros de más, fecha en formato ISO, huso horario sin dos puntos, huella anterior en minúsculas.
- **Registros XML.** Pega uno o varios RegistroAlta o RegistroAnulacion y comprueba la huella de cada uno y el encadenamiento entre ellos.
- **Código QR.** Genera la URL y el QR del servicio de cotejo de la AEAT, en producción o pruebas, VERI*FACTU o no, y valida una URL existente.

## Benchmark para modelos de IA

[`kaggle-bench/`](kaggle-bench/) mide si un modelo de lenguaje sabe seguir la especificación de la huella: construir el texto exacto, calcularla con una herramienta SHA-256, admitir cuando no puede y encontrar el registro manipulado de una cadena. Se corrige por código y está anclado a los vectores oficiales de la AEAT. Se publica como [Kaggle Benchmark](https://www.kaggle.com/benchmarks).

## Uso local

```bash
npm test        # pruebas sin conexión, incluido el ejemplo oficial de la AEAT
npm run dev     # http://localhost:3000
```

## Seguridad

Página estática sin backend ni peticiones de red. Política de seguridad de contenido estricta y sin scripts de terceros: la librería de QR es qrcode-generator 1.4.4, licencia MIT, descargada del registro de npm con su integridad verificada.

## Aviso

Herramienta orientativa basada en las especificaciones técnicas publicadas por la AEAT. No sustituye a la validación del servicio web de la AEAT.

## Licencia

MIT
