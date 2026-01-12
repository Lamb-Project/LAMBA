<script>
	import '../../app.css';
	import AdminNav from '$lib/components/AdminNav.svelte';
	import { onMount } from 'svelte';
	import { initI18n } from '$lib/i18n';
	import { page } from '$app/stores';
	import { adminAuth } from '$lib/admin';
	import { goto } from '$app/navigation';

	let { children } = $props();
	let i18nReady = $state(false);
	let username = $state('');
	let isLoggedIn = $state(false);

	// Check if we're on the login page
	let isLoginPage = $derived($page.url.pathname === '/admin');

	async function ensureSession() {
		try {
			const session = await adminAuth.checkSession();
			if (session?.success) {
				isLoggedIn = true;
				username = session.username || 'Admin';
			}
		} catch (error) {
			console.error('Session check error:', error);
		}
	}

	// Initialize i18n before mounting
	onMount(async () => {
		await initI18n();
		i18nReady = true;
		await ensureSession();
	});

	// Re-check session when navigating away from login if not yet loaded
	$effect(() => {
		const onLoginPage = $page.url.pathname === '/admin';
		if (!onLoginPage && !isLoggedIn) {
			ensureSession();
		}
	});

	async function handleLogout() {
		try {
			await adminAuth.logout();
			isLoggedIn = false;
			goto('/admin');
		} catch (error) {
			console.error('Logout error:', error);
		}
	}
</script>

{#if i18nReady}
	<div class="min-h-screen bg-gray-50">
		<AdminNav 
			showUserInfo={!isLoginPage} 
			showNavLinks={!isLoginPage}
			username={username}
			onLogout={isLoggedIn ? handleLogout : null}
		/>
		{@render children()}
	</div>
{/if}
