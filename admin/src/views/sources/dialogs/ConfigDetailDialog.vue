<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { CopyDocument } from "@element-plus/icons-vue";
import { updateCrawlConfig } from "../../../api";
import { useMobile } from "../../../composables/useMobile";

const props = defineProps<{
  visible: boolean;
  row: Record<string, unknown> | null;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "saved"): void;
}>();

const { isMobile } = useMobile();

const data = ref<Record<string, unknown>>({});
const editing = ref(false);
const saving = ref(false);
const togglingFlash = ref(false);
const form = ref({ name: "", url_norm: "", list_config: "", content_extract: "", crawl_order: 0, is_flash: 0 });

watch(
  () => props.row,
  (row) => {
    if (row) {
      data.value = { ...row };
      editing.value = false;
      form.value = {
        name: (row.name as string) || "",
        url_norm: (row.url_norm as string) || "",
        list_config: typeof row.list_config === "string" ? (row.list_config as string) : JSON.stringify(row.list_config, null, 2),
        content_extract: typeof row.content_extract === "string" ? (row.content_extract as string) : JSON.stringify(row.content_extract, null, 2),
        crawl_order: (row.crawl_order as number) || 0,
        is_flash: (row.is_flash as number) || 0,
      };
    }
  },
  { immediate: true }
);

function formatJsonOrString(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

async function copyToClipboard(text: string, successMsg: string = "已复制") {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success(successMsg);
  } catch {
    ElMessage.error("复制失败");
  }
}

async function handleSave() {
  saving.value = true;
  try {
    await updateCrawlConfig(data.value.id as number, {
      name: form.value.name,
      url_norm: form.value.url_norm,
      list_config: form.value.list_config,
      content_extract: form.value.content_extract,
      crawl_order: form.value.crawl_order,
      is_flash: form.value.is_flash,
    });
    ElMessage.success("保存成功");
    editing.value = false;
    emit("saved");
  } catch {
    // interceptor shows popup
  } finally {
    saving.value = false;
  }
}

async function toggleFlash() {
  if (!data.value.id) return;
  const next = data.value.is_flash ? 0 : 1;
  togglingFlash.value = true;
  try {
    await updateCrawlConfig(data.value.id as number, { is_flash: next });
    data.value.is_flash = next;
    form.value.is_flash = next;
    ElMessage.success(next ? "已设为快讯" : "已取消快讯");
    emit("saved");
  } catch {
    // interceptor shows popup
  } finally {
    togglingFlash.value = false;
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="(v: boolean) => emit('update:visible', v)"
    :title="`配置详情 - ${data.name || ''}`"
    :fullscreen="isMobile"
    :width="isMobile ? '100%' : '700px'"
  >
    <div :style="isMobile ? '' : 'max-height: 60vh; overflow-y: auto'">
      <div v-if="!editing">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ data.id }}</el-descriptions-item>
          <el-descriptions-item label="名称">{{ data.name }}</el-descriptions-item>
          <el-descriptions-item label="URL" :span="2">
            <div style="display: flex; align-items: center; gap: 8px">
              <span style="flex: 1; word-break: break-all">{{ data.url_norm }}</span>
              <el-button size="small" link @click="copyToClipboard((data.url_norm as string) || '', 'URL已复制')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="类型">{{ data.source_type || 'html' }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ data.crawl_order }}</el-descriptions-item>
          <el-descriptions-item label="已确认">
            <el-tag :type="data.checked ? 'success' : 'info'" size="small">
              {{ data.checked ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="快讯">
            <div style="display: flex; align-items: center; gap: 8px">
              <el-tag v-if="data.is_flash" type="warning" size="small">是</el-tag>
              <span v-else style="color: var(--text-muted)">否</span>
              <el-button
                size="small"
                type="primary"
                link
                :loading="togglingFlash"
                @click="toggleFlash"
              >
                {{ data.is_flash ? '取消' : '设为快讯' }}
              </el-button>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">{{ data.created_at }}</el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">{{ data.updated_at }}</el-descriptions-item>
          <el-descriptions-item label="列表配置" :span="2">
            <div v-if="data.list_config" style="display: flex; align-items: flex-start; gap: 8px">
              <pre style="flex: 1; margin: 0; white-space: pre-wrap; word-break: break-all; font-size: 12px">{{ formatJsonOrString(data.list_config) }}</pre>
              <el-button size="small" link @click="copyToClipboard(formatJsonOrString(data.list_config), '列表配置已复制')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
            <span v-else style="color: var(--text-muted)">无</span>
          </el-descriptions-item>
          <el-descriptions-item label="正文配置" :span="2">
            <div v-if="data.content_extract" style="display: flex; align-items: flex-start; gap: 8px">
              <pre style="flex: 1; margin: 0; white-space: pre-wrap; word-break: break-all; font-size: 12px">{{ formatJsonOrString(data.content_extract) }}</pre>
              <el-button size="small" link @click="copyToClipboard(formatJsonOrString(data.content_extract), '正文配置已复制')">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </div>
            <span v-else style="color: var(--text-muted)">无</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <div v-else>
        <el-form label-position="top">
          <el-form-item label="名称">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="URL">
            <el-input v-model="form.url_norm" placeholder="https://example.com/news" />
          </el-form-item>
          <el-form-item label="优先级">
            <el-input-number v-model="form.crawl_order" :min="0" />
          </el-form-item>
          <el-form-item label="快讯">
            <el-switch
              v-model="form.is_flash"
              :active-value="1"
              :inactive-value="0"
              active-text="是"
              inactive-text="否"
            />
          </el-form-item>
          <el-form-item label="列表配置（JSON）">
            <el-input v-model="form.list_config" type="textarea" :rows="6" />
          </el-form-item>
          <el-form-item label="正文配置（JSON）">
            <el-input v-model="form.content_extract" type="textarea" :rows="6" />
          </el-form-item>
        </el-form>
      </div>
    </div>
    <template #footer>
      <template v-if="!editing">
        <el-button @click="emit('update:visible', false)">关闭</el-button>
        <el-button type="primary" @click="editing = true">编辑</el-button>
      </template>
      <template v-else>
        <el-button @click="editing = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </template>
  </el-dialog>
</template>
