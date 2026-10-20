import { TextDecoder, TextEncoder } from 'util';
import postEventStream from '../utils/sseStream';

describe('postEventStream', () => {
  const originalFetch = global.fetch;
  const originalTextDecoder = global.TextDecoder;
  const options = { body: { message: 'Hello' }, onEvent: jest.fn() };

  beforeEach(() => {
    global.fetch = jest.fn();
    global.TextDecoder = TextDecoder;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    global.TextDecoder = originalTextDecoder;
    jest.clearAllMocks();
  });

  test.each([
    'NetworkError when attempting to fetch resource.',
    'Failed to fetch',
  ])('explains a rejected fetch: %s', async (message) => {
    const cause = new TypeError(message);
    fetch.mockRejectedValue(cause);

    await expect(postEventStream('http://localhost:8093/api/v1/chat', options))
      .rejects.toMatchObject({
        message: 'Unable to reach the plant agent. Check your connection and try again.',
        cause,
      });
  });

  test.each([
    new DOMException('Aborted', 'AbortError'),
    new Error('Unexpected failure'),
  ])('preserves other fetch errors: %s', async (error) => {
    fetch.mockRejectedValue(error);

    await expect(postEventStream('/api/v1/chat', options)).rejects.toBe(error);
  });

  test('preserves HTTP errors', async () => {
    fetch.mockResolvedValue({ ok: false, status: 503 });

    await expect(postEventStream('/api/v1/chat', options))
      .rejects.toThrow('Chat request failed: HTTP 503');
  });

  test('does not misclassify event handler bugs as connection failures', async () => {
    const error = new TypeError('Invalid event handler');
    fetch.mockResolvedValue({
      ok: true,
      body: {
        getReader: () => ({
          read: jest.fn().mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('event: token\ndata: {"text":"Hi"}\n\n'),
          }),
        }),
      },
    });

    await expect(postEventStream('/api/v1/chat', {
      ...options,
      onEvent: () => { throw error; },
    })).rejects.toBe(error);
  });
});
