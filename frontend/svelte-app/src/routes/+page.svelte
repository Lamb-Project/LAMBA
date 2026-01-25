<script>
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { fetchLTIData, isStudentRole, isTeacherOrAdminRole, ltiAwareFetch } from '$lib/auth.js';
  import ActivityForm from '$lib/components/ActivityForm.svelte';
  import { _, locale } from 'svelte-i18n';
  import { formatDate, formatFileSize } from '$lib/i18n/formatters.js';

  let userRole = $state(null); // 'student', 'teacher', or 'unknown'
  let studentView = $state(null);
	let loading = $state(true);
	let error = $state(null);
  let uploading = $state(false);
  let uploadError = $state(null);
  let uploadSuccess = $state(null);
  
  // File upload
  let fileInput = $state();
  let selectedFile = $state(null);
  
  // Student note to professor
  let studentNote = $state('');
  
  // Group code submission
  let groupCode = $state('');
  let submittingCode = $state(false);
  let codeError = $state(null);
  let codeSuccess = $state(null);
  let groupMembers = $state([]);

  // Activities list (for teachers/admins)
  let courseInfo = $state(null);
  
  // Activity creation state for teachers
  let showErrorMessage = $state(false);
  let errorMessage = $state('');
  
  // Get initial title from LTI data (for Moodle integration)
  let initialTitle = $state('');

	onMount(async () => {
    try {
      const result = await fetchLTIData();
      
      if (result.success) {
        if (isTeacherOrAdminRole(result.data.roles)) {
          userRole = 'teacher';
          // Get initial title from LTI data for teachers
          initialTitle = result.data.resource_link_title || '';
          await loadCourseInfo();
        } else if (isStudentRole(result.data.roles)) {
          userRole = 'student';
          await loadStudentView();
        } else {
          userRole = 'unknown';
          throw new Error($_('errors.unknownRole'));
        }
      } else {
        throw new Error(result.error || $_('errors.connectionError'));
      }
    } catch (err) {
      error = err.message;
      console.error('Error:', err);
    } finally {
      loading = false;
    }
  });

  async function loadStudentView() {
    try {
      loading = true;
      // Obtener el activity_id de los datos LTI
      const ltiResponse = await ltiAwareFetch('/api/lti-data');
      const ltiData = await ltiResponse.json();
      const activityId = ltiData.data.resource_link_id;
      
      const response = await ltiAwareFetch(`/api/activities/${activityId}/view`);
			
			if (!response.ok) {
        if (response.status === 400) {
          throw new Error($_('errors.noActivityInfo'));
        } else if (response.status === 401) {
          throw new Error($_('errors.noSession'));
				} else {
          throw new Error(`${$_('common.error')}: ${response.status}`);
        }
      }

      studentView = await response.json();
      
      // Force UI language to activity's language (if activity exists and has a language set)
      if (studentView?.activity?.language) {
        const activityLang = studentView.activity.language;
        // Only change if it's a supported language
        if (['en', 'es', 'ca', 'eu'].includes(activityLang)) {
          locale.set(activityLang);
        }
      }
      
      // If student has a group submission, load group members
      if (studentView?.student_submission?.file_submission?.group_code) {
        await loadGroupMembers(studentView.student_submission.file_submission.group_code);
			}
		} catch (err) {
			error = err.message;
      console.error('Error loading student view:', err);
		} finally {
			loading = false;
		}
  }

  function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
      // Check file size (max 50MB)
      const maxSize = 50 * 1024 * 1024;
      if (file.size > maxSize) {
        uploadError = $_('activity.student.fileTooLarge');
        selectedFile = null;
        return;
      }
      selectedFile = file;
      uploadError = null;
    } else {
      selectedFile = null;
    }
  }

  async function submitDocument() {
    if (!selectedFile || !studentView?.activity?.id) {
      uploadError = $_('activity.student.selectFileError');
      return;
    }

    try {
      uploading = true;
      uploadError = null;
      uploadSuccess = null;

      const formData = new FormData();
      formData.append('file', selectedFile);
      // Add student note if provided
      if (studentNote.trim()) {
        formData.append('student_note', studentNote.trim());
      }

      const response = await ltiAwareFetch(`/api/activities/${studentView.activity.id}/submissions`, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (response.ok && result.success) {
        uploadSuccess = result.message;
        selectedFile = null;
        studentNote = ''; // Clear the note
        if (fileInput) {
          fileInput.value = '';
        }
        
        // Reload student view to show updated submission
        await loadStudentView();
      } else {
        uploadError = result.detail || $_('errors.connectionError');
      }
    } catch (err) {
      uploadError = $_('errors.connectionError');
      console.error('Error submitting document:', err);
    } finally {
      uploading = false;
    }
  }

  async function submitGroupCode() {
    if (!groupCode.trim() || !studentView?.activity?.id) {
      codeError = $_('activity.student.enterValidCode');
      return;
    }

    try {
      submittingCode = true;
      codeError = null;
      codeSuccess = null;

      const response = await ltiAwareFetch('/api/submissions/join', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          activity_id: studentView.activity.id,
          group_code: groupCode.trim().toUpperCase()
        })
      });

      const result = await response.json();

      if (response.ok && result.success) {
        codeSuccess = result.message;
        groupCode = '';
        
        // Reload student view to show updated submission
        await loadStudentView();
      } else {
        codeError = result.detail || $_('errors.connectionError');
      }
    } catch (err) {
      codeError = $_('errors.connectionError');
      console.error('Error submitting group code:', err);
    } finally {
      submittingCode = false;
    }
  }

  async function loadGroupMembers(code) {
    if (!code || !studentView?.student_submission?.file_submission?.id) return;
    
    try {
      const submissionId = studentView.student_submission.file_submission.id;
      const response = await ltiAwareFetch(`/api/submissions/${submissionId}/members`);

      if (response.ok) {
        const result = await response.json();
        groupMembers = result || [];
      }
    } catch (err) {
      console.error('Error loading group members:', err);
    }
  }

  // Functions for teachers/admins
  async function loadCourseInfo() {
    try {
      const ltiResult = await fetchLTIData();
      if (ltiResult.success) {
        courseInfo = {
          title: ltiResult.data.context_title,
          label: ltiResult.data.context_label
        };
      }
    } catch (err) {
      console.error('Error loading course info:', err);
    }
  }
  
  function handleSuccess(event) {
    const createdActivity = event.detail.activity;
    
    // Redirect immediately to the activity's submissions page
    if (createdActivity && createdActivity.id) {
      goto(`/actividad/${createdActivity.id}`);
    }
  }
  
  function handleError(event) {
    errorMessage = event.detail.message;
    showErrorMessage = true;
    
    // Hide error message after 5 seconds
    setTimeout(() => {
      showErrorMessage = false;
    }, 5000);
  }

