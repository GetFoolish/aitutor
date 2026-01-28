/**
 * Homework Service - API Client
 *
 * This service provides methods for interacting with the Homework Assistant API.
 * Handles file uploads, homework management, and AI-powered homework assistance.
 *
 * Features:
 * - Multi-format file upload (PDF, images, text, Word docs)
 * - Homework list and detail retrieval
 * - AI-powered homework assistance with conversation history
 * - Homework deletion
 *
 * All methods use JWT authentication via apiUtils
 */

import { apiUtils } from '../lib/api-utils';
import { httpClient } from '../lib/http-client';
import { jwtUtils } from '../lib/jwt-utils';

const HOMEWORK_SERVICE_URL = import.meta.env.VITE_HOMEWORK_SERVICE_URL || 'http://localhost:8004';

// ============================================================================
// Type Definitions
// ============================================================================

export interface UploadResponse {
  homework_id: string;
  file_type: string;
  status: string;
  filename: string;
  file_size: number;
  uploaded_at: string;
}

export interface HomeworkItem {
  homework_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  uploaded_at: string;
}

export interface HomeworkListResponse {
  homework_items: HomeworkItem[];
  total: number;
}

export interface ConversationTurn {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface HomeworkDetailResponse {
  homework_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  uploaded_at: string;
  conversation_history: ConversationTurn[];
  extracted_text?: string;  // Text content extracted from the file
}

export interface AssistRequest {
  homework_id: string;
  question: string;
}

export interface AssistResponse {
  response: string;
  homework_id: string;
  timestamp: string;
}

export interface DeleteResponse {
  success: boolean;
  message: string;
}

export interface SkillDetection {
  skill_name: string;
  skill_id: string;
  confidence: number;
  question_numbers: number[];
  description: string;
}

export interface AnalyzeResponse {
  homework_id: string;
  skills: SkillDetection[];
  total_questions: number;
  analyzed_at: string;
}

// ============================================================================
// Homework Service Class
// ============================================================================

export class HomeworkService {
  /**
   * Upload a homework file
   *
   * Supported formats:
   * - PDF (.pdf)
   * - Images (.jpg, .jpeg, .png, .gif, .bmp)
   * - Text files (.txt)
   * - Word documents (.doc, .docx)
   *
   * @param file - File to upload (max 10MB)
   * @returns UploadResponse with homework_id and metadata
   * @throws Error if upload fails or file is invalid
   */
  async uploadHomework(file: File): Promise<UploadResponse> {
    try {
      // Create FormData for multipart/form-data upload
      const formData = new FormData();
      formData.append('file', file);

      // For file uploads, we need to use httpClient directly to avoid
      // the default Content-Type: application/json header set by apiUtils
      const token = jwtUtils.getToken();

      const response = await httpClient.fetch(`${HOMEWORK_SERVICE_URL}/homework/upload`, {
        method: 'POST',
        body: formData,
        headers: {
          // Only set Authorization, let browser set Content-Type with multipart boundary
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });

      if (!response.ok) {
        // Handle different error status codes with user-friendly messages
        if (response.status === 413) {
          throw new Error('File size exceeds server limit. Please upload a file smaller than 10MB.');
        }
        if (response.status === 415) {
          throw new Error('Unsupported file type. Please upload PDF, JPG, PNG, DOCX, or TXT files.');
        }
        if (response.status === 401 || response.status === 403) {
          throw new Error('Authentication required. Please sign in and try again.');
        }
        if (response.status === 503) {
          throw new Error('Service temporarily unavailable. Please try again in a few moments.');
        }
        if (response.status >= 500) {
          throw new Error('Server error occurred. Please try again later.');
        }

        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }

      const data: UploadResponse = await response.json();
      return data;
    } catch (error) {
      // Handle network errors separately from API errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error. Please check your internet connection and try again.');
      }

      // Re-throw other errors (including our custom error messages)
      throw error;
    }
  }

