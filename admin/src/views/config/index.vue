<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getAppConfig, updateAppConfig, getEnvConfig, updateEnvConfig } from "../../api";

const appConfig = ref<Record<string, unknown>>({});
const envConfig = ref<Record<string, unknown>>({});
const loading = ref(false);
const saving = ref(false);
const activeTab = ref("app");

const appForm = ref({
  app_name: "",
  app_subtitle: "",
  subscription_pay_method: "wechat",
  sms_login_enabled: true,
  password_login_enabled: true,
  subscription_enabled: true,
});

const envForm = ref({
  ADMIN_EMAIL: "",
  SMTP_HOST: "",
  SMTP_PORT: "",
  SMTP_USER: "",
});

async function fetchConfig() {
  loading.value = true;
  try {
    const [appData, envData] = await Promise.all([
      getAppConfig() as Promise<Record<string, unknown>>,
      getEnvConfig() as Promise<Record<string, unknown>>,
    ]);
    appConfig.value = appData;
    envConfig.value = envData;

    // 填充表单
    if (appData) {
      const features = (appData["features"] as Record<string, unknown>) || {};
      appForm.value = {
        app_name: (appData["app_name"] as string) || "",
        app_subtitle: (appData["app_subtitle"] as string) || "",
        subscription_pay_method: (appData["subscription_pay_method"] as string) || "wechat",
        sms_login_enabled: Boolean(appData["sms_login_enabled"]),
        password_login_enabled: Boolean(appData["password_login_enabled"]),
        subscription_enabled: Boolean(features["subscription_enabled"] ?? true),
      };
    }
    if (envData) {
      envForm.value = {
        ADMIN_EMAIL: (envData["ADMIN_EMAIL"] as string) || "",
        SMTP_HOST: (envData["SMTP_HOST"] as string) || "",
        SMTP_PORT: (envData["SMTP_PORT"] as string) || "",
        SMTP_USER: (envData["SMTP_USER"] as string) || "",
      };
    }
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function handleSaveApp() {
  saving.value = true;
  try {
    // 提取 features 中的字段，其余为顶级配置
    const { subscription_enabled, ...rest } = appForm.value;
    const payload = {
      ...rest,
      features: {
        subscription_enabled,
      },
    };
    await updateAppConfig(payload);
    alert("应用配置保存成功");
  } catch (e) {
    console.error(e);
    alert("保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleSaveEnv() {
  saving.value = true;
  try {
    await updateEnvConfig(envForm.value);
    alert("环境变量保存成功");
  } catch (e) {
    console.error(e);
    alert("保存失败");
  } finally {
    saving.value = false;
  }
}

onMounted(fetchConfig);
</script>

<template>
  <div>
    <h2 style="color: var(--text-h); margin-bottom: 20px">后台配置</h2>

    <el-tabs v-model="activeTab" type="border-card" style="background: transparent">
      <el-tab-pane label="应用配置" name="app">
        <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
          <el-form :model="appForm" label-width="140px" style="max-width: 600px">
            <el-form-item label="应用名称">
              <el-input v-model="appForm.app_name" placeholder="应用名称" />
            </el-form-item>
            <el-form-item label="应用副标题">
              <el-input v-model="appForm.app_subtitle" placeholder="应用副标题" />
            </el-form-item>
            <el-form-item label="订阅支付方式">
              <el-select v-model="appForm.subscription_pay_method" style="width: 100%">
                <el-option label="微信支付" value="wechat" />
                <el-option label="个人收款码" value="personal" />
                <el-option label="模拟支付" value="mock" />
              </el-select>
            </el-form-item>
            <el-form-item label="短信登录">
              <el-switch v-model="appForm.sms_login_enabled" />
            </el-form-item>
            <el-form-item label="密码登录">
              <el-switch v-model="appForm.password_login_enabled" />
            </el-form-item>
            <el-form-item label="订阅功能">
              <el-switch v-model="appForm.subscription_enabled" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveApp">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="环境变量" name="env">
        <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
          <el-form :model="envForm" label-width="140px" style="max-width: 600px">
            <el-form-item label="管理员邮箱">
              <el-input v-model="envForm.ADMIN_EMAIL" placeholder="admin@example.com" />
            </el-form-item>
            <el-form-item label="SMTP 服务器">
              <el-input v-model="envForm.SMTP_HOST" placeholder="smtp.example.com" />
            </el-form-item>
            <el-form-item label="SMTP 端口">
              <el-input v-model="envForm.SMTP_PORT" placeholder="587" />
            </el-form-item>
            <el-form-item label="SMTP 用户">
              <el-input v-model="envForm.SMTP_USER" placeholder="user@example.com" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveEnv">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>