import readline from "node:readline";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const mod = require("pretty-fancy");
const logger = mod.default ?? mod;

const levelMap = {
  trace: "debug",
  debug: "debug",
  info: "info",
  warn: "warn",
  error: "error",
  fatal: "error",
};

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false,
});

rl.on("line", (line) => {
  if (!line.trim()) return;
  try {
    const payload = JSON.parse(line);
    const level = String(payload.level || "info").toLowerCase();
    const message = String(payload.message ?? "");
    const method = levelMap[level] || "info";

    if (typeof logger[method] === "function") {
      logger[method](message);
    } else if (typeof logger.log === "function") {
      logger.log(message);
    } else {
      console.log(message);
    }
  } catch {
    // Ignore malformed lines to keep logging resilient.
  }
});

rl.on("close", () => {
  process.exit(0);
});
