import { gzipSync } from 'node:zlib';
import { describe, expect, it } from 'vitest';
import { decodeBytes } from './files';

describe('decodeBytes', () => {
  it('decompresses gzip by content, whatever the file name', async () => {
    expect(await decodeBytes(new Uint8Array(gzipSync('>a s1\nACGT\n')))).toBe('>a s1\nACGT\n');
  });

  it('reads plain text even when the name says .gz', async () => {
    expect(await decodeBytes(new TextEncoder().encode('>a s1\nACGT\n'))).toBe('>a s1\nACGT\n');
  });
});
