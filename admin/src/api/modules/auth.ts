import api from "../client";

export const login = (phone: string, code: string) =>
  api.post("/api/auth/login_code", { phone, code });

export const loginPassword = (email: string, password: string) =>
  api.post("/api/auth/login_password", { email, password });

export const sendCode = (phone: string) =>
  api.post("/api/auth/send_code", { phone });
