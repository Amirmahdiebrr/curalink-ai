/**
 * build.js
 *
 * Build pipeline ساده مبتنی بر esbuild: فایل‌های CSS و JS پروژه را
 * می‌خواند، minify می‌کند و در app/static/dist/ خروجی می‌دهد.
 * فایل‌های اصلی (توسعه) دست‌نخورده در app/static/css و
 * app/static/js باقی می‌مانند؛ فقط تمپلیت‌ها باید در production
 * به فایل‌های .min.css/.min.js داخل dist/ اشاره کنند.
 *
 * اجرا:
 *   npm install
 *   npm run build       (یک‌بار build نهایی)
 *   npm run watch        (build خودکار هنگام توسعه)
 */

const esbuild = require("esbuild");
const path = require("path");

const isWatch = process.argv.includes("--watch");

const CSS_ENTRY_POINTS = [
  "app/static/css/style.css",
  "app/static/css/chat.css",
  "app/static/css/workspace.css",
];

const JS_ENTRY_POINTS = [
  "app/static/js/main.js",
  "app/static/js/ai-doctor.js",
  "app/static/js/workspace.js",
];

const OUT_DIR = "app/static/dist";

async function buildCSS() {
  const ctx = await esbuild.context({
    entryPoints: CSS_ENTRY_POINTS,
    outdir: OUT_DIR,
    entryNames: "[name].min",
    minify: true,
    sourcemap: true,
    loader: { ".css": "css" },
    logLevel: "info",
  });

  if (isWatch) {
    await ctx.watch();
    console.log("👀 Watching CSS for changes...");
  } else {
    await ctx.rebuild();
    await ctx.dispose();
    console.log("✅ CSS build complete.");
  }
}

async function buildJS() {
  const ctx = await esbuild.context({
    entryPoints: JS_ENTRY_POINTS,
    outdir: OUT_DIR,
    entryNames: "[name].min",
    bundle: false,
    minify: true,
    sourcemap: true,
    target: ["es2018"],
    logLevel: "info",
  });

  if (isWatch) {
    await ctx.watch();
    console.log("👀 Watching JS for changes...");
  } else {
    await ctx.rebuild();
    await ctx.dispose();
    console.log("✅ JS build complete.");
  }
}

async function main() {
  await buildCSS();
  await buildJS();

  if (!isWatch) {
    console.log(`\n🎉 Build finished. Output in ${path.resolve(OUT_DIR)}`);
  }
}

main().catch((err) => {
  console.error("❌ Build failed:", err);
  process.exit(1);
});