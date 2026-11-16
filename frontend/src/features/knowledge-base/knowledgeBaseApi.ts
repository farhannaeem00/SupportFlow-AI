
import api from "../../lib/api";

export interface KnowledgeBase {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  document_count: number;
}

export interface KnowledgeDocument {
  id: string;
  organization_id: string;
  knowledge_base_id: string;
  uploaded_by: string | null;
  original_filename: string;
  content_type: string;
  file_size: number;
  checksum: string;
  status: string;
  error_message: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeBaseCreate {
  name: string;
  description?: string | null;
}

export interface KnowledgeBaseUpdate {
  name?: string;
  description?: string | null;
  is_active?: boolean;
}

interface PaginationParams {
  skip?: number;
  limit?: number;
}

export const knowledgeBaseApi = {
  async list(params: PaginationParams = {}): Promise<KnowledgeBase[]> {
    const response = await api.get<KnowledgeBase[]>("/knowledge-bases", {
      params,
    });

    return response.data;
  },

  async get(knowledgeBaseId: string): Promise<KnowledgeBase> {
    const response = await api.get<KnowledgeBase>(
      `/knowledge-bases/${knowledgeBaseId}`,
    );

    return response.data;
  },

  async create(data: KnowledgeBaseCreate): Promise<KnowledgeBase> {
    const response = await api.post<KnowledgeBase>("/knowledge-bases", data);

    return response.data;
  },

  async update(
    knowledgeBaseId: string,
    data: KnowledgeBaseUpdate,
  ): Promise<KnowledgeBase> {
    const response = await api.patch<KnowledgeBase>(
      `/knowledge-bases/${knowledgeBaseId}`,
      data,
    );

    return response.data;
  },

  async delete(knowledgeBaseId: string): Promise<void> {
    await api.delete(`/knowledge-bases/${knowledgeBaseId}`);
  },

  async listDocuments(
    knowledgeBaseId: string,
    params: PaginationParams = {},
  ): Promise<KnowledgeDocument[]> {
    const response = await api.get<KnowledgeDocument[]>(
      `/knowledge-bases/${knowledgeBaseId}/documents`,
      { params },
    );

    return response.data;
  },

  async getDocument(
    knowledgeBaseId: string,
    documentId: string,
  ): Promise<KnowledgeDocument> {
    const response = await api.get<KnowledgeDocument>(
      `/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`,
    );

    return response.data;
  },

  async uploadDocument(
    knowledgeBaseId: string,
    file: File,
  ): Promise<KnowledgeDocument> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post<KnowledgeDocument>(
      `/knowledge-bases/${knowledgeBaseId}/documents`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      },
    );

    return response.data;
  },

  async deleteDocument(
    knowledgeBaseId: string,
    documentId: string,
  ): Promise<void> {
    await api.delete(
      `/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`,
    );
  },
};
