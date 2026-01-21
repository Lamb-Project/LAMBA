// Authentication and authorization utilities

const LTI_SESSION_KEY = 'lti_session';

/**
 * Initialize LTI session from URL parameter (fallback for iframe cookie issues)
 * Should be called on app startup
 */
export function initLTISession() {
  if (typeof window === 'undefined') return;
  
  // Check if there's a session ID in the URL
  const urlParams = new URLSearchParams(window.location.search);
  const sessionFromUrl = urlParams.get('lti_session');
  
  if (sessionFromUrl) {
    // Store in sessionStorage for subsequent requests
    sessionStorage.setItem(LTI_SESSION_KEY, sessionFromUrl);
    
    // Clean the URL by removing the lti_session parameter
    urlParams.delete('lti_session');
    const newSearch = urlParams.toString();
    const newUrl = window.location.pathname + (newSearch ? '?' + newSearch : '') + window.location.hash;
    window.history.replaceState({}, '', newUrl);
    
    console.log('LTI session captured from URL and stored in sessionStorage');
  }
}

/**
 * Get the stored LTI session ID
 * @returns {string|null}
 */
export function getLTISessionId() {
  if (typeof window === 'undefined') return null;
  return sessionStorage.getItem(LTI_SESSION_KEY);
}

/**
 * Create fetch options with LTI session header
 * @param {RequestInit} options - Original fetch options
 * @returns {RequestInit} - Options with LTI session header added
 */
export function withLTISession(options = {}) {
  const sessionId = getLTISessionId();
  
  const headers = new Headers(options.headers || {});
  
  if (sessionId) {
    headers.set('X-LTI-Session', sessionId);
  }
  
  return {
    ...options,
    credentials: 'include',
    headers
  };
}

/**
 * Fetch wrapper that automatically includes LTI session
 * @param {string} url - URL to fetch
 * @param {RequestInit} options - Fetch options
 * @returns {Promise<Response>}
 */
export async function ltiAwareFetch(url, options = {}) {
  return fetch(url, withLTISession(options));
}

/**
 * Check if user has student role
 * @param {string} roles - LTI roles string
 * @returns {boolean}
 */
export function isStudentRole(roles) {
  if (!roles) return false;
  const rolesLower = roles.toLowerCase();
  return rolesLower.includes('learner') || rolesLower.includes('student');
}

/**
 * Check if user has teacher or admin role
 * @param {string} roles - LTI roles string
 * @returns {boolean}
 */
export function isTeacherOrAdminRole(roles) {
  if (!roles) return false;
  const rolesLower = roles.toLowerCase();
  return rolesLower.includes('administrator') || 
         rolesLower.includes('instructor') || 
         rolesLower.includes('teacher') || 
         rolesLower.includes('admin');
}

/**
 * Fetch current LTI session data
 * @returns {Promise<{success: boolean, data?: any, error?: string}>}
 */
export async function fetchLTIData() {
  try {
    const response = await ltiAwareFetch('/api/lti-data');
    
    if (!response.ok) {
      return {
        success: false,
        error: response.status === 401 ? 'No active LTI session' : 'Failed to fetch LTI data'
      };
    }

    const result = await response.json();
    
    if (result.success) {
      return {
        success: true,
        data: result.data
      };
    } else {
      return {
        success: false,
        error: 'Failed to retrieve LTI data'
      };
    }
  } catch (err) {
    return {
      success: false,
      error: 'Connection error'
    };
  }
}

/**
 * Check if teacher has a pending activity to create
 * @returns {Promise<{hasPendingActivity: boolean, resourceLinkId?: string}>}
 */
export async function checkPendingActivity() {
  try {
    const ltiResult = await fetchLTIData();
    
    if (!ltiResult.success || !isTeacherOrAdminRole(ltiResult.data?.roles)) {
      return { hasPendingActivity: false };
    }
    
    const resourceLinkId = ltiResult.data.resource_link_id;
    
    // If no resource_link_id, there's no pending activity
    if (!resourceLinkId) {
      return { hasPendingActivity: false };
    }
    
    // Check if the activity already exists
    try {
      const response = await ltiAwareFetch(`/api/activities/${resourceLinkId}`, {
        cache: 'no-cache' // Force fresh data
      });
      
      // If activity exists (200), no pending creation
      if (response.ok) {
        return { hasPendingActivity: false };
      }
      
      // If activity doesn't exist (404), there's a pending creation
      if (response.status === 404) {
        return { 
          hasPendingActivity: true, 
          resourceLinkId: resourceLinkId 
        };
      }
      
      // For other errors, assume no pending activity
      return { hasPendingActivity: false };
      
    } catch (error) {
      // On fetch error, assume no pending activity
      return { hasPendingActivity: false };
    }
    
  } catch (err) {
    return { hasPendingActivity: false };
  }
}