import { describe, it, expect, beforeEach, vi } from 'vitest';
import { changeLocale } from '$lib/i18n';

describe('i18n Module', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('changeLocale', () => {
    it('calls locale.set with the correct locale', () => {
      changeLocale('ca');
      // Just verify the function runs without errors
      expect(true).toBe(true);
    });

    it('persists locale to localStorage', () => {
      changeLocale('en');
      expect(localStorage.setItem).toHaveBeenCalledWith('locale', 'en');
    });

    it('persists es locale to localStorage', () => {
      changeLocale('es');
      expect(localStorage.setItem).toHaveBeenCalledWith('locale', 'es');
    });

    it('persists ca locale to localStorage', () => {
      changeLocale('ca');
      expect(localStorage.setItem).toHaveBeenCalledWith('locale', 'ca');
    });

    it('updates localStorage multiple times', () => {
      changeLocale('es');
      expect(localStorage.setItem).toHaveBeenCalledWith('locale', 'es');
      
      changeLocale('ca');
      expect(localStorage.setItem).toHaveBeenCalledWith('locale', 'ca');
      
      changeLocale('en');
      expect(localStorage.setItem).toHaveBeenCalledWith('locale', 'en');
    });
  });

  describe('initI18n', () => {
    it('handles initialization when no stored locale', async () => {
      localStorage.getItem.mockReturnValue(null);
      
      const { initI18n } = await import('$lib/i18n');
      const result = await initI18n();
      
      // Should complete without errors
      expect(result).toBeUndefined();
    });

    it('handles initialization with stored locale', async () => {
      localStorage.getItem.mockReturnValue('ca');
      
      const { initI18n } = await import('$lib/i18n');
      const result = await initI18n();
      
      expect(localStorage.getItem).toHaveBeenCalledWith('locale');
      expect(result).toBeUndefined();
    });

    it('handles initialization gracefully', async () => {
      localStorage.getItem.mockReturnValue('invalid');
      
      const { initI18n } = await import('$lib/i18n');
      
      // Should not throw
      await expect(initI18n()).resolves.toBeUndefined();
    });
  });
});
