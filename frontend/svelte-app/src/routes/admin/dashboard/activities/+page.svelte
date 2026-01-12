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
    { key: 'title', label: $_('admin.columns.title'), width: '200px' },
    { key: 'activity_type', label: $_('admin.columns.activityType'), width: '100px' },
    { key: 'course_id', label: $_('admin.columns.course'), width: '150px' },
    { key: 'creator_id', label: $_('admin.columns.creator'), width: '100px' },
    { key: 'created_at', label: $_('admin.columns.createdAt'), width: '180px' }
  ];

  onMount(async () => {
    try {
      const response = await adminAPI.getActivities();
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
  title={$_('admin.nav.activities')}
  icon="✏️"
  {data}
  {columns}
  {loading}
  {error}
/>
