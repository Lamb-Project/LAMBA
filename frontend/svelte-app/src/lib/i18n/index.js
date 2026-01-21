import { register, init, getLocaleFromNavigator, locale, waitLocale } from 'svelte-i18n';

// Register translations
register('en', () => import('./locales/en.json'));
register('es', () => import('./locales/es.json'));
register('ca', () => import('./locales/ca.json'));
register('eu', () => import('./locales/eu.json'));

// Initialize i18n
export async function initI18n() {
  // Get stored locale or default to browser/English
  const storedLocale = typeof window !== 'undefined' ? localStorage.getItem('locale') : null;
  const browserLocale = getLocaleFromNavigator();
  // Map browser locale to supported locales
  const supportedLocales = ['en', 'es', 'ca', 'eu'];
  const shortBrowserLocale = browserLocale?.split('-')[0];
  const detectedLocale = supportedLocales.includes(shortBrowserLocale) ? shortBrowserLocale : 'en';
  const fallbackLocale = storedLocale || detectedLocale;
  
  await init({
    fallbackLocale: 'en',
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

