/**
 * Admin authentication and API service
 */

const API_BASE_URL = '/api/admin';

export const adminAuth = {
  /**
   * @param {string} username
   * @param {string} password
   */
  async login(username, password) {
    const response = await fetch('/api/admin/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al iniciar sesión');
    }

    return await response.json();
  },

  async logout() {
    const response = await fetch('/api/admin/logout', {
      method: 'POST',
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error al cerrar sesión');
    }

    return await response.json();
  },

  async checkSession() {
    try {
      const response = await fetch('/api/admin/check-session', {
        credentials: 'include'
      });

      if (!response.ok) {
        return null;
      }

      return await response.json();
    } catch (error) {
      return null;
    }
  }
};

export const adminAPI = {
  async getStatistics() {
    const response = await fetch(`${API_BASE_URL}/statistics`, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error obteniendo estadísticas');
    }

    return await response.json();
  },

  async getMoodleInstances() {
    const response = await fetch(`${API_BASE_URL}/moodle-instances`, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error obteniendo instancias Moodle');
    }

    return await response.json();
  },

  async getCourses() {
    const response = await fetch(`${API_BASE_URL}/courses`, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error obteniendo cursos');
    }

    return await response.json();
  },

  async getActivities() {
    const response = await fetch(`${API_BASE_URL}/activities`, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error obteniendo actividades');
    }

    return await response.json();
  },

  async getUsers() {
    const response = await fetch(`${API_BASE_URL}/users`, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error obteniendo usuarios');
    }

    return await response.json();
  },

  async getSubmissions() {
    const response = await fetch(`${API_BASE_URL}/submissions`, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error obteniendo entregas');
    }

    return await response.json();
  },

  async getFiles() {
    const response = await fetch(`${API_BASE_URL}/files`, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error obteniendo ficheros');
    }

    return await response.json();
  },

  async getGrades() {
    const response = await fetch(`${API_BASE_URL}/grades`, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error obteniendo calificaciones');
    }

    return await response.json();
  },

  async getLambDebugInfo() {
    const response = await fetch(`${API_BASE_URL}/debug/lamb`, {
      credentials: 'include'
    });

    if (!response.ok) {
      throw new Error('Error obteniendo información de debug LAMB');
    }

    return await response.json();
  },

  async verifyLambModel(evaluatorId) {
    const response = await fetch(`${API_BASE_URL}/debug/lamb/verify-model`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ evaluator_id: evaluatorId })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error verificando modelo LAMB');
    }

    return await response.json();
  }
};
