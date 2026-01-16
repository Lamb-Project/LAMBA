import { describe, it, expect } from 'vitest';
import { isStudentRole, isTeacherOrAdminRole } from '$lib/auth.js';

describe('Auth Utilities', () => {
  describe('isStudentRole', () => {
    it('returns true for Learner role', () => {
      expect(isStudentRole('Learner')).toBe(true);
    });

    it('returns true for Student role', () => {
      expect(isStudentRole('Student')).toBe(true);
    });

    it('returns true for learner (lowercase)', () => {
      expect(isStudentRole('learner')).toBe(true);
    });

    it('returns true for mixed case student', () => {
      expect(isStudentRole('STUDENT')).toBe(true);
    });

    it('returns true when role contains learner among other roles', () => {
      expect(isStudentRole('Learner,Member')).toBe(true);
    });

    it('returns false for Teacher role', () => {
      expect(isStudentRole('Teacher')).toBe(false);
    });

    it('returns false for Instructor role', () => {
      expect(isStudentRole('Instructor')).toBe(false);
    });

    it('returns false for null', () => {
      expect(isStudentRole(null)).toBe(false);
    });

    it('returns false for undefined', () => {
      expect(isStudentRole(undefined)).toBe(false);
    });

    it('returns false for empty string', () => {
      expect(isStudentRole('')).toBe(false);
    });
  });

  describe('isTeacherOrAdminRole', () => {
    it('returns true for Administrator role', () => {
      expect(isTeacherOrAdminRole('Administrator')).toBe(true);
    });

    it('returns true for Instructor role', () => {
      expect(isTeacherOrAdminRole('Instructor')).toBe(true);
    });

    it('returns true for Teacher role', () => {
      expect(isTeacherOrAdminRole('Teacher')).toBe(true);
    });

    it('returns true for Admin role', () => {
      expect(isTeacherOrAdminRole('Admin')).toBe(true);
    });

    it('returns true for administrator (lowercase)', () => {
      expect(isTeacherOrAdminRole('administrator')).toBe(true);
    });

    it('returns true for INSTRUCTOR (uppercase)', () => {
      expect(isTeacherOrAdminRole('INSTRUCTOR')).toBe(true);
    });

    it('returns true when role contains instructor among other roles', () => {
      expect(isTeacherOrAdminRole('Instructor,Member')).toBe(true);
    });

    it('returns false for Student role', () => {
      expect(isTeacherOrAdminRole('Student')).toBe(false);
    });

    it('returns false for Learner role', () => {
      expect(isTeacherOrAdminRole('Learner')).toBe(false);
    });

    it('returns false for null', () => {
      expect(isTeacherOrAdminRole(null)).toBe(false);
    });

    it('returns false for undefined', () => {
      expect(isTeacherOrAdminRole(undefined)).toBe(false);
    });

    it('returns false for empty string', () => {
      expect(isTeacherOrAdminRole('')).toBe(false);
    });
  });
});
