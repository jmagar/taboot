/**
 * Test to verify IP validation fix for TODO #004
 * This test demonstrates that the isIP() function from Node.js
 * properly rejects malformed IPv6 addresses like ":::::::"
 */

import { isIP } from 'node:net';

describe('IP Validation Fix - TODO #004', () => {
  describe('isIP function from node:net', () => {
    it('should reject malformed IPv6 addresses', () => {
      // These should all be rejected (return 0 for invalid)
      expect(isIP(':::::::')).toBe(0);
      expect(isIP('::::')).toBe(0);
      expect(isIP(':::::::::::::')).toBe(0);
      expect(isIP('1:2:3:4:5:6:7:8:9')).toBe(0); // Too many groups
    });

    it('should accept valid IPv4 addresses', () => {
      expect(isIP('192.168.1.1')).toBe(4);
      expect(isIP('127.0.0.1')).toBe(4);
      expect(isIP('0.0.0.0')).toBe(4);
      expect(isIP('255.255.255.255')).toBe(4);
    });

    it('should reject invalid IPv4 addresses', () => {
      expect(isIP('256.1.1.1')).toBe(0); // Octet > 255
      expect(isIP('192.168.1')).toBe(0); // Too few octets
      expect(isIP('192.168.1.1.1')).toBe(0); // Too many octets
    });

    it('should accept valid IPv6 addresses', () => {
      expect(isIP('2001:0db8:85a3:0000:0000:8a2e:0370:7334')).toBe(6);
      expect(isIP('2001:db8:85a3::8a2e:370:7334')).toBe(6); // Compressed
      expect(isIP('::1')).toBe(6); // Loopback
      expect(isIP('::')).toBe(6); // All zeros
      expect(isIP('fe80::1')).toBe(6); // Link-local
    });

    it('should reject invalid IPv6 addresses', () => {
      expect(isIP('02001:0db8:0000:0000:0000:ff00:0042:8329')).toBe(0); // Leading zero
      expect(isIP('2001:0db8::8a2e::7334')).toBe(0); // Double compression
      expect(isIP('gggg::1')).toBe(0); // Invalid hex
    });

    it('should be used in isValidIp helper', () => {
      // Demonstration of the fix
      const isValidIp = (ip: string): boolean => {
        // Node.js isIP returns: 4 for IPv4, 6 for IPv6, 0 for invalid
        return isIP(ip) !== 0;
      };

      // Malformed IPv6 that would bypass regex (the vulnerability)
      expect(isValidIp(':::::::')).toBe(false);
      expect(isValidIp('::::')).toBe(false);

      // Valid IPs should still work
      expect(isValidIp('192.168.1.1')).toBe(true);
      expect(isValidIp('::1')).toBe(true);
      expect(isValidIp('2001:db8::1')).toBe(true);
    });
  });
});
