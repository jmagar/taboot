import { TabootAPIClient, APIError } from '@taboot/api-client';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('TabootAPIClient', () => {
  let client: TabootAPIClient;
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    client = new TabootAPIClient({
      baseUrl: 'http://localhost:8000',
      credentials: 'include',
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetAllMocks();
  });

  describe('GET requests', () => {
    it('should make GET request with correct URL and credentials', async () => {
      const mockData = { data: { id: 1, name: 'Test' }, error: null };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await client.get('/api/test');

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/test', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
      });
      expect(result).toEqual(mockData);
    });

    it('should handle successful responses', async () => {
      const mockData = { data: { message: 'success' }, error: null };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await client.get('/health');

      expect(result.data).toEqual({ message: 'success' });
      expect(result.error).toBeNull();
    });
  });

  describe('POST requests', () => {
    it('should make POST request with JSON body', async () => {
      const mockData = { data: { id: 1 }, error: null };
      const payload = { name: 'Test', value: 123 };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await client.post('/api/items', payload);

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/items', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(payload),
      });
    });
  });

  describe('Error handling', () => {
    it('should throw APIError for non-ok responses with error field', async () => {
      const mockResponse = {
        ok: false,
        status: 400,
        json: vi.fn(async () => ({ data: null, error: 'Bad request' })),
      };
      mockFetch.mockResolvedValueOnce(mockResponse);

      await expect(client.get('/api/error')).rejects.toThrow(APIError);

      // Reset for second call
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: vi.fn(async () => ({ data: null, error: 'Bad request' })),
      });
      await expect(client.get('/api/error')).rejects.toThrow('Bad request');
    });

    it('should throw APIError for non-ok responses without error field', async () => {
      const mockResponse = {
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: vi.fn(async () => ({})),
      };
      mockFetch.mockResolvedValueOnce(mockResponse);

      await expect(client.get('/api/missing')).rejects.toThrow(APIError);

      // Reset for second call
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: vi.fn(async () => ({})),
      });
      await expect(client.get('/api/missing')).rejects.toThrow('Not Found');
    });

    it('should throw APIError for network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(client.get('/api/network-fail')).rejects.toThrow(APIError);

      // Reset for second call
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      await expect(client.get('/api/network-fail')).rejects.toThrow('Network error');
    });

    it('should include status code in APIError', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: vi.fn(async () => ({ data: null, error: 'Server error' })),
      });

      try {
        await client.get('/api/error');
      } catch (error) {
        expect(error).toBeInstanceOf(APIError);
        if (error instanceof APIError) {
          expect(error.status).toBe(500);
          expect(error.message).toBe('Server error');
        }
      }
    });
  });

  describe('Other HTTP methods', () => {
    it('should make PUT request', async () => {
      const mockData = { data: { updated: true }, error: null };
      const payload = { name: 'Updated' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await client.put('/api/items/1', payload);

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/items/1', {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(payload),
      });
    });

    it('should make PATCH request', async () => {
      const mockData = { data: { patched: true }, error: null };
      const payload = { field: 'value' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await client.patch('/api/items/1', payload);

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/items/1', {
        method: 'PATCH',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(payload),
      });
    });

    it('should make DELETE request', async () => {
      const mockData = { data: { deleted: true }, error: null };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await client.delete('/api/items/1');

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/items/1', {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
      });
    });
  });
});
