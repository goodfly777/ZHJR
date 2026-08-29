<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'

const senderId = ref('CUS00000001')
const draftMessage = ref('')
const isSending = ref(false)
const errorMessage = ref('')
const messages = ref([])
const messagesContainer = ref(null)

const accounts = ref([])
const wealthProducts = ref([])
const loanProducts = ref([])
const isLoadingSidebar = ref(false)
const sidebarError = ref('')
const activeTab = ref('accounts')

const sessionState = ref(null)
const isLoadingState = ref(false)

const chatStreamEndpoint = computed(() => '/api/chat/stream')
const chatStateEndpoint = computed(
  () => `/api/chat/state?sender_id=${encodeURIComponent(senderId.value.trim())}`
)
const financeAccountsEndpoint = computed(
  () => `/finance/api/v1/customers/${encodeURIComponent(senderId.value.trim())}/accounts`
)
const financeWealthEndpoint = computed(() => '/finance/api/v1/wealth/products')
const financeLoanEndpoint = computed(() => '/finance/api/v1/loan/products')

// 侧栏以客户身份访问 finance：Bearer = 客户号 + 渠道码
const financeHeaders = computed(() => ({
  Authorization: `Bearer ${senderId.value.trim()}`,
  'X-Channel-Code': 'OPEN_API',
}))

// 快捷功能话术（对应后端金融流程触发词）
const quickButtons = [
  { label: '查账户余额', text: '帮我查一下账户余额' },
  { label: '查交易流水', text: '帮我查一下昨天的交易记录' },
  { label: '申请贷款', text: '我要申请消费贷款' },
  { label: '信用卡挂失', text: '我的信用卡丢了' },
  { label: '投诉', text: '我的转账一直没有到账' },
]

function createBaseMessage(role) {
  return {
    id: crypto.randomUUID(),
    role,
    buttons: [],
  }
}

function appendUserText(text) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'text',
    text,
  })
}

function appendUserObject(objectType, payload) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'object',
    objectType,
    payload,
  })
}

function appendBotMessages(botMessages) {
  for (const message of botMessages) {
    appendMessage('bot', message)
  }
}

function appendMessage(role, message) {
  if (role === 'divider') {
    messages.value.push({
      ...createBaseMessage('divider'),
      type: 'divider',
      text: message.text ?? '以上为历史消息',
    })
    return
  }

  if (message.object) {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'object',
      objectType: message.object.type,
      payload: message.object,
    })
  } else {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'text',
      text: message.text ?? '',
    })
  }
}

function setHistoryMessages(historyMessages) {
  messages.value = []
  for (const message of historyMessages) {
    const role = ['user', 'bot', 'divider'].includes(message.role) ? message.role : 'bot'
    appendMessage(role, message)
  }
}

async function scrollToBottom() {
  await nextTick()
  const container = messagesContainer.value
  if (!container) {
    return
  }
  container.scrollTop = container.scrollHeight
}

watch(
  () => messages.value.length,
  async () => {
    await scrollToBottom()
  }
)

function resetConversation() {
  messages.value = []
  errorMessage.value = ''
}

function formatAmount(amount) {
  if (amount === null || amount === undefined || amount === '') {
    return ''
  }
  const numericAmount = Number(amount)
  if (Number.isNaN(numericAmount)) {
    return String(amount)
  }
  return `¥${numericAmount.toFixed(2)}`
}

// finance 收益率以比率返回（如 0.0183 = 1.83%），转换为百分比字符串
function formatRate(rate) {
  if (rate === null || rate === undefined || rate === '') {
    return ''
  }
  const numericRate = Number(rate)
  if (Number.isNaN(numericRate)) {
    return String(rate)
  }
  return `${(numericRate * 100).toFixed(2)}%`
}

// ---- 对象卡片渲染 ----

const OBJECT_TYPE_LABEL = {
  account: '账户对象',
  transaction: '交易对象',
  wealth: '理财产品',
  loan: '贷款产品',
  card: '卡片对象',
}

function getObjectBadge(objectType) {
  return OBJECT_TYPE_LABEL[objectType] || '业务对象'
}

