<script>
  import { _, locale } from 'svelte-i18n';

  export let title = '';
  export let icon = '';
  export let data = [];
  export let columns = [];
  export let loading = false;
  export let error = '';

  let currentLocale = 'es';

  $: currentLocale = $locale || 'es';

  function getNestedValue(obj, path) {
    return path.split('.').reduce((current, prop) => current?.[prop], obj);
  }

  function formatValue(value) {
    if (value === null || value === undefined) {
      return '-';
    }
    if (typeof value === 'boolean') {
      return value ? $_('admin.table.yes') : $_('admin.table.no');
    }
    
    // Try to parse as date if it looks like a date string
    if (typeof value === 'string') {
      // Check if it's an ISO date string
      if (value.includes('T') && (value.includes('Z') || value.match(/[+-]\d{2}:\d{2}$/))) {
        try {
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            return date.toLocaleString(currentLocale);
          }
        } catch (e) {
          // Fall through to return as string
        }
      }
      // Return as-is if not a date
      return value;
    }
    
    if (value instanceof Date) {
      if (!isNaN(value.getTime())) {
        return value.toLocaleString(currentLocale);
      }
      return '-';
    }
    
    if (typeof value === 'number') {
      // Check if it looks like a timestamp (in milliseconds)
      if (value > 1000000000000 && value < 9999999999999) {
        try {
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            return date.toLocaleString(currentLocale);
          }
        } catch (e) {
          return value.toString();
        }
      }
      return value.toString();
    }
    
    return String(value);
  }
</script>

<div class="bg-white rounded-lg shadow overflow-hidden">
  <!-- Header -->
  <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
    <h2 class="text-lg font-medium text-gray-900 flex items-center gap-2">
      {#if icon}
        <span class="text-2xl">{icon}</span>
      {/if}
      {title}
    </h2>
    <span class="text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded-full">
      {$_('admin.table.count', { values: { count: data.length } })}
    </span>
  </div>

  {#if error}
    <div class="px-6 py-4 bg-red-50 border-t border-red-200">
      <p class="text-sm text-red-800">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="px-6 py-12 flex justify-center">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand"></div>
    </div>
  {:else if data.length === 0}
    <div class="px-6 py-12 text-center text-gray-500">
      <p>{$_('admin.table.noData')}</p>
    </div>
  {:else}
    <!-- Table -->
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            {#each columns as column}
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                {column.label}
              </th>
            {/each}
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          {#each data as row}
            <tr class="hover:bg-gray-50">
              {#each columns as column}
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  <div class="max-w-xs overflow-hidden text-ellipsis" title={formatValue(getNestedValue(row, column.key))}>
                    {formatValue(getNestedValue(row, column.key))}
                  </div>
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
