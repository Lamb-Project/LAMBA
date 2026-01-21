<script>
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { ltiAwareFetch } from '$lib/auth.js';
  
  const dispatch = createEventDispatcher();
  
  // Props
  let { initialTitle = '' } = $props();
  
  // Form data
  let title = $state(initialTitle);
  let description = $state('');
  let activityType = $state('individual');
  let maxGroupSize = $state(2);
  let deadline = $state('');
  let evaluatorId = $state('');
  
  // Initialize deadline with default value (3 weeks from now at 23:59)
  function getDefaultDeadline() {
    const now = new Date();
    const defaultDate = new Date(now.getTime() + (21 * 24 * 60 * 60 * 1000)); // 21 days = 3 weeks
    defaultDate.setHours(23, 59, 0, 0); // Set to 23:59:00
    
    // Format for datetime-local input (YYYY-MM-DDTHH:MM)
    const year = defaultDate.getFullYear();
    const month = String(defaultDate.getMonth() + 1).padStart(2, '0');
    const day = String(defaultDate.getDate()).padStart(2, '0');
    const hours = String(defaultDate.getHours()).padStart(2, '0');
    const minutes = String(defaultDate.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  }
  
  // Set default deadline on component mount using effect
  $effect(() => {
    if (!deadline) {
      deadline = getDefaultDeadline();
    }
  });
  
  // Form state
  let isSubmitting = $state(false);
  let errors = $state({});

  // Validation
  function validateForm() {
    const newErrors = {};
    
    if (!title.trim()) {
      newErrors.title = $_('validation.titleRequired');
    } else if (title.trim().length < 3) {
      newErrors.title = $_('validation.titleMinLength');
    }
    
    if (!description.trim()) {
      newErrors.description = $_('validation.descriptionRequired');
    } else if (description.trim().length < 10) {
      newErrors.description = $_('validation.descriptionMinLength');
    }
    
    if (activityType === 'group' && (!maxGroupSize || maxGroupSize < 2)) {
      newErrors.maxGroupSize = $_('validation.maxGroupSizeMin');
    }
    
    if (!deadline) {
      newErrors.deadline = $_('validation.deadlineRequired');
    } else {
      // Validate deadline is not in the past
      const deadlineDate = new Date(deadline);
      const now = new Date();
      if (deadlineDate < now) {
        newErrors.deadline = $_('validation.deadlinePast');
      }
    }
    
    errors = newErrors;
    return Object.keys(newErrors).length === 0;
  }
  
  // Submit handler
  async function handleSubmit(event) {
    event.preventDefault();
    if (!validateForm()) return;
    
    isSubmitting = true;
    
    try {
      const activityData = {
        title: title.trim(),
        description: description.trim(),
        activity_type: activityType,
        max_group_size: activityType === 'group' ? maxGroupSize : null,
        deadline: deadline ? new Date(deadline).toISOString() : null,
        evaluator_id: evaluatorId.trim() || null
      };
      
      const response = await ltiAwareFetch('/api/activities', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(activityData)
      });
      
      const result = await response.json();
      
      if (response.ok && result.success) {
        // Reset form
        title = initialTitle;
        description = '';
        activityType = 'individual';
        maxGroupSize = 2;
        deadline = getDefaultDeadline();
        evaluatorId = '';
        errors = {};
        
        // Dispatch success event
        dispatch('success', {
          message: result.message,
          activity: result.activity
        });
      } else {
        dispatch('error', {
          message: result.detail || 'Error al crear la actividad'
        });
      }
    } catch (error) {
      dispatch('error', {
        message: 'Error de conexión. Intenta de nuevo.'
      });
    } finally {
      isSubmitting = false;
    }
  }
  
  // Reset form
  export function resetForm() {
    title = initialTitle;
    description = '';
    activityType = 'individual';
    maxGroupSize = 2;
    deadline = getDefaultDeadline();
    evaluatorId = '';
    errors = {};
  }
</script>

