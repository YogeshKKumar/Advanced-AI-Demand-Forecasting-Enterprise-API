import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
  headers: { Accept: "application/json" }
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("enterprise_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("enterprise_token");
      localStorage.removeItem("enterprise_user");
    }
    return Promise.reject(error);
  }
);

export default api;
