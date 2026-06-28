<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "../../stores/user";

const router = useRouter();
const userStore = useUserStore();

const loginMode = ref("email"); // "email" | "code"
const email = ref("");
const password = ref("");
const phone = ref("");
const code = ref("");
const loading = ref(false);

async function handleLogin() {
  loading.value = true;
  try {
    if (loginMode.value === "email") {
      if (!email.value || !password.value) return;
      await userStore.loginByEmail(email.value, password.value);
    } else {
      if (!phone.value || !code.value) return;
      await userStore.loginByPhoneCode(phone.value, code.value);
    }
    router.push("/dashboard");
  } catch (e) {
    alert(e);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div style="display: flex; align-items: center; justify-content: center; height: 100vh; background: var(--bg)">
    <el-card style="width: 360px; background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px">
      <template #header>
        <div style="text-align: center; color: var(--gold); font-size: 20px; font-weight: bold">
          新闻风向标 · 管理员登录
        </div>
      </template>

      <el-tabs v-model="loginMode" style="margin-bottom: 16px">
        <el-tab-pane label="邮箱登录" name="email" />
        <el-tab-pane label="手机验证码" name="code" />
      </el-tabs>

      <el-form label-position="top">
        <template v-if="loginMode === 'email'">
          <el-form-item label="邮箱">
            <el-input v-model="email" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="password" type="password" placeholder="请输入密码" show-password />
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="手机号">
            <el-input v-model="phone" placeholder="请输入手机号" />
          </el-form-item>
          <el-form-item label="验证码">
            <el-input v-model="code" placeholder="请输入验证码" />
          </el-form-item>
        </template>
        <el-button type="primary" style="width: 100%; margin-top: 8px" :loading="loading" @click="handleLogin">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>