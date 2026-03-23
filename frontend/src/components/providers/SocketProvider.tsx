"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { io, type Socket } from "socket.io-client";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

export interface RealtimeEvent {
  event_id: string;
  matter_id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  changes: Record<string, unknown> | null;
  actor_id: string | null;
  actor_type: string;
}

interface SocketContextType {
  status: ConnectionStatus;
  socket: Socket | null;
  joinMatter: (matterId: string) => void;
  leaveMatter: (matterId: string) => void;
}

const SocketContext = createContext<SocketContextType>({
  status: "disconnected",
  socket: null,
  joinMatter: () => {},
  leaveMatter: () => {},
});

export function useSocket() {
  return useContext(SocketContext);
}

// ─── Provider ─────────────────────────────────────────────────────────────────

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function SocketProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [socket, setSocket] = useState<Socket | null>(null);
  const socketRef = useRef<Socket | null>(null);
  const joinedRoomsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    let mounted = true;

    async function connect() {
      // Fetch auth token
      let token: string | null = null;
      try {
        const res = await fetch("/auth/token");
        if (res.ok) {
          const data = await res.json();
          token = data.accessToken ?? null;
        }
      } catch {
        // No token — proceed without WebSocket
      }

      if (!token || !mounted) return;

      const sock = io(`${API_URL}/matters`, {
        path: "/ws/socket.io",
        auth: { token: `Bearer ${token}` },
        transports: ["websocket", "polling"],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 30000,
        reconnectionAttempts: Infinity,
      });

      sock.on("connect", () => {
        if (!mounted) return;
        setStatus("connected");

        // Re-join any rooms we were in before reconnect
        for (const matterId of joinedRoomsRef.current) {
          sock.emit("join_matter", { matter_id: matterId });
        }
      });

      sock.on("disconnect", () => {
        if (mounted) setStatus("disconnected");
      });

      sock.on("connect_error", () => {
        if (mounted) setStatus("disconnected");
      });

      sock.io.on("reconnect_attempt", () => {
        if (mounted) setStatus("connecting");
      });

      socketRef.current = sock;
      setSocket(sock);
      setStatus("connecting");
    }

    connect();

    return () => {
      mounted = false;
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
      setSocket(null);
      setStatus("disconnected");
    };
  }, []);

  const joinMatter = useCallback((matterId: string) => {
    joinedRoomsRef.current.add(matterId);
    if (socketRef.current?.connected) {
      socketRef.current.emit("join_matter", { matter_id: matterId });
    }
  }, []);

  const leaveMatter = useCallback((matterId: string) => {
    joinedRoomsRef.current.delete(matterId);
    if (socketRef.current?.connected) {
      socketRef.current.emit("leave_matter", { matter_id: matterId });
    }
  }, []);

  return (
    <SocketContext.Provider
      value={{
        status,
        socket,
        joinMatter,
        leaveMatter,
      }}
    >
      {children}
    </SocketContext.Provider>
  );
}