function getObjectTitle(message) {
  const payload = message.payload ?? {}
  if (payload.title) {
    return payload.title
  }
  return getObjectBadge(message.objectType)
}

function getObjectIdentifier(message) {
  const payload = message.payload ?? {}
  const map = {
    account: ['account_no', '账户号'],
    transaction: ['transaction_no', '交易号'],
    wealth: ['product_code', '产品代码'],
    loan: ['product_code', '产品代码'],
    card: ['card_no', '卡号'],
  }
  const [idKey, label] = map[message.objectType] || ['id', '编号']
  const id = payload[idKey] ?? payload.id
  return id ? `${label}：${id}` : label
}

function getObjectSummary(message) {
  const payload = message.payload ?? {}
  if (message.objectType === 'account') {
    const balance = payload.balance_amount ?? payload.attributes?.balance_amount
    return balance ? `账户余额：${formatAmount(balance)}` : '账户信息'
  }
  if (message.objectType === 'transaction') {
    return payload.attributes?.description || '交易信息'
  }
  if (message.objectType === 'wealth') {
    const rate = payload.expected_yield_rate ?? payload.attributes?.expected_yield_rate
    return rate ? `业绩基准：${formatRate(rate)}` : '理财产品'
  }
  if (message.objectType === 'loan') {
    const rate = payload.attributes?.rate_range || ''
    return rate ? `利率区间：${rate}` : '贷款产品'
  }
  return getObjectBadge(message.objectType)
}

function getObjectAmount(message) {
  const payload = message.payload ?? {}
  if (message.objectType === 'account') {
    const balance = payload.balance_amount ?? payload.attributes?.balance_amount
    return formatAmount(balance)
  }
  if (message.objectType === 'wealth') {
    const rate = payload.expected_yield_rate ?? payload.attributes?.expected_yield_rate
    return rate ? formatRate(rate) : ''
  }
  if (message.objectType === 'loan') {
    const rate = payload.attributes?.rate_range
    return rate ? `年化 ${rate}` : ''
  }
  return ''
}

// ---- 侧栏数据 ----

async function fetchSidebarData() {
  const currentSenderId = senderId.value.trim()
  accounts.value = []
  wealthProducts.value = []
  loanProducts.value = []
  sidebarError.value = ''

  if (!currentSenderId) {
    return
  }

  isLoadingSidebar.value = true
  try {
    const [accountsRes, wealthRes, loanRes] = await Promise.all([
      fetch(financeAccountsEndpoint.value, { headers: financeHeaders.value }),
      fetch(financeWealthEndpoint.value, { headers: financeHeaders.value }),
      fetch(financeLoanEndpoint.value, { headers: financeHeaders.value }),
    ])

    const [accountsPayload, wealthPayload, loanPayload] = await Promise.all([
      accountsRes.json(),
      wealthRes.json(),
      loanRes.json(),
    ])

    accounts.value = Array.isArray(accountsPayload?.data?.list) ? accountsPayload.data.list : []
    wealthProducts.value = Array.isArray(wealthPayload?.data?.list) ? wealthPayload.data.list : []
    loanProducts.value = Array.isArray(loanPayload?.data?.list) ? loanPayload.data.list : []
  } catch (error) {
    sidebarError.value = error instanceof Error ? error.message : '加载右侧对象列表失败。请确认 finance 服务已启动。'
  } finally {
    isLoadingSidebar.value = false
  }
}

async function fetchChatHistory() {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    messages.value = []
    return
  }

  try {
    const response = await fetch(`/api/chat/history?sender_id=${encodeURIComponent(currentSenderId)}`)
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '加载历史消息失败。')
    }
    if (currentSenderId === senderId.value.trim()) {
      setHistoryMessages(Array.isArray(data?.messages) ? data.messages : [])
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载历史消息失败。'
  }
}

async function fetchChatState() {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    sessionState.value = null
    return
  }
  isLoadingState.value = true
  try {
    const response = await fetch(chatStateEndpoint.value)
    const data = await response.json()
    if (currentSenderId === senderId.value.trim()) {
      sessionState.value = data
    }
  } catch (error) {
    sessionState.value = null
  } finally {
    isLoadingState.value = false
  }
}

