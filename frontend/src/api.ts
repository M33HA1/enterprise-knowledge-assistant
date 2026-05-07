import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8000/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("eka_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh access token on 401, then retry the original request once
let _refreshing = false;
let _refreshQueue: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;

    // Only attempt refresh on 401, and not on the refresh endpoint itself
    if (
      error.response?.status !== 401 ||
      original._retried ||
      original.url?.includes("/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem("eka_refresh_token");
    if (!refreshToken) {
      // No refresh token — clear storage and let the app handle logout
      localStorage.removeItem("eka_access_token");
      return Promise.reject(error);
    }

    original._retried = true;

    if (_refreshing) {
      // Queue this request until the in-flight refresh completes
      return new Promise((resolve) => {
        _refreshQueue.push((newToken: string) => {
          original.headers.Authorization = `Bearer ${newToken}`;
          resolve(api.request(original));
        });
      });
    }

    _refreshing = true;
    try {
      const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });
      const newToken: string = res.data.access_token;
      localStorage.setItem("eka_access_token", newToken);
      if (res.data.refresh_token) {
        localStorage.setItem("eka_refresh_token", res.data.refresh_token);
      }

      // Flush queued requests
      _refreshQueue.forEach((cb) => cb(newToken));
      _refreshQueue = [];

      original.headers.Authorization = `Bearer ${newToken}`;
      return api.request(original);
    } catch {
      // Refresh failed — clear tokens so the app redirects to login
      localStorage.removeItem("eka_access_token");
      localStorage.removeItem("eka_refresh_token");
      _refreshQueue = [];
      return Promise.reject(error);
    } finally {
      _refreshing = false;
    }
  },
);
