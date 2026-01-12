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
    { key: 'file_name', label: $_('admin.columns.fileName'), width: '200px' },
    { key: 'file_size', label: $_('admin.columns.fileSize'), width: '120px' },
    { key: 'file_type', label: $_('admin.columns.fileType'), width: '120px' },
    { key: 'uploaded_by', label: $_('admin.columns.uploadedBy'), width: '120px' },
    { key: 'uploaded_at', label: $_('admin.columns.uploadedAt'), width: '180px' }
  ];

  onMount(async () => {
    try {
      const response = await adminAPI.getFiles();
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
  title={$_('admin.nav.files')}
  icon="📁"
  {data}
  {columns}
  {loading}
  {error}
/>