// ---- SSE 流式发送 ----

async function sendPayload(payload) {
  if (isSending.value) {
    return
  }

  errorMessage.value = ''
  isSending.value = true

  try {
    const response = await fetch(chatStreamEndpoint.value, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sender_id: senderId.value.trim(),
        ...payload,
      }),
    })

    if (!response.ok || !response.body) {
      const text = await response.text()
      throw new Error(text || '请求失败。')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    // 流式接收 SSE data 行，逐条渲染 bot 消息
    while (true) {
      const { value, done } = await reader.read()
      if (done) {
        break
      }
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) {
          continue
        }
        const dataStr = trimmed.slice(5).trim()
        if (!dataStr) {
          continue
        }
        try {
          const data = JSON.parse(dataStr)
          if (data.done) {
            continue
          }
          if (data.text || data.object) {
            appendMessage('bot', { text: data.text ?? '', object: data.object })
          }
        } catch {
          // 忽略无法解析的 SSE 行
        }
      }
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '请求失败。'
  } finally {
    isSending.value = false
    await fetchChatState()
  }
}

async function sendTextMessage() {
  const text = draftMessage.value.trim()
  const currentSenderId = senderId.value.trim()

  if (!currentSenderId) {
    errorMessage.value = '请先输入客户号。'
    return
  }
  if (!text) {
    return
  }

  draftMessage.value = ''
  appendUserText(text)
  await sendPayload({ text })
}

async function sendQuick(text) {
  draftMessage.value = text
  await sendTextMessage()
}

async function sendAccount(account) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入客户号。'
    return
  }

  const product = account.account_product || {}
  appendUserObject('account', account)
  await sendPayload({
    object: {
      type: 'account',
      id: account.account_no,
      title: product.product_name || account.account_no,
      attributes: {
        customer_no: currentSenderId,
        balance_amount: account.balance_amount,
        currency_code: account.currency_code,
      },
    },
  })
}

async function sendWealth(product) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入客户号。'
    return
  }

  appendUserObject('wealth', product)
  await sendPayload({
    object: {
      type: 'wealth',
      id: product.product_code,
      title: product.product_name,
      attributes: {
        expected_yield_rate: product.expected_yield_rate,
        risk_level: product.risk_level,
      },
    },
  })
}

async function sendLoan(product) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入客户号。'
    return
  }

  const rate = product.rate_range
    ? `${formatRate(product.rate_range.min)}~${formatRate(product.rate_range.max)}`
    : ''
  appendUserObject('loan', product)
  await sendPayload({
    object: {
      type: 'loan',
      id: product.product_code,
      title: product.product_code,
      attributes: {
        rate_range: rate,
        term_range: product.term_range ? `${product.term_range.min}~${product.term_range.max}个月` : '',
      },
    },
  })
}

watch(
  () => senderId.value.trim(),
  async (value, previousValue) => {
    if (value === previousValue) {
      return
    }

    resetConversation()
    sessionState.value = null
    if (!value) {
      accounts.value = []
      wealthProducts.value = []
      loanProducts.value = []
      return
    }
    await Promise.all([fetchSidebarData(), fetchChatHistory(), fetchChatState()])
  }
)

onMounted(async () => {
  await Promise.all([fetchSidebarData(), fetchChatHistory(), fetchChatState()])
})
</script>

