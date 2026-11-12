export async function readBoundedJson(request: Request): Promise<unknown> {
  const reader = request.body?.getReader();
  if (!reader) throw new Error("Expected a JSON body");

  const decoder = new TextDecoder("utf-8", { fatal: true });
  let body = "";
  let byteCount = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) return JSON.parse(body + decoder.decode());
      byteCount += value.byteLength;
      if (byteCount > 4096) throw new RangeError("Event exceeds 4096 bytes");
      body += decoder.decode(value, { stream: true });
    }
  } finally {
    void reader.cancel().catch(() => {});
  }
}

