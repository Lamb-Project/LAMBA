<script>
  import { base } from '$app/paths';
  import { page } from '$app/stores';
  import LanguageSelector from '$lib/components/LanguageSelector.svelte';
  import { _ } from 'svelte-i18n';
  
  let { 
    showUserInfo = true, 
    showNavLinks = true,
    username = '', 
    onLogout = null 
  } = $props();

  const primaryNav = [
    { key: 'statistics', href: '/admin/dashboard' },
    { key: 'moodleInstances', href: '/admin/dashboard/moodle' }
  ];

  const secondaryNav = [
    { key: 'courses', href: '/admin/dashboard/courses' },
    { key: 'activities', href: '/admin/dashboard/activities' },
    { key: 'users', href: '/admin/dashboard/users' },
    { key: 'submissions', href: '/admin/dashboard/submissions' },
    { key: 'files', href: '/admin/dashboard/files' },
    { key: 'grades', href: '/admin/dashboard/grades' }
  ];

  let moreOpen = $state(false);

  const isActive = (path) => {
    // Exact match for dashboard home
    if (path === '/admin/dashboard') {
      return $page.url.pathname === '/admin/dashboard';
    }
    // Starts with for other paths
    return $page.url.pathname.startsWith(path);
  };
  const isMoreActive = () => secondaryNav.some((item) => isActive(item.href));

  function toggleMore() {
    moreOpen = !moreOpen;
  }
</script>

<nav class="bg-white shadow">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <div class="flex">
        <!-- Logo -->
        <div class="flex-shrink-0 flex items-center">
          <div class="flex items-center space-x-2">
            <!-- Image path updated to be relative to static dir -->
            <img src="{base}/img/lamb_1.png" alt="LAMB Logo" class="h-14">
            <div>
              <div class="text-lg font-bold">
                <span>{$_('nav.title')}</span> 
                <span class="text-xs bg-gray-200 px-1 py-0.5 rounded">v1.0</span>
              </div>
              <span class="text-xs text-gray-600">{$_('nav.subtitle')}</span>
            </div>
          </div>
        </div>

        {#if showNavLinks}
          <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
            {#each primaryNav as item}
              <a
                href={item.href}
                class={
                  isActive(item.href)
                    ? 'inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium border-[#2271b3] text-gray-900'
                    : 'inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }
              >
                {$_('admin.nav.' + item.key)}
              </a>
            {/each}

            <div class="relative tools-menu h-full flex items-center">
              <button
                aria-haspopup="true"
                aria-expanded={moreOpen ? 'true' : 'false'}
                onclick={toggleMore}
                class={
                  isMoreActive()
                    ? 'inline-flex items-center h-full px-1 border-b-2 text-sm font-medium focus:outline-none border-[#2271b3] text-gray-900'
                    : 'inline-flex items-center h-full px-1 border-b-2 text-sm font-medium focus:outline-none border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }
                aria-disabled="false"
              >
                {$_('admin.nav.more')}
                <svg
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  class={`ml-1 h-4 w-4 transition-transform duration-200 ${moreOpen ? 'rotate-180' : ''}`}
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>
              {#if moreOpen}
                <div class="absolute z-[100] left-0 top-full mt-0 w-52 bg-white border border-gray-200 rounded-b-md shadow-lg">
                  <div class="py-2">
                    {#each secondaryNav as item}
                      <a
                        href={item.href}
                        class={
                          isActive(item.href)
                            ? 'block px-4 py-3 text-sm font-medium text-gray-700 hover:text-[#2271b3] hover:bg-gray-50 transition-colors duration-150 bg-blue-50 text-[#2271b3]'
                            : 'block px-4 py-3 text-sm font-medium text-gray-700 hover:text-[#2271b3] hover:bg-gray-50 transition-colors duration-150'
                        }
                      >
                            {$_('admin.nav.' + item.key)}
                      </a>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <!-- User info and language selector section -->
      <div class="flex items-center space-x-4 ml-4 shrink-0">
        <!-- Language Selector -->
        <LanguageSelector />
        
        <!-- User info -->
        {#if showUserInfo}
          <div class="text-right">
            <div class="flex items-center justify-end space-x-2">
              <div class="text-sm font-medium text-gray-700">
                {username}
              </div>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[#2271b3] text-white">
                  {$_('admin.nav.admin')}
              </span>
            </div>
          </div>
          {#if onLogout}
            <button
              onclick={onLogout}
              class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
                {$_('admin.nav.logout')}
            </button>
          {/if}
        {/if}
      </div>
    </div>
  </div>
</nav>
