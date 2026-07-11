/* ==========================================================================
   NASHE DESIGNS — Frontend interactivity
   Cart is kept in localStorage on the client, then submitted to the server
   at checkout (see templates/checkout.html).
   ========================================================================== */

const CART_KEY = "nashe_cart_v1";
const USD_RATE = window.NASHE_USD_RATE || 1750;

function getCart() {
  try { return JSON.parse(localStorage.getItem(CART_KEY)) || []; }
  catch (e) { return []; }
}
function setCart(items) {
  localStorage.setItem(CART_KEY, JSON.stringify(items));
  renderCart();
}
function money(n) {
  return "MWK " + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function addToCart(item) {
  const cart = getCart();
  const existing = cart.find(
    (i) => i.id === item.id && i.size === item.size && i.color === item.color
  );
  if (existing) {
    existing.qty += item.qty;
  } else {
    cart.push(item);
  }
  setCart(cart);
  openCart();
}

function updateQty(index, delta) {
  const cart = getCart();
  if (!cart[index]) return;
  cart[index].qty += delta;
  if (cart[index].qty <= 0) cart.splice(index, 1);
  setCart(cart);
}

function removeFromCart(index) {
  const cart = getCart();
  cart.splice(index, 1);
  setCart(cart);
}

function cartTotal() {
  return getCart().reduce((sum, i) => sum + i.price * i.qty, 0);
}

function renderCart() {
  const cart = getCart();
  const container = document.getElementById("cartItemsContainer");
  const badge = document.getElementById("cartBadge");
  const subtotalEl = document.getElementById("cartSubtotal");
  if (!container) return;

  const count = cart.reduce((s, i) => s + i.qty, 0);
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? "flex" : "none";
  }
  if (subtotalEl) subtotalEl.textContent = money(cartTotal());

  if (cart.length === 0) {
    container.innerHTML = '<div class="cart-empty">Your bag is empty.<br><br><a href="/shop" class="btn btn-outline on-light">Browse the Shop</a></div>';
    return;
  }

  container.innerHTML = cart.map((item, idx) => `
    <div class="cart-line">
      <div class="cart-line-thumb">${item.image ? `<img src="${item.image}" style="width:100%;height:100%;object-fit:cover;">` : ""}</div>
      <div class="cart-line-info">
        <div class="name">${item.name}</div>
        <div class="meta">${item.size ? "Size " + item.size : ""}${item.color ? " · " + item.color : ""}</div>
        <div class="qty-control">
          <button onclick="updateQty(${idx},-1)">−</button>
          <span>${item.qty}</span>
          <button onclick="updateQty(${idx},1)">+</button>
        </div>
        <span class="cart-line-remove" onclick="removeFromCart(${idx})">Remove</span>
      </div>
      <div style="font-size:13px;font-weight:600;">${money(item.price * item.qty)}</div>
    </div>
  `).join("");
}

function openCart() {
  document.getElementById("cartDrawer")?.classList.add("open");
  document.getElementById("cartOverlay")?.classList.add("open");
}
function closeCart() {
  document.getElementById("cartDrawer")?.classList.remove("open");
  document.getElementById("cartOverlay")?.classList.remove("open");
}

document.addEventListener("DOMContentLoaded", () => {
  renderCart();

  document.getElementById("cartToggle")?.addEventListener("click", openCart);
  document.getElementById("cartClose")?.addEventListener("click", closeCart);
  document.getElementById("cartOverlay")?.addEventListener("click", closeCart);

  // Mobile nav
  document.getElementById("mobileNavToggle")?.addEventListener("click", () => {
    document.getElementById("mobileNav")?.classList.add("open");
  });
  document.getElementById("mobileNavClose")?.addEventListener("click", () => {
    document.getElementById("mobileNav")?.classList.remove("open");
  });

  // Add-to-cart buttons rendered on shop/home grids
  document.querySelectorAll(".add-cart-btn[data-product]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const p = JSON.parse(btn.dataset.product);
      addToCart({
        id: p.id, name: p.name, price: p.price_mwk, image: p.image_url,
        size: p.sizes && p.sizes.length ? p.sizes[0] : "", color: p.colors && p.colors.length ? p.colors[0] : "",
        qty: 1,
      });
    });
  });

  // Nav search (debounced)
  const searchInput = document.getElementById("navSearchInput");
  const searchResults = document.getElementById("navSearchResults");
  let searchTimer;
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(searchTimer);
      const q = searchInput.value.trim();
      if (q.length < 2) { searchResults.classList.remove("show"); return; }
      searchTimer = setTimeout(() => {
        fetch(`/api/search?q=${encodeURIComponent(q)}`)
          .then((r) => r.json())
          .then((data) => {
            if (!data.length) {
              searchResults.innerHTML = '<div class="search-empty">No products found.</div>';
            } else {
              searchResults.innerHTML = data.map((p) => `
                <a href="/product/${p.id}" class="search-result-item">
                  <div class="search-result-thumb">${p.image ? `<img src="/static/uploads/products/${p.image}" style="width:100%;height:100%;object-fit:cover;">` : ""}</div>
                  <div>
                    <div style="font-size:13px;font-weight:600;">${p.name}</div>
                    <div style="font-size:12px;color:#888;">MWK ${Number(p.price_mwk).toLocaleString()}</div>
                  </div>
                </a>
              `).join("");
            }
            searchResults.classList.add("show");
          });
      }, 300);
    });
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".nav-search")) searchResults?.classList.remove("show");
    });
  }

  // Newsletter
  document.getElementById("newsletterForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const contact = e.target.contact.value;
    fetch("/api/newsletter", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contact }),
    }).then(() => {
      e.target.reset();
      alert("Thanks for joining the Nashe Designs list!");
    });
  });

  // Chatbot
  const chatToggle = document.getElementById("chatToggle");
  const chatWindow = document.getElementById("chatWindow");
  const chatClose = document.getElementById("chatClose");
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const chatBody = document.getElementById("chatBody");
  let chatHistory = [];

  chatToggle?.addEventListener("click", () => {
    chatWindow.classList.toggle("open");
    chatToggle.classList.remove("has-pulse");
  });
  chatClose?.addEventListener("click", () => chatWindow.classList.remove("open"));

  function addChatMsg(text, who) {
    const div = document.createElement("div");
    div.className = `chat-msg ${who}`;
    div.textContent = text;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
    return div;
  }

  chatForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = chatInput.value.trim();
    if (!msg) return;
    addChatMsg(msg, "user");
    chatHistory.push({ role: "user", content: msg });
    chatInput.value = "";

    const typingEl = document.createElement("div");
    typingEl.className = "chat-msg bot typing";
    typingEl.innerHTML = "<span></span><span></span><span></span>";
    chatBody.appendChild(typingEl);
    chatBody.scrollTop = chatBody.scrollHeight;

    fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, history: chatHistory.slice(0, -1) }),
    })
      .then((r) => r.json())
      .then((data) => {
        typingEl.remove();
        const reply = data.reply || "Sorry, something went wrong.";
        addChatMsg(reply, "bot");
        chatHistory.push({ role: "assistant", content: reply });
      })
      .catch(() => {
        typingEl.remove();
        addChatMsg("I'm having trouble connecting — please try again shortly.", "bot");
      });
  });
});
