<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/state";

    type Message = {
        author: string;
        message: string;
        timestamp: string;
    };

    let messages: Message[] = [];
    let username: string = "";
    let message: string = "";
    let ws: WebSocket | null = null;
    let apiUrl = "/api"; // Default for dev, overridden by VITE_API_URL if set

    // Use VITE_API_URL if provided (for Docker/production)
    if (typeof import.meta.env.VITE_API_URL === "string") {
        apiUrl = import.meta.env.VITE_API_URL.replace(/\/$/, "") + "/api";
    }

    const wsUrl =
        (typeof import.meta.env.VITE_API_URL === "string"
            ? import.meta.env.VITE_API_URL.replace(/^http/, "ws").replace(
                  /\/$/,
                  "",
              )
            : page.url.origin.replace(/^http/, "ws")) + "/ws";

    async function fetchMessages() {
        try {
            const res = await fetch(`${apiUrl}/get/msg`);
            if (res.ok) {
                messages = await res.json();
            }
        } catch (e) {
            console.error("Failed to fetch messages:", e);
        }
    }

    async function sendMessage() {
        const trimmedMessage = message.trim();
        const trimmedUsername = username.trim();
        if (!trimmedUsername) {
            alert("Please enter a username before sending a message.");
            return;
        }
        if (!trimmedMessage) return;
        if (trimmedMessage.length > 255) {
            alert("Message too long (max 255 characters).");
            return;
        }
        if (trimmedUsername.length > 255) {
            alert("Username too long (max 255 characters).");
            return;
        }
        try {
            const res = await fetch(`${apiUrl}/post/send`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    author: trimmedUsername,
                    message: trimmedMessage,
                }),
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                alert(data.detail || "Failed to send message");
            } else {
                message = "";
                // fetchMessages(); // Not needed, websocket will trigger update
            }
        } catch (e) {
            alert("Failed to send message");
        }
    }

    function handleKeyUp(event: KeyboardEvent) {
        if (
            event.key === "Enter" &&
            !event.shiftKey &&
            !event.ctrlKey &&
            !event.altKey
        ) {
            sendMessage();
        }
    }

    function connectWebSocket() {
        if (ws) {
            ws.close();
        }
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
            console.log("WebSocket connected");
        };
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.author && data.message) {
                    // New message notification, refresh messages
                    fetchMessages();
                }
            } catch (e) {
                console.warn("WebSocket message parse error", e);
            }
        };
        ws.onclose = () => {
            console.log("WebSocket disconnected, retrying in 2s...");
            setTimeout(connectWebSocket, 2000);
        };
        ws.onerror = (e) => {
            console.error("WebSocket error", e);
            ws?.close();
        };
    }

    onMount(() => {
        fetchMessages();
        connectWebSocket();
    });
</script>

<svelte:head>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
</svelte:head>

<div class="chat-container">
    <h2>Chat Room</h2>
    <div id="chat">
        {#each messages as msg (msg.timestamp + msg.author + msg.message)}
            <div class="message">
                <span class="author">{msg.author}</span>
                <span class="timestamp"
                    >{new Date(msg.timestamp).toLocaleString()}</span
                >
                <p>{msg.message}</p>
            </div>
        {/each}
    </div>
    <div class="buttons">
        <input
            type="text"
            id="username"
            bind:value={username}
            placeholder="Username"
            maxlength="255"
            required
            autocomplete="username"
        />
    </div>
    <div class="inputs">
        <input
            type="text"
            id="message"
            bind:value={message}
            placeholder="Type your message..."
            maxlength="255"
            on:keyup={handleKeyUp}
            autocomplete="off"
        />
        <button id="send" on:click={sendMessage} aria-label="Send Message"
            ><i class="nf nf-cod-send"></i></button
        >
    </div>
</div>
