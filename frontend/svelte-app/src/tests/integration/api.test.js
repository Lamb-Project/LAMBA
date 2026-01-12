import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fetchLTIData, checkPendingActivity } from '$lib/auth.js';

describe('API Integration - fetchLTIData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches LTI data successfully', async () => {
    const mockLTIData = {
      lis_person_name_full: 'John Doe',
      roles: 'Instructor',
      resource_link_id: 'activity123',
      ext_user_username: 'jdoe'
    };

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ success: true, data: mockLTIData })
      })
    );

    const result = await fetchLTIData();

    expect(global.fetch).toHaveBeenCalledWith('/api/lti-data', {
      credentials: 'include'
    });
    expect(result.success).toBe(true);
    expect(result.data).toEqual(mockLTIData);
  });

  it('handles 401 unauthorized error', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 401
      })
    );

    const result = await fetchLTIData();

    expect(result.success).toBe(false);
    expect(result.error).toBe('No active LTI session');
  });

  it('handles other HTTP errors', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500
      })
    );

    const result = await fetchLTIData();

    expect(result.success).toBe(false);
    expect(result.error).toBe('Failed to fetch LTI data');
  });

  it('handles connection errors', async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error('Network error')));

    const result = await fetchLTIData();

    expect(result.success).toBe(false);
    expect(result.error).toBe('Connection error');
  });

  it('handles failed response with success=false', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ success: false })
      })
    );

    const result = await fetchLTIData();

    expect(result.success).toBe(false);
    expect(result.error).toBe('Failed to retrieve LTI data');
  });

  it('includes credentials in the request', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: {} })
      })
    );

    await fetchLTIData();

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/lti-data',
      expect.objectContaining({
        credentials: 'include'
      })
    );
  });
});

describe('API Integration - checkPendingActivity', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns false when user is not teacher or admin', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ 
          success: true, 
          data: { roles: 'Learner' } 
        })
      })
    );

    const result = await checkPendingActivity();

    expect(result.hasPendingActivity).toBe(false);
  });

  it('returns false when no resource_link_id', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ 
          success: true, 
          data: { roles: 'Instructor' } 
        })
      })
    );

    const result = await checkPendingActivity();

    expect(result.hasPendingActivity).toBe(false);
  });

  it('returns false when activity already exists', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ 
          success: true, 
          data: { roles: 'Instructor', resource_link_id: 'activity123' } 
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200
      });

    const result = await checkPendingActivity();

    expect(result.hasPendingActivity).toBe(false);
  });

  it('returns true when activity does not exist (404)', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ 
          success: true, 
          data: { roles: 'Instructor', resource_link_id: 'activity123' } 
        })
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 404
      });

    const result = await checkPendingActivity();

    expect(result.hasPendingActivity).toBe(true);
    expect(result.resourceLinkId).toBe('activity123');
  });

  it('checks activity endpoint with correct resource_link_id', async () => {
    const resourceLinkId = 'test-activity-456';
    
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ 
          success: true, 
          data: { roles: 'Administrator', resource_link_id: resourceLinkId } 
        })
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 404
      });

    const result = await checkPendingActivity();

    expect(global.fetch).toHaveBeenCalledWith(
      `/api/activities/${resourceLinkId}`,
      expect.objectContaining({
        credentials: 'include',
        cache: 'no-cache'
      })
    );
    expect(result.hasPendingActivity).toBe(true);
  });

  it('handles errors when checking activity', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ 
          success: true, 
          data: { roles: 'Instructor', resource_link_id: 'activity123' } 
        })
      })
      .mockRejectedValueOnce(new Error('Network error'));

    const result = await checkPendingActivity();

    expect(result.hasPendingActivity).toBe(false);
  });
});

describe('API Integration - Activity Creation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates activity with correct payload', async () => {
    const mockResponse = {
      success: true,
      activity_id: 'new-activity-123'
    };

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse)
      })
    );

    const activityData = {
      title: 'Test Activity',
      description: 'Test Description',
      activity_type: 'individual',
      max_group_size: null,
      deadline: '2025-12-31T23:59:00Z',
      evaluator_id: null
    };

    const response = await fetch('/api/activities', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(activityData)
    });

    const result = await response.json();

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/activities',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json'
        }),
        body: JSON.stringify(activityData)
      })
    );
    expect(result.success).toBe(true);
    expect(result.activity_id).toBe('new-activity-123');
  });

  it('handles activity creation errors', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ 
          success: false, 
          error: 'Invalid activity data' 
        })
      })
    );

    const activityData = {
      title: '',
      description: 'Test'
    };

    const response = await fetch('/api/activities', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(activityData)
    });

    const result = await response.json();

    expect(response.ok).toBe(false);
    expect(result.success).toBe(false);
    expect(result.error).toBe('Invalid activity data');
  });
});

describe('API Integration - File Upload', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('uploads file with FormData', async () => {
    const mockResponse = {
      success: true,
      file_id: 'file-123',
      filename: 'test.pdf'
    };

    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockResponse)
      })
    );

    const formData = new FormData();
    formData.append('file', new Blob(['test content'], { type: 'application/pdf' }), 'test.pdf');

    const response = await fetch('/api/activities/activity123/submit', {
      method: 'POST',
      body: formData,
      credentials: 'include'
    });

    const result = await response.json();

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/activities/activity123/submit',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: formData
      })
    );
    expect(result.success).toBe(true);
    expect(result.file_id).toBe('file-123');
  });

  it('handles file upload errors', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 413,
        json: () => Promise.resolve({ 
          success: false, 
          error: 'File too large' 
        })
      })
    );

    const formData = new FormData();
    formData.append('file', new Blob(['x'.repeat(20000000)]), 'large-file.pdf');

    const response = await fetch('/api/activities/activity123/submit', {
      method: 'POST',
      body: formData,
      credentials: 'include'
    });

    const result = await response.json();

    expect(response.ok).toBe(false);
    expect(result.error).toBe('File too large');
  });
});
