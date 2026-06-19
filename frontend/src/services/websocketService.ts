import type {
  WsInboundMessage,
  WsOutboundMessage,
  WsConnectionStatus,
  WsConnectionState,
  WsSessionConfig,
  WsStartSessionMessage,
  WsStopSessionMessage,
  WsPauseSessionMessage,
  WsResumeSessionMessage,
  WsHeartbeatAckMessage,
  WsUpdateConfigMessage,
  WsVideoFrameMessage,
} from '@/types/websocket.types';
import { WS_URL } from '@/utils/constants';

// ============================================================
// 🔧 Callback Types
// ============================================================

type MessageHandler = (msg: WsInboundMessage) => void;
type StatusHandler  = (status: WsConnectionStatus) => void;
type StateHandler   = (state: WsConnectionState) => void;

// ============================================================
// 🌐 WebSocket Service Class
// ============================================================

class WebSocketService {
  private ws:              WebSocket | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private statusHandlers:  Set<StatusHandler>  = new Set();
  private stateHandlers:   Set<StateHandler>   = new Set();

  private reconnectTimer:  ReturnType<typeof setTimeout>  | null = null;
  private heartbeatTimer:  ReturnType<typeof setInterval> | null = null;
  private pendingMessages: WsOutboundMessage[] = [];

  private _state: WsConnectionState = {
    status:         'idle',
    url:            WS_URL,
    sessionId:      null,
    connectedAt:    null,
    lastMessageAt:  null,
    reconnectCount: 0,
    latencyMs:      null,
    error:          null,
  };

  private readonly MAX_RECONNECT      = 5;
  private readonly RECONNECT_DELAY    = 2000;
  private readonly HEARTBEAT_INTERVAL = 15000;

  // ============================================================
  // 📡 Kết nối
  // ============================================================

  connect(url?: string): void {
    if (url) this._state.url = url;

    if (
      this.ws?.readyState === WebSocket.OPEN ||
      this.ws?.readyState === WebSocket.CONNECTING
    ) return;

    this.updateState({ status: 'connecting', error: null });

    this.ws = new WebSocket(this._state.url);

    // ✅ Fix F1: Dùng đúng WebSocket event handlers
    // (noscript không phải WebSocket property — bị overwrite liên tục)
    this.ws.onopen = () => {
      this.updateState({
        status:         'connected',
        connectedAt:    Date.now(),
        reconnectCount: 0,
        error:          null,
      });
      this.startHeartbeat();
      this.flushPendingMessages();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      this.updateState({ lastMessageAt: Date.now() });
      try {
        const msg = JSON.parse(event.data as string) as WsInboundMessage;
        this.messageHandlers.forEach((h) => h(msg));
      } catch {
        console.error('[WS] Failed to parse message:', event.data);
      }
    };

    this.ws.onclose = (event: CloseEvent) => {
      this.stopHeartbeat();
      if (event.wasClean) {
        this.updateState({ status: 'disconnected' });
      } else {
        this.tryReconnect();
      }
    };

    this.ws.onerror = () => {
      this.updateState({
        status: 'error',
        error:  'WebSocket connection error',
      });
    };
  }

  // ============================================================
  // 🔌 Ngắt kết nối
  // ============================================================

