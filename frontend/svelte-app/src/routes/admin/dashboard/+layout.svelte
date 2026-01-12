<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { adminAuth } from '$lib/admin';

  let isLoggedIn = false;
  let loading = true;

  onMount(async () => {
    try {
      const session = await adminAuth.checkSession();
      if (!session?.success) {
        goto('/admin');
      } else {
        isLoggedIn = true;
      }
    } catch (error) {
      goto('/admin');
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <div class="flex items-center justify-center min-h-screen bg-gray-50">
    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-brand"></div>
  </div>
{:else if isLoggedIn}
  <main class="max-w-7xl mx-auto px-4 py-6 md:px-6 lg:px-8">
    <slot />
  </main>
{/if}
