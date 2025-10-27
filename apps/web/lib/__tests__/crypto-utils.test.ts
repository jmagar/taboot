import { describe, expect, it, afterEach, vi } from "vitest";

import { toBase64Url } from "../crypto-utils";

const originalBtoa = globalThis.btoa;

afterEach(() => {
  globalThis.btoa = originalBtoa;
  vi.restoreAllMocks();
});

describe("toBase64Url", () => {
  it("encodes bytes using Buffer when btoa is unavailable", () => {
    // Ensure btoa is undefined to test Node.js code path
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).btoa = undefined;

    const bytes = Uint8Array.from(Buffer.from("hello-world", "utf8"));
    const encoded = toBase64Url(bytes);
    expect(encoded).toBe("aGVsbG8td29ybGQ");
  });

  it("encodes large byte arrays using btoa without stack overflow", () => {
    // Mock btoa to use Buffer internally (Edge/browser simulation)
    globalThis.btoa = (input: string): string => Buffer.from(input, "binary").toString("base64");

    const size = 90_000;
    const bytes = new Uint8Array(size);
    for (let i = 0; i < size; i += 1) {
      bytes[i] = i % 256;
    }

    const encodedWithBtoa = toBase64Url(bytes);

    // Cross-check with Buffer implementation for correctness
    const expected = Buffer.from(bytes).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
    expect(encodedWithBtoa).toBe(expected);
  });

  it("throws when input is not a Uint8Array", () => {
    expect(() => toBase64Url("not-bytes" as unknown as Uint8Array)).toThrow(
      "Expected bytes to be a Uint8Array",
    );
  });
});
