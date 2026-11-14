// Uncaught errors of the interface are sent to the server, which writes them
// to its log (see api/diagnostics.py): an error on a phone is otherwise
// invisible. Each distinct error is sent once, and at most MAX per page load.

import { ApiError } from './api';

const MAX = 20;
const sent = new Set<string>();

function report(message: string, stack: string): void {
  const key = `${message}\n${stack.split('\n')[0] ?? ''}`;
  if (sent.has(key) || sent.size >= MAX) return;
  sent.add(key);
  const body = JSON.stringify({
    message: message.slice(0, 500),
    stack: stack.slice(0, 4000),
    page: location.hash.slice(0, 200) || '#/',
    agent: navigator.userAgent.slice(0, 300),
  });
  // keepalive: still sent if the page is being closed.
  fetch('/api/client-errors', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body,
    keepalive: true,
  }).catch(() => {});
}

function describe(reason: unknown): [string, string] {
  if (reason instanceof Error) return [`${reason.name}: ${reason.message}`, reason.stack ?? ''];
  return [String(reason), ''];
}

export function reportErrors(): void {
  window.addEventListener('error', (event) => {
    // Resource errors (a missing cover...) are not script errors.
    if (!(event instanceof ErrorEvent) || !event.message) return;
    const [message, stack] = event.error ? describe(event.error) : [event.message, `${event.filename}:${event.lineno}`];
    report(message, stack);
  });
  window.addEventListener('unhandledrejection', (event) => {
    // Failed requests are already handled and shown by the app.
    if (event.reason instanceof ApiError) return;
    const [message, stack] = describe(event.reason);
    if (/^(AbortError|TypeError: (Failed to fetch|Load failed|NetworkError))/.test(message)) return;
    report(message, stack);
  });
}
