import { describe, expect, it } from 'vitest';
import { ApiError, jobRefetchInterval, shouldRetry } from './api';

describe('job polling', () => {
  it('does not retry or keep polling a job that does not exist', () => {
    const missing = new ApiError(404, ['Job not found']);
    expect(shouldRetry(0, missing)).toBe(false);
    expect(jobRefetchInterval(undefined, missing)).toBe(false);
  });

  it('keeps polling through transient errors and stops when finished', () => {
    expect(shouldRetry(0, new TypeError('network'))).toBe(true);
    expect(jobRefetchInterval(undefined, new TypeError('network'))).toBe(2000);
    expect(jobRefetchInterval('done', null)).toBe(false);
    expect(jobRefetchInterval('placing', null)).toBe(2000);
  });
});
