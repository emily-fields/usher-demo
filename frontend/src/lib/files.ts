export async function readFileText(file: File): Promise<string> {
  if (file.name.toLowerCase().endsWith('.gz')) {
    const stream = file.stream().pipeThrough(new DecompressionStream('gzip'));
    return new Response(stream).text();
  }
  return file.text();
}
