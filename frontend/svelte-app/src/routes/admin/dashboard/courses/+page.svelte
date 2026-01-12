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
    { key: 'id', label: $_('admin.columns.id'), width: '150px' },
    { key: 'moodle_id', label: $_('admin.columns.moodleInstance'), width: '150px' },
    { key: 'title', label: $_('admin.columns.title'), width: '250px' },
    { key: 'created_at', label: $_('admin.columns.createdAt'), width: '180px' }
  ];

  onMount(async () => {
    try {
      const response = await adminAPI.getCourses();
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
  title={$_('admin.nav.courses')}
  icon="📚"
  {data}
  {columns}
  {loading}
  {error}
/>
