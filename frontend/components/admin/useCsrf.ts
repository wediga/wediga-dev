"use client";

import { useEffect, useState } from "react";
import { getCsrfToken } from "@/lib/adminClient";

// Fetch the CSRF token once on mount. The admin forms send it on every write.
export function useCsrf(): string {
  const [token, setToken] = useState("");
  useEffect(() => {
    getCsrfToken()
      .then(setToken)
      .catch(() => setToken(""));
  }, []);
  return token;
}
