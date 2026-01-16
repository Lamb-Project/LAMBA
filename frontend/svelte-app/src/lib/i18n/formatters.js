import { get } from 'svelte/store';
import { locale } from 'svelte-i18n';

/**
 * Format a date according to the current locale
 * @param {string|Date} dateString - The date to format
 * @param {object} options - Intl.DateTimeFormat options
 * @returns {string} Formatted date string
 */
export function formatDate(dateString, options = {}) {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const currentLocale = get(locale) || 'es';
  
  const defaultOptions = {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  };
  
  const mergedOptions = { ...defaultOptions, ...options };
  
  try {
    return date.toLocaleString(currentLocale, mergedOptions);
  } catch (error) {
    console.error('Error formatting date:', error);
    return date.toLocaleString('es-ES', mergedOptions);
  }
}

/**
 * Format file size in human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size string
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0 || isNaN(bytes)) return '0 Bytes';
  
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  
  return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
}

/**
 * Format a date for datetime-local input
 * The input datetime-local always works in local time, so we format in local time
 * @param {string|Date} dateString - The date to format (typically in UTC from backend)
 * @returns {string} Formatted date string (YYYY-MM-DDTHH:mm) in local time
 */
export function formatDateForInput(dateString) {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  // Use local methods because datetime-local input expects local time
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

