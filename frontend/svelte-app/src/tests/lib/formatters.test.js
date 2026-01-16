import { describe, it, expect, beforeEach, vi } from 'vitest';
import { formatDate, formatFileSize, formatDateForInput } from '$lib/i18n/formatters.js';
import { locale } from 'svelte-i18n';

describe('Formatters', () => {
  describe('formatDate', () => {
    beforeEach(() => {
      locale.set('es');
    });

    it('formats a date string correctly', () => {
      const date = '2024-12-25T15:30:00Z';
      const formatted = formatDate(date);
      
      // Should contain date components
      expect(formatted).toBeTruthy();
      expect(formatted.length).toBeGreaterThan(0);
    });

    it('formats with custom options', () => {
      const date = '2024-12-25T15:30:00Z';
      const formatted = formatDate(date, { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      });
      
      expect(formatted).toBeTruthy();
    });

    it('handles null date', () => {
      expect(formatDate(null)).toBe('');
    });

    it('handles undefined date', () => {
      expect(formatDate(undefined)).toBe('');
    });

    it('handles empty string', () => {
      expect(formatDate('')).toBe('');
    });

    it('formats date according to locale', () => {
      const date = '2024-12-25T15:30:00Z';
      
      locale.set('en');
      const enFormatted = formatDate(date);
      
      locale.set('es');
      const esFormatted = formatDate(date);
      
      // The formats might differ based on locale
      expect(enFormatted).toBeTruthy();
      expect(esFormatted).toBeTruthy();
    });

    it('handles Date objects', () => {
      const date = new Date('2024-12-25T15:30:00Z');
      const formatted = formatDate(date);
      
      expect(formatted).toBeTruthy();
      expect(formatted.length).toBeGreaterThan(0);
    });
  });

  describe('formatFileSize', () => {
    it('formats 0 bytes', () => {
      expect(formatFileSize(0)).toBe('0 Bytes');
    });

    it('formats bytes', () => {
      expect(formatFileSize(500)).toBe('500.00 Bytes');
    });

    it('formats kilobytes', () => {
      expect(formatFileSize(1024)).toBe('1.00 KB');
      expect(formatFileSize(2048)).toBe('2.00 KB');
    });

    it('formats megabytes', () => {
      expect(formatFileSize(1024 * 1024)).toBe('1.00 MB');
      expect(formatFileSize(5 * 1024 * 1024)).toBe('5.00 MB');
    });

    it('formats gigabytes', () => {
      expect(formatFileSize(1024 * 1024 * 1024)).toBe('1.00 GB');
      expect(formatFileSize(2 * 1024 * 1024 * 1024)).toBe('2.00 GB');
    });

    it('handles null', () => {
      expect(formatFileSize(null)).toBe('0 Bytes');
    });

    it('handles undefined', () => {
      expect(formatFileSize(undefined)).toBe('0 Bytes');
    });

    it('handles NaN', () => {
      expect(formatFileSize(NaN)).toBe('0 Bytes');
    });

    it('handles decimal values', () => {
      const result = formatFileSize(1536); // 1.5 KB
      expect(result).toBe('1.50 KB');
    });
  });

  describe('formatDateForInput', () => {
    it('formats date for datetime-local input', () => {
      const date = '2024-12-25T15:30:00Z';
      const formatted = formatDateForInput(date);
      
      // Should match YYYY-MM-DDTHH:mm format
      expect(formatted).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
    });

    it('handles Date objects', () => {
      const date = new Date(2024, 11, 25, 15, 30); // Month is 0-indexed
      const formatted = formatDateForInput(date);
      
      expect(formatted).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
      expect(formatted).toContain('2024-12-25');
      expect(formatted).toContain('15:30');
    });

    it('handles null', () => {
      expect(formatDateForInput(null)).toBe('');
    });

    it('handles undefined', () => {
      expect(formatDateForInput(undefined)).toBe('');
    });

    it('handles empty string', () => {
      expect(formatDateForInput('')).toBe('');
    });

    it('pads single digits correctly', () => {
      const date = new Date(2024, 0, 5, 9, 5); // Jan 5, 09:05
      const formatted = formatDateForInput(date);
      
      expect(formatted).toContain('2024-01-05'); // Month and day padded
      expect(formatted).toContain('09:05'); // Hours and minutes padded
    });

    it('preserves time correctly', () => {
      const date = new Date(2024, 11, 25, 23, 59); // 23:59
      const formatted = formatDateForInput(date);
      
      expect(formatted).toContain('23:59');
    });
  });
});
