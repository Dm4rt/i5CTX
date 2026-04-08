document.getElementById("submit-btn").addEventListener("click", async () => {
  const flag = document.getElementById("flag-input").value;
  const result = document.getElementById("result");

  try {
    const csrf =
      window.init?.csrfNonce ||
      document.querySelector('meta[name="csrf-token"]')?.getAttribute("content");

    const res = await fetch("/api/v1/global-submit", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(csrf ? { "CSRF-Token": csrf } : {})
      },
      body: JSON.stringify({ submission: flag })
    });

    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      const text = await res.text();
      console.error("Non-JSON response:", text);
      result.innerText = `❌ Request failed (${res.status})`;
      return;
    }

    const payload = await res.json();
    const data = payload.data || payload;

    if (data.status === "correct") {
      result.innerText = `✅ Solved: ${data.challenge}`;
    } else if (data.status === "already_solved") {
      result.innerText = `⚠️ Already solved: ${data.challenge}`;
    } else if (data.status === "partial") {
      result.innerText = `🟡 ${data.message}`;
    } else {
      result.innerText = `❌ ${data.message || "Incorrect flag"}`;
    }
  } catch (err) {
    console.error(err);
    result.innerText = "❌ Submission failed";
  }
});