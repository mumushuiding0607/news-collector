<script setup lang="ts">
import { ref, onMounted } from "vue";
import { getAppConfig, updateAppConfig, getEnvConfig, updateEnvConfig, getSourcesConfig, updateSourcesConfig } from "../../api";

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
  comments_enabled: false,
  share_enabled: false,
});

const envForm = ref({
  ADMIN_EMAIL: "",
  SMTP_HOST: "",
  SMTP_PORT: "",
  SMTP_USER: "",
});

const aiNewsForm = ref({
  crawNumPerSource: 30,
  maxConsecutiveNonToday: 10,
  maxArticlesPerSource: 500,
  maxSourceConcurrency: 5,
  htmlFallbackArticles: 50,
  skipIfNoDate: false,
  titleMinLength: 10,
  days: 30,
});

const stockNewsForm = ref({
  crawNumPerSource: 30,
  maxConsecutiveNonToday: 10,
  maxArticlesPerSource: 500,
  maxSourceConcurrency: 5,
  htmlFallbackArticles: 50,
  skipIfNoDate: false,
  titleMinLength: 10,
  days: 0,
});

const sourcesForm = ref({
  llmBatchSize: 20,
  llmTimeout: 120,
  llmMaxRetries: 3,
  newsFilterTimeout: 40,
  scorerTimeout: 90,
  findStocksTimeout: 80,
  newsCache: {
    minScore: 5,
    hotNewsMinScore: 8,
    historyDays: 3,
    latestNewsCount: 10,
  },
});

