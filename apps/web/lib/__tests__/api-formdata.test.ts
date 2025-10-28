/**
 * Tests for FormData/Blob handling in CsrfAwareAPIClient
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the csrf-client module
vi.mock("../csrf-client", () => ({
  csrfFetch: vi.fn(),
}));

// Mock the TabootAPIClient
vi.mock("@taboot/api-client", () => ({
  TabootAPIClient: class MockTabootAPIClient {
    // Mock constructor - intentionally empty
  },
}));

import { api } from "../api";
import { csrfFetch } from "../csrf-client";

describe("CsrfAwareAPIClient FormData/Blob handling", () => {
  const mockCsrfFetch = vi.mocked(csrfFetch);

  const getCallByPath = (path: string): [RequestInfo, RequestInit] => {
    const call = mockCsrfFetch.mock.calls.find(([url]) => String(url).includes(path));
    if (!call) {
      throw new Error(`No csrfFetch call found for path: ${path}`);
    }
    const [url, init] = call;
    return [url, (init ?? {}) as RequestInit];
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockCsrfFetch.mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ data: { success: true }, error: null }),
    });
  });

  describe("POST method", () => {
    it("should pass FormData directly without JSON.stringify", async () => {
      const formData = new FormData();
      formData.append("file", new Blob(["test"], { type: "text/plain" }), "test.txt");
      formData.append("name", "Test File");

      await api.post("/upload", formData);

      expect(mockCsrfFetch).toHaveBeenCalledWith(
        expect.stringContaining("/upload"),
        expect.objectContaining({
          method: "POST",
          body: formData, // Should be FormData, not stringified
        }),
      );

      const [, opts] = getCallByPath("/upload");
      expect(opts.body).toBeInstanceOf(FormData);
    });

    it("should pass Blob directly without JSON.stringify", async () => {
      const blob = new Blob(["test content"], { type: "text/plain" });

      await api.post("/upload-blob", blob);

      expect(mockCsrfFetch).toHaveBeenCalledWith(
        expect.stringContaining("/upload-blob"),
        expect.objectContaining({
          method: "POST",
          body: blob,
        }),
      );

      const [, opts] = getCallByPath("/upload-blob");
      expect(opts.body).toBeInstanceOf(Blob);
    });

    it("should pass ArrayBuffer directly without JSON.stringify", async () => {
      const buffer = new ArrayBuffer(8);

      await api.post("/upload-buffer", buffer);

      expect(mockCsrfFetch).toHaveBeenCalledWith(
        expect.stringContaining("/upload-buffer"),
        expect.objectContaining({
          method: "POST",
          body: buffer,
        }),
      );

      const [, opts] = getCallByPath("/upload-buffer");
      expect(opts.body).toBeInstanceOf(ArrayBuffer);
    });

    it("should JSON.stringify plain objects", async () => {
      const data = { name: "test", value: 123 };

      await api.post("/data", data);

      expect(mockCsrfFetch).toHaveBeenCalledWith(
        expect.stringContaining("/data"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(data),
        }),
      );

      const [, opts] = getCallByPath("/data");
      expect(typeof opts.body).toBe("string");
    });

    it("should preserve options.body if provided", async () => {
      const customBody = "custom body content";
      const data = { ignored: "this should be ignored" };

      await api.post("/custom", data, { body: customBody });

      expect(mockCsrfFetch).toHaveBeenCalledWith(
        expect.stringContaining("/custom"),
        expect.objectContaining({
          method: "POST",
          body: customBody, // Should use options.body, not data
        }),
      );
    });

    it("should handle null/undefined data", async () => {
      await api.post("/null-data", null);

      expect(mockCsrfFetch).toHaveBeenCalledWith(
        expect.stringContaining("/null-data"),
        expect.objectContaining({
          method: "POST",
          body: undefined,
        }),
      );

      await api.post("/undefined-data");

      expect(mockCsrfFetch).toHaveBeenCalledWith(
        expect.stringContaining("/undefined-data"),
        expect.objectContaining({
          method: "POST",
          body: undefined,
        }),
      );
    });
  });

  describe("PUT method", () => {
    it("should pass FormData directly without JSON.stringify", async () => {
      const formData = new FormData();
      formData.append("field", "value");

      await api.put("/update", formData);

      const [, opts] = getCallByPath("/update");
      expect(opts.method).toBe("PUT");
      expect(opts.body).toBeInstanceOf(FormData);
    });

    it("should JSON.stringify plain objects", async () => {
      const data = { field: "value" };

      await api.put("/update", data);

      const [, opts] = getCallByPath("/update");
      expect(opts.method).toBe("PUT");
      expect(typeof opts.body).toBe("string");
      expect(opts.body).toBe(JSON.stringify(data));
    });
  });

  describe("PATCH method", () => {
    it("should pass FormData directly without JSON.stringify", async () => {
      const formData = new FormData();
      formData.append("field", "value");

      await api.patch("/partial-update", formData);

      const [, opts] = getCallByPath("/partial-update");
      expect(opts.method).toBe("PATCH");
      expect(opts.body).toBeInstanceOf(FormData);
    });

    it("should pass Blob directly without JSON.stringify", async () => {
      const blob = new Blob(["patch content"], { type: "application/octet-stream" });

      await api.patch("/partial-update-blob", blob);

      const [, opts] = getCallByPath("/partial-update-blob");
      expect(opts.method).toBe("PATCH");
      expect(opts.body).toBeInstanceOf(Blob);
    });

    it("should JSON.stringify plain objects", async () => {
      const data = { field: "value" };

      await api.patch("/partial-update", data);

      const [, opts] = getCallByPath("/partial-update");
      expect(opts.method).toBe("PATCH");
      expect(typeof opts.body).toBe("string");
      expect(opts.body).toBe(JSON.stringify(data));
    });
  });

  describe("Content-Type header handling", () => {
    it("should not set Content-Type for FormData", async () => {
      const formData = new FormData();
      formData.append("file", new Blob(["test"]));

      await api.post("/upload", formData);

      const [, opts] = getCallByPath("/upload");
      const headers = opts.headers as Headers;

      // Content-Type should not be set (browser sets it with boundary)
      expect(headers.get("Content-Type")).toBeNull();
    });

    it("should not set Content-Type for Blob", async () => {
      const blob = new Blob(["test"], { type: "application/octet-stream" });

      await api.post("/upload", blob);

      const [, opts] = getCallByPath("/upload");
      const headers = opts.headers as Headers;

      // Content-Type should not be set for Blob
      expect(headers.get("Content-Type")).toBeNull();
    });

    it("should set Content-Type for JSON", async () => {
      const data = { test: "value" };

      await api.post("/data", data);

      const [, opts] = getCallByPath("/data");
      const headers = opts.headers as Headers;

      expect(headers.get("Content-Type")).toBe("application/json");
    });

    it("should pass URLSearchParams as-is without Content-Type", async () => {
      const params = new URLSearchParams();
      params.append("key1", "value1");
      params.append("key2", "value2");

      await api.post("/form-urlencoded", params);

      const [, opts] = getCallByPath("/form-urlencoded");
      const headers = opts.headers as Headers;

      // URLSearchParams should be sent as-is
      expect(opts.body).toBeInstanceOf(URLSearchParams);
      // Content-Type should not be auto-set (browser will set application/x-www-form-urlencoded)
      expect(headers.get("Content-Type")).toBeNull();
    });

    it("should pass Uint8Array/TypedArray without Content-Type and preserve binary body", async () => {
      const buffer = new Uint8Array([0x48, 0x65, 0x6c, 0x6c, 0x6f]); // "Hello" in bytes

      await api.post("/binary-data", buffer);

      const [, opts] = getCallByPath("/binary-data");
      const headers = opts.headers as Headers;

      // Uint8Array should remain binary (ArrayBufferView)
      expect(opts.body).toBeInstanceOf(Uint8Array);
      // Content-Type should not be auto-set for binary data
      expect(headers.get("Content-Type")).toBeNull();
      // Body should not be stringified
      expect(typeof opts.body).not.toBe("string");
    });

    it("should preserve Accept header when provided by caller", async () => {
      const data = { test: "value" };
      const customAccept = "application/vnd.api+json";

      await api.post("/data", data, {
        headers: { Accept: customAccept },
      });

      const [, opts] = getCallByPath("/data");
      const headers = opts.headers as Headers;

      // Custom Accept header should be preserved, not overwritten
      expect(headers.get("Accept")).toBe(customAccept);
      // Content-Type should still be set for JSON
      expect(headers.get("Content-Type")).toBe("application/json");
    });
  });

  describe("Binary response handling", () => {
    it("should handle binary responses (application/octet-stream)", async () => {
      const binaryData = new Uint8Array([0x89, 0x50, 0x4e, 0x47]); // PNG header
      const blob = new Blob([binaryData], { type: "application/octet-stream" });

      mockCsrfFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/octet-stream" }),
        blob: async () => blob,
      });

      const response = await api.get<Blob>("/download/binary");

      expect(response.data).toBeInstanceOf(Blob);
      expect(response.error).toBeNull();
    });

    it("should handle PDF responses", async () => {
      const pdfBlob = new Blob(["%PDF-1.4"], { type: "application/pdf" });

      mockCsrfFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/pdf" }),
        blob: async () => pdfBlob,
      });

      const response = await api.get<Blob>("/download/document.pdf");

      expect(response.data).toBeInstanceOf(Blob);
      expect(response.error).toBeNull();
    });

    it("should handle image responses", async () => {
      const imageBlob = new Blob(["fake-image-data"], { type: "image/png" });

      mockCsrfFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "image/png" }),
        blob: async () => imageBlob,
      });

      const response = await api.get<Blob>("/download/image.png");

      expect(response.data).toBeInstanceOf(Blob);
      expect(response.error).toBeNull();
    });

    it("should handle video responses", async () => {
      const videoBlob = new Blob(["fake-video-data"], { type: "video/mp4" });

      mockCsrfFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "video/mp4" }),
        blob: async () => videoBlob,
      });

      const response = await api.get<Blob>("/download/video.mp4");

      expect(response.data).toBeInstanceOf(Blob);
      expect(response.error).toBeNull();
    });
  });
});
