import React, { createContext, useContext, useMemo, useState } from "react";
import gateway from "../services/gateway";

const IdentityContext = createContext(null);

export function IdentityProvider({ children }) {
  const [account, setAccount] = useState(() => JSON.parse(localStorage.getItem("enhancement_account") || "null"));
  const [working, setWorking] = useState(false);

  const enter = async (mode, form) => {
    setWorking(true);
    try {
      const endpoint = mode === "signup" ? "/session/signup" : "/session/signin";
      const { data } = await gateway.post(endpoint, form);
      localStorage.setItem("enhancement_token", data.access_token);
      localStorage.setItem("enhancement_account", JSON.stringify(data.account));
      setAccount(data.account);
    } finally {
      setWorking(false);
    }
  };

  const leave = () => {
    localStorage.removeItem("enhancement_token");
    localStorage.removeItem("enhancement_account");
    setAccount(null);
  };

  const value = useMemo(() => ({ account, working, enter, leave }), [account, working]);
  return <IdentityContext.Provider value={value}>{children}</IdentityContext.Provider>;
}

export function useIdentity() {
  return useContext(IdentityContext);
}