<template>
  <div class="app-shell">
    <div class="workspace">
      <div class="chat-card">
        <header class="chat-header">
          <div>
            <h1>中州银行智能客服</h1>
            <p>账户查询 · 交易流水 · 贷款申请 · 信用卡挂失 · 投诉工单</p>
          </div>
        </header>

        <section class="controls">
          <label class="field">
            <span>客户号（sender_id）</span>
            <div class="field-row">
              <input v-model="senderId" type="text" placeholder="CUS00000001" />
              <button
                type="button"
                class="secondary-button"
                :disabled="isLoadingSidebar"
                @click="fetchSidebarData"
              >
                {{ isLoadingSidebar ? '加载中...' : '刷新对象列表' }}
              </button>
            </div>
          </label>

          <div class="quick-row">
            <button
              v-for="btn in quickButtons"
              :key="btn.text"
              type="button"
              class="quick-button"
              :disabled="isSending"
              @click="sendQuick(btn.text)"
            >
              {{ btn.label }}
            </button>
          </div>
        </section>

        <section ref="messagesContainer" class="messages">
          <div v-if="messages.length === 0" class="empty-state">
            你好，我是中州银行智能客服。可以先发一句 <code>你好</code>、<code>查一下账户余额</code>、
            <code>我要申请消费贷款</code>、<code>我的信用卡丢了</code>，
            也可以点击右侧的账户或产品对象，把业务对象送入会话。
          </div>

          <article
            v-for="message in messages"
            :key="message.id"
            class="message"
            :class="message.role"
          >
            <template v-if="message.type === 'divider'">
              <div class="history-divider">
                <span>{{ message.text }}</span>
              </div>
            </template>

            <template v-else>
            <div class="meta">
              {{ message.role === 'user' ? '你' : '客服 Bot' }}
            </div>

            <div class="bubble">
              <template v-if="message.type === 'object'">
                <div class="object-card" :class="`object-card-${message.objectType}`">
                  <div class="object-card-badge">
                    {{ getObjectBadge(message.objectType) }}
                  </div>
                  <div class="object-card-title">{{ getObjectTitle(message) }}</div>
                  <div class="object-card-meta">{{ getObjectIdentifier(message) }}</div>
                  <div class="object-card-meta">{{ getObjectSummary(message) }}</div>
                  <div class="object-card-price">{{ getObjectAmount(message) }}</div>
                </div>
              </template>

              <template v-else>
                <p>{{ message.text }}</p>
              </template>
            </div>
            </template>
          </article>
        </section>

        <div v-if="sessionState" class="state-panel">
          <div class="state-title">会话状态</div>
          <div v-if="sessionState.active_task" class="state-item">
            <span class="state-key">当前流程：</span>
            <span>{{ sessionState.active_task.flow_id }}</span>
            <span v-if="sessionState.active_task.step_id" class="state-key">｜步骤：{{ sessionState.active_task.step_id }}</span>
          </div>
          <div v-if="sessionState.active_task && Object.keys(sessionState.active_task.slots || {}).length" class="state-item">
            <span class="state-key">已收集：</span>
            <span>{{ JSON.stringify(sessionState.active_task.slots) }}</span>
          </div>
          <div v-if="!sessionState.active_task && sessionState.paused_tasks && sessionState.paused_tasks.length" class="state-item">
            <span class="state-key">暂停任务：</span>
            <span>{{ sessionState.paused_tasks.map(t => t.flow_id).join('、') }}</span>
          </div>
          <div v-if="!sessionState.active_task && (!sessionState.paused_tasks || !sessionState.paused_tasks.length)" class="state-item">
            <span class="state-key">当前无进行中的业务流程。</span>
          </div>
        </div>

        <p v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </p>

        <form class="composer" @submit.prevent="sendTextMessage">
          <input
            v-model="draftMessage"
            type="text"
            placeholder="请输入咨询内容..."
            :disabled="isSending"
          />
          <button type="submit" :disabled="isSending || !draftMessage.trim()">
            {{ isSending ? '发送中...' : '发送' }}
          </button>
        </form>
      </div>

      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>业务对象</h2>
        </div>

        <div class="tabs">
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'accounts' }"
            @click="activeTab = 'accounts'"
          >
            账户
          </button>
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'wealth' }"
            @click="activeTab = 'wealth'"
          >
            理财
          </button>
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'loans' }"
            @click="activeTab = 'loans'"
          >
            贷款
          </button>
        </div>

        <p v-if="sidebarError" class="sidebar-error">{{ sidebarError }}</p>

        <div v-if="activeTab === 'accounts'" class="sidebar-list">
          <div v-if="!accounts.length && !isLoadingSidebar" class="sidebar-empty">
            暂无账户数据（请确认 finance 服务已启动）
          </div>

          <article v-for="account in accounts" :key="account.account_no" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ (account.account_product && account.account_product.product_name) || account.account_no }}</div>
              <div class="card-amount">{{ formatAmount(account.balance_amount) }}</div>
            </div>
            <div class="card-meta">账户号：{{ account.account_no }}</div>
            <div class="card-meta">币种：{{ account.currency_code }}</div>
            <button
              type="button"
              class="secondary-button full-width"
              :disabled="isSending"
              @click="sendAccount(account)"
            >
              发送账户
            </button>
          </article>
        </div>

        <div v-else-if="activeTab === 'wealth'" class="sidebar-list">
          <div v-if="!wealthProducts.length && !isLoadingSidebar" class="sidebar-empty">
            暂无理财产品数据
          </div>

          <article v-for="product in wealthProducts" :key="product.product_code" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ product.product_name }}</div>
              <div class="card-amount">{{ formatRate(product.expected_yield_rate) }}</div>
            </div>
            <div class="card-meta">产品代码：{{ product.product_code }}</div>
            <div class="card-meta">风险等级：{{ product.risk_level }}</div>
            <button
              type="button"
              class="secondary-button full-width"
              :disabled="isSending"
              @click="sendWealth(product)"
            >
              发送产品
            </button>
          </article>
        </div>

        <div v-else class="sidebar-list">
          <div v-if="!loanProducts.length && !isLoadingSidebar" class="sidebar-empty">
            暂无贷款产品数据
          </div>

          <article v-for="product in loanProducts" :key="product.product_code" class="sidebar-card">
            <div class="card-top">
              <div class="card-title">{{ product.product_code }}</div>
              <div class="card-amount">{{ product.rate_range ? `${formatRate(product.rate_range.min)}~${formatRate(product.rate_range.max)}` : '' }}</div>
            </div>
            <div class="card-meta">期限：{{ product.term_range ? `${product.term_range.min}~${product.term_range.max}个月` : '--' }}</div>
            <button
              type="button"
              class="secondary-button full-width"
              :disabled="isSending"
              @click="sendLoan(product)"
            >
              发送产品
            </button>
          </article>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
