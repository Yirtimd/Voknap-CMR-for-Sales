import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const css = fs.readFileSync(path.join(root, "src/design-system/tokens.css"), "utf8");
function parseTokens(block) {
  return Object.fromEntries(
    [...block.matchAll(/--([\w-]+):\s*(#[\da-fA-F]{6})\s*;/g)].map((match) => [match[1], match[2]])
  );
}

const lightBlock = css.match(/:root\s*{([\s\S]*?)}/)?.[1] ?? "";
const darkBlock = css.match(/:root\[data-theme="dark"\]\s*{([\s\S]*?)}/)?.[1] ?? "";
const lightTokens = parseTokens(lightBlock);
const darkTokens = { ...lightTokens, ...parseTokens(darkBlock) };

const pairs = [
  ["color-text-primary", "color-surface", 4.5],
  ["color-text-secondary", "color-surface", 4.5],
  ["color-text-muted", "color-surface", 4.5],
  ["color-primary", "color-surface", 4.5],
  ["color-text-on-accent", "color-primary", 4.5],
  ["color-success-text", "color-success-soft", 4.5],
  ["color-warning-text", "color-warning-soft", 4.5],
  ["color-danger-text", "color-danger-soft", 4.5],
  ["color-ai", "color-surface", 4.5]
];

function luminance(hex) {
  const channels = hex.slice(1).match(/.{2}/g).map((value) => {
    const channel = Number.parseInt(value, 16) / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrast(foreground, background) {
  const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

const failures = [];
for (const [theme, tokens] of [["light", lightTokens], ["dark", darkTokens]]) {
  for (const [foregroundName, backgroundName, minimum] of pairs) {
    const foreground = tokens[foregroundName];
    const background = tokens[backgroundName];
    if (!foreground || !background) {
      failures.push(`${theme} ${foregroundName}/${backgroundName}: token missing`);
      continue;
    }
    const ratio = contrast(foreground, background);
    const result = `${theme} ${foregroundName} on ${backgroundName}: ${ratio.toFixed(2)}:1`;
    if (ratio < minimum) failures.push(`${result} < ${minimum}:1`);
    else console.log(`PASS ${result}`);
  }
}

if (failures.length) {
  console.error(failures.map((failure) => `FAIL ${failure}`).join("\n"));
  process.exitCode = 1;
}
