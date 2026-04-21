import { useMessageStore } from "@/stores/message"

const getWebSocketBaseUrl = () => {
  const configuredBase = import.meta.env.VITE_API_URL || window.location.origin
  const normalizedUrl = new URL(configuredBase, window.location.origin)
  normalizedUrl.protocol = normalizedUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  normalizedUrl.pathname = '/ws/notifications/'
  normalizedUrl.search = ''
  return normalizedUrl.toString()
}

let ws: WebSocket | null = null
let reconnectTimer: number | null = null
let shouldReconnect = true

interface WebSocketMessage {
  [key: string]: any
}



const websocket = {
  Init(): void {
    if (!('WebSocket' in window)) {
      console.log('您的浏览器不支持websocket', 'error')
      return
    }

    const token = localStorage.getItem('2-token')
    ws = new WebSocket(`${getWebSocketBaseUrl()}?token=${token}`)

    ws.onopen = () => {
      console.log('✅ WebSocket 连接成功')
    }

    ws.onerror = (e) => {
      console.warn('❌ WebSocket 发生错误', e)
      // snackbar.showMessage('数据传输发生错误', 'error')
      reconnect()
    }

    ws.onclose = (e) => {
      console.log('⚠️ WebSocket 连接关闭', e)
      reconnect()
    }

    ws.onmessage = function (e) {
      const raw = e.data
      if (raw === 'ok') return // 心跳包
      try {
        const msg = JSON.parse(raw)
        useMessageStore().addNotification(msg.message)
      } catch (err) {
        console.error('WebSocket 消息解析失败:', err)
      }
    }
  },

  Close(): Promise<void> {
    return new Promise((resolve) => {
      shouldReconnect = false
      if (ws) {
        ws.close()
      }
      resolve()
    })
  },

  Send(data: WebSocketMessage): void {
    const message = JSON.stringify(data)
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(message)
    } else {
      console.warn('⚠️ WebSocket 未连接，发送失败')
    }
  },

  getWebSocket(): WebSocket | null {
    return ws
  },
}

// 自动重连逻辑
function reconnect(): void {
  if (!shouldReconnect) return
  if (reconnectTimer) clearTimeout(reconnectTimer)

  reconnectTimer = window.setTimeout(() => {
    console.log('🔄 尝试断线重连...')
    websocket.Init()
  }, 4000)
}



// 刷新重连（不在登录页时）
const entries = performance.getEntriesByType('navigation')
if (entries.length > 0 && (entries[0] as PerformanceNavigationTiming).type === 'reload' && window.location.pathname !== '/login') {
  websocket.Init()
}

export default websocket
