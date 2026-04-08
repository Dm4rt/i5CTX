document.getElementById("submit-btn").onclick = async () => {
  const flag = document.getElementById("flag-input").value;
  const result = document.getElementById("result");

  const res = await fetch("/api/v1/global-submit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ submission: flag })
  });

  const data = await res.json();

  if (data.success && data.status === "correct") {
    result.innerText = `✅ Solved: ${data.challenge}`;
  } else if (data.success && data.status === "already_solved") {
    result.innerText = `⚠️ Already solved: ${data.challenge}`;
  } else {
    result.innerText = `❌ ${data.message}`;
  }
};