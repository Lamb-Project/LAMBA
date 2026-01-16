import { register, init, getLocaleFromNavigator, locale, waitLocale } from 'svelte-i18n';

// Register translations
register('es', () => import('./locales/es.json'));
register('ca', () => import('./locales/ca.json'));
register('en', () => import('./locales/en.json'));

// Initialize i18n
export async function initI18n() {
  // Get stored locale or default to browser/Spanish
  const storedLocale = typeof window !== 'undefined' ? localStorage.getItem('locale') : null;
  const fallbackLocale = storedLocale || getLocaleFromNavigator() || 'es';
  
  await init({
    fallbackLocale: 'es',
    initialLocale: fallbackLocale,
  });
  
  // Wait for the locale to be loaded
  await waitLocale();
}

// Export locale store for reactivity
export { locale, waitLocale };

// Helper to change locale and persist preference
export function changeLocale(newLocale) {
  locale.set(newLocale);
  if (typeof window !== 'undefined') {
    localStorage.setItem('locale', newLocale);
  }
}