  disconnect(): void {
    this.clearReconnect();
    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, 'User disconnected');
      this.ws = null;
    }

    this.updateState({
      status:      'disconnected',
      sessionId:   null,
      connectedAt: null,
    });
  }

  // ============================================================
  // 📤 Gửi message (generic)
  // ============================================================

  send(msg: WsOutboundMessage): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      this.pendingMessages.push(msg);
      if (
        !this.ws ||
        this.ws.readyState === WebSocket.CLOSED ||
        this.ws.readyState === WebSocket.CLOSING
      ) {
        this.connect();
      }
      console.warn('[WS] Queued message until connected. Status:', this._state.status);
      return;
    }
    this.ws.send(JSON.stringify(msg));
  }

  private flushPendingMessages(): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    const messages = this.pendingMessages.splice(0);
    messages.forEach((msg) => this.ws?.send(JSON.stringify(msg)));
  }

  // ============================================================
  // 📤 Các lệnh gửi cụ thể (type-safe)
  // ============================================================

  /** Yêu cầu backend bắt đầu phiên mới */
  startSession(config: WsSessionConfig): void {
    const msg: WsStartSessionMessage = {
      type:      'start_session',
      timestamp: Date.now(),
      messageId: crypto.randomUUID(),
      payload:   { config },
    };
    this.send(msg);
  }

  /** Yêu cầu backend dừng phiên */
  stopSession(sessionId: string): void {
    const msg: WsStopSessionMessage = {
      type:      'stop_session',
      timestamp: Date.now(),
      messageId: crypto.randomUUID(),
      payload:   { sessionId },
    };
    this.send(msg);
    this.updateState({ sessionId: null });
  }

  /** Tạm dừng phiên */
  pauseSession(sessionId: string): void {
    const msg: WsPauseSessionMessage = {
      type:      'pause_session',
      timestamp: Date.now(),
      messageId: crypto.randomUUID(),
      payload:   { sessionId },
    };
    this.send(msg);
  }

  /** Tiếp tục phiên sau khi pause */
  resumeSession(sessionId: string): void {
    const msg: WsResumeSessionMessage = {
      type:      'resume_session',
      timestamp: Date.now(),
      messageId: crypto.randomUUID(),
      payload:   { sessionId },
    };
    this.send(msg);
  }

  /** Cập nhật config realtime */
  updateConfig(config: Partial<WsSessionConfig>): void {
    const msg: WsUpdateConfigMessage = {
      type:      'update_config',
      timestamp: Date.now(),
      messageId: crypto.randomUUID(),
      payload:   { config },
    };
    this.send(msg);
  }

  sendVideoFrame(image: string, width: number, height: number): void {
    const msg: WsVideoFrameMessage = {
      type:      'video_frame',
      timestamp: Date.now(),
      messageId: crypto.randomUUID(),
      payload:   { image, width, height },
    };
    this.send(msg);
  }

  /** Phản hồi heartbeat từ server */
  private sendHeartbeatAck(): void {
    const msg: WsHeartbeatAckMessage = {
      type:      'heartbeat_ack',
      timestamp: Date.now(),
      messageId: crypto.randomUUID(),
      payload:   { clientTime: Date.now() },
    };
    this.send(msg);
  }

  // ============================================================
  // 🔔 Đăng ký / Hủy handlers
  // ============================================================

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  onStateChange(handler: StateHandler): () => void {
    this.stateHandlers.add(handler);
    return () => this.stateHandlers.delete(handler);
  }

  // ============================================================
  // 📊 Getters
  // ============================================================

  get state(): WsConnectionState {
    return { ...this._state };
  }

  get status(): WsConnectionStatus {
    return this._state.status;
  }

  get isConnected(): boolean {
    return this._state.status === 'connected';
  }

  // ============================================================
  // 🔁 Reconnect logic
  // ============================================================

  private tryReconnect(): void {
    if (this._state.reconnectCount >= this.MAX_RECONNECT) {
      this.updateState({
        status: 'error',
        error:  `Không thể kết nối sau ${this.MAX_RECONNECT} lần thử`,
      });
      return;
    }

    this.updateState({
      status:         'reconnecting',
      reconnectCount: this._state.reconnectCount + 1,
    });

    const delay = this.RECONNECT_DELAY * this._state.reconnectCount;

    this.reconnectTimer = setTimeout(() => {
      console.log(`[WS] Reconnecting... ( ${this._state.reconnectCount}/${this.MAX_RECONNECT})`);
      this.connect();
    }, delay);
  }

  private clearReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  // ============================================================
  // 💓 Heartbeat
  // ============================================================

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendHeartbeatAck();
      }
    }, this.HEARTBEAT_INTERVAL);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  // ============================================================
  // 🔧 State management
  // ============================================================

  private updateState(patch: Partial<WsConnectionState>): void {
    this._state = { ...this._state, ...patch };

    // Notify status handlers
    if (patch.status !== undefined) {
      this.statusHandlers.forEach((h) => h(this._state.status));
    }

    // Notify state handlers
    this.stateHandlers.forEach((h) => h({ ...this._state }));
  }

  /** Cập nhật sessionId sau khi nhận session_started */
  setSessionId(sessionId: string | null): void {
    this.updateState({ sessionId });
  }

  /** Cập nhật latency sau khi đo ping-pong */
  setLatency(latencyMs: number): void {
    this.updateState({ latencyMs });
  }
}

// ============================================================
// 🏭 Singleton export
// ============================================================

export const websocketService = new WebSocketService();
export default websocketService;

