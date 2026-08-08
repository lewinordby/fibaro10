const fs = require("node:fs/promises");
const path = require("node:path");
const sharp = require("sharp");

const root = path.resolve(__dirname, "..");
const staticDir = path.join(root, "static");
const markSource = path.join(staticDir, "lilletorget-mark.svg");
const wordmarkSource = path.join(staticDir, "lilletorget-wordmark.svg");

async function squareIcon(size, markSize, destination, background) {
  const mark = await sharp(markSource)
    .resize(markSize, markSize, { fit: "contain" })
    .png()
    .toBuffer();
  const offset = Math.round((size - markSize) / 2);
  await sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background,
    },
  })
    .composite([{ input: mark, left: offset, top: offset }])
    .png({ compressionLevel: 9 })
    .toFile(destination);
}

async function copyPwaIcons(targetDir) {
  await fs.mkdir(targetDir, { recursive: true });
  for (const name of ["pwa-icon-192.png", "pwa-icon-512.png", "pwa-icon-maskable-512.png"]) {
    await fs.copyFile(path.join(staticDir, name), path.join(targetDir, name));
  }
}

async function main() {
  await sharp(markSource)
    .resize(512, 512)
    .png({ compressionLevel: 9 })
    .toFile(path.join(staticDir, "lilletorget-mark.png"));
  await sharp(markSource)
    .resize(128, 128)
    .png({ compressionLevel: 9 })
    .toFile(path.join(staticDir, "lilletorget-favicon.png"));
  await sharp(wordmarkSource)
    .resize({ width: 1280 })
    .png({ compressionLevel: 9 })
    .toFile(path.join(staticDir, "lilletorget-logo.png"));
  await sharp(wordmarkSource)
    .resize({ width: 1000 })
    .png({ compressionLevel: 9 })
    .toFile(path.join(staticDir, "lilletorget-wordmark.png"));

  await squareIcon(192, 146, path.join(staticDir, "pwa-icon-192.png"), "#F7F9FC");
  await squareIcon(512, 390, path.join(staticDir, "pwa-icon-512.png"), "#F7F9FC");
  await squareIcon(512, 286, path.join(staticDir, "pwa-icon-maskable-512.png"), "#F2F5F9");

  await copyPwaIcons(path.join(root, "microapp_backend"));
  await copyPwaIcons(path.join(root, "owntracks_service", "app"));
  console.log("Lilletorget brand assets generated.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
