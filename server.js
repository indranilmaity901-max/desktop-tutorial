import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const port = Number(process.env.PORT || 4173);
const root = fileURLToPath(new URL(".", import.meta.url));

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8"
};

function resolvePath(urlPath) {
  const requested = urlPath === "/" ? "/public/index.html" : urlPath;
  const cleanPath = normalize(decodeURIComponent(requested)).replace(/^(\.\.[/\\])+/, "");
  return join(root, cleanPath);
}

createServer(async (request, response) => {
  try {
    const url = new URL(request.url, `http://${request.headers.host}`);
    const filePath = resolvePath(url.pathname);
    const body = await readFile(filePath);
    response.writeHead(200, {
      "Content-Type": contentTypes[extname(filePath)] || "application/octet-stream"
    });
    response.end(body);
  } catch {
    const shell = await readFile(join(root, "public", "index.html"));
    response.writeHead(200, { "Content-Type": contentTypes[".html"] });
    response.end(shell);
  }
}).listen(port, "127.0.0.1", () => {
  console.log(`WPACS dashboard running at http://127.0.0.1:${port}`);
});
