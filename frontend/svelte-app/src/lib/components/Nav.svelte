<script>
  import { page } from '$app/stores';
  import { base } from '$app/paths';
  import { onMount } from 'svelte';
  import { checkPendingActivity } from '../auth.js';
  import { _ } from 'svelte-i18n';
  
  // Props para recibir datos LTI
  let { ltiData = null } = $props();
  
  // State for pending activity
  let hasPendingActivity = $state(false);
  
  // Function to check if user has admin or teacher role
  function hasAdminOrTeacherRole(ltiData) {
    if (!ltiData || !ltiData.roles) return false;
    
    const roles = ltiData.roles.toLowerCase();
    return roles.includes('administrator') || 
           roles.includes('instructor') || 
           roles.includes('teacher') || 
           roles.includes('admin');
  }
  
  // Function to check if user has student role
  function hasStudentRole(ltiData) {
    if (!ltiData || !ltiData.roles) return false;
    
    const roles = ltiData.roles.toLowerCase();
    return roles.includes('learner') || roles.includes('student');
  }
  
  // Check for pending activity when component mounts and when ltiData changes
  onMount(async () => {
    await updatePendingActivity();
  });
  
  // Update pending activity status
  async function updatePendingActivity() {
    if (ltiData && hasAdminOrTeacherRole(ltiData)) {
      const result = await checkPendingActivity();
      hasPendingActivity = result.hasPendingActivity;
    } else {
      hasPendingActivity = false;
    }
  }
  
  // React to ltiData changes
  $effect(async () => {
    if (ltiData) {
      await updatePendingActivity();
    }
  });
  
  // React to page changes to refresh pending activity status
  $effect(async () => {
    // Re-check pending activity when the page changes
    if ($page.url.pathname && ltiData) {
      await updatePendingActivity();
    }
  });
</script>

<nav class="bg-white shadow">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-20">
      <div class="flex">
        <!-- Logo -->
        <div class="flex-shrink-0 flex items-center">
          <a href="https://lamb-project.org" target="_blank" rel="noopener noreferrer" class="flex items-center space-x-2 hover:opacity-80 transition-opacity">
            <!-- Image path updated to be relative to static dir -->
            <img src="{base}/img/lamba.jpg" alt="LAMBA Logo" class="h-20">
            <div>
              <div class="text-xl font-bold text-gray-900">
                <span>{$_('nav.title')}</span> 
                <span class="text-sm bg-gray-200 text-gray-700 px-1 py-0.5 rounded">v0.2</span>
              </div>
              <span class="text-sm text-gray-600">{$_('nav.subtitle')}</span>
            </div>
          </a>
        </div>
      </div>
      
      <!-- User info section -->
      <div class="flex items-center space-x-4">
        
        <!-- User info -->
        {#if ltiData}
          <div class="text-right">
            <div class="flex items-center justify-end space-x-2">
              <div class="text-sm font-medium text-gray-700">
                {ltiData.lis_person_name_full || ltiData.ext_user_username || ltiData.lis_person_contact_email_primary || $_('nav.user')}
              </div>
              {#if hasAdminOrTeacherRole(ltiData)}
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[#2271b3] text-white">
                  {ltiData.roles.includes('Administrator') || ltiData.roles.includes('administrator') ? $_('nav.roleAdmin') : $_('nav.roleTeacher')}
                </span>
              {:else if hasStudentRole(ltiData)}
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-600 text-white">
                  {$_('nav.roleStudent')}
                </span>
              {/if}
            </div>
            {#if ltiData.lis_person_contact_email_primary}
              <div class="text-xs text-gray-500">
                {ltiData.lis_person_contact_email_primary}
              </div>
            {/if}
          </div>
        {:else}
          <span class="text-sm text-gray-500">{$_('nav.userLoading')}</span>
        {/if}
      </div>
      
    </div>
  </div>
</nav>

<!-- Help container (temporarily disabled) -->
<!-- 
<div class="bg-gray-100 py-2">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex items-center">
      <input 
        type="text" 
        id="helpInput" 
        placeholder={$_('nav.helpPlaceholder')}
        class="flex-grow px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3]"
      >
      <button 
        id="helpButton" 
        class="ml-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-[#2271b3] hover:bg-[#195a91]"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd" />
        </svg>
        {$_('nav.helpButton')}
      </button>
    </div>
  </div>
</div>
--> 