async function fetchConfig() {
  loading.value = true;
  try {
    const [appData, envData, sourcesData] = await Promise.all([
      getAppConfig() as unknown as Record<string, unknown>,
      getEnvConfig() as unknown as Record<string, unknown>,
      getSourcesConfig() as unknown as Record<string, unknown>,
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
        comments_enabled: Boolean(features["comments_enabled"] ?? false),
        share_enabled: Boolean(features["share_enabled"] ?? false),
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
    if (sourcesData) {
      // AI新闻配置
      const aiNews = (sourcesData["AI新闻"] as Record<string, unknown>) || {};
      aiNewsForm.value = {
        crawNumPerSource: (aiNews["crawNumPerSource"] as number) ?? 30,
        maxConsecutiveNonToday: (aiNews["maxConsecutiveNonToday"] as number) ?? 10,
        maxArticlesPerSource: (aiNews["maxArticlesPerSource"] as number) ?? 500,
        maxSourceConcurrency: (aiNews["maxSourceConcurrency"] as number) ?? 5,
        htmlFallbackArticles: (aiNews["htmlFallbackArticles"] as number) ?? 50,
        skipIfNoDate: Boolean(aiNews["skipIfNoDate"]),
        titleMinLength: (aiNews["titleMinLength"] as number) ?? 10,
        days: (aiNews["days"] as number) ?? 30,
      };

      // 股市新闻配置
      const stockNews = (sourcesData["股市新闻"] as Record<string, unknown>) || {};
      stockNewsForm.value = {
        crawNumPerSource: (stockNews["crawNumPerSource"] as number) ?? 30,
        maxConsecutiveNonToday: (stockNews["maxConsecutiveNonToday"] as number) ?? 10,
        maxArticlesPerSource: (stockNews["maxArticlesPerSource"] as number) ?? 500,
        maxSourceConcurrency: (stockNews["maxSourceConcurrency"] as number) ?? 5,
        htmlFallbackArticles: (stockNews["htmlFallbackArticles"] as number) ?? 50,
        skipIfNoDate: Boolean(stockNews["skipIfNoDate"]),
        titleMinLength: (stockNews["titleMinLength"] as number) ?? 10,
        days: (stockNews["days"] as number) ?? 0,
      };

      // 全局配置
      sourcesForm.value = {
        llmBatchSize: (sourcesData["llmBatchSize"] as number) ?? 20,
        llmTimeout: (sourcesData["llmTimeout"] as number) ?? 120,
        llmMaxRetries: (sourcesData["llmMaxRetries"] as number) ?? 3,
        newsFilterTimeout: (sourcesData["newsFilterTimeout"] as number) ?? 40,
        scorerTimeout: (sourcesData["scorerTimeout"] as number) ?? 90,
        findStocksTimeout: (sourcesData["findStocksTimeout"] as number) ?? 80,
        newsCache: {
          minScore: (sourcesData["newsCache"] as Record<string, unknown>)?.["minScore"] as number ?? 5,
          hotNewsMinScore: (sourcesData["newsCache"] as Record<string, unknown>)?.["hotNewsMinScore"] as number ?? 8,
          historyDays: (sourcesData["newsCache"] as Record<string, unknown>)?.["historyDays"] as number ?? 3,
          latestNewsCount: (sourcesData["newsCache"] as Record<string, unknown>)?.["latestNewsCount"] as number ?? 10,
        },
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
    const { subscription_enabled, comments_enabled, share_enabled, ...rest } = appForm.value;
    const payload = {
      ...rest,
      features: {
        subscription_enabled,
        comments_enabled,
        share_enabled,
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

async function handleSaveSources() {
  saving.value = true;
  try {
    const payload = {
      "AI新闻": { ...aiNewsForm.value },
      "股市新闻": { ...stockNewsForm.value },
      ...sourcesForm.value,
    };
    await updateSourcesConfig(payload);
    alert("Sources 配置保存成功");
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
            <el-form-item label="评论功能">
              <el-switch v-model="appForm.comments_enabled" />
            </el-form-item>
            <el-form-item label="分享功能">
              <el-switch v-model="appForm.share_enabled" />
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

      <el-tab-pane label="Sources 配置" name="sources">
        <el-card style="background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px">
          <el-form :model="sourcesForm" label-width="160px" style="max-width: 800px">

            <el-divider content-position="left">AI新闻采集参数</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="每源采集数量">
                  <el-input-number v-model="aiNewsForm.crawNumPerSource" :min="1" :max="1000" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="最大连续非当日数">
                  <el-input-number v-model="aiNewsForm.maxConsecutiveNonToday" :min="1" :max="100" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="每源硬上限">
                  <el-input-number v-model="aiNewsForm.maxArticlesPerSource" :min="1" :max="1000" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="跨源并发数">
                  <el-input-number v-model="aiNewsForm.maxSourceConcurrency" :min="1" :max="20" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="HTML Fallback文章数">
                  <el-input-number v-model="aiNewsForm.htmlFallbackArticles" :min="1" :max="200" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="标题最短长度">
                  <el-input-number v-model="aiNewsForm.titleMinLength" :min="1" :max="50" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="日期范围（天）">
                  <el-input-number v-model="aiNewsForm.days" :min="0" :max="365" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="无日期时跳过">
                  <el-switch v-model="aiNewsForm.skipIfNoDate" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">股市新闻采集参数</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="每源采集数量">
                  <el-input-number v-model="stockNewsForm.crawNumPerSource" :min="1" :max="1000" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="最大连续非当日数">
                  <el-input-number v-model="stockNewsForm.maxConsecutiveNonToday" :min="1" :max="100" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="每源硬上限">
                  <el-input-number v-model="stockNewsForm.maxArticlesPerSource" :min="1" :max="1000" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="跨源并发数">
                  <el-input-number v-model="stockNewsForm.maxSourceConcurrency" :min="1" :max="20" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="HTML Fallback文章数">
                  <el-input-number v-model="stockNewsForm.htmlFallbackArticles" :min="1" :max="200" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="标题最短长度">
                  <el-input-number v-model="stockNewsForm.titleMinLength" :min="1" :max="50" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="日期范围（天）">
                  <el-input-number v-model="stockNewsForm.days" :min="0" :max="365" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="无日期时跳过">
                  <el-switch v-model="stockNewsForm.skipIfNoDate" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left">LLM 参数</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="LLM 批次大小">
                  <el-input-number v-model="sourcesForm.llmBatchSize" :min="1" :max="200" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="LLM 超时（秒）">
                  <el-input-number v-model="sourcesForm.llmTimeout" :min="10" :max="600" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="LLM 最大重试">
              <el-input-number v-model="sourcesForm.llmMaxRetries" :min="0" :max="10" />
            </el-form-item>

            <el-divider content-position="left">超时配置</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="新闻过滤超时（秒）">
                  <el-input-number v-model="sourcesForm.newsFilterTimeout" :min="5" :max="300" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="评分超时（秒）">
                  <el-input-number v-model="sourcesForm.scorerTimeout" :min="5" :max="300" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="找股票超时（秒）">
              <el-input-number v-model="sourcesForm.findStocksTimeout" :min="5" :max="300" style="width: 100%" />
            </el-form-item>

            <el-divider content-position="left">缓存配置</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="最低分数">
                  <el-input-number v-model="sourcesForm.newsCache.minScore" :min="0" :max="100" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="热点新闻最低分">
                  <el-input-number v-model="sourcesForm.newsCache.hotNewsMinScore" :min="0" :max="100" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="历史天数">
                  <el-input-number v-model="sourcesForm.newsCache.historyDays" :min="1" :max="30" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="最新新闻显示数量">
                  <el-input-number v-model="sourcesForm.newsCache.latestNewsCount" :min="1" :max="100" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveSources">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>
