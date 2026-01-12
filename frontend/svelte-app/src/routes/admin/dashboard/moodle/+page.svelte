<script>
  import { onMount } from 'svelte';
  import { adminAPI } from '$lib/admin';
  import DataTable from '$lib/components/DataTable.svelte';
  import { _ } from 'svelte-i18n';

  let data = [];
  let loading = true;
  let error = '';

  let columns = [];

  $: columns = [
    { key: 'id', label: $_('admin.columns.id'), width: '200px' },
    { key: 'name', label: $_('admin.columns.name'), width: '200px' },
    { key: 'lis_outcome_service_url', label: $_('admin.columns.serviceUrl'), width: '250px' },
    { key: 'created_at', label: $_('admin.columns.createdAt'), width: '180px' }
  ];

  onMount(async () => {
    try {
      const response = await adminAPI.getMoodleInstances();
      if (response.success) {
        data = response.data;
      }
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  });
</script>

<DataTable
  title={$_('admin.nav.moodleInstances')}
  icon="🎓"
  {data}
  {columns}
  {loading}
  {error}
/>
