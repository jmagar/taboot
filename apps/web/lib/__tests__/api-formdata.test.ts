/**
 * Tests for FormData/Blob handling in CsrfAwareAPIClient
 */

import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";

// Mock the csrf-client module
vi.mock("../csrf-client", () => ({
  csrfFetch: vi.fn(),
}));

// Mock the TabootAPIClient
vi.mock("@taboot/api-client", () => ({
  TabootAPIClient: class MockTabootAPIClient {
    constructor(_config?: unknown) {
      // Mock constructor
    }
  },
}));

import { api } from "../api";
import { csrfFetch } from "../csrf-client";

describe("CsrfAwareAPIClient FormData/Blob handling", () => {
  const mockCsrfFetch = csrfFetch as Mock;

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

      // Verify body is the exact FormData instance
      const callArgs = mockCsrfFetch.mock.calls[0];
      expect(callArgs[1].body).toBeInstanceOf(FormData);
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

      const callArgs = mockCsrfFetch.mock.calls[0];
      expect(callArgs[1].body).toBeInstanceOf(Blob);
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

      const callArgs = mockCsrfFetch.mock.calls[0];
      expect(callArgs[1].body).toBeInstanceOf(ArrayBuffer);
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

      const callArgs = mockCsrfFetch.mock.calls[0];
      expect(typeof callArgs[1].body).toBe("string");
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

      const callArgs = mockCsrfFetch.mock.calls[0];
      expect(callArgs[1].method).toBe("PUT");
      expect(callArgs[1].body).toBeInstanceOf(FormData);
    });

    it("should JSON.stringify plain objects", async () => {
      const data = { field: "value" };

      await api.put("/update", data);

      const callArgs = mockCsrfFetch.mock.calls[0];
      expect(callArgs[1].method).toBe("PUT");
      expect(typeof callArgs[1].body).toBe("string");
      expect(callArgs[1].body).toBe(JSON.stringify(data));
    });
  });

  describe("PATCH method", () => {
    it("should pass FormData directly without JSON.stringify", async () => {
      const formData = new FormData();
      formData.append("field", "value");

      await api.patch("/partial-update", formData);

      const callArgs = mockCsrfFetch.mock.calls[0];
      expect(callArgs[1].method).toBe("PATCH");
      expect(callArgs[1].body).toBeInstanceOf(FormData);
    });

    it("should pass Blob directly without JSON.stringify", async () => {
      const blob = new Blob(["patch content"], { type: "application/octet-stream" });

      await api.patch("/partial-update-blob", blob);

      const callArgs = mockCsrfFetch.mock.calls[0];
      expect(callArgs[1].method).toBe("PATCH");
      expect(callArgs[1].body).toBeInstanceOf(Blob);
    });

    it("should JSON.stringify plain objects", async () => {
      const data = { field: "value" };

      await api.patch("/partial-update", data);

      const callArgs = mockCsrfFetch.mock.calls[0];
      expect(callArgs[1].method).toBe("PATCH");
      expect(typeof callArgs[1].body).toBe("string");
      expect(callArgs[1].body).toBe(JSON.stringify(data));
    });
  });

  describe("Content-Type header handling", () => {
    it("should not set Content-Type for FormData", async () => {
      const formData = new FormData();
      formData.append("file", new Blob(["test"]));

      await api.post("/upload", formData);

      const callArgs = mockCsrfFetch.mock.calls[0];
      const headers = callArgs[1].headers as Headers;

      // Content-Type should not be set (browser sets it with boundary)
      expect(headers.get("Content-Type")).toBeNull();
    });

    it("should not set Content-Type for Blob", async () => {
      const blob = new Blob(["test"], { type: "application/octet-stream" });

      await api.post("/upload", blob);

      const callArgs = mockCsrfFetch.mock.calls[0];
      const headers = callArgs[1].headers as Headers;

      // Content-Type should not be set for Blob
      expect(headers.get("Content-Type")).toBeNull();
    });

    it("should set Content-Type for JSON", async () => {
      const data = { test: "value" };

      await api.post("/data", data);

      const callArgs = mockCsrfFetch.mock.calls[0];
      const headers = callArgs[1].headers as Headers;

      expect(headers.get("Content-Type")).toBe("application/json");
    });
  });
});
