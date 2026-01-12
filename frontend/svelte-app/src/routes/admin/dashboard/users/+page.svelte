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
    { key: 'full_name', label: $_('admin.columns.fullName'), width: '200px' },
    { key: 'email', label: $_('admin.columns.email'), width: '200px' },
    { key: 'role', label: $_('admin.columns.role'), width: '100px' },
    { key: 'created_at', label: $_('admin.columns.createdAt'), width: '180px' }
  ];

  onMount(async () => {
    try {
      const response = await adminAPI.getUsers();
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
  title={$_('admin.nav.users')}
  icon="👥"
  {data}
  {columns}
  {loading}
  {error}
/>
