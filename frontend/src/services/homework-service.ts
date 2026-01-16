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
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(errorData.detail || `Upload failed with status ${response.status}`);
      }

      const data: UploadResponse = await response.json();
      console.log(`Homework uploaded successfully: ${data.homework_id}`);
      return data;
    } catch (error) {
      console.error('Error uploading homework:', error);
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
        const errorData = await response.json().catch(() => ({ detail: 'Failed to list homework' }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: HomeworkListResponse = await response.json();
      console.log(`Retrieved ${data.total} homework items`);
      return data;
    } catch (error) {
      console.error('Error listing homework:', error);
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
          throw new Error('Homework not found');
        }
        const errorData = await response.json().catch(() => ({ detail: 'Failed to retrieve homework' }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: HomeworkDetailResponse = await response.json();
      console.log(`Retrieved homework details for ${homeworkId}`);
      return data;
    } catch (error) {
      console.error('Error getting homework details:', error);
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
          throw new Error('Homework not found');
        }
        const errorData = await response.json().catch(() => ({ detail: 'Failed to get assistance' }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: AssistResponse = await response.json();
      console.log(`Received AI assistance for homework ${homeworkId}`);
      return data;
    } catch (error) {
      console.error('Error asking question:', error);
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
          throw new Error('Homework not found');
        }
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete homework' }));
        throw new Error(errorData.detail || `Request failed with status ${response.status}`);
      }

      const data: DeleteResponse = await response.json();
      console.log(`Homework ${homeworkId} deleted successfully`);
      return data;
    } catch (error) {
      console.error('Error deleting homework:', error);
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
          throw new Error('File not found');
        }
        throw new Error(`Failed to fetch file: ${response.status}`);
      }

      const blob = await response.blob();
      return blob;
    } catch (error) {
      console.error('Error fetching file:', error);
      throw error;
    }
  }
}

// Export singleton instance
export const homeworkService = new HomeworkService();
