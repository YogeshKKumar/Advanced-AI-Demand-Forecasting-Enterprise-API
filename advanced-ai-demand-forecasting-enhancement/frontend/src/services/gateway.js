import axios from "axios";

const gateway = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8100/api/v1",
  headers: { Accept: "application/json" }
});

gateway.interceptors.request.use((config) => {
  const token = localStorage.getItem("enhancement_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default gateway;