:global(*) {
  box-sizing: border-box;
}

:global(body) {
  margin: 0;
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: linear-gradient(180deg, #eef4ff 0%, #e6edf8 100%);
  color: #142033;
}

:global(button),
:global(input) {
  font: inherit;
}

#app {
  min-height: 100vh;
}

.app-shell {
  min-height: 100vh;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(180, 140, 60, 0.12), transparent 30%),
    radial-gradient(circle at bottom right, rgba(20, 60, 120, 0.14), transparent 28%),
    linear-gradient(180deg, #f5f1e8 0%, #e7eef8 100%);
}

.workspace {
  width: min(1760px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 20px;
}

.chat-card,
.sidebar {
  min-height: calc(100vh - 48px);
  height: calc(100vh - 48px);
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.chat-card {
  display: flex;
  flex-direction: column;
}

.chat-header,
.sidebar-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.chat-header h1,
.sidebar-header h2 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.sidebar-header h2 {
  font-size: 22px;
}

.chat-header p,
.sidebar-header p {
  margin: 10px 0 0;
  color: #52627a;
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: #4f5f77;
  font-size: 14px;
}

.field-row {
  display: flex;
  gap: 12px;
}

.quick-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-button {
  min-height: 32px;
  padding: 6px 12px;
  border: 1px solid rgba(180, 150, 80, 0.4);
  border-radius: 999px;
  background: rgba(255, 250, 240, 0.9);
  color: #6b4d1f;
  cursor: pointer;
  font-size: 13px;
  line-height: 1.2;
}

.quick-button:hover {
  background: rgba(255, 240, 215, 0.9);
}

.quick-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.field input,
.composer input {
  width: 100%;
  min-width: 0;
  min-height: 46px;
  padding: 11px 14px;
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.86);
  color: #142033;
  font-size: 15px;
  line-height: 1.4;
}

.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state,
.sidebar-empty {
  margin: auto;
  max-width: 440px;
  color: #61718a;
  text-align: center;
  line-height: 1.7;
}

.message {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-width: min(78%, 720px);
}

.message.user {
  align-self: flex-end;
}

.message.bot {
  align-self: flex-start;
}

.message.divider {
  align-self: stretch;
  max-width: none;
}

.history-divider {
  display: flex;
  align-items: center;
  gap: 14px;
  color: #7a8aa3;
  font-size: 13px;
}

.history-divider::before,
.history-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: rgba(148, 163, 184, 0.36);
}

