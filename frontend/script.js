const API = "https://thermonuclear-geostatic-hezekiah.ngrok-free.dev/chat";

function add(text, cls) {
  const d = document.createElement("div");
  d.className = "msg " + cls;
  d.innerText = text;
  document.getElementById("chat-box").appendChild(d);
}

async function send() {
  const msg = document.getElementById("msg").value;
  add(msg, "user");
  document.getElementById("msg").value = "";

  const res = await fetch(API, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({message: msg})
  });

  const data = await res.json();
  add(data.fulfillmentText, "bot");
}
