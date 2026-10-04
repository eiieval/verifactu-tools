// Tailwind is compiled at build time (npm run build:css) so no third-party script runs in the browser.
module.exports = { content: ['./public/**/*.html', './public/app.js', './public/js/*.js'], theme: { extend: {} }, plugins: [] };
