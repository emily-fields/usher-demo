// Detect gzip by its magic bytes, as the server does: browsers often save an
// already-decompressed download under its .gz name, and gzip files get renamed.
export async function decodeBytes(bytes: Uint8Array): Promise<string> {
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
    const stream = new Response(bytes as BodyInit).body!.pipeThrough(new DecompressionStream('gzip'));
    return new Response(stream).text();
  }
  return new TextDecoder().decode(bytes);
}

export async function readFileText(file: File): Promise<string> {
  return decodeBytes(new Uint8Array(await file.arrayBuffer()));
}