.history-divider span {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.22);
}

.meta {
  font-size: 13px;
  color: #71829a;
}

.bubble {
  padding: 15px 17px;
  border-radius: 20px;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.message.user .bubble {
  background: linear-gradient(135deg, #1e3a8a, #1d4ed8);
  border-color: transparent;
  color: #eff6ff;
  box-shadow: 0 12px 30px rgba(29, 78, 216, 0.22);
}

.message.bot .bubble {
  background: rgba(255, 255, 255, 0.94);
  color: #1b2a40;
}

.bubble p {
  margin: 0;
  font-size: 15px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.object-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 240px;
}

.object-card-badge {
  width: fit-content;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(20, 32, 51, 0.08);
  color: #27415f;
  font-size: 12px;
  line-height: 1;
}

.message.user .object-card-badge {
  background: rgba(255, 255, 255, 0.18);
  color: #eff6ff;
}

.object-card-title {
  font-size: 16px;
  line-height: 1.5;
  font-weight: 600;
}

.object-card-meta {
  font-size: 14px;
  color: inherit;
  opacity: 0.86;
}

.object-card-price {
  font-size: 15px;
  font-weight: 600;
}

.state-panel {
  flex-shrink: 0;
  margin: 0 24px 8px;
  padding: 12px 14px;
  border: 1px dashed rgba(148, 163, 184, 0.5);
  border-radius: 12px;
  background: rgba(241, 245, 249, 0.7);
  font-size: 13px;
  color: #52627a;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.state-title {
  font-weight: 600;
  color: #27415f;
}

.state-key {
  color: #7a8aa3;
}

.state-item {
  line-height: 1.6;
  word-break: break-all;
}

.composer button,
.secondary-button,
.tab-button {
  min-height: 40px;
  padding: 9px 14px;
  border: 1px solid rgba(148, 163, 184, 0.36);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.88);
  color: #1b2a40;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.2;
  transition:
    transform 0.16s ease,
    box-shadow 0.16s ease,
    background 0.16s ease;
}

.composer button:hover,
.secondary-button:hover,
.tab-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.composer button:disabled,
.secondary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.error-message,
.sidebar-error {
  margin: 0;
  padding: 0 24px 14px;
  color: #c2410c;
}

.composer {
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 16px 24px 24px;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.72);
}

.composer button {
  min-width: 96px;
  padding-inline: 18px;
  background: linear-gradient(135deg, #1e3a8a, #1d4ed8);
  border-color: transparent;
  color: #f0f6ff;
  box-shadow: 0 14px 28px rgba(29, 78, 216, 0.2);
}

.sidebar {
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  gap: 8px;
  padding: 16px 24px 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.tab-button {
  min-width: 72px;
}

.tab-button.active {
  background: linear-gradient(135deg, #1e3a8a, #1d4ed8);
  border-color: transparent;
  color: #eff6ff;
}

.sidebar-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-card {
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-top {
  display: flex;
  gap: 12px;
  justify-content: space-between;
  align-items: flex-start;
}

.card-title {
  font-size: 15px;
  line-height: 1.5;
  color: #18283f;
  font-weight: 600;
}

.card-amount {
  flex-shrink: 0;
  color: #10233f;
  font-weight: 700;
}

.card-meta {
  font-size: 14px;
  color: #607189;
}

.full-width {
  width: 100%;
}

.sidebar .secondary-button.full-width {
  min-height: 40px;
}

@media (max-width: 1180px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .chat-header {
    flex-direction: column;
  }

  .sidebar {
    min-height: auto;
    height: auto;
  }
}

@media (max-width: 720px) {
  .app-shell {
    padding: 0;
  }

  .workspace {
    gap: 0;
  }

  .chat-card,
  .sidebar {
    min-height: auto;
    height: auto;
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  .chat-card {
    min-height: 100vh;
  }

  .message {
    max-width: 100%;
  }

  .composer,
  .field-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
