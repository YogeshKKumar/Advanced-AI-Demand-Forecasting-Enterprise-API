import React, { createContext, useContext, useMemo, useState } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("enterprise_user") || "null"));
  const [busy, setBusy] = useState(false);

  const authenticate = async (mode, payload) => {
    setBusy(true);
    try {
      const { data } = await api.post(mode === "register" ? "/auth/register" : "/auth/login", payload);
      localStorage.setItem("enterprise_token", data.access_token);
      localStorage.setItem("enterprise_user", JSON.stringify(data.user));
      setUser(data.user);
      return data.user;
    } finally {
      setBusy(false);
    }
  };

  const setUserFromProfile = (nextUser) => {
    localStorage.setItem("enterprise_user", JSON.stringify(nextUser));
    setUser(nextUser);
  };

  const logout = () => {
    localStorage.removeItem("enterprise_token");
    localStorage.removeItem("enterprise_user");
    setUser(null);
  };

  const value = useMemo(() => ({ user, busy, authenticate, logout, setUserFromProfile }), [user, busy]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}



