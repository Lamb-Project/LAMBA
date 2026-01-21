<script>
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { _ } from 'svelte-i18n';
  import { formatDate, formatFileSize, formatDateForInput } from '$lib/i18n/formatters.js';
  import { ltiAwareFetch } from '$lib/auth.js';
  
  let submissionsData = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let sendingGrades = $state(false);
  let gradesSentMessage = $state(null);
  let creatingEvaluation = $state(false);
  let evaluationMessage = $state(null);
  let isEditingDescription = $state(false);
  let editedDescription = $state('');
  let updatingDescription = $state(false);
  let descriptionSaveTimer = null;
  let descriptionSaveStatus = $state(''); // 'saving', 'saved', 'error'
  
  let deadlineValue = $state('');
  let updatingDeadline = $state(false);
  let deadlineSaveStatus = $state(''); // 'saving', 'saved', 'error'
  
  let evaluatorIdValue = $state('');
  let updatingEvaluator = $state(false);
  let evaluatorSaveStatus = $state(''); // 'saving', 'saved', 'error'
  
  // Manual grading state - now inline, not modal
  let editedGrades = $state({}); // {file_submission_id: {score: '', comment: ''}}
  let savingGrades = $state(false);
  let saveGradesError = $state(null);
  let saveGradesSuccess = $state(null);
  
  // Automatic evaluation selection state
  let selectedForEvaluation = $state({}); // {file_submission_id: boolean}
  let selectAllEvaluation = $state(false);
  
  // Get activity ID from URL params
  let activityId = $derived($page.params.activityId);
  
  onMount(async () => {
    if (browser && activityId) {
      await loadSubmissions();
    }
  });
  
  async function loadSubmissions() {
    try {
      loading = true;
      error = null;
      
      const response = await ltiAwareFetch(`/api/activities/${activityId}/submissions`);
      
      if (!response.ok) {
        if (response.status === 403) {
          throw new Error($_('errors.noPermissions'));
        } else if (response.status === 401) {
          throw new Error($_('errors.sessionExpired'));
        } else if (response.status === 404) {
          throw new Error($_('errors.activityNotFound'));
        } else {
          throw new Error($_('errors.loadingError'));
        }
      }
      
      submissionsData = await response.json();
      
      // Initialize editedGrades with existing grades
      initializeEditedGrades();
      
      // Initialize deadline value
      deadlineValue = submissionsData?.activity?.deadline ? formatDateForInput(submissionsData.activity.deadline) : '';
      
      // Initialize evaluator value
      evaluatorIdValue = submissionsData?.activity?.evaluator_id || '';
      
      // Reset evaluation selections
      selectedForEvaluation = {};
      selectAllEvaluation = false;
    } catch (err) {
      error = err.message;
      console.error('Error loading submissions:', err);
    } finally {
      loading = false;
    }
  }
  
  function initializeEditedGrades() {
    if (!submissionsData) return;
    
    const newEditedGrades = {};
    
    if (submissionsData.activity_type === 'individual' && submissionsData.submissions) {
      submissionsData.submissions.forEach(submission => {
        const fileSubId = submission.file_submission.id;
        newEditedGrades[fileSubId] = {
          score: submission.grade?.score?.toString() || '',
          comment: submission.grade?.comment || ''
        };
      });
    } else if (submissionsData.activity_type === 'group' && submissionsData.groups) {
      submissionsData.groups.forEach(group => {
        const fileSubId = group.file_submission.id;
        newEditedGrades[fileSubId] = {
          score: group.grade?.score?.toString() || '',
          comment: group.grade?.comment || ''
        };
      });
    }
    
    editedGrades = newEditedGrades;
  }
  
  function downloadFile(filePath) {
    // Create a download link for the file
    // The backend will provide the correct filename based on student name or group code
    const link = document.createElement('a');
    link.href = `/api/downloads/${encodeURIComponent(filePath)}`;
    link.click();
  }
  
  async function sendGradesToMoodle() {
    try {
      sendingGrades = true;
      gradesSentMessage = null;
      
      const response = await ltiAwareFetch(`/api/activities/${activityId}/grades/sync`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (response.ok) {
        gradesSentMessage = {
          type: result.success ? 'success' : 'warning',
          message: result.message,
          details: result.details
        };
      } else {
        gradesSentMessage = {
          type: 'error',
          message: result.detail || $_('errors.connectionError'),
          details: null
        };
      }
      
      // Clear message after 10 seconds
      setTimeout(() => {
        gradesSentMessage = null;
      }, 10000);
      
    } catch (err) {
      console.error('Error sending grades:', err);
      gradesSentMessage = {
        type: 'error',
        message: $_('errors.connectionError'),
        details: null
      };
      
      // Clear message after 10 seconds
      setTimeout(() => {
        gradesSentMessage = null;
      }, 10000);
    } finally {
      sendingGrades = false;
    }
  }
  
  async function createAutomaticEvaluation() {
    try {
      creatingEvaluation = true;
      evaluationMessage = null;
      
      // Get selected file submissions
      const selectedSubmissions = Object.entries(selectedForEvaluation)
        .filter(([_, selected]) => selected)
        .map(([id, _]) => id);
      
      // If no submissions selected, show warning
      if (selectedSubmissions.length === 0) {
        evaluationMessage = {
          type: 'error',
          message: $_('activity.submissions.selectSubmissionsToEvaluate'),
          details: null
        };
        
        setTimeout(() => {
          evaluationMessage = null;
        }, 5000);
        
        return;
      }
      
      const response = await ltiAwareFetch(`/api/activities/${activityId}/evaluate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_submission_ids: selectedSubmissions
        })
      });
      
      const result = await response.json();
      
      if (response.ok && result.success) {
        evaluationMessage = {
          type: 'success',
          message: result.message,
          details: result.grades_created > 0 ? $_('activity.submissions.gradesCreated', { values: { count: result.grades_created } }) : null
        };
        
        // Clear selections
        selectedForEvaluation = {};
        selectAllEvaluation = false;
        
        // Reload submissions to show new grades
        await loadSubmissions();
      } else {
        evaluationMessage = {
          type: 'error',
          message: result.detail || result.message || $_('errors.connectionError'),
          details: null
        };
      }
      
      // Clear message after 10 seconds
      setTimeout(() => {
        evaluationMessage = null;
      }, 10000);
      
    } catch (err) {
      console.error('Error creating automatic evaluation:', err);
      evaluationMessage = {
        type: 'error',
        message: $_('errors.connectionError'),
        details: null
      };
      
      // Clear message after 10 seconds
      setTimeout(() => {
        evaluationMessage = null;
      }, 10000);
    } finally {
      creatingEvaluation = false;
    }
  }
  
  function toggleSelectAll() {
    selectAllEvaluation = !selectAllEvaluation;
    
    if (submissionsData.activity_type === 'individual' && submissionsData.submissions) {
      submissionsData.submissions.forEach(submission => {
        selectedForEvaluation[submission.file_submission.id] = selectAllEvaluation;
      });
    } else if (submissionsData.activity_type === 'group' && submissionsData.groups) {
      submissionsData.groups.forEach(group => {
        selectedForEvaluation[group.file_submission.id] = selectAllEvaluation;
      });
    }
  }
  
  function toggleSubmissionSelection(fileSubmissionId) {
    selectedForEvaluation[fileSubmissionId] = !selectedForEvaluation[fileSubmissionId];
    
    // Update selectAll checkbox if needed
    if (submissionsData.activity_type === 'individual' && submissionsData.submissions) {
      const allSelected = submissionsData.submissions.every(s => selectedForEvaluation[s.file_submission.id]);
      selectAllEvaluation = allSelected;
    } else if (submissionsData.activity_type === 'group' && submissionsData.groups) {
      const allSelected = submissionsData.groups.every(g => selectedForEvaluation[g.file_submission.id]);
      selectAllEvaluation = allSelected;
    }
  }
  
  function getPreviewDescription(description, maxLength = 200) {
    if (!description) return '';
    if (description.length <= maxLength) return description;
    return description.substring(0, maxLength) + '...';
  }

  function onDescriptionInput(value) {
    editedDescription = value;
    descriptionSaveStatus = 'saving';
    
    // Clear previous timer
    if (descriptionSaveTimer) {
      clearTimeout(descriptionSaveTimer);
    }
    
    // Set new timer for auto-save (1.5 seconds after user stops typing)
    descriptionSaveTimer = setTimeout(async () => {
      await saveDescription();
    }, 1500);
  }

  async function saveDescription() {
    if (!activityId || !editedDescription.trim()) return;
    
    try {
      updatingDescription = true;
      descriptionSaveStatus = 'saving';
      
      const response = await ltiAwareFetch(`/api/activities/${activityId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          description: editedDescription.trim()
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || $_('activity.details.errorSaving'));
      }

      const result = await response.json();
      
      if (result.success && result.activity) {
        // Update the local data
        submissionsData.activity.description = result.activity.description;
        descriptionSaveStatus = 'saved';
        
        // Clear saved status after 3 seconds
        setTimeout(() => {
          descriptionSaveStatus = '';
        }, 3000);
      } else {
        throw new Error(result.message || $_('activity.details.errorSaving'));
      }
      
    } catch (err) {
      console.error('Error updating description:', err);
      descriptionSaveStatus = 'error';
      setTimeout(() => {
        descriptionSaveStatus = '';
      }, 5000);
    } finally {
      updatingDescription = false;
    }
  }
  
  async function saveDeadline() {
    if (!activityId) return;
    
    // Check if deadline has actually changed
    const currentDeadline = submissionsData?.activity?.deadline ? formatDateForInput(submissionsData.activity.deadline) : '';
    if (deadlineValue === currentDeadline) {
      return; // No changes, don't save
    }
    
    try {
      updatingDeadline = true;
      deadlineSaveStatus = 'saving';
      
      // Convert to ISO string or null
      const deadlineToSave = deadlineValue ? new Date(deadlineValue).toISOString() : null;
      
      const response = await ltiAwareFetch(`/api/activities/${activityId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          deadline: deadlineToSave
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || $_('activity.details.errorSavingDeadline'));
      }

      const result = await response.json();
      
      if (result.success && result.activity) {
        // Update the local data
        submissionsData.activity.deadline = result.activity.deadline;
        deadlineValue = result.activity.deadline ? formatDateForInput(result.activity.deadline) : '';
        deadlineSaveStatus = 'saved';
        
        // Clear saved status after 3 seconds
        setTimeout(() => {
          deadlineSaveStatus = '';
        }, 3000);
      } else {
        throw new Error(result.message || $_('activity.details.errorSavingDeadline'));
      }
      
    } catch (err) {
      console.error('Error updating deadline:', err);
      deadlineSaveStatus = 'error';
      setTimeout(() => {
        deadlineSaveStatus = '';
      }, 5000);
    } finally {
      updatingDeadline = false;
    }
  }
  
  // Save all grades function
  async function saveAllGrades() {
    try {
      savingGrades = true;
      saveGradesError = null;
      saveGradesSuccess = null;
      
      // Collect all grades to save
      const gradesToSave = [];
      
      for (const [fileSubmissionId, gradeData] of Object.entries(editedGrades)) {
        // Only save if there's a score (skip empty fields)
        if (gradeData.score && gradeData.score.trim() !== '') {
          const score = parseFloat(gradeData.score);
          
          // Validate score
          if (isNaN(score) || score < 0 || score > 10) {
            saveGradesError = $_('activity.grading.invalidScore');
            return;
          }
          
          gradesToSave.push({
            file_submission_id: fileSubmissionId,
            score: score,
            comment: gradeData.comment.trim() || null
          });
        }
      }
      
      if (gradesToSave.length === 0) {
        saveGradesError = $_('activity.grading.noGradesToSave');
        return;
      }
      
      // Save each grade
      let savedCount = 0;
      let failedCount = 0;
      
      for (const gradeRequest of gradesToSave) {
        try {
          const response = await ltiAwareFetch(`/api/grades/${gradeRequest.file_submission_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              score: gradeRequest.score,
              comment: gradeRequest.comment
            })
          });
          
          if (response.ok) {
            savedCount++;
          } else {
            failedCount++;
            console.error('Failed to save grade for submission:', gradeRequest.file_submission_id);
          }
        } catch (err) {
          failedCount++;
          console.error('Error saving grade:', err);
        }
      }
      
      // Show results
      if (savedCount > 0) {
        if (failedCount > 0) {
          saveGradesSuccess = $_('activity.grading.savedWithErrors', { values: { saved: savedCount, failed: failedCount } });
        } else {
          saveGradesSuccess = $_('activity.grading.saved', { values: { count: savedCount } });
        }
        
        // Reload submissions to show updated grades
        await loadSubmissions();
        
        // Clear success message after 5 seconds
        setTimeout(() => {
          saveGradesSuccess = null;
        }, 5000);
      } else {
        saveGradesError = $_('activity.grading.errorSaving');
      }
      
    } catch (err) {
      console.error('Error saving grades:', err);
      saveGradesError = $_('activity.grading.errorSaving');
    } finally {
      savingGrades = false;
    }
  }
  
  function updateGrade(fileSubmissionId, field, value) {
    if (!editedGrades[fileSubmissionId]) {
      editedGrades[fileSubmissionId] = { score: '', comment: '' };
    }
    editedGrades[fileSubmissionId][field] = value;
  }
  
  async function saveEvaluatorSettings() {
    if (!activityId) return;
    
    // Check if evaluator settings have actually changed
    const currentEvaluatorId = submissionsData?.activity?.evaluator_id || '';
    if (evaluatorIdValue === currentEvaluatorId) {
      return; // No changes, don't save
    }
    
    try {
      updatingEvaluator = true;
      evaluatorSaveStatus = 'saving';
      
      const response = await ltiAwareFetch(`/api/activities/${activityId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          evaluator_id: evaluatorIdValue.trim() || null
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || $_('activity.details.errorSavingEvaluator'));
      }

      const result = await response.json();
      
      if (result.success && result.activity) {
        // Update the local data
        submissionsData.activity.evaluator_id = result.activity.evaluator_id;
        evaluatorIdValue = result.activity.evaluator_id || '';
        evaluatorSaveStatus = 'saved';
        
        // Clear saved status after 3 seconds
        setTimeout(() => {
          evaluatorSaveStatus = '';
        }, 3000);
      } else {
        throw new Error(result.message || $_('activity.details.errorSavingEvaluator'));
      }
      
    } catch (err) {
      console.error('Error updating evaluator settings:', err);
      evaluatorSaveStatus = 'error';
      setTimeout(() => {
        evaluatorSaveStatus = '';
      }, 5000);
    } finally {
      updatingEvaluator = false;
    }
  }
</script>

<svelte:head>
  <title>{$_('activity.student.title')} | LAMBA</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

  {#if submissionsData?.activity}
    <!-- Activity Information -->
    <div class="bg-white shadow rounded-lg mb-6">
      <div class="px-6 py-4 border-b border-gray-200">
        <h1 class="text-2xl font-bold text-gray-900">{submissionsData.activity.title}</h1>
      </div>
      
      <div class="p-6">
        <div class="space-y-4">
          <!-- Description Section with Auto-save -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <label for="activity-description" class="block text-sm font-medium text-gray-700">{$_('activity.details.description')}</label>
              {#if descriptionSaveStatus === 'saving'}}
                <span class="text-xs text-gray-500 flex items-center">
                  <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-500 mr-1"></div>
                  {$_('activity.details.saving')}
                </span>
              {:else if descriptionSaveStatus === 'saved'}
                <span class="text-xs text-green-600 flex items-center">
                  <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  {$_('activity.details.saved')}
                </span>
              {:else if descriptionSaveStatus === 'error'}
                <span class="text-xs text-red-600">{$_('activity.details.errorSaving')}</span>
              {/if}
            </div>
            <textarea
              id="activity-description"
              value={editedDescription || submissionsData.activity.description}
              oninput={(e) => onDescriptionInput(e.target.value)}
              class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] resize-y text-sm"
              rows="4"
              placeholder={$_('activity.create.descriptionPlaceholder')}
            ></textarea>
          </div>
          
          <!-- Deadline Section with Manual Save -->
          <div>
            <label for="activity-deadline" class="block text-sm font-medium text-gray-700 mb-2">{$_('activity.details.deadline')}</label>
            <div class="flex items-center space-x-2">
              <input
                id="activity-deadline"
                type="datetime-local"
                bind:value={deadlineValue}
                min={new Date().toISOString().slice(0, 16)}
                class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] text-sm"
              />
              <button
                onclick={saveDeadline}
                disabled={updatingDeadline}
                class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#2271b3] hover:bg-[#195a91] disabled:bg-gray-400 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3]"
              >
                {#if updatingDeadline}
                  <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {$_('activity.details.saving')}
                {:else}
                  <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                  </svg>
                  {$_('common.save')}
                {/if}
              </button>
            </div>
            {#if deadlineSaveStatus === 'saved'}
              <p class="mt-1 text-xs text-green-600 flex items-center">
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
                {$_('activity.details.deadlineUpdated')}
              </p>
            {:else if deadlineSaveStatus === 'error'}
              <p class="mt-1 text-xs text-red-600">{$_('activity.details.errorSavingDeadline')}</p>
            {/if}
          </div>
          
          <!-- Evaluator Settings Section -->
          <div class="border-t border-gray-200 pt-4">
            <h3 class="text-sm font-medium text-gray-700 mb-1">{$_('activity.create.evaluatorTitle')}</h3>
            <p class="text-xs text-gray-500 mb-3">{$_('activity.create.evaluatorSubtitle')}</p>
            <div class="flex items-end gap-2">
              <div class="flex-1">
                <label for="evaluatorId" class="block text-sm font-medium text-gray-700 mb-1">
                  {$_('activity.create.evaluatorIdLabel')}
                </label>
                <input
                  type="text"
                  id="evaluatorId"
                  bind:value={evaluatorIdValue}
                  class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] text-sm"
                  placeholder={$_('activity.create.evaluatorIdPlaceholder')}
                />
              </div>
              <button
                onclick={saveEvaluatorSettings}
                disabled={updatingEvaluator}
                class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#2271b3] hover:bg-[#195a91] disabled:bg-gray-400 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3] whitespace-nowrap"
              >
                {#if updatingEvaluator}
                  <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  {$_('activity.details.saving')}
                {:else}
                  <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                  </svg>
                  {$_('common.save')}
                {/if}
              </button>
            </div>
            {#if evaluatorSaveStatus === 'saved'}
              <p class="mt-2 text-xs text-green-600 flex items-center">
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
                {$_('activity.create.evaluatorSubtitle')}
              </p>
            {:else if evaluatorSaveStatus === 'error'}
              <p class="mt-2 text-xs text-red-600">{$_('activity.details.errorSaving')}</p>
            {/if}
          </div>
          
          <!-- Activity Info Badges -->
          <div class="pt-2 flex flex-wrap items-center gap-2">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {submissionsData.activity.activity_type === 'group' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}">
              {submissionsData.activity.activity_type === 'group' ? $_('activity.details.typeGroup') : $_('activity.details.typeIndividual')}
            </span>
            {#if submissionsData.activity.activity_type === 'group' && submissionsData.activity.max_group_size}
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                {$_('activity.details.maxGroupSize', { values: { count: submissionsData.activity.max_group_size } })}
              </span>
            {/if}
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              {$_('activity.details.submissions', { values: { count: submissionsData.total_submissions, type: submissionsData.activity.activity_type === 'group' ? $_('activity.details.submissionsGroups') : $_('activity.details.submissionsDeliveries') } })}
            </span>
            {#if submissionsData.activity.activity_type === 'group'}
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                {$_('activity.details.students', { values: { count: submissionsData.groups ? submissionsData.groups.reduce((total, group) => total + group.members.length, 0) : 0 } })}
              </span>
            {/if}
          </div>
        </div>
      </div>
    </div>
  {/if}
  
  <!-- Submissions Section -->
  <div class="bg-white shadow rounded-lg">
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="flex justify-between items-center">
        <h2 class="text-xl font-bold text-gray-900">
          {submissionsData?.activity_type === 'group' ? $_('activity.submissions.titleGroup') : $_('activity.submissions.title')}
        </h2>
        
        <!-- Action Buttons -->
        {#if !loading && !error && submissionsData && submissionsData.total_submissions > 0}
          <div class="flex space-x-3">
            <!-- Automatic Evaluation Button -->
            <button
              onclick={createAutomaticEvaluation}
              disabled={creatingEvaluation || Object.values(selectedForEvaluation).filter(Boolean).length === 0 || !submissionsData?.activity?.evaluator_id}
              class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#2271b3] hover:bg-[#195a91] disabled:bg-gray-400 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              {#if creatingEvaluation}
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {$_('activity.submissions.evaluating')}
              {:else}
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                </svg>
                {$_('activity.submissions.automaticEvaluation')}
              {/if}
            </button>
            
            <!-- Send Grades to Moodle Button -->
            <button
              onclick={sendGradesToMoodle}
              disabled={sendingGrades}
              class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              {#if sendingGrades}
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {$_('activity.submissions.sending')}
              {:else}
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path>
                </svg>
                {$_('activity.submissions.sendToMoodle')}
              {/if}
            </button>
          </div>
        {/if}
      </div>
      
      <!-- Grade Sending Status Message -->
      {#if gradesSentMessage}
        <div class="mt-4 p-4 rounded-md {gradesSentMessage.type === 'success' ? 'bg-green-50 border border-green-200' : gradesSentMessage.type === 'warning' ? 'bg-yellow-50 border border-yellow-200' : 'bg-red-50 border border-red-200'}">
          <div class="flex">
            <div class="flex-shrink-0">
              {#if gradesSentMessage.type === 'success'}
                <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              {:else if gradesSentMessage.type === 'warning'}
                <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              {:else}
                <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
              {/if}
            </div>
            <div class="ml-3">
              <p class="text-sm font-medium {gradesSentMessage.type === 'success' ? 'text-green-800' : gradesSentMessage.type === 'warning' ? 'text-yellow-800' : 'text-red-800'}">
                {gradesSentMessage.message}
              </p>
              {#if gradesSentMessage.details && gradesSentMessage.details.sent_count > 0}
                <p class="mt-1 text-xs {gradesSentMessage.type === 'success' ? 'text-green-600' : gradesSentMessage.type === 'warning' ? 'text-yellow-600' : 'text-red-600'}">
                  {$_('activity.submissions.activity')}: {gradesSentMessage.details.activity_title} | {$_('activity.submissions.course')}: {gradesSentMessage.details.course_title}
                </p>
                <p class="mt-1 text-xs {gradesSentMessage.type === 'success' ? 'text-green-600' : gradesSentMessage.type === 'warning' ? 'text-yellow-600' : 'text-red-600'}">
                  {$_('activity.submissions.sent')}: {gradesSentMessage.details.sent_count} | {$_('activity.submissions.failed')}: {gradesSentMessage.details.failed_count} | {$_('activity.submissions.total')}: {gradesSentMessage.details.total_submissions}
                </p>
              {/if}
            </div>
          </div>
        </div>
      {/if}
      
      <!-- Automatic Evaluation Status Message -->
      {#if evaluationMessage}
        <div class="mt-4 p-4 rounded-md {evaluationMessage.type === 'success' ? 'bg-blue-50 border border-blue-200' : 'bg-red-50 border border-red-200'}">
          <div class="flex">
            <div class="flex-shrink-0">
              {#if evaluationMessage.type === 'success'}
                <svg class="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              {:else}
                <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
              {/if}
            </div>
            <div class="ml-3">
              <p class="text-sm font-medium {evaluationMessage.type === 'success' ? 'text-blue-800' : 'text-red-800'}">
                {evaluationMessage.message}
              </p>
              {#if evaluationMessage.details}
                <p class="mt-1 text-xs {evaluationMessage.type === 'success' ? 'text-blue-600' : 'text-red-600'}">
                  {evaluationMessage.details}
                </p>
              {/if}
            </div>
          </div>
        </div>
      {/if}
    </div>

    {#if loading}
      <div class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#2271b3]"></div>
        <span class="ml-3 text-gray-600">{$_('activity.submissions.loadingSubmissions')}</span>
      </div>
    {:else if error}
      <div class="text-center py-12">
        <div class="text-red-600 mb-4">
          <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.382 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
          </svg>
        </div>
        <h3 class="text-lg font-medium text-gray-900 mb-2">{$_('activity.submissions.errorLoading')}</h3>
        <p class="text-gray-600 mb-4">{error}</p>
        <button
          onclick={loadSubmissions}
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#2271b3] hover:bg-[#195a91] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3]"
        >
          {$_('activity.submissions.retry')}
        </button>
      </div>
    {:else if !submissionsData || submissionsData.total_submissions === 0}
      <div class="text-center py-12">
        <div class="text-gray-400 mb-4">
          <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
        </div>
        <h3 class="text-lg font-medium text-gray-900 mb-2">{$_('activity.submissions.noSubmissions')}</h3>
        <p class="text-gray-600">
          {$_('activity.submissions.noSubmissionsDescription', { values: { type: submissionsData?.activity_type === 'group' ? $_('activity.submissions.noSubmissionsGroup') : $_('activity.submissions.noSubmissionsIndividual') } })}
        </p>
      </div>
    {:else}
      <div class="overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">
            {$_('activity.submissions.found', { values: { count: submissionsData.total_submissions, type: submissionsData.activity_type === 'group' ? $_('activity.submissions.foundGroup') : $_('activity.submissions.foundIndividual') } })}
          </h3>
        </div>
        
        <!-- Individual Submissions -->
        {#if submissionsData.activity_type === 'individual'}
          <div class="divide-y divide-gray-200">
            <!-- Select All Checkbox -->
            {#if submissionsData.submissions && submissionsData.submissions.length > 0}
              <div class="px-6 py-3 bg-gray-100 border-b border-gray-200 flex items-center">
                <input
                  type="checkbox"
                  id="selectAllIndividual"
                  checked={selectAllEvaluation}
                  onchange={toggleSelectAll}
                  class="h-4 w-4 text-[#2271b3] focus:ring-[#2271b3] border-gray-300 rounded cursor-pointer"
                />
                <label for="selectAllIndividual" class="ml-2 text-sm font-medium text-gray-700 cursor-pointer">
                  {$_('activity.submissions.selectAllForEvaluation')}
                </label>
              </div>
            {/if}
            
            {#each submissionsData.submissions as submission (submission.student_submission.id)}
              <div class="p-6 hover:bg-gray-50">
                <div class="flex items-start justify-between mb-4">
                  <div class="flex-1">
                    <div class="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        id="eval-{submission.file_submission.id}"
                        checked={selectedForEvaluation[submission.file_submission.id] || false}
                        onchange={() => toggleSubmissionSelection(submission.file_submission.id)}
                        class="h-4 w-4 text-[#2271b3] focus:ring-[#2271b3] border-gray-300 rounded cursor-pointer"
                      />
                      <h4 class="text-lg font-medium text-gray-900">{submission.student_name}</h4>
                      {#if submission.student_email}
                        <span class="text-sm text-gray-500">{submission.student_email}</span>
                      {/if}
                    </div>
                    
                    <div class="mt-2 flex items-center space-x-4 text-sm text-gray-600">
                      <span>📄 {submission.file_submission.file_name}</span>
                      <span>📊 {formatFileSize(submission.file_submission.file_size)}</span>
                      <span>🕒 {formatDate(submission.file_submission.uploaded_at)}</span>
                    </div>
                  </div>
                  
                  <div class="ml-4 flex-shrink-0">
                    <button
                      onclick={() => downloadFile(submission.file_submission.file_path)}
                      class="inline-flex items-center justify-center px-3 py-1.5 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3]"
                    >
                      <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                      </svg>
                      {$_('common.download')}
                    </button>
                  </div>
                </div>
                
                <!-- Inline Grading Fields -->
                <div class="mt-4 p-4 bg-gray-50 rounded-md border border-gray-200">
                  <h5 class="text-sm font-medium text-gray-700 mb-3">{$_('activity.grading.title')}</h5>
                  <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="md:col-span-1">
                      <label for="score-{submission.file_submission.id}" class="block text-sm font-medium text-gray-700 mb-1">
                        {$_('activity.grading.scoreLabel')}
                      </label>
                      <input
                        id="score-{submission.file_submission.id}"
                        type="number"
                        min="0"
                        max="10"
                        step="0.1"
                        value={editedGrades[submission.file_submission.id]?.score || ''}
                        oninput={(e) => updateGrade(submission.file_submission.id, 'score', e.target.value)}
                        class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] text-sm"
                        placeholder={$_('activity.grading.scorePlaceholder')}
                      />
                    </div>
                    <div class="md:col-span-3">
                      <label for="comment-{submission.file_submission.id}" class="block text-sm font-medium text-gray-700 mb-1">
                        {$_('activity.grading.commentLabel')}
                      </label>
                      <textarea
                        id="comment-{submission.file_submission.id}"
                        value={editedGrades[submission.file_submission.id]?.comment || ''}
                        oninput={(e) => updateGrade(submission.file_submission.id, 'comment', e.target.value)}
                        rows={editedGrades[submission.file_submission.id]?.comment ? '10' : '2'}
                        class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] text-sm"
                        placeholder={$_('activity.grading.commentPlaceholder')}
                      ></textarea>
                    </div>
                  </div>
                  {#if submission.grade}
                    <div class="mt-2 text-xs text-gray-500">
                      {$_('activity.grading.lastUpdate', { values: { date: formatDate(submission.grade.created_at) } })}
                    </div>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
        
        <!-- Group Submissions -->
        {#if submissionsData.activity_type === 'group'}
          <div class="divide-y divide-gray-200">
            <!-- Select All Checkbox -->
            {#if submissionsData.groups && submissionsData.groups.length > 0}
              <div class="px-6 py-3 bg-gray-100 border-b border-gray-200 flex items-center">
                <input
                  type="checkbox"
                  id="selectAllGroup"
                  checked={selectAllEvaluation}
                  onchange={toggleSelectAll}
                  class="h-4 w-4 text-[#2271b3] focus:ring-[#2271b3] border-gray-300 rounded cursor-pointer"
                />
                <label for="selectAllGroup" class="ml-2 text-sm font-medium text-gray-700 cursor-pointer">
                  {$_('activity.submissions.selectAllForEvaluation')}
                </label>
              </div>
            {/if}
            
            {#each submissionsData.groups as group (group.group_code)}
              <div class="p-6 hover:bg-gray-50">
                <div class="flex items-start justify-between mb-4">
                  <div class="flex-1">
                    <div class="flex items-center space-x-3 mb-3">
                      <input
                        type="checkbox"
                        id="eval-{group.file_submission.id}"
                        checked={selectedForEvaluation[group.file_submission.id] || false}
                        onchange={() => toggleSubmissionSelection(group.file_submission.id)}
                        class="h-4 w-4 text-[#2271b3] focus:ring-[#2271b3] border-gray-300 rounded cursor-pointer"
                      />
                      <h4 class="text-lg font-medium text-gray-900">{$_('activity.group.code', { values: { code: group.group_code } })}</h4>
                      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                        {$_('activity.group.members' + (group.members.length !== 1 ? '_plural' : ''), { values: { count: group.members.length } })}
                      </span>
                    </div>
                    
                    <!-- File info -->
                    <div class="mb-3 flex items-center space-x-4 text-sm text-gray-600">
                      <span>📄 {group.file_submission.file_name}</span>
                      <span>📊 {formatFileSize(group.file_submission.file_size)}</span>
                      <span>🕒 {formatDate(group.file_submission.uploaded_at)}</span>
                    </div>
                    
                    <!-- Group members -->
                    <div class="space-y-2 mb-4">
                      <h5 class="text-sm font-medium text-gray-700">{$_('activity.student.groupMembers')}:</h5>
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {#each group.members as member (member.student_id)}
                          <div class="flex items-center space-x-2 text-sm">
                            <span class="flex-1">{member.student_name}</span>
                            {#if member.is_group_leader}
                              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                                {$_('activity.student.leader')}
                              </span>
                            {/if}
                            <span class="text-gray-500 text-xs">
                              {formatDate(member.joined_at)}
                            </span>
                          </div>
                        {/each}
                      </div>
                    </div>
                  </div>
                  
                  <div class="ml-4 flex-shrink-0">
                    <button
                      onclick={() => downloadFile(group.file_submission.file_path)}
                      class="inline-flex items-center justify-center px-3 py-1.5 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3]"
                    >
                      <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                      </svg>
                      {$_('common.download')}
                    </button>
                  </div>
                </div>
                
                <!-- Inline Grading Fields -->
                <div class="mt-4 p-4 bg-gray-50 rounded-md border border-gray-200">
                  <h5 class="text-sm font-medium text-gray-700 mb-3">{$_('activity.grading.groupTitle')}</h5>
                  <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="md:col-span-1">
                      <label for="score-{group.file_submission.id}" class="block text-sm font-medium text-gray-700 mb-1">
                        {$_('activity.grading.scoreLabel')}
                      </label>
                      <input
                        id="score-{group.file_submission.id}"
                        type="number"
                        min="0"
                        max="10"
                        step="0.1"
                        value={editedGrades[group.file_submission.id]?.score || ''}
                        oninput={(e) => updateGrade(group.file_submission.id, 'score', e.target.value)}
                        class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] text-sm"
                        placeholder={$_('activity.grading.scorePlaceholder')}
                      />
                    </div>
                    <div class="md:col-span-3">
                      <label for="comment-{group.file_submission.id}" class="block text-sm font-medium text-gray-700 mb-1">
                        {$_('activity.grading.commentLabel')}
                      </label>
                      <textarea
                        id="comment-{group.file_submission.id}"
                        value={editedGrades[group.file_submission.id]?.comment || ''}
                        oninput={(e) => updateGrade(group.file_submission.id, 'comment', e.target.value)}
                        rows={editedGrades[group.file_submission.id]?.comment ? '6' : '2'}
                        class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] text-sm"
                        placeholder={$_('activity.grading.commentPlaceholderGroup')}
                      ></textarea>
                    </div>
                  </div>
                  {#if group.grade}
                    <div class="mt-2 text-xs text-gray-500">
                      {$_('activity.grading.lastUpdate', { values: { date: formatDate(group.grade.created_at) } })}
                    </div>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>
  
  <!-- Save All Grades Button -->
  {#if !loading && !error && submissionsData && submissionsData.total_submissions > 0}
    <div class="mt-6 bg-white shadow rounded-lg p-6">
      <div class="flex items-center justify-between">
        <div class="flex-1">
          <h3 class="text-lg font-medium text-gray-900">{$_('activity.grading.saveAll')}</h3>
          <p class="mt-1 text-sm text-gray-600">
            {$_('activity.grading.saveAllDescription')}
          </p>
        </div>
        <button
          onclick={saveAllGrades}
          disabled={savingGrades}
          class="ml-4 inline-flex items-center px-6 py-3 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
        >
          {#if savingGrades}
            <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
            {$_('activity.grading.saving')}
          {:else}
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path>
            </svg>
            {$_('activity.grading.saveAll')}
          {/if}
        </button>
      </div>
      
      <!-- Success/Error Messages -->
      {#if saveGradesSuccess}
        <div class="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <p class="text-sm font-medium text-green-800">{saveGradesSuccess}</p>
            </div>
          </div>
        </div>
      {/if}
      
      {#if saveGradesError}
        <div class="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <p class="text-sm font-medium text-red-800">{saveGradesError}</p>
            </div>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

