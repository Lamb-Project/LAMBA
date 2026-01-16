// Authentication and authorization utilities

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
    const response = await fetch('/api/lti-data', {
      credentials: 'include'
    });
    
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
      const response = await fetch(`/api/activities/${resourceLinkId}`, {
        credentials: 'include',
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