<div class="bg-white shadow rounded-lg">
  <div class="px-6 py-4 border-b border-gray-200">
    <h2 class="text-lg font-medium text-gray-900">{$_('activity.create.subtitle')}</h2>
    <p class="text-sm text-gray-600">{$_('activity.create.description')}</p>
  </div>
  
  <form onsubmit={handleSubmit} class="p-6 space-y-6">
    <!-- Título -->
    <div>
      <label for="title" class="block text-sm font-medium text-gray-700 mb-1">
        {$_('activity.create.titleLabel')} <span class="text-red-500">*</span>
      </label>
      <input
        type="text"
        id="title"
        bind:value={title}
        class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] {errors.title ? 'border-red-500' : ''}"
        placeholder={$_('activity.create.titlePlaceholder')}
        disabled={isSubmitting}
      />
      {#if errors.title}
        <p class="mt-1 text-sm text-red-600">{errors.title}</p>
      {/if}
    </div>
    
    <!-- Descripción -->
    <div>
      <label for="description" class="block text-sm font-medium text-gray-700 mb-1">
        {$_('activity.create.descriptionLabel')} <span class="text-red-500">*</span>
      </label>
      <textarea
        id="description"
        bind:value={description}
        rows="4"
        class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] {errors.description ? 'border-red-500' : ''}"
        placeholder={$_('activity.create.descriptionPlaceholder')}
        disabled={isSubmitting}
      ></textarea>
      {#if errors.description}
        <p class="mt-1 text-sm text-red-600">{errors.description}</p>
      {/if}
    </div>
    
    <!-- Tipo de actividad -->
    <div>
      <fieldset>
        <legend class="block text-sm font-medium text-gray-700 mb-3">
          {$_('activity.create.typeLabel')} <span class="text-red-500">*</span>
        </legend>
        <div class="space-y-3">
          <label class="flex items-center">
            <input
              type="radio"
              bind:group={activityType}
              value="individual"
              class="h-4 w-4 text-[#2271b3] focus:ring-[#2271b3] focus:ring-offset-0 border-[#2271b3]"
              disabled={isSubmitting}
            />
            <span class="ml-2 text-sm text-gray-700">{$_('activity.create.typeIndividual')}</span>
          </label>
          <label class="flex items-center">
            <input
              type="radio"
              bind:group={activityType}
              value="group"
              class="h-4 w-4 text-[#2271b3] focus:ring-[#2271b3] focus:ring-offset-0 border-[#2271b3]"
              disabled={isSubmitting}
            />
            <span class="ml-2 text-sm text-gray-700">{$_('activity.create.typeGroup')}</span>
          </label>
        </div>
      </fieldset>
    </div>
    
    <!-- Tamaño máximo del grupo (solo si es actividad en grupo) -->
    {#if activityType === 'group'}
      <div>
        <label for="maxGroupSize" class="block text-sm font-medium text-gray-700 mb-1">
          {$_('activity.create.maxGroupSizeLabel')} <span class="text-red-500">*</span>
        </label>
        <input
          type="number"
          id="maxGroupSize"
          bind:value={maxGroupSize}
          min="2"
          max="20"
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] {errors.maxGroupSize ? 'border-red-500' : ''}"
          disabled={isSubmitting}
        />
        {#if errors.maxGroupSize}
          <p class="mt-1 text-sm text-red-600">{errors.maxGroupSize}</p>
        {:else}
          <p class="mt-1 text-sm text-gray-500">{$_('activity.create.maxGroupSizeHint')}</p>
        {/if}
      </div>
    {/if}
    
    <!-- Fecha y hora límite -->
    <div>
      <label for="deadline" class="block text-sm font-medium text-gray-700 mb-1">
        {$_('activity.create.deadlineLabel')} <span class="text-red-500">*</span>
      </label>     
      <input
        type="datetime-local"
        id="deadline"
        bind:value={deadline}
        min={new Date().toISOString().slice(0, 16)}
        class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3] {errors.deadline ? 'border-red-500' : ''}"
        disabled={isSubmitting}
      />
      {#if errors.deadline}
        <p class="mt-1 text-sm text-red-600">{errors.deadline}</p>
      {/if}
    </div>
    
    <!-- Configuración del Evaluador Automático -->
    <div class="border-t border-gray-200 pt-4">
      <h3 class="text-sm font-medium text-gray-700 mb-1">{$_('activity.create.evaluatorTitle')}</h3>
      <p class="text-xs text-gray-500 mb-3">{$_('activity.create.evaluatorSubtitle')}</p>
      <div>
        <label for="evaluatorId" class="block text-sm font-medium text-gray-700 mb-1">
          {$_('activity.create.evaluatorIdLabel')}
        </label>
        <input
          type="text"
          id="evaluatorId"
          bind:value={evaluatorId}
          class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-[#2271b3] focus:border-[#2271b3]"
          placeholder={$_('activity.create.evaluatorIdPlaceholder')}
          disabled={isSubmitting}
        />
      </div>
    </div>
    
    <!-- Botones -->
    <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
      <button
        type="button"
        onclick={resetForm}
        class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3]"
        disabled={isSubmitting}
      >
        {$_('common.clear')}
      </button>
      <button
        type="submit"
        class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-[#2271b3] hover:bg-[#195a91] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#2271b3] disabled:opacity-50 disabled:cursor-not-allowed"
        disabled={isSubmitting}
      >
        {isSubmitting ? $_('activity.create.creating') : $_('activity.create.createButton')}
      </button>
    </div>
  </form>
</div>