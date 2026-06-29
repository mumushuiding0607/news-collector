import { defineStore } from "pinia";
import { ref } from "vue";
import { login as apiLogin, loginPassword as apiLoginPassword } from "../api";

export const useUserStore = defineStore("user", () => {
  const token = ref(localStorage.getItem("admin_token") || "");
  const userInfo = ref<Record<string, unknown>>({});

  async function login(phone: string, code: string) {
    const data = await apiLogin(phone, code) as unknown as Record<string, unknown>;
    token.value = (data.token as string) || "";
    userInfo.value = (data.user as Record<string, unknown>) || {};
    if (token.value) {
      localStorage.setItem("admin_token", token.value);
    }
    return token.value;
  }

  async function loginByEmail(email: string, password: string) {
    const data = await apiLoginPassword(email, password) as unknown as Record<string, unknown>;
    token.value = (data.token as string) || "";
    userInfo.value = (data.user as Record<string, unknown>) || {};
    if (token.value) {
      localStorage.setItem("admin_token", token.value);
    }
    return token.value;
  }

  async function loginByPhoneCode(phone: string, code: string) {
    return login(phone, code);
  }

  function logout() {
    token.value = "";
    userInfo.value = {};
    localStorage.removeItem("admin_token");
  }

  return { token, userInfo, login, loginByEmail, loginByPhoneCode, logout };
});