import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import { fetchLTIData, isStudentRole, isTeacherOrAdminRole } from '$lib/auth.js';

/** @type {import('./$types').PageLoad} */
export async function load({ url }) {
  if (browser) {
    const ltiResult = await fetchLTIData();
    
    if (ltiResult.success) {
      // If user is a teacher/admin, check if activity already exists
      if (isTeacherOrAdminRole(ltiResult.data.roles)) {
        const resourceLinkId = ltiResult.data.resource_link_id;
        
        // Check if the activity already exists
        if (resourceLinkId) {
          try {
            const response = await fetch(`/api/activities/${resourceLinkId}`, {
              credentials: 'include'
            });
            
            // If activity exists, redirect to activity submissions page
            if (response.ok) {
              throw redirect(302, `/actividad/${resourceLinkId}`);
            }
            // If activity doesn't exist (404), stay on create page
          } catch (error) {
            // If it's already a redirect, let it through
            if (error && typeof error === 'object' && 'status' in error && error.status === 302) {
              throw error;
            }
            // For other errors, continue to create page
          }
        }
      }
      // If user is a student, stay on main page (will show student view)
    }
  }
  
  return {};
}
