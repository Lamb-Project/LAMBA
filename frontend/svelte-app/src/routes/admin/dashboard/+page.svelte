<script>
  import { onMount } from 'svelte';
  import { adminAPI } from '$lib/admin';
  import { _, locale } from 'svelte-i18n';

  let statistics = null;
  let loading = true;
  let error = '';
  let currentLocale = 'es';

  $: currentLocale = $locale || 'es';

  $: stats = [
    { key: 'moodle_instances', labelKey: 'admin.dashboard.totalMoodle', icon: '🎓', color: 'bg-blue-50 border-blue-200' },
    { key: 'courses', labelKey: 'admin.dashboard.totalCourses', icon: '📚', color: 'bg-purple-50 border-purple-200' },
    { key: 'activities', labelKey: 'admin.dashboard.totalActivities', icon: '✏️', color: 'bg-pink-50 border-pink-200' },
    { key: 'users', labelKey: 'admin.dashboard.totalUsers', icon: '👥', color: 'bg-cyan-50 border-cyan-200' },
    { key: 'submissions', labelKey: 'admin.dashboard.totalSubmissions', icon: '📤', color: 'bg-green-50 border-green-200' },
    { key: 'files', labelKey: 'admin.dashboard.totalFiles', icon: '📁', color: 'bg-red-50 border-red-200' },
    { key: 'grades', labelKey: 'admin.dashboard.totalGrades', icon: '⭐', color: 'bg-yellow-50 border-yellow-200' }
  ];

  onMount(async () => {
    try {
      const response = await adminAPI.getStatistics();
      if (response.success) {
        statistics = response.data;
      }
    } catch (err) {
      error = $_('admin.dashboard.error');
    } finally {
      loading = false;
    }
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-3xl font-bold text-gray-900">{$_('admin.dashboard.title')}</h1>
    <p class="mt-2 text-gray-600">{$_('admin.dashboard.welcome')}</p>
  </div>

  {#if error}
    <div class="rounded-md bg-red-50 p-4 border border-red-200">
      <p class="text-sm font-medium text-red-800">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-brand"></div>
    </div>
  {:else if statistics}
    <!-- Statistics Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {#each stats as stat}
        <div class="bg-white rounded-lg shadow p-6 border-l-4 border-brand {stat.color}">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <span class="text-3xl">{stat.icon}</span>
            </div>
            <div class="ml-4">
              <p class="text-sm font-medium text-gray-600">{$_(stat.labelKey)}</p>
              <p class="text-2xl font-bold text-gray-900">
                {statistics[stat.key] || 0}
              </p>
            </div>
          </div>
        </div>
      {/each}
    </div>

    <!-- Summary Section -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-medium text-gray-900">{$_('admin.dashboard.overview')}</h2>
      </div>
      <div class="px-6 py-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p class="text-sm text-gray-600">{$_('admin.dashboard.totalEntities')}</p>
            <p class="text-3xl font-bold text-brand">
              {Object.values(statistics).reduce((a, b) => a + b, 0)}
            </p>
          </div>
          <div>
            <p class="text-sm text-gray-600">{$_('admin.dashboard.lastUpdate')}</p>
            <p class="text-lg font-medium text-gray-900">
              {new Date().toLocaleString(currentLocale)}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Stats -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-medium text-gray-900">{$_('admin.dashboard.detailedStats')}</h2>
      </div>
      <div class="divide-y divide-gray-200">
        {#each stats as stat}
          <div class="px-6 py-4 flex justify-between items-center">
            <div class="flex items-center">
              <span class="text-2xl mr-3">{stat.icon}</span>
              <span class="text-sm font-medium text-gray-700">{$_(stat.labelKey)}</span>
            </div>
            <span class="text-2xl font-bold text-gray-900">
              {statistics[stat.key] || 0}
            </span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
