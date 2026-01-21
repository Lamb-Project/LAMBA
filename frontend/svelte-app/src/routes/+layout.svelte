<script>
	import '../app.css';
	import Nav from '$lib/components/Nav.svelte';
	import { onMount } from 'svelte';
	import { initI18n, locale } from '$lib/i18n';
	import { isLoading } from 'svelte-i18n';
	import { page } from '$app/stores';
	import { initLTISession, ltiAwareFetch } from '$lib/auth.js';

	let { children } = $props();
	let ltiData = $state(null);
	let i18nReady = $state(false);

	// Check if we're in admin routes
	let isAdminRoute = $derived($page.url.pathname.startsWith('/admin'));

	// Initialize LTI session from URL (for iframe cookie fallback)
	onMount(() => {
		initLTISession();
	});

	// Initialize i18n before mounting
	onMount(async () => {
		await initI18n();
		i18nReady = true;
	});

	// Update HTML lang attribute when locale changes
	$effect(() => {
		if (typeof document !== 'undefined' && $locale) {
			document.documentElement.lang = $locale;
		}
	});

	// Fetch LTI data for the nav (only if not in admin routes)
	onMount(async () => {
		// Skip LTI data fetch if we're in admin routes
		if (isAdminRoute) {
			return;
		}
		
		try {
			const response = await ltiAwareFetch('/api/lti-data');
			
			if (response.ok) {
				const result = await response.json();
				if (result.success) {
					ltiData = result.data;
				}
			}
		} catch (err) {
			console.error('Error fetching LTI data for nav:', err);
		}
	});
</script>

{#if i18nReady && !$isLoading}
	<div class="min-h-screen bg-gray-50">
		{#if !isAdminRoute}
			<Nav {ltiData} />
			<main class="py-6">
				{@render children()}
			</main>
		{:else}
			{@render children()}
		{/if}
	</div>
{:else}
	<!-- Loading screen while i18n initializes -->
	<div class="min-h-screen bg-gray-50 flex items-center justify-center">
		<div class="text-center">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-[#2271b3] mx-auto"></div>
		</div>
	</div>
{/if}
