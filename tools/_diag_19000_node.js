const http = require("http");
const body = JSON.stringify({
  model: "pool-deepseek-v4-pro",
  messages: [{ role: "user", content: "hi" }],
  max_tokens: 50,
});
const req = http.request(
  {
    hostname: "127.0.0.1",
    port: 19000,
    path: "/proxy/llm/chat/completions",
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + (process.env.QCLAW_GATEWAY_TOKEN || "") + "",
      "Content-Length": Buffer.byteLength(body),
    },
  },
  (res) => {
    let data = "";
    res.on("data", (c) => (data += c));
    res.on("end", () => {
      console.log("status", res.statusCode, "reasoning", data.includes("reasoning_content"));
      console.log(data.slice(0, 200));
    });
  }
);
req.on("error", (e) => console.log("ERR", e.message));
req.write(body);
req.end();
