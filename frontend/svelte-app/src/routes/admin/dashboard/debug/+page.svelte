<script>
  import { onMount } from 'svelte';
  import { adminAPI } from '$lib/admin';
  import { _ } from 'svelte-i18n';

  /** @type {any} */
  let lambDebugInfo = $state(null);
  let loading = $state(true);
  let error = $state('');
  
  // Model verification
  let evaluatorId = $state('');
  let verifying = $state(false);
  /** @type {any} */
  let verificationResult = $state(null);
  let verificationError = $state('');

  onMount(async () => {
    await loadLambDebugInfo();
  });

  async function loadLambDebugInfo() {
    loading = true;
    error = '';
    try {
      const response = await adminAPI.getLambDebugInfo();
      if (response.success) {
        lambDebugInfo = response.debug_info;
      } else {
        error = response.error || $_('admin.debug.errorLoading');
      }
    } catch (/** @type {any} */ err) {
      error = err.message || $_('admin.debug.errorLoading');
    } finally {
      loading = false;
    }
  }

  async function verifyModel() {
    if (!evaluatorId.trim()) {
      verificationError = $_('admin.debug.enterEvaluatorId');
      return;
    }
    
    verifying = true;
    verificationError = '';
    verificationResult = null;
    
    try {
      const response = await adminAPI.verifyLambModel(evaluatorId.trim());
      verificationResult = response;
    } catch (/** @type {any} */ err) {
      verificationError = err.message || $_('admin.debug.errorVerifying');
    } finally {
      verifying = false;
    }
  }

  /** @param {boolean} success */
  function getStatusColor(success) {
    return success ? 'text-green-600' : 'text-red-600';
  }

  /** @param {boolean} success */
  function getStatusBg(success) {
    return success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200';
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-3xl font-bold text-gray-900">{$_('admin.debug.title')}</h1>
    <p class="mt-2 text-gray-600">{$_('admin.debug.subtitle')}</p>
  </div>

  {#if error}
    <div class="rounded-md bg-red-50 p-4 border border-red-200">
      <p class="text-sm font-medium text-red-800">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-brand"></div>
    </div>
  {:else if lambDebugInfo}
    <!-- Configuration Section -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h2 class="text-lg font-medium text-gray-900">{$_('admin.debug.configuration')}</h2>
        <button
          onclick={loadLambDebugInfo}
          class="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand"
        >
          🔄 {$_('admin.debug.refresh')}
        </button>
      </div>
      <div class="px-6 py-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="p-4 bg-gray-50 rounded-lg">
            <p class="text-sm font-medium text-gray-500">{$_('admin.debug.lambApiUrl')}</p>
            <p class="mt-1 text-sm font-mono text-gray-900 break-all">
              {lambDebugInfo.config?.LAMB_API_URL || 'Not configured'}
            </p>
          </div>
          <div class="p-4 bg-gray-50 rounded-lg">
            <p class="text-sm font-medium text-gray-500">{$_('admin.debug.lambToken')}</p>
            <p class="mt-1 text-sm font-mono text-gray-900">
              {lambDebugInfo.config?.LAMB_BEARER_TOKEN || 'Not configured'}
            </p>
          </div>
          <div class="p-4 bg-gray-50 rounded-lg">
            <p class="text-sm font-medium text-gray-500">{$_('admin.debug.lambTimeout')}</p>
            <p class="mt-1 text-sm font-mono text-gray-900">
              {lambDebugInfo.config?.LAMB_TIMEOUT || 30}s
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Connectivity Test Section -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-medium text-gray-900">{$_('admin.debug.connectivityTest')}</h2>
      </div>
      <div class="px-6 py-4">
        {#if lambDebugInfo.tests?.connectivity}
          {@const conn = lambDebugInfo.tests.connectivity}
          {#if conn.error}
            <div class="p-4 bg-red-50 rounded-lg border border-red-200">
              <div class="flex items-center">
                <span class="text-2xl mr-3">❌</span>
                <div>
                  <p class="font-medium text-red-800">{$_('admin.debug.connectionFailed')}</p>
                  <p class="text-sm text-red-600 mt-1">{conn.error}</p>
                </div>
              </div>
            </div>
          {:else}
            <div class="space-y-4">
              <!-- Status -->
              <div class="p-4 {getStatusBg(conn.status_code === 200)} rounded-lg border">
                <div class="flex items-center">
                  <span class="text-2xl mr-3">{conn.status_code === 200 ? '✅' : '⚠️'}</span>
                  <div>
                    <p class="font-medium {getStatusColor(conn.status_code === 200)}">
                      {$_('admin.debug.httpStatus')}: {conn.status_code}
                    </p>
                    <p class="text-sm text-gray-600 mt-1">
                      URL: <span class="font-mono">{conn.url}</span>
                    </p>
                  </div>
                </div>
              </div>

              <!-- JSON Parsing -->
              <div class="p-4 {getStatusBg(conn.json_parsed)} rounded-lg border">
                <div class="flex items-center">
                  <span class="text-2xl mr-3">{conn.json_parsed ? '✅' : '❌'}</span>
                  <div>
                    <p class="font-medium {getStatusColor(conn.json_parsed)}">
                      {$_('admin.debug.jsonParsing')}: {conn.json_parsed ? $_('admin.debug.success') : $_('admin.debug.failed')}
                    </p>
                    {#if conn.json_error}
                      <p class="text-sm text-red-600 mt-1">{conn.json_error}</p>
                    {/if}
                  </div>
                </div>
              </div>

              <!-- Available Models -->
              {#if conn.available_models}
                <div class="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p class="font-medium text-blue-800 mb-2">
                    {$_('admin.debug.availableModels')} ({conn.models_count || 0})
                  </p>
                  {#if conn.available_models.length > 0}
                    <div class="max-h-60 overflow-y-auto">
                      <div class="space-y-1">
                        {#each conn.available_models as model}
                          <div class="px-2 py-1 bg-white rounded text-sm font-mono text-gray-700">
                            {model}
                          </div>
                        {/each}
                      </div>
                    </div>
                  {:else}
                    <p class="text-sm text-blue-600">{$_('admin.debug.noModelsFound')}</p>
                  {/if}
                </div>
              {/if}

              <!-- Response Details -->
              {#if conn.response_preview}
                <details class="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <summary class="cursor-pointer font-medium text-gray-700">
                    {$_('admin.debug.rawResponse')} ({conn.response_length} bytes)
                  </summary>
                  <pre class="mt-2 p-2 bg-gray-100 rounded text-xs overflow-x-auto">{conn.response_preview}</pre>
                </details>
              {/if}
            </div>
          {/if}
        {:else}
          <p class="text-gray-500">{$_('admin.debug.noTestResults')}</p>
        {/if}
      </div>
    </div>

    <!-- Model Verification Section -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-medium text-gray-900">{$_('admin.debug.verifyModel')}</h2>
        <p class="text-sm text-gray-500 mt-1">{$_('admin.debug.verifyModelDescription')}</p>
      </div>
      <div class="px-6 py-4 space-y-4">
        <div class="flex gap-4">
          <div class="flex-1">
            <label for="evaluatorId" class="block text-sm font-medium text-gray-700 mb-1">
              {$_('admin.debug.evaluatorId')}
            </label>
            <input
              id="evaluatorId"
              type="text"
              bind:value={evaluatorId}
              placeholder={$_('admin.debug.evaluatorIdPlaceholder')}
              class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-brand focus:border-brand"
              onkeydown={(e) => e.key === 'Enter' && verifyModel()}
            />
          </div>
          <div class="flex items-end">
            <button
              onclick={verifyModel}
              disabled={verifying}
              class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-brand hover:bg-brand-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {#if verifying}
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {$_('admin.debug.verifying')}
              {:else}
                🔍 {$_('admin.debug.verify')}
              {/if}
            </button>
          </div>
        </div>

        {#if verificationError}
          <div class="p-4 bg-red-50 rounded-lg border border-red-200">
            <p class="text-sm text-red-800">{verificationError}</p>
          </div>
        {/if}

        {#if verificationResult}
          <div class="p-4 {getStatusBg(verificationResult.verification_result?.success)} rounded-lg border">
            <div class="space-y-2">
              <div class="flex items-center">
                <span class="text-2xl mr-3">
                  {verificationResult.verification_result?.success ? '✅' : '❌'}
                </span>
                <div>
                  <p class="font-medium {getStatusColor(verificationResult.verification_result?.success)}">
                    {verificationResult.verification_result?.success 
                      ? $_('admin.debug.modelFound') 
                      : $_('admin.debug.modelNotFound')}
                  </p>
                </div>
              </div>
              
              <div class="pl-11 space-y-1 text-sm">
                <p><span class="text-gray-500">{$_('admin.debug.evaluatorId')}:</span> <span class="font-mono">{verificationResult.evaluator_id}</span></p>
                <p><span class="text-gray-500">{$_('admin.debug.modelId')}:</span> <span class="font-mono">{verificationResult.model_id}</span></p>
                {#if verificationResult.verification_result?.message}
                  <p class="text-green-600">{verificationResult.verification_result.message}</p>
                {/if}
                {#if verificationResult.verification_result?.error}
                  <p class="text-red-600">{verificationResult.verification_result.error}</p>
                {/if}
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>

    <!-- Help Section -->
    <div class="bg-blue-50 rounded-lg shadow overflow-hidden border border-blue-200">
      <div class="px-6 py-4">
        <h3 class="text-lg font-medium text-blue-900 mb-2">{$_('admin.debug.helpTitle')}</h3>
        <div class="text-sm text-blue-800 space-y-2">
          <p>{$_('admin.debug.helpText1')}</p>
          <p>{$_('admin.debug.helpText2')}</p>
          <ul class="list-disc list-inside ml-2 space-y-1">
            <li>{$_('admin.debug.helpItem1')}</li>
            <li>{$_('admin.debug.helpItem2')}</li>
            <li>{$_('admin.debug.helpItem3')}</li>
            <li>{$_('admin.debug.helpItem4')}</li>
          </ul>
        </div>
      </div>
    </div>
  {/if}
</div>
