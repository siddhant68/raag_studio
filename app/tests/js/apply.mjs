// Helper for the pytest suite: node apply.mjs <function> < json-args   -> prints the JSON result of logic.js's function.
import * as L from "../../web/js/logic.js";
const chunks = [];
for await (const c of process.stdin) chunks.push(c);
const args = JSON.parse(Buffer.concat(chunks).toString() || "[]");
console.log(JSON.stringify(L[process.argv[2]](...args)));
