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
    { key: 'student_id', label: $_('admin.columns.student'), width: '120px' },
    { key: 'activity_id', label: $_('admin.columns.activity'), width: '150px' },
    { key: 'joined_at', label: $_('admin.columns.joinedAt'), width: '180px' },
    { key: 'sent_to_moodle', label: $_('admin.columns.sent'), width: '80px' },
    { key: 'sent_to_moodle_at', label: $_('admin.columns.sentAt'), width: '180px' }
  ];

  onMount(async () => {
    try {
      const response = await adminAPI.getSubmissions();
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
  title={$_('admin.nav.submissions')}
  icon="📤"
  {data}
  {columns}
  {loading}
  {error}
/>
