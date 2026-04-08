(function () {
  console.log("chatbot.js loaded");
  let isSending = false;

  // prevent duplicate instances
  if (document.getElementById("chat-container")) {
    console.log("chatbot already exists, skipping init");
    return;
  }
  // --- Create toggle button ---
  const toggle = document.createElement("div");
  toggle.id = "chat-toggle";
  toggle.innerText = "💬";

  // --- Create chat container ---
  const container = document.createElement("div");
  container.id = "chat-container";
  container.innerHTML = `
    <div id="chat-header">Chat</div>
    <div id="chat"></div>
    <div id="input-area">
      <input id="input" placeholder="Ask something..." />
      <button id="send">Send</button>
    </div>
  `;

  document.body.appendChild(toggle);
  document.body.appendChild(container);

  console.log("binding events now");

  // --- Toggle behavior ---
  toggle.onclick = () => {
    container.style.display =
      container.style.display === "flex" ? "none" : "flex";
  };

  // --- Send function ---
  async function send() {
    const input = container.querySelector("#input");
    const chat = container.querySelector("#chat");
    const sendBtn = container.querySelector("#send");

    const controller = new AbortController();
    const timeout = setTimeout(() => {
      controller.abort();
    }, 20000); // 20 seconds

    if (isSending) return;

    const message = input.value;
    if (!message.trim()) return;

    isSending = true;

    input.disabled = true;
    sendBtn.disabled = true;

    input.value = "";

    const userMsg = document.createElement("div");
    userMsg.className = "message user";
    userMsg.innerText = message;
    chat.appendChild(userMsg);

    const botMsg = document.createElement("div");
    botMsg.className = "message bot";
    botMsg.innerText = "Thinking...";
    chat.appendChild(botMsg);

    // --- Animated dots ---
    let dotCount = 0;
    const thinkingInterval = setInterval(() => {
      dotCount = (dotCount + 1) % 4; // 0 → 3
      botMsg.innerText = "Thinking" + ".".repeat(dotCount);
    }, 500);

    chat.scrollTop = chat.scrollHeight;

    let response;

    try {
      response = await fetch("http://127.0.0.1:8001/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message }),
        signal: controller.signal
      });
    } catch (err) {
      clearInterval(thinkingInterval);

      if (err.name === "AbortError") {
        botMsg.innerText = "⏱️ Request timed out.";
      } else {
        botMsg.innerText = "⚠️ Unable to reach the server.";
      }
      isSending = false;
      input.disabled = false;
      container.querySelector("#send").disabled = false;
      return;
    }

    if (!response.ok) {
      botMsg.innerText = "⚠️ Server error.";
      isSending = false;
      input.disabled = false;
      container.querySelector("#send").disabled = false;
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let result = "";
    let firstChunk = true;

   while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    if (firstChunk) {
      clearInterval(thinkingInterval);
      botMsg.innerText = "";
      firstChunk = false;
    }

    const chunk = decoder.decode(value);
    result += chunk;

    try {
      botMsg.innerHTML = marked.parse(result);
    } catch {
      botMsg.innerText = result;
    }

    chat.scrollTop = chat.scrollHeight;
  }
    isSending = false;
    input.disabled = false;
    container.querySelector("#send").disabled = false;
  }

  // --- Event binding (direct, not delegated) ---
  const inputEl = container.querySelector("#input");
  const sendBtn = container.querySelector("#send");

  sendBtn.onclick = send;

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      send();
    }
  });

})();