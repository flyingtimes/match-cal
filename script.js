async function getPhrase() {
  const res = await fetch("/api/phrases");
  const data = await res.json();
  document.getElementById("phrase").innerText = data.phrase;
}

async function startGame() {
  await fetch("/api/start");
  getPhrase();
}

const input = document.getElementById("input");
let startTime;

input.addEventListener("focus", () => {
  startTime = Date.now();
});

input.addEventListener("input", async () => {
  const phrase = document.getElementById("phrase").innerText.trim();
  const typed = input.value.trim();
  if (typed === phrase) {
    const endTime = Date.now();
    const elapsed = (endTime - startTime) / 1000;
    const res = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ correct: phrase.length, time: elapsed })
    });
    const data = await res.json();
    document.getElementById("result").innerText =
      `✅ Speed: ${data.wpm} WPM`;
    input.value = "";
    getPhrase();
  }
});

startGame();