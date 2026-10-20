import React from 'react';
import { TextDecoder, TextEncoder } from 'util';
import { fireEvent, render, screen } from '@testing-library/react';
import * as Sentry from '@sentry/react';
import ChatWidget from '../components/ChatWidget';

jest.mock('@sentry/react', () => ({
  setConversationId: jest.fn(),
  startNewTrace: (callback) => callback(),
  startInactiveSpan: () => ({ end: jest.fn(), setAttribute: jest.fn() }),
  withActiveSpan: (span, callback) => callback(),
  startSpan: (options, callback) => callback({ setAttribute: jest.fn() }),
  captureException: jest.fn(),
  logger: { info: jest.fn() },
  metrics: { count: jest.fn() },
}));

test('shows connection guidance, reports the cause, and allows a successful retry', async () => {
  const originalFetch = global.fetch;
  const originalTextDecoder = global.TextDecoder;
  const cause = new TypeError('NetworkError when attempting to fetch resource.');
  global.TextDecoder = TextDecoder;
  global.fetch = jest.fn().mockRejectedValueOnce(cause).mockResolvedValueOnce({
    ok: true,
    body: {
      getReader: () => ({
        read: jest.fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('event: token\ndata: {"text":"Hello again"}\n\n'),
          })
          .mockResolvedValueOnce({ done: true }),
      }),
    },
  });

  const { unmount } = render(<ChatWidget />);
  try {
    fireEvent.click(screen.getByRole('button', { name: 'Chat with AI Agent' }));
    const input = screen.getByPlaceholderText('Ask me anything...');
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(screen.getByText('Send'));

    await screen.findByText('Unable to reach the plant agent. Check your connection and try again.');
    expect(Sentry.captureException).toHaveBeenCalledWith(expect.objectContaining({ cause }));
    expect(screen.queryByText('Thinking…')).toBeNull();

    fireEvent.change(input, { target: { value: 'Try again' } });
    fireEvent.click(screen.getByText('Send'));

    await screen.findByText('Hello again');
    await screen.findByPlaceholderText('Ask me anything...');
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(Sentry.captureException).toHaveBeenCalledTimes(1);
  } finally {
    unmount();
    global.fetch = originalFetch;
    global.TextDecoder = originalTextDecoder;
    jest.clearAllMocks();
  }
});
