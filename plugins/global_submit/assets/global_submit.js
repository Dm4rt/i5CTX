document.getElementById("submit-btn").addEventListener("click", async () => {
  const flag = document.getElementById("flag-input").value;
  const result = document.getElementById("result");

  try {
    const res = await fetch("/api/v1/global-submit", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "CSRF-Token": init.csrfNonce
      },
      body: JSON.stringify({ submission: flag })
    });

    const contentType = res.headers.get("content-type") || "";

    // If response is NOT JSON (like HTML error page)
    if (!contentType.includes("application/json")) {
      const text = await res.text();
      console.error("Non-JSON response:", text);
      result.innerText = `❌ Request failed (${res.status})`;
      return;
    }

    const data = await res.json();

    if (data.success && data.status === "correct") {
      result.innerText = `✅ Solved: ${data.challenge}`;
    } else if (data.success && data.status === "already_solved") {
      result.innerText = `⚠️ Already solved: ${data.challenge}`;
    } else {
      result.innerText = `❌ ${data.message || "Incorrect flag"}`;
    }
  } catch (err) {
    console.error(err);
    result.innerText = "❌ Submission failed";
  }
});