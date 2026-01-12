<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { adminAuth } from '$lib/admin';
  import { _ } from 'svelte-i18n';

  let username = '';
  let password = '';
  let loading = false;
  let error = '';

  onMount(async () => {
    // Check if already logged in
    const session = await adminAuth.checkSession();
    if (session?.success) {
      goto('/admin/dashboard');
    }
  });

  async function handleLogin(e) {
    e.preventDefault();
    error = '';
    loading = true;

    try {
      if (!username.trim() || !password.trim()) {
        error = $_('admin.login.errorCredentials');
        return;
      }

      await adminAuth.login(username, password);
      goto('/admin/dashboard');
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }
</script>

<main class="w-full mx-auto py-6 sm:px-6 lg:px-8 flex-grow">
  <div class="container mx-auto px-4 py-8">
    <!-- Login Form Container -->
    <div class="max-w-md mx-auto bg-white shadow-md rounded-lg overflow-hidden">
      <div class="p-6">
        <h2 class="text-2xl font-bold mb-6">{$_('admin.login.title')}</h2>
        
        <form class="space-y-4" on:submit={handleLogin}>
          <!-- Username Field -->
          <div class="space-y-2">
            <label for="username" class="block text-sm font-medium">{$_('admin.login.username')}</label>
            <input
              type="text"
              id="username"
              bind:value={username}
              required
              disabled={loading}
              class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-brand focus:border-brand"
            />
          </div>

          <!-- Password Field -->
          <div class="space-y-2">
            <label for="password" class="block text-sm font-medium">{$_('admin.login.password')}</label>
            <input
              type="password"
              id="password"
              bind:value={password}
              required
              disabled={loading}
              class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-brand focus:border-brand"
            />
          </div>

          <!-- Error Message -->
          {#if error}
            <div class="rounded-md bg-red-50 p-4 border border-red-200">
              <p class="text-sm font-medium text-red-800">{error}</p>
            </div>
          {/if}

          <!-- Submit Button -->
          <button
            type="submit"
            disabled={loading}
            class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#2271b3] hover:bg-[#195a91] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3] disabled:opacity-50"
          >
            <span>{loading ? $_('admin.login.loggingIn') : $_('admin.login.loginButton')}</span>
          </button>
        </form>
      </div>
    </div>
  </div>

  <!-- LAMB Logo Section -->
  <div class="text-center mt-8">
    <div class="mx-auto bg-[#e9ecef] p-4 rounded-lg" style="max-width: 400px;">
      <h2 class="text-3xl font-bold text-[#2271b3]">{$_('admin.login.brandName')}</h2>
      <p class="text-[#195a91]">{$_('admin.login.brandSubtitle')}</p>
    </div>
  </div>
</main>