</script>

<svelte:head>
  <title>{userRole === 'teacher' ? $_('activity.create.title') : $_('activity.student.title')} | LAMBA</title>
</svelte:head>

				{#if loading}
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="bg-white shadow rounded-lg">
      <div class="flex items-center justify-center py-12">
						<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#2271b3]"></div>
        <span class="ml-3 text-gray-600">{$_('common.loading')}</span>
      </div>
    </div>
					</div>
				{:else if error}
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="bg-white shadow rounded-lg">
      <div class="p-6">
					<div class="bg-red-50 border border-red-200 rounded-md p-4">
						<div class="flex">
							<div class="flex-shrink-0">
								<svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
									<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
								</svg>
							</div>
							<div class="ml-3">
								<h3 class="text-sm font-medium text-red-800">{$_('common.error')}</h3>
								<p class="text-sm text-red-700 mt-1">{error}</p>
							</div>
						</div>
					</div>
								</div>
								</div>
								</div>
{:else if userRole === 'teacher'}
  <!-- Teacher/Admin View - Create Activity -->
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Page Header -->
    <div class="mb-8">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">{$_('activity.create.title')}</h1>
          {#if courseInfo}
            <p class="mt-1 text-lg font-medium text-[#2271b3]">
              {courseInfo.title}
              {#if courseInfo.label && courseInfo.label !== courseInfo.title}
                <span class="text-sm text-gray-500 font-normal ml-2">({courseInfo.label})</span>
              {/if}
            </p>
          {/if}
        </div>
      </div>
    </div>
    
    <!-- Error Message -->
    {#if showErrorMessage}
      <div class="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="ml-3">
            <p class="text-sm font-medium text-red-800">
              {errorMessage}
            </p>
          </div>
        </div>
      </div>
    {/if}
    
    <!-- Activity Form -->
    <ActivityForm 
      initialTitle={initialTitle}
      on:success={handleSuccess}
      on:error={handleError}
    />
  </div>
{:else if userRole === 'student' && !studentView?.activity}
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <div class="bg-white shadow rounded-lg">
      <div class="p-6">
        <div class="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <h3 class="text-sm font-medium text-yellow-800">{$_('activity.student.notFound')}</h3>
              <p class="mt-1 text-sm text-yellow-700">
                {$_('activity.student.notFoundDescription')}
              </p>
            </div>
          </div>
        </div>
      </div>
							</div>
					</div>
				{:else}
  <!-- Student View - Activity Information and Submission -->
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <!-- Activity Information -->
    <div class="bg-white shadow rounded-lg mb-6">
      <div class="px-6 py-4 border-b border-gray-200">
        <h1 class="text-2xl font-bold text-gray-900">{studentView.activity.title}</h1>
      </div>
      
      <div class="p-6">
        <div class="prose max-w-none">
          <p class="text-gray-700 whitespace-pre-wrap">{studentView.activity.description}</p>
          {#if studentView.activity.activity_type === 'group' && studentView.activity.max_group_size}
            <div class="mt-4 p-3 bg-[#2271b3]/5 border border-[#2271b3]/20 rounded-md">
              <p class="text-sm text-[#2271b3]">
                <strong>{$_('activity.student.groupActivity')}:</strong> {$_('activity.student.maxMembers', { values: { count: studentView.activity.max_group_size } })}
              </p>
					</div>
				{/if}
			</div>
	</div>
</div>

    <!-- Submission Section -->
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-xl font-bold text-gray-900">
          {studentView.activity.activity_type === 'individual' ? $_('activity.student.submissionIndividual') : $_('activity.student.submissionGroup')}
        </h2>
        <p class="text-sm text-gray-600 mt-1">
            {$_('activity.student.deadline', { values: { date: formatDate(studentView.activity.deadline) } })}
        </p>
      </div>
      
      <div class="p-6">
        {#if studentView.student_submission}
          <!-- Existing Submission -->
          <div class="mb-6 p-4 bg-green-50 border border-green-200 rounded-md">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-green-800">
                  {studentView.student_submission.is_group_leader ? $_('activity.student.documentSentLeader') : 
                   studentView.activity.activity_type === 'group' ? $_('activity.student.joinedGroup') : $_('activity.student.documentSent')}
                </h3>
                <div class="mt-2 text-sm text-green-700">
                  <p><strong>{$_('activity.student.file')}:</strong> {studentView.student_submission.file_submission.file_name}</p>
                  <p><strong>{$_('activity.student.size')}:</strong> {formatFileSize(studentView.student_submission.file_submission.file_size)}</p>
                  <p><strong>{$_('activity.student.sent')}:</strong> {formatDate(studentView.student_submission.file_submission.uploaded_at)}</p>
                  
                  {#if studentView.activity.activity_type === 'group' && studentView.student_submission.file_submission.group_code && !studentView.student_submission.is_group_leader}
                    <p><strong>{$_('activity.student.groupCode')}:</strong> <span class="font-mono bg-gray-100 px-2 py-1 rounded">{studentView.student_submission.file_submission.group_code}</span></p>
                  {/if}
                </div>
              </div>
            </div>
          </div>
          
          <!-- Prominent Group Code Display for Group Leaders -->
          {#if studentView.activity.activity_type === 'group' && studentView.student_submission.file_submission.group_code && studentView.student_submission.is_group_leader}
            <div class="mb-6 p-6 bg-gradient-to-r from-amber-400 to-orange-400 rounded-xl shadow-lg border-4 border-amber-500">
              <div class="text-center">
                <div class="flex items-center justify-center mb-3">
                  <svg class="w-8 h-8 text-amber-900 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
                  </svg>
                  <h3 class="text-xl font-bold text-amber-900">{$_('activity.student.groupCode')}</h3>
                </div>
                
                <!-- Large Code Display -->
                <div class="bg-white rounded-lg p-4 mb-4 shadow-inner">
                  <p class="font-mono text-4xl font-black tracking-widest text-gray-900 select-all">
                    {studentView.student_submission.file_submission.group_code}
                  </p>
                </div>
                
                <!-- Copy Button -->
                <button
                  type="button"
                  onclick={() => {
                    navigator.clipboard.writeText(studentView.student_submission.file_submission.group_code);
                    // Show brief feedback
                    const btn = event.target;
                    const originalText = btn.innerText;
                    btn.innerText = '✓ ' + $_('activity.student.codeCopied');
                    setTimeout(() => { btn.innerText = originalText; }, 2000);
                  }}
                  class="inline-flex items-center px-6 py-3 bg-amber-900 text-white font-bold rounded-lg hover:bg-amber-800 focus:outline-none focus:ring-4 focus:ring-amber-300 transition-all transform hover:scale-105 shadow-md"
                >
                  <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path>
                  </svg>
                  {$_('activity.student.copyCode')}
                </button>
                
                <!-- Share Message -->
                <p class="mt-4 text-amber-900 font-semibold text-lg">
                  {$_('activity.student.shareCode')}
                </p>
                
                <!-- Group Display Name (if available) -->
                {#if studentView.student_submission.file_submission.group_display_name}
                  <p class="mt-2 text-amber-800 text-sm">
                    {$_('activity.group.displayName', { values: { name: studentView.student_submission.file_submission.group_display_name } })}
                  </p>
                {/if}
              </div>
            </div>
          {/if}

          <!-- Display Grade if sent to Moodle -->
          {#if studentView.student_submission.student_submission.sent_to_moodle && studentView.student_submission.grade}
            <div class="mb-6 p-4 bg-[#2271b3]/5 border border-[#2271b3]/20 rounded-md">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg class="h-6 w-6 text-[#2271b3]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                </div>
                <div class="ml-3 flex-1">
                  <h3 class="text-lg font-semibold text-[#2271b3] mb-3">{$_('activity.student.grade')}</h3>
                  <div class="space-y-2">
                    <div class="flex items-center">
                      <span class="text-sm font-medium text-[#2271b3] mr-2">{$_('activity.student.gradeScore')}:</span>
                      <span class="inline-flex items-center px-3 py-1 rounded-full text-lg font-bold {studentView.student_submission.grade.score >= 5 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                        {studentView.student_submission.grade.score} / 10
                      </span>
                    </div>
                    {#if studentView.student_submission.grade.comment}
                      <div class="mt-3">
                        <p class="text-sm font-medium text-[#2271b3] mb-1">{$_('activity.student.gradeFeedback')}:</p>
                        <div class="bg-white p-3 rounded-md border border-[#2271b3]/20">
                          <p class="text-sm text-gray-700 whitespace-pre-wrap">{studentView.student_submission.grade.comment}</p>
                        </div>
                      </div>
                    {/if}
                    <div class="mt-2 pt-2 border-t border-[#2271b3]/20">
                      <p class="text-xs text-[#2271b3]">
                        {$_('activity.student.gradeSentToMoodle', { values: { date: formatDate(studentView.student_submission.student_submission.sent_to_moodle_at) } })}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          {/if}

          {#if groupMembers.length > 0}
            <!-- Group Members -->
            <div class="mb-6">
              <h3 class="text-lg font-medium text-gray-900 mb-3">{$_('activity.student.groupMembers')}</h3>
              <div class="bg-gray-50 border border-gray-200 rounded-md p-4">
                <div class="space-y-2">
                  {#each groupMembers as member}
                    <div class="flex items-center justify-between">
                      <span class="text-sm font-medium text-gray-900">{member.student_name}</span>
                      <div class="flex items-center space-x-2">
                        {#if member.is_group_leader}
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                            {$_('activity.student.leader')}
                          </span>
                        {/if}
                        <span class="text-xs text-gray-500">{formatDate(member.submitted_at)}</span>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            </div>
          {/if}

          <!-- Option to update submission (only for group leaders or individual submissions, and only if not sent to Moodle) -->
          {#if (studentView.student_submission.is_group_leader || studentView.activity.activity_type === 'individual') && !studentView.student_submission.student_submission.sent_to_moodle}
            <div class="border-t border-gray-200 pt-6">
              <h3 class="text-lg font-medium text-gray-900 mb-4">{$_('activity.student.updateSubmission')}</h3>
              
              <div>
                <label for="file-upload-update" class="block text-sm font-medium text-gray-700 mb-2">
                  {$_('activity.student.selectNewFile')}
                </label>
                <input
                  bind:this={fileInput}
                  id="file-upload-update"
                  type="file"
                  onchange={handleFileSelect}
                  class="hidden"
                  disabled={uploading}
                />
                <button
                  type="button"
                  onclick={() => fileInput?.click()}
                  disabled={uploading}
                  class="w-full px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 hover:border-[#2271b3] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <div class="flex items-center justify-center space-x-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                    </svg>
                    <span>{selectedFile ? $_('activity.student.changeFile') : $_('activity.student.chooseFile')}</span>
                  </div>
                  {#if !selectedFile}
                    <p class="mt-1 text-xs text-gray-500">{$_('activity.student.noFileSelected')}</p>
                  {/if}
                </button>
                <p class="mt-2 text-xs text-gray-500">
                  {$_('activity.student.maxFileSize')}
                </p>
              </div>

              {#if selectedFile}
                <div class="mt-4 p-3 bg-gray-50 border border-gray-200 rounded-md">
                  <p class="text-sm text-gray-700">
                    <strong>{$_('activity.student.selectedFile')}:</strong> {selectedFile.name}
                  </p>
                  <p class="text-sm text-gray-500">
                    <strong>{$_('activity.student.size')}:</strong> {formatFileSize(selectedFile.size)}
                  </p>
                </div>
              {/if}

              <button
                onclick={submitDocument}
                disabled={!selectedFile || uploading}
                class="mt-4 w-full px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#2271b3] hover:bg-[#195a91] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? $_('activity.student.updating') : $_('activity.student.updateButton')}
              </button>
            </div>
          {:else if studentView.student_submission.student_submission.sent_to_moodle}
            <!-- Message when grades have been sent -->
            <div class="border-t border-gray-200 pt-6">
              <div class="p-4 bg-gray-50 border border-gray-300 rounded-md">
                <div class="flex">
                  <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                    </svg>
                  </div>
                  <div class="ml-3">
                    <h3 class="text-sm font-medium text-gray-800">{$_('activity.student.submissionFinalized')}</h3>
                    <p class="mt-1 text-sm text-gray-600">
                      {$_('activity.student.submissionFinalizedDescription')}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          {/if}
        {:else}
          <!-- No Submission Yet -->
          {#if studentView.activity.activity_type === 'individual'}
            <!-- Individual Activity Submission -->
            <div class="space-y-4">
              <h3 class="text-lg font-medium text-gray-900">{$_('activity.student.uploadDocument')}</h3>
              <p class="text-sm text-gray-600">
                {$_('activity.student.uploadDescription')}
              </p>
              
              <div>
                <label for="file-upload-individual" class="block text-sm font-medium text-gray-700 mb-2">
                  {$_('activity.student.selectFile')}
                </label>
                <input
                  bind:this={fileInput}
                  id="file-upload"
                  type="file"
                  onchange={handleFileSelect}
                  class="hidden"
                  disabled={uploading}
                />
                <button
                  type="button"
                  onclick={() => fileInput?.click()}
                  disabled={uploading}
                  class="w-full px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 hover:border-[#2271b3] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <div class="flex items-center justify-center space-x-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                    </svg>
                    <span>{selectedFile ? $_('activity.student.changeFile') : $_('activity.student.chooseFile')}</span>
                  </div>
                  {#if !selectedFile}
                    <p class="mt-1 text-xs text-gray-500">{$_('activity.student.noFileSelected')}</p>
                  {/if}
                </button>
                <p class="mt-2 text-xs text-gray-500">
                  {$_('activity.student.maxFileSize')}
                </p>
              </div>

              {#if selectedFile}
                <div class="p-3 bg-gray-50 border border-gray-200 rounded-md">
                  <p class="text-sm text-gray-700">
                    <strong>{$_('activity.student.selectedFile')}:</strong> {selectedFile.name}
                  </p>
                  <p class="text-sm text-gray-500">
                    <strong>{$_('activity.student.size')}:</strong> {formatFileSize(selectedFile.size)}
                  </p>
                </div>
              {/if}

              <!-- Student Note to Professor -->
              <div>
                <label for="student-note-individual" class="block text-sm font-medium text-gray-700 mb-2">
                  {$_('activity.student.studentNoteLabel')}
                </label>
                <textarea
                  id="student-note-individual"
                  bind:value={studentNote}
                  rows="3"
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] text-gray-900 bg-white"
                  placeholder={$_('activity.student.studentNotePlaceholder')}
                  disabled={uploading}
                ></textarea>
                <p class="mt-1 text-xs text-gray-500">{$_('activity.student.studentNoteHint')}</p>
              </div>

              <button
                onclick={submitDocument}
                disabled={!selectedFile || uploading}
                class="w-full px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#2271b3] hover:bg-[#195a91] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? $_('activity.student.sending') : $_('activity.student.sendButton')}
              </button>
            </div>
          {:else}
            <!-- Group Activity Submission -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <!-- Create Group by Uploading -->
              <div class="space-y-4">
                <h3 class="text-lg font-medium text-gray-900">{$_('activity.student.option1')}</h3>
                <p class="text-sm text-gray-600">
                  {$_('activity.student.option1Description')}
                </p>
                
                <div>
                  <label for="file-upload-group" class="block text-sm font-medium text-gray-700 mb-2">
                    {$_('activity.student.selectFile')}
                  </label>
                  <input
                    bind:this={fileInput}
                    id="file-upload-group"
                    type="file"
                    onchange={handleFileSelect}
                    class="hidden"
                    disabled={uploading}
                  />
                  <button
                    type="button"
                    onclick={() => fileInput?.click()}
                    disabled={uploading}
                    class="w-full px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 hover:border-[#2271b3] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <div class="flex items-center justify-center space-x-2">
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                      </svg>
                      <span>{selectedFile ? $_('activity.student.changeFile') : $_('activity.student.chooseFile')}</span>
                    </div>
                    {#if !selectedFile}
                      <p class="mt-1 text-xs text-gray-500">{$_('activity.student.noFileSelected')}</p>
                    {/if}
                  </button>
                  <p class="mt-2 text-xs text-gray-500">
                    {$_('activity.student.maxFileSize')}
                  </p>
                </div>

                {#if selectedFile}
                  <div class="p-3 bg-gray-50 border border-gray-200 rounded-md">
                    <p class="text-sm text-gray-700">
                      <strong>{$_('activity.student.selectedFile')}:</strong> {selectedFile.name}
                    </p>
                    <p class="text-sm text-gray-500">
                      <strong>{$_('activity.student.size')}:</strong> {formatFileSize(selectedFile.size)}
                    </p>
                  </div>
                {/if}

                <!-- Student Note to Professor (Group) -->
                <div>
                  <label for="student-note-group" class="block text-sm font-medium text-gray-700 mb-2">
                    {$_('activity.student.studentNoteLabel')}
                  </label>
                  <textarea
                    id="student-note-group"
                    bind:value={studentNote}
                    rows="3"
                    class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] text-gray-900 bg-white"
                    placeholder={$_('activity.student.studentNotePlaceholder')}
                    disabled={uploading}
                  ></textarea>
                  <p class="mt-1 text-xs text-gray-500">{$_('activity.student.studentNoteHint')}</p>
                </div>

                <button
                  onclick={submitDocument}
                  disabled={!selectedFile || uploading}
                  class="w-full px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#2271b3] hover:bg-[#195a91] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? $_('activity.student.sending') : $_('activity.student.uploadAndCreate')}
                </button>
              </div>

              <!-- Join Group with Code -->
              <div class="space-y-4">
                <h3 class="text-lg font-medium text-gray-900">{$_('activity.student.option2')}</h3>
                <p class="text-sm text-gray-600">
                  {$_('activity.student.option2Description')}
                </p>
                
                <div>
                  <label for="group-code" class="block text-sm font-medium text-gray-700 mb-2">
                    {$_('activity.student.groupCodeLabel')}
                  </label>
                  <input
                    bind:value={groupCode}
                    id="group-code"
                    type="text"
                    placeholder={$_('activity.student.groupCodePlaceholder')}
                    maxlength="8"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] sm:text-sm font-mono uppercase"
                    disabled={submittingCode}
                    oninput={(e) => { e.target.value = e.target.value.toUpperCase(); }}
                  />
                  <p class="mt-1 text-xs text-gray-500">
                    {$_('activity.student.groupCodeHint')}
                  </p>
                </div>

                <button
                  onclick={submitGroupCode}
                  disabled={!groupCode.trim() || submittingCode}
                  class="w-full px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submittingCode ? $_('activity.student.joining') : $_('activity.student.joinButton')}
                </button>
              </div>
            </div>

            <!-- Error and Success Messages -->
            {#if uploadError}
              <div class="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                <p class="text-sm text-red-700">{uploadError}</p>
              </div>
            {/if}

            {#if codeError}
              <div class="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                <p class="text-sm text-red-700">{codeError}</p>
              </div>
            {/if}

            {#if uploadSuccess}
              <div class="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
                <p class="text-sm text-green-700">{uploadSuccess}</p>
              </div>
            {/if}

            {#if codeSuccess}
              <div class="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
                <p class="text-sm text-green-700">{codeSuccess}</p>
              </div>
            {/if}
          {/if}
        {/if}
      </div>
    </div>
  </div>
{/if}