<script>
  import { locale } from 'svelte-i18n';
  import { changeLocale } from '$lib/i18n';
  
  let isOpen = $state(false);
  
  const languages = [
    { code: 'ca', name: 'Català', shortName: 'CA' },
    { code: 'es', name: 'Español', shortName: 'ES' },
    { code: 'en', name: 'English', shortName: 'EN' }
  ];
  
  function toggleDropdown() {
    isOpen = !isOpen;
  }
  
  function selectLanguage(code) {
    changeLocale(code);
    isOpen = false;
  }
  
  function handleClickOutside(event) {
    if (isOpen && !event.target.closest('.language-selector')) {
      isOpen = false;
    }
  }
  
  $effect(() => {
    if (typeof window !== 'undefined') {
      document.addEventListener('click', handleClickOutside);
      return () => {
        document.removeEventListener('click', handleClickOutside);
      };
    }
  });
  
  let currentLanguage = $derived(languages.find(lang => lang.code === $locale) || languages[1]);
</script>

<div class="language-selector relative inline-block">
  <button
    onclick={toggleDropdown}
    class="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-0 focus:ring-[#2271b3] transition-all shadow-sm"
    aria-label="Select language"
    aria-expanded={isOpen}
    title="Change language"
  >
    <svg 
      class="w-4 h-4 text-gray-600" 
      fill="none" 
      stroke="currentColor" 
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"></path>
    </svg>
    <span class="font-semibold">{currentLanguage.shortName}</span>
    <svg 
      class="w-3.5 h-3.5 text-gray-500 transition-transform {isOpen ? 'rotate-180' : ''}" 
      fill="none" 
      stroke="currentColor" 
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"></path>
    </svg>
  </button>
  
  {#if isOpen}
    <div class="absolute right-0 mt-2 w-40 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50 overflow-hidden">
      <div class="py-1" role="menu" aria-orientation="vertical">
        {#each languages as lang}
          <button
            onclick={() => selectLanguage(lang.code)}
            class="flex items-center justify-between w-full px-4 py-2.5 text-sm text-gray-700 hover:bg-[#2271b3] hover:text-white transition-colors {$locale === lang.code ? 'bg-[#2271b3]/5 font-medium' : ''}"
            role="menuitem"
          >
            <span>{lang.name}</span>
            {#if $locale === lang.code}
              <svg class="w-4 h-4 text-[#2271b3]" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
              </svg>
            {/if}
          </button>
        {/each}
      </div>
    </div>
  {/if}
</div>

