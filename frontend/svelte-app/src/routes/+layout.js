import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';

/** @type {import('./$types').LayoutLoad} */
export const load = async ({ url }) => {
  // Only run redirection logic in the browser and not for the root path
  if (browser && url.pathname !== '/') {
    try {
      // Fetch LTI data to check user role
      const response = await fetch('/api/lti-data', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.success && result.data.roles) {
          const roles = result.data.roles.toLowerCase();
          const isStudent = roles.includes('learner') || roles.includes('student');
          
          // If user is a student and trying to access any route other than root, redirect to root
          if (isStudent) {
            throw redirect(302, '/');
          }
        }
      }
    } catch (error) {
      // If it's already a redirect, let it through
      if (error?.status === 302) {
        throw error;
      }
      // For other errors, continue normally
      console.warn('Error checking user role for redirection:', error);
    }
  }
  
  return {};
}; 