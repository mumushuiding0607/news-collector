# 指南针AI - 发布自动化

## 目录结构

```
publish/
├── .env               # 所有配置（凭证/路径/版本）
├── load_env.bat       # 环境变量加载器
├── build_app.bat     # 构建 APK
├── deploy_privacy.bat # 部署隐私政策到服务器
├── publish.bat       # 构建 + 发布到小米/华为
└── README.md # 本文件
```

## 快速开始

### 1. 首次配置

**在应用市场创建应用（各一次）**

| 市场 | 网址 | 说明 |
|------|------|------|
| 小米开放平台 | https://open.xiaomi.com | 上传首次 APK 后创建应用 |
| 华为 AppGallery Connect | https://developer.huawei.com/consumer | 同上 |

**将凭证填入 `.env`**

打开 `.env`，填入以下内容：

```env
# 小米
MI_APP_ID=你的小米AppId
MI_API_KEY=你的APIKey
MI_ACCESS_TOKEN=你的AccessToken

# 华为
HW_APP_ID=你的华为AppId
HW_CLIENT_ID=你的ClientId
HW_CLIENT_SECRET=你的ClientSecret
```

### 2. 日常发布

```
双击 publish.bat
   ├→ build_app.bat      构建 APK
   ├→ 发布到小米（如已配置）
   └→ 发布到华为（如已配置）
```

### 3. 单独操作

| 操作 | 脚本 |
|------|------|
| 仅构建 APK | `build_app.bat` |
| 仅部署隐私政策 | `deploy_privacy.bat` |
| 构建+发布 | `publish.bat` |

## 注意事项

- **`.env` 不会提交到 Git**，包含敏感凭证，请妥善保管
- 首次发布需先在应用市场后台**手动上传 APK 创建应用**，获取 AppId
- 小米/华为的 API Token 有有效期（如过期需重新获取）
- 每次发布后需在**开发者后台手动提交审核**（自动化仅上传 APK）

公钥：8cc2b448f3f35022e502c8dd4430d5e552b27106e1d5ee882fcc73b1cb9256a6
证书MD5: 6a4452b32c46727a1577d2fc0a7be79a