  /**
   * List all homework for the authenticated user
   *
   * Returns a list of uploaded homework files with metadata.
   * Does not include full extracted text or conversation history.
   *
   * @returns HomeworkListResponse with array of homework items and total count
   * @throws Error if request fails
   */
  async listHomework(): Promise<HomeworkListResponse> {
    try {
      const response = await apiUtils.get(`${HOMEWORK_SERVICE_URL}/homework/list`);

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          throw new Error('Authentication required. Please sign in and try again.');
        }
        if (response.status === 503) {
          throw new Error('Service temporarily unavailable. Please try again in a few moments.');
        }
        if (response.status >= 500) {
          throw new Error('Server error occurred. Please try again later.');
        }

        const errorData = await response.json().catch(() => ({ detail: 'Failed to list homework' }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: HomeworkListResponse = await response.json();
      return data;
    } catch (error) {
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error. Please check your internet connection and try again.');
      }
      throw error;
    }
  }

  /**
   * Get detailed information about a specific homework
   *
   * Includes conversation history but not the full extracted text content.
   *
   * @param homeworkId - Homework ID
   * @returns HomeworkDetailResponse with homework details and conversation history
   * @throws Error if homework not found or request fails
   */
  async getHomework(homeworkId: string): Promise<HomeworkDetailResponse> {
    try {
      const response = await apiUtils.get(`${HOMEWORK_SERVICE_URL}/homework/${homeworkId}`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Homework not found. It may have been deleted.');
        }
        if (response.status === 401 || response.status === 403) {
          throw new Error('Authentication required. Please sign in and try again.');
        }
        if (response.status === 503) {
          throw new Error('Service temporarily unavailable. Please try again in a few moments.');
        }
        if (response.status >= 500) {
          throw new Error('Server error occurred. Please try again later.');
        }

        const errorData = await response.json().catch(() => ({ detail: 'Failed to retrieve homework' }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: HomeworkDetailResponse = await response.json();
      return data;
    } catch (error) {
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error. Please check your internet connection and try again.');
      }
      throw error;
    }
  }

  /**
   * Ask a question about uploaded homework
   *
   * Get AI-powered assistance for homework questions.
   * Maintains conversation history for follow-up questions.
   *
   * @param homeworkId - Homework ID
   * @param question - Question to ask about the homework
   * @returns AssistResponse with AI response, homework_id, and timestamp
   * @throws Error if homework not found or request fails
   */
  async askQuestion(homeworkId: string, question: string): Promise<AssistResponse> {
    try {
      const requestBody: AssistRequest = {
        homework_id: homeworkId,
        question: question,
      };

      const response = await apiUtils.post(`${HOMEWORK_SERVICE_URL}/homework/assist`, requestBody);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Homework not found. It may have been deleted.');
        }
        if (response.status === 401 || response.status === 403) {
          throw new Error('Authentication required. Please sign in and try again.');
        }
        if (response.status === 503) {
          throw new Error('AI service temporarily unavailable. Please try again in a few moments.');
        }
        if (response.status >= 500) {
          throw new Error('Server error occurred. Please try again later.');
        }

        const errorData = await response.json().catch(() => ({ detail: 'Failed to get assistance' }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: AssistResponse = await response.json();
      return data;
    } catch (error) {
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error. Please check your internet connection and try again.');
      }
      throw error;
    }
  }

  /**
   * Analyze homework to detect math skills
   *
   * Examines extracted questions to identify specific math skills being practiced
   * (e.g., addition, counting, fractions) and maps them to the skill tracking system.
   *
   * @param homeworkId - Homework ID
   * @returns AnalyzeResponse with detected skills and question mappings
   * @throws Error if homework not found or analysis fails
   */
  async analyzeHomeworkSkills(homeworkId: string): Promise<AnalyzeResponse> {
    try {
      const response = await apiUtils.post(`${HOMEWORK_SERVICE_URL}/homework/${homeworkId}/analyze`, {});

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Homework not found. It may have been deleted.');
        }
        if (response.status === 401 || response.status === 403) {
          throw new Error('Authentication required. Please sign in and try again.');
        }
        if (response.status === 503) {
          throw new Error('Service temporarily unavailable. Please try again in a few moments.');
        }
        if (response.status >= 500) {
          throw new Error('Server error occurred. Please try again later.');
        }

        const errorData = await response.json().catch(() => ({ detail: 'Failed to analyze skills' }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: AnalyzeResponse = await response.json();
      return data;
    } catch (error) {
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error. Please check your internet connection and try again.');
      }
      throw error;
    }
  }

  /**
   * Delete a homework and its associated file
   *
   * Removes the homework document and GridFS file from MongoDB.
   *
   * @param homeworkId - Homework ID
   * @returns DeleteResponse with success status and message
   * @throws Error if homework not found or deletion fails
   */
  async deleteHomework(homeworkId: string): Promise<DeleteResponse> {
    try {
      const response = await apiUtils.authenticatedFetch(`${HOMEWORK_SERVICE_URL}/homework/${homeworkId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Homework not found. It may have already been deleted.');
        }
        if (response.status === 401 || response.status === 403) {
          throw new Error('Authentication required. Please sign in and try again.');
        }
        if (response.status === 503) {
          throw new Error('Service temporarily unavailable. Please try again in a few moments.');
        }
        if (response.status >= 500) {
          throw new Error('Server error occurred. Please try again later.');
        }

        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete homework' }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: DeleteResponse = await response.json();
      return data;
    } catch (error) {
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error. Please check your internet connection and try again.');
      }
      throw error;
    }
  }

  /**
   * Fetch homework thumbnail image with authentication
   *
   * For PDFs, returns a PNG rendering of the specified page.
   * For images, returns the original image.
   * Used for sidebar preview where CSS overlay positioning needs to work.
   *
   * @param homeworkId - Homework ID
   * @param page - Page number (0-indexed, default 0)
   * @returns Blob containing the PNG thumbnail
   * @throws Error if file not found or request fails
   */
  async getThumbnailBlob(homeworkId: string, page: number = 0): Promise<Blob> {
    try {
      const response = await apiUtils.authenticatedFetch(
        `${HOMEWORK_SERVICE_URL}/homework/${homeworkId}/thumbnail?page=${page}`,
        { method: 'GET' }
      );

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Thumbnail not found.');
        }
        throw new Error(`Failed to fetch thumbnail: ${response.status}`);
      }

      return await response.blob();
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error. Please check your internet connection.');
      }
      throw error;
    }
  }

  /**
   * Fetch homework file content with authentication
   *
   * Downloads the file content and returns it as a Blob.
   * Used for displaying image thumbnails and PDF previews.
   *
   * @param homeworkId - Homework ID
   * @returns Blob containing the file content
   * @throws Error if file not found or request fails
   */
  async getFileBlob(homeworkId: string): Promise<Blob> {
    try {
      const response = await apiUtils.authenticatedFetch(`${HOMEWORK_SERVICE_URL}/homework/${homeworkId}/file`, {
        method: 'GET',
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('File not found. It may have been deleted.');
        }
        if (response.status === 401 || response.status === 403) {
          throw new Error('Authentication required. Please sign in and try again.');
        }
        if (response.status === 503) {
          throw new Error('Service temporarily unavailable. Please try again in a few moments.');
        }
        if (response.status >= 500) {
          throw new Error('Server error occurred. Please try again later.');
        }
        throw new Error(`Failed to fetch file: ${response.status}`);
      }

      const blob = await response.blob();
      return blob;
    } catch (error) {
      // Handle network errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error. Please check your internet connection and try again.');
      }
      throw error;
    }
  }
}

// Export singleton instance
export const homeworkService = new HomeworkService();
