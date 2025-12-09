document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("toggle-theme");
    const body = document.body;

    // Carrega tema salvo
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "dark") {
        body.classList.add("dark-theme");
        btn.textContent = "☀️";
    }

    btn.addEventListener("click", () => {
        body.classList.toggle("dark-theme");

        if (body.classList.contains("dark-theme")) {
            btn.textContent = "☀️";
            localStorage.setItem("theme", "dark");
        } else {
            btn.textContent = "🌙";
            localStorage.setItem("theme", "light");
        }
    });
});
