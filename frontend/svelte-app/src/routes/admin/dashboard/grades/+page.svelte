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
    { key: 'id', label: $_('admin.columns.id'), width: '120px' },
    { key: 'file_submission_id', label: $_('admin.columns.submission'), width: '200px' },
    { key: 'score', label: $_('admin.columns.score'), width: '100px' },
    { key: 'comment', label: $_('admin.columns.comment'), width: '250px' },
    { key: 'created_at', label: $_('admin.columns.createdAt'), width: '180px' }
  ];

  onMount(async () => {
    try {
      const response = await adminAPI.getGrades();
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
  title={$_('admin.nav.grades')}
  icon="⭐"
  {data}
  {columns}
  {loading}
  {error}
/>
