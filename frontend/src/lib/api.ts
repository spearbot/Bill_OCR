import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(e);
  }
);

export const authApi = {
  login: (email: string, password: string) => api.post("/api/auth/login", { email, password }),
  register: (name: string, email: string, password: string) =>
    api.post("/api/auth/register", { name, email, password }),
  getMe: () => api.get("/api/auth/me"),
  updateMe: (data: any) => api.put("/api/auth/me", data),
};

export const billsApi = {
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/api/bills/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
  },
  list: (params?: any) => api.get("/api/bills/", { params }),
  get: (id: string) => api.get(`/api/bills/${id}`),
  update: (id: string, data: any) => api.put(`/api/bills/${id}`, data),
  delete: (id: string) => api.delete(`/api/bills/${id}`),
  getImage: (id: string) => `${API_BASE_URL}/api/bills/${id}/image`,
  getItems: (id: string) => api.get(`/api/bills/${id}/items`),
};

export const datasetApi = {
  list: (params?: { page?: number; page_size?: number; search?: string }) =>
    api.get("/api/bills/dataset/items", { params }),
  exportCsv: (params?: any) =>
    api.get("/api/bills/export/csv", { params, responseType: "blob" }),
  exportXlsx: (params?: any) =>
    api.get("/api/bills/export/xlsx", { params, responseType: "blob" }),
};

export const adminApi = {
  stats: () => api.get("/api/admin/stats"),
  users: () => api.get("/api/admin/users"),
  updateUser: (id: string, data: any) => api.put(`/api/admin/users/${id}`, data),
  deleteUser: (id: string) => api.delete(`/api/admin/users/${id}`),
};
