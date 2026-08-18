import "@testing-library/jest-dom";

// Minimal WebSocket stub so components that open a socket don't crash in jsdom.
class FakeWebSocket {
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 1;
  constructor(public url: string) {}
  send() {}
  close() {}
}
// @ts-expect-error override for tests
global.WebSocket = FakeWebSocket